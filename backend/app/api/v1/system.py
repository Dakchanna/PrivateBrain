from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.monitoring.metrics import metrics_collector
from app.monitoring.resources import resource_monitor
from app.inference.router import model_router
from app.scheduler.scheduler import scheduler
from app.schemas.schemas import SystemStatus, SystemMetrics
from app.core.config import settings

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/status", response_model=SystemStatus)
async def get_status():
    """Return PrivateBrain system status and version."""
    return SystemStatus(
        status="operational",
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=resource_monitor.get_uptime(),
    )


@router.get("/metrics", response_model=SystemMetrics)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Return comprehensive system operational metrics."""
    req_stats = await metrics_collector.get_request_stats(db)
    robot_stats = await metrics_collector.get_robot_stats(db)
    resources = await resource_monitor.get_metrics()
    model_health = {
        name: info["status"]
        for name, info in model_router.get_available_models().items()
    }
    queue_state = scheduler.get_queue_state()

    return SystemMetrics(
        total_requests=req_stats["total_requests"],
        active_requests=req_stats["active_requests"],
        queued_requests=req_stats["queued_requests"],
        completed_requests=req_stats["completed_requests"],
        failed_requests=req_stats["failed_requests"],
        avg_latency_ms=req_stats["avg_latency_ms"],
        total_robots=robot_stats["total_robots"],
        online_robots=robot_stats["online_robots"],
        cpu_percent=resources["cpu_percent"],
        memory_percent=resources["memory_percent"],
        gpu_percent=resources.get("gpu_percent"),
        gpu_available=resources.get("gpu_available", False),
        worker_utilization=queue_state.get("worker_utilization", 0.0),
        ai_utilization=req_stats["active_requests"] / max(settings.max_workers, 1),
        model_health=model_health,
    )


@router.get("/events")
async def get_system_events(limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Return recent system events for dashboard event stream."""
    from sqlalchemy import select
    from app.database.models import SystemEvent
    result = await db.execute(
        select(SystemEvent)
        .order_by(SystemEvent.timestamp.desc())
        .limit(limit)
    )
    events = list(result.scalars().all())
    return [
        {
            "id": e.id,
            "type": e.event_type,
            "robot_id": e.robot_id,
            "request_id": e.request_id,
            "message": e.message,
            "severity": e.severity,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in reversed(events)
    ]


@router.get("/health")
async def health():
    return {"status": "ok"}
