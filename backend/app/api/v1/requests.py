from __future__ import annotations
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.database.repositories.request_repository import (
    RequestRepository, RequestEventRepository, InferenceResultRepository, AgentDecisionRepository
)
from app.database.models import RequestStatus, RobotStatus, AgentDecision
from app.schemas.schemas import AIRequestCreate, AIRequestResponse, AIRequestDetail
from app.security.authentication import get_current_robot
from app.services.request_processor import RequestProcessor
from app.scheduler.scheduler import scheduler
from app.database.repositories.robot_repository import RobotRepository
from app.websocket import events as ws_events

router = APIRouter(prefix="/requests", tags=["Requests"])

_request_counter = {"value": 0}
_year = datetime.now(timezone.utc).year


def generate_request_id() -> str:
    _request_counter["value"] += 1
    return f"PB-{_year}-{_request_counter['value']:06d}"


@router.post("", response_model=AIRequestResponse, status_code=202)
async def submit_request(
    body: AIRequestCreate,
    background_tasks: BackgroundTasks,
    auth: dict = Depends(get_current_robot),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit an AI task request from a robot.
    The request is immediately accepted and queued for agent processing.
    """
    if auth["robot_id"] != body.robot_id:
        raise HTTPException(
            status_code=403,
            detail="Authenticated robot_id does not match request robot_id"
        )

    request_id = generate_request_id()
    req_repo = RequestRepository(db)
    event_repo = RequestEventRepository(db)
    robot_repo = RobotRepository(db)

    robot = await robot_repo.get_by_robot_id(body.robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")

    req = await req_repo.create(
        request_id=request_id,
        robot_id=body.robot_id,
        task_type=body.task_type,
        priority=body.priority,
        payload=body.payload,
        metadata=body.metadata,
    )

    await robot_repo.update_status(body.robot_id, RobotStatus.PROCESSING)
    await ws_events.emit_request_received(
        request_id, body.robot_id, body.task_type.value, body.priority.value
    )
    await event_repo.add_event(request_id, "RECEIVED", "Request received by PrivateBrain")
    await req_repo.update_status(request_id, RequestStatus.VALIDATED)
    await event_repo.add_event(request_id, "VALIDATED", "Request validated")
    await req_repo.update_status(request_id, RequestStatus.QUEUED)
    await event_repo.add_event(request_id, "QUEUED", f"Queued with {body.priority.value} priority")
    await ws_events.emit_request_queued(request_id, body.robot_id, body.priority.value)

    async def process_with_fresh_db(req_id: str, priority: str) -> None:
        from app.database.session import AsyncSessionLocal
        async with AsyncSessionLocal() as fresh_db:
            processor = RequestProcessor(fresh_db)
            await processor.process(req_id, priority)

    scheduler.set_process_fn(process_with_fresh_db)
    await scheduler.enqueue(request_id, body.priority.value)

    return AIRequestResponse(
        request_id=request_id,
        robot_id=body.robot_id,
        task_type=body.task_type.value,
        priority=body.priority.value,
        status="QUEUED",
        created_at=req.created_at,
        message="Request accepted and queued for AI agent processing",
    )


@router.get("/{request_id}", response_model=AIRequestDetail)
async def get_request(request_id: str, db: AsyncSession = Depends(get_db)):
    """Return the current state and lifecycle of a request."""
    req_repo = RequestRepository(db)
    event_repo = RequestEventRepository(db)
    result_repo = InferenceResultRepository(db)

    req = await req_repo.get_by_request_id(request_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")

    events = await event_repo.get_for_request(request_id)
    result = await result_repo.get_by_request_id(request_id)
    decisions_result = await db.execute(
        select(AgentDecision)
        .where(AgentDecision.request_id == request_id)
        .order_by(AgentDecision.timestamp.asc())
    )
    decisions_list = list(decisions_result.scalars().all())

    return AIRequestDetail(
        request_id=req.request_id,
        robot_id=req.robot_id,
        task_type=req.task_type.value,
        priority=req.priority.value,
        status=req.status.value,
        selected_model=req.selected_model,
        retry_count=req.retry_count,
        failure_reason=req.failure_reason,
        latency_ms=req.latency_ms,
        created_at=req.created_at,
        started_at=req.started_at,
        completed_at=req.completed_at,
        events=[{"event": e.event_type, "message": e.message, "timestamp": e.timestamp.isoformat()}
                for e in events],
        result={"model": result.model_used, "data": result.result_data,
                "confidence": result.confidence, "is_fallback": result.is_fallback,
                "processing_time_ms": result.processing_time_ms} if result else None,
        agent_decisions=[{"action": d.action, "reason": d.reason,
                          "model": d.selected_model, "timestamp": d.timestamp.isoformat()}
                         for d in decisions_list],
    )


@router.get("/{request_id}/result")
async def get_result(request_id: str, db: AsyncSession = Depends(get_db)):
    """Return only the inference result for a completed request."""
    result_repo = InferenceResultRepository(db)
    result = await result_repo.get_by_request_id(request_id)
    if not result:
        req_repo = RequestRepository(db)
        req = await req_repo.get_by_request_id(request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        return {"request_id": request_id, "status": req.status.value, "result": None}
    return {
        "request_id": request_id,
        "status": "COMPLETED",
        "model": result.model_used,
        "result": result.result_data,
        "confidence": result.confidence,
        "is_fallback": result.is_fallback,
        "processing_time_ms": result.processing_time_ms,
    }


@router.get("")
async def list_requests(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Return the most recent requests."""
    req_repo = RequestRepository(db)
    requests = await req_repo.get_recent(limit)
    return [
        {
            "request_id": r.request_id,
            "robot_id": r.robot_id,
            "task_type": r.task_type.value,
            "priority": r.priority.value,
            "status": r.status.value,
            "selected_model": r.selected_model,
            "latency_ms": r.latency_ms,
            "retry_count": r.retry_count,
            "created_at": r.created_at.isoformat(),
        }
        for r in requests
    ]
