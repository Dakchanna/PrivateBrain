from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_
from typing import Optional
from datetime import datetime, timezone
from app.database.models import (
    AIRequest, RequestEvent, InferenceResult, AgentDecision,
    RequestStatus, Priority, TaskType
)


class RequestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request_id: str, robot_id: str, task_type: TaskType,
                     priority: Priority, payload: dict | None = None,
                     metadata: dict | None = None) -> AIRequest:
        req = AIRequest(
            request_id=request_id,
            robot_id=robot_id,
            task_type=task_type,
            priority=priority,
            payload=payload,
            metadata_=metadata,
            status=RequestStatus.RECEIVED,
        )
        self.db.add(req)
        await self.db.commit()
        await self.db.refresh(req)
        return req

    async def get_by_request_id(self, request_id: str) -> Optional[AIRequest]:
        result = await self.db.execute(
            select(AIRequest).where(AIRequest.request_id == request_id)
        )
        return result.scalar_one_or_none()

    async def update_status(self, request_id: str, status: RequestStatus,
                            started_at: datetime | None = None,
                            completed_at: datetime | None = None,
                            failure_reason: str | None = None,
                            selected_model: str | None = None,
                            retry_count: int | None = None) -> None:
        values: dict = {"status": status}
        if started_at:
            values["started_at"] = started_at
        if completed_at:
            values["completed_at"] = completed_at
        if failure_reason is not None:
            values["failure_reason"] = failure_reason
        if selected_model is not None:
            values["selected_model"] = selected_model
        if retry_count is not None:
            values["retry_count"] = retry_count
        await self.db.execute(
            update(AIRequest).where(AIRequest.request_id == request_id).values(**values)
        )
        await self.db.commit()

    async def set_latency(self, request_id: str, latency_ms: float) -> None:
        await self.db.execute(
            update(AIRequest)
            .where(AIRequest.request_id == request_id)
            .values(latency_ms=latency_ms)
        )
        await self.db.commit()

    async def get_recent(self, limit: int = 50) -> list[AIRequest]:
        result = await self.db.execute(
            select(AIRequest).order_by(AIRequest.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self) -> dict:
        total = await self.db.scalar(select(func.count()).select_from(AIRequest))
        active = await self.db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status.in_([RequestStatus.PROCESSING, RequestStatus.SCHEDULED]))
        )
        queued = await self.db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status == RequestStatus.QUEUED)
        )
        completed = await self.db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status == RequestStatus.COMPLETED)
        )
        failed = await self.db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status.in_([RequestStatus.FAILED, RequestStatus.ERROR]))
        )
        avg_latency = await self.db.scalar(
            select(func.avg(AIRequest.latency_ms))
            .where(AIRequest.latency_ms.isnot(None))
        )
        return {
            "total": total or 0,
            "active": active or 0,
            "queued": queued or 0,
            "completed": completed or 0,
            "failed": failed or 0,
            "avg_latency_ms": round(avg_latency or 0, 2),
        }


class RequestEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_event(self, request_id: str, event_type: str,
                        message: str | None = None, data: dict | None = None) -> RequestEvent:
        event = RequestEvent(
            request_id=request_id, event_type=event_type,
            message=message, data=data
        )
        self.db.add(event)
        await self.db.commit()
        return event

    async def get_for_request(self, request_id: str) -> list[RequestEvent]:
        result = await self.db.execute(
            select(RequestEvent)
            .where(RequestEvent.request_id == request_id)
            .order_by(RequestEvent.timestamp.asc())
        )
        return list(result.scalars().all())


class InferenceResultRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, request_id: str, model_used: str, result_data: dict,
                     confidence: float | None = None, processing_time_ms: float = 0,
                     is_fallback: bool = False) -> InferenceResult:
        result = InferenceResult(
            request_id=request_id, model_used=model_used, result_data=result_data,
            confidence=confidence, processing_time_ms=processing_time_ms, is_fallback=is_fallback
        )
        self.db.add(result)
        await self.db.commit()
        await self.db.refresh(result)
        return result

    async def get_by_request_id(self, request_id: str) -> Optional[InferenceResult]:
        result = await self.db.execute(
            select(InferenceResult).where(InferenceResult.request_id == request_id)
        )
        return result.scalar_one_or_none()


class AgentDecisionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(self, request_id: str, action: str, reason: str | None = None,
                     selected_model: str | None = None, priority: str | None = None,
                     context_snapshot: dict | None = None) -> AgentDecision:
        decision = AgentDecision(
            request_id=request_id, action=action, reason=reason,
            selected_model=selected_model, priority=priority,
            context_snapshot=context_snapshot
        )
        self.db.add(decision)
        await self.db.commit()
        return decision
