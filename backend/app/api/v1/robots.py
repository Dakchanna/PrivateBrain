from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.repositories.robot_repository import RobotRepository
from app.database.models import RobotStatus
from app.schemas.schemas import (
    RobotRegisterRequest, RobotRegisterResponse,
    RobotAuthRequest, RobotAuthResponse, RobotInfo
)
from app.security.authentication import (
    generate_api_key, hash_api_key, verify_api_key,
    create_robot_token, get_current_robot
)
from app.websocket import events as ws_events

router = APIRouter(prefix="/robots", tags=["Robots"])


@router.post("/register", response_model=RobotRegisterResponse, status_code=201)
async def register_robot(body: RobotRegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new robot with PrivateBrain.
    Returns a one-time API key — store it securely.
    """
    repo = RobotRepository(db)
    existing = await repo.get_by_robot_id(body.robot_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Robot '{body.robot_id}' already registered")

    api_key = generate_api_key()
    hashed = hash_api_key(api_key)
    await repo.create(
        robot_id=body.robot_id,
        api_key_hash=hashed,
        name=body.name,
        description=body.description,
    )
    await ws_events.emit_robot_connected(body.robot_id)
    return RobotRegisterResponse(
        robot_id=body.robot_id,
        api_key=api_key,
        message="Robot registered. Store the API key — it cannot be retrieved again.",
    )


@router.post("/authenticate", response_model=RobotAuthResponse)
async def authenticate_robot(body: RobotAuthRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate robot with API key. Returns a 24-hour JWT.
    """
    repo = RobotRepository(db)
    robot = await repo.get_by_robot_id(body.robot_id)
    if not robot or not verify_api_key(body.api_key, robot.api_key_hash):
        raise HTTPException(status_code=401, detail="Invalid robot_id or api_key")

    await repo.update_status(body.robot_id, RobotStatus.ONLINE)
    await ws_events.emit_robot_connected(body.robot_id)
    token = create_robot_token(body.robot_id)
    return RobotAuthResponse(robot_id=body.robot_id, token=token)


@router.get("", response_model=list[RobotInfo])
async def list_robots(db: AsyncSession = Depends(get_db)):
    """Return all registered robots."""
    repo = RobotRepository(db)
    robots = await repo.get_all()
    return [RobotInfo.model_validate(r) for r in robots]


@router.get("/{robot_id}", response_model=RobotInfo)
async def get_robot(robot_id: str, db: AsyncSession = Depends(get_db)):
    """Return a specific robot's profile."""
    repo = RobotRepository(db)
    robot = await repo.get_by_robot_id(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail=f"Robot '{robot_id}' not found")
    return RobotInfo.model_validate(robot)


@router.get("/{robot_id}/status")
async def get_robot_status(robot_id: str, db: AsyncSession = Depends(get_db)):
    """Return just the current status of a robot."""
    repo = RobotRepository(db)
    robot = await repo.get_by_robot_id(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    return {"robot_id": robot_id, "status": robot.status.value, "last_seen": robot.last_seen}


@router.post("/{robot_id}/disconnect")
async def disconnect_robot(
    robot_id: str,
    auth: dict = Depends(get_current_robot),
    db: AsyncSession = Depends(get_db)
):
    """Mark a robot as offline."""
    if auth["robot_id"] != robot_id:
        raise HTTPException(status_code=403, detail="Cannot disconnect another robot")
    repo = RobotRepository(db)
    await repo.update_status(robot_id, RobotStatus.OFFLINE)
    await ws_events.emit_robot_disconnected(robot_id)
    return {"message": f"Robot {robot_id} marked as OFFLINE"}
