from __future__ import annotations
"""
Agent Tools — controlled backend operations available to the PrivateBrain AI agent.

Each tool:
  - validates inputs strictly
  - executes controlled backend operations
  - returns structured output
  - logs important operations
  - NEVER exposes SQL, shell, Docker, or filesystem access to the LLM
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Optional
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolResult:
    success: bool
    data: dict
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Tool: get_robot_status
# ──────────────────────────────────────────────
async def get_robot_status(robot_id: str, robot_repo) -> ToolResult:
    """Return current status of a specific robot."""
    try:
        robot = await robot_repo.get_by_robot_id(robot_id)
        if not robot:
            return ToolResult(success=False, data={}, error=f"Robot {robot_id} not found")
        return ToolResult(success=True, data={
            "robot_id": robot.robot_id,
            "status": robot.status.value,
            "last_seen": robot.last_seen.isoformat() if robot.last_seen else None,
            "total_requests": robot.total_requests,
            "success_count": robot.success_count,
            "failure_count": robot.failure_count,
            "avg_latency_ms": robot.avg_latency_ms,
        })
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: get_system_resources
# ──────────────────────────────────────────────
async def get_system_resources(resource_monitor) -> ToolResult:
    """Return current CPU, memory, GPU and worker utilization."""
    try:
        metrics = await resource_monitor.get_metrics()
        return ToolResult(success=True, data=metrics)
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: inspect_queue
# ──────────────────────────────────────────────
async def inspect_queue(scheduler) -> ToolResult:
    """Return current queue state: sizes, priorities, top items."""
    try:
        state = scheduler.get_queue_state()
        return ToolResult(success=True, data=state)
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: inspect_available_models
# ──────────────────────────────────────────────
async def inspect_available_models(model_router) -> ToolResult:
    """Return health and availability of all AI model services."""
    try:
        models = model_router.get_available_models()
        return ToolResult(success=True, data={"models": models})
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: estimate_task_resources
# ──────────────────────────────────────────────
async def estimate_task_resources(task_type: str) -> ToolResult:
    """Return estimated resource requirements for a given task type."""
    _estimates = {
        "object_detection":      {"cpu_pct": 35, "memory_mb": 512,  "gpu_recommended": True,  "typical_ms": 200},
        "image_classification":  {"cpu_pct": 20, "memory_mb": 256,  "gpu_recommended": False, "typical_ms": 120},
        "speech_processing":     {"cpu_pct": 45, "memory_mb": 384,  "gpu_recommended": False, "typical_ms": 500},
    }
    est = _estimates.get(task_type)
    if not est:
        return ToolResult(success=False, data={}, error=f"Unknown task type: {task_type}")
    return ToolResult(success=True, data={"task_type": task_type, **est})


# ──────────────────────────────────────────────
# Tool: schedule_request
# ──────────────────────────────────────────────
async def schedule_request(request_id: str, priority: str, scheduler) -> ToolResult:
    """Enqueue a request into the priority scheduler."""
    valid_priorities = {"critical", "high", "normal", "low"}
    if priority.lower() not in valid_priorities:
        return ToolResult(success=False, data={}, error=f"Invalid priority: {priority}")
    try:
        await scheduler.enqueue(request_id, priority.lower())
        return ToolResult(success=True, data={
            "request_id": request_id,
            "queued": True,
            "priority": priority,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: select_model
# ──────────────────────────────────────────────
async def select_model(task_type: str, model_router) -> ToolResult:
    """Select the best available model for the given task."""
    try:
        svc = model_router.get_service_for_task(task_type)
        if not svc:
            return ToolResult(success=False, data={},
                              error=f"No available model for task: {task_type}")
        return ToolResult(success=True, data={
            "model_name": svc.name,
            "task_type": task_type,
            "is_fallback": svc.is_fallback,
            "status": "AVAILABLE",
        })
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: execute_inference
# ──────────────────────────────────────────────
async def execute_inference(request_id: str, task_type: str, payload: dict,
                            model_router) -> ToolResult:
    """Run inference for a request through the model router."""
    from app.inference.base import InferenceRequest
    try:
        inf_request = InferenceRequest(
            request_id=request_id, task_type=task_type, payload=payload
        )
        result = await model_router.route(inf_request)
        return ToolResult(success=result.error is None, data={
            "model_name": result.model_name,
            "result": result.result,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms,
            "is_fallback": result.is_fallback,
        }, error=result.error)
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: retry_request
# ──────────────────────────────────────────────
async def retry_request(request_id: str, current_retry_count: int, max_retries: int,
                        scheduler) -> ToolResult:
    """Re-enqueue a failed request for retry if under retry limit."""
    if current_retry_count >= max_retries:
        return ToolResult(success=False, data={
            "request_id": request_id,
            "can_retry": False,
            "retry_count": current_retry_count,
        }, error="Max retries exceeded")
    try:
        await scheduler.enqueue(request_id, "high")  # retries get elevated priority
        return ToolResult(success=True, data={
            "request_id": request_id,
            "can_retry": True,
            "retry_count": current_retry_count + 1,
        })
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: fallback_request
# ──────────────────────────────────────────────
async def fallback_request(request_id: str, task_type: str, payload: dict,
                           model_router) -> ToolResult:
    """Force a fallback inference attempt using mock adapter."""
    from app.inference.base import InferenceRequest
    try:
        svc = model_router.get_service_for_task(task_type)
        if not svc:
            return ToolResult(success=False, data={}, error="No service available for fallback")
        # Force fallback
        original_fallback = svc.is_fallback
        original_available = svc.is_available
        svc.is_fallback = True
        svc.is_available = True
        try:
            inf_request = InferenceRequest(
                request_id=request_id, task_type=task_type, payload=payload
            )
            result = await svc.infer(inf_request)
        finally:
            svc.is_fallback = original_fallback
            svc.is_available = original_available
        return ToolResult(success=True, data={
            "model_name": result.model_name,
            "result": result.result,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms,
            "is_fallback": True,
        })
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: update_request_status
# ──────────────────────────────────────────────
async def update_request_status(request_id: str, status: str, request_repo,
                                failure_reason: str | None = None) -> ToolResult:
    """Update request status in the database (validated input only)."""
    valid_statuses = {
        "RECEIVED", "AUTHENTICATING", "VALIDATED", "QUEUED", "SCHEDULED",
        "PROCESSING", "COMPLETED", "RETRYING", "RECOVERING", "ERROR", "FAILED"
    }
    if status not in valid_statuses:
        return ToolResult(success=False, data={}, error=f"Invalid status: {status}")
    try:
        from app.database.models import RequestStatus
        await request_repo.update_status(
            request_id, RequestStatus(status), failure_reason=failure_reason
        )
        return ToolResult(success=True, data={
            "request_id": request_id, "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))


# ──────────────────────────────────────────────
# Tool: record_agent_decision
# ──────────────────────────────────────────────
async def record_agent_decision(request_id: str, action: str, reason: str,
                                selected_model: str | None, priority: str | None,
                                context_snapshot: dict | None, decision_repo) -> ToolResult:
    """Persist a structured agent decision to the database."""
    try:
        await decision_repo.record(
            request_id=request_id, action=action, reason=reason,
            selected_model=selected_model, priority=priority,
            context_snapshot=context_snapshot
        )
        return ToolResult(success=True, data={
            "request_id": request_id,
            "action": action,
            "recorded": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return ToolResult(success=False, data={}, error=str(e))
