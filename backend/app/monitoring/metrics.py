from __future__ import annotations
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.models import Robot, AIRequest, RequestStatus, RobotStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Aggregates system-wide operational metrics from the database."""

    async def get_request_stats(self, db: AsyncSession) -> dict:
        total = await db.scalar(select(func.count()).select_from(AIRequest)) or 0
        active = await db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status.in_([RequestStatus.PROCESSING, RequestStatus.SCHEDULED]))
        ) or 0
        queued = await db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status == RequestStatus.QUEUED)
        ) or 0
        completed = await db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status == RequestStatus.COMPLETED)
        ) or 0
        failed = await db.scalar(
            select(func.count()).select_from(AIRequest)
            .where(AIRequest.status.in_([RequestStatus.FAILED, RequestStatus.ERROR]))
        ) or 0
        avg_latency = await db.scalar(
            select(func.avg(AIRequest.latency_ms))
            .where(AIRequest.latency_ms.isnot(None))
        ) or 0.0
        return {
            "total_requests": total,
            "active_requests": active,
            "queued_requests": queued,
            "completed_requests": completed,
            "failed_requests": failed,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": round((completed / max(total, 1)) * 100, 1),
            "failure_rate": round((failed / max(total, 1)) * 100, 1),
        }

    async def get_robot_stats(self, db: AsyncSession) -> dict:
        total = await db.scalar(select(func.count()).select_from(Robot)) or 0
        online = await db.scalar(
            select(func.count()).select_from(Robot)
            .where(Robot.status.in_([RobotStatus.ONLINE, RobotStatus.PROCESSING, RobotStatus.IDLE]))
        ) or 0
        return {"total_robots": total, "online_robots": online}


metrics_collector = MetricsCollector()
