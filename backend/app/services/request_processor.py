from __future__ import annotations
"""
Request Processing Service

Orchestrates the complete lifecycle of an AI request:
RECEIVED → AGENT → SCHEDULED → PROCESSING → COMPLETED/FAILED
"""

import asyncio
import time
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import privatebrain_agent, AgentContext
from app.agent.tools import agent_tools
from app.database.models import RequestStatus, Priority, RobotStatus
from app.database.repositories.request_repository import (
    RequestRepository, RequestEventRepository,
    InferenceResultRepository, AgentDecisionRepository
)
from app.database.repositories.robot_repository import RobotRepository
from app.inference.router import model_router
from app.inference.base import InferenceRequest
from app.scheduler.scheduler import scheduler
from app.monitoring.resources import resource_monitor
from app.websocket import events as ws_events
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestProcessor:
    """
    Coordinates the full AI request lifecycle with agent decision-making,
    inference execution, failure handling, and WebSocket event emission.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.req_repo = RequestRepository(db)
        self.event_repo = RequestEventRepository(db)
        self.result_repo = InferenceResultRepository(db)
        self.decision_repo = AgentDecisionRepository(db)
        self.robot_repo = RobotRepository(db)

    async def process(self, request_id: str, priority: str) -> None:
        """Main processing entry point called by the scheduler worker."""
        t_start = time.monotonic()

        # Mark as scheduled
        await self.req_repo.update_status(
            request_id, RequestStatus.SCHEDULED,
            started_at=datetime.now(timezone.utc)
        )
        await self.event_repo.add_event(request_id, "SCHEDULED", "Request scheduled for processing")

        # Load request from DB
        req = await self.req_repo.get_by_request_id(request_id)
        if not req:
            logger.error({"event": "request_not_found", "request_id": request_id})
            return

        # Run AI Agent to get orchestration decision
        ctx = AgentContext(
            request_id=request_id,
            robot_id=req.robot_id,
            task_type=req.task_type.value,
            priority=priority,
            payload=req.payload or {},
            robot_repo=self.robot_repo,
            request_repo=self.req_repo,
            decision_repo=self.decision_repo,
            scheduler=scheduler,
            model_router=model_router,
            resource_monitor=resource_monitor,
        )

        try:
            decision = await privatebrain_agent.process_request(ctx)
        except Exception as e:
            logger.error({"event": "agent_error", "request_id": request_id, "error": str(e)})
            decision = {
                "action": "SCHEDULE",
                "priority": priority,
                "selected_model": None,
                "reason": f"Agent error, defaulting to schedule: {str(e)[:100]}",
                "llm_used": False,
            }

        # Record agent decision
        await self.decision_repo.record(
            request_id=request_id,
            action=decision.get("action", "SCHEDULE"),
            reason=decision.get("reason"),
            selected_model=decision.get("selected_model"),
            priority=decision.get("priority"),
            context_snapshot={"llm_used": decision.get("llm_used", False)}
        )
        await ws_events.emit_agent_decision(
            request_id=request_id,
            action=decision.get("action", "SCHEDULE"),
            reason=decision.get("reason"),
            selected_model=decision.get("selected_model"),
        )

        action = decision.get("action", "SCHEDULE")

        if action == "REJECT":
            await self.req_repo.update_status(
                request_id, RequestStatus.FAILED,
                failure_reason=decision.get("reason", "Rejected by agent")
            )
            await ws_events.emit_request_failed(request_id, req.robot_id,
                                                decision.get("reason", "Rejected"))
            return

        # Execute inference
        await self._execute_with_retry(req, decision, t_start)

    async def _execute_with_retry(self, req, decision: dict, t_start: float) -> None:
        """Run inference with retry/fallback support."""
        request_id = req.request_id
        task_type = req.task_type.value
        payload = req.payload or {}
        selected_model = decision.get("selected_model")

        # Mark as PROCESSING
        await self.req_repo.update_status(
            request_id, RequestStatus.PROCESSING,
            selected_model=selected_model
        )
        await self.event_repo.add_event(request_id, "PROCESSING",
                                        f"Running inference on {selected_model or 'auto'}")
        await ws_events.emit_request_started(request_id, req.robot_id, selected_model or "auto")

        for attempt in range(settings.max_retries + 1):
            try:
                if attempt > 0:
                    await self.req_repo.update_status(
                        request_id, RequestStatus.RETRYING,
                        retry_count=attempt
                    )
                    await self.event_repo.add_event(request_id, "RETRYING",
                                                    f"Retry attempt {attempt}")
                    await ws_events.emit_retry_started(request_id, attempt)

                inf_request = InferenceRequest(
                    request_id=request_id,
                    task_type=task_type,
                    payload=payload,
                )
                result = await model_router.route(inf_request)

                if result.error and attempt < settings.max_retries:
                    # Retry
                    logger.warning({"event": "inference_failed_retrying",
                                    "request_id": request_id, "attempt": attempt,
                                    "error": result.error})
                    continue

                # Success (or final attempt with error uses fallback)
                if result.error and attempt >= settings.max_retries:
                    await ws_events.emit_fallback_selected(request_id, "Max retries reached — using fallback")
                    await self.event_repo.add_event(request_id, "FALLBACK",
                                                    "Fallback adapter activated")
                    await self.req_repo.update_status(request_id, RequestStatus.RECOVERING)
                    # Force fallback inference
                    svc = model_router.get_service_for_task(task_type)
                    if svc:
                        svc_fallback = svc.is_fallback
                        svc.is_fallback = True
                        result = await svc.infer(inf_request)
                        svc.is_fallback = svc_fallback
                    await ws_events.emit_recovery_completed(request_id)

                # Persist result
                elapsed_ms = (time.monotonic() - t_start) * 1000
                await self.result_repo.create(
                    request_id=request_id,
                    model_used=result.model_name,
                    result_data=result.result,
                    confidence=result.confidence,
                    processing_time_ms=result.processing_time_ms,
                    is_fallback=result.is_fallback,
                )
                await self.req_repo.update_status(
                    request_id, RequestStatus.COMPLETED,
                    completed_at=datetime.now(timezone.utc)
                )
                await self.req_repo.set_latency(request_id, elapsed_ms)
                await self.event_repo.add_event(
                    request_id, "COMPLETED",
                    f"Inference completed in {elapsed_ms:.0f}ms on {result.model_name}"
                )

                # Update robot stats
                await self.robot_repo.increment_request_count(
                    req.robot_id, success=True, latency_ms=elapsed_ms
                )
                await self.robot_repo.update_status(req.robot_id, RobotStatus.IDLE)
                await ws_events.emit_request_completed(request_id, req.robot_id,
                                                       elapsed_ms, result.model_name)
                return

            except Exception as e:
                logger.error({"event": "processing_error", "request_id": request_id,
                              "attempt": attempt, "error": str(e)})
                if attempt >= settings.max_retries:
                    await self._mark_failed(req, str(e), t_start)
                    return

    async def _mark_failed(self, req, reason: str, t_start: float) -> None:
        """Mark request as permanently failed."""
        elapsed_ms = (time.monotonic() - t_start) * 1000
        await self.req_repo.update_status(
            req.request_id, RequestStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
            failure_reason=reason
        )
        await self.req_repo.set_latency(req.request_id, elapsed_ms)
        await self.event_repo.add_event(req.request_id, "FAILED", reason)
        await self.robot_repo.increment_request_count(req.robot_id, success=False, latency_ms=elapsed_ms)
        await ws_events.emit_request_failed(req.request_id, req.robot_id, reason)
