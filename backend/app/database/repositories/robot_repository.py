from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import Optional
from datetime import datetime, timezone
from app.database.models import Robot, RobotStatus


class RobotRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, robot_id: str, api_key_hash: str, name: str | None = None,
                     description: str | None = None) -> Robot:
        robot = Robot(
            robot_id=robot_id,
            api_key_hash=api_key_hash,
            name=name,
            description=description,
            status=RobotStatus.OFFLINE,
        )
        self.db.add(robot)
        await self.db.commit()
        await self.db.refresh(robot)
        return robot

    async def get_by_robot_id(self, robot_id: str) -> Optional[Robot]:
        result = await self.db.execute(select(Robot).where(Robot.robot_id == robot_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Robot]:
        result = await self.db.execute(select(Robot).order_by(Robot.created_at.desc()))
        return list(result.scalars().all())

    async def update_status(self, robot_id: str, status: RobotStatus) -> None:
        await self.db.execute(
            update(Robot)
            .where(Robot.robot_id == robot_id)
            .values(status=status, last_seen=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def increment_request_count(self, robot_id: str, success: bool, latency_ms: float) -> None:
        robot = await self.get_by_robot_id(robot_id)
        if not robot:
            return
        robot.total_requests += 1
        if success:
            robot.success_count += 1
        else:
            robot.failure_count += 1
        # Rolling average latency
        total = robot.total_requests
        robot.avg_latency_ms = (robot.avg_latency_ms * (total - 1) + latency_ms) / total
        robot.last_seen = datetime.now(timezone.utc)
        await self.db.commit()
