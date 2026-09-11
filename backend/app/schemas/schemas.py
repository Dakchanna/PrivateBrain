from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any
from datetime import datetime
from app.database.models import RobotStatus, TaskType, Priority, RequestStatus


# ──────────────────────────────────────────────
# Robot Schemas
# ──────────────────────────────────────────────

class RobotRegisterRequest(BaseModel):
    robot_id: str = Field(..., min_length=2, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    metadata: Optional[dict] = None


class RobotRegisterResponse(BaseModel):
    robot_id: str
    api_key: str  # Only returned once at registration
    message: str


class RobotAuthRequest(BaseModel):
    robot_id: str
    api_key: str


class RobotAuthResponse(BaseModel):
    robot_id: str
    token: str
    expires_in: int = 86400  # seconds


class RobotInfo(BaseModel):
    robot_id: str
    name: Optional[str]
    status: str
    last_seen: Optional[datetime]
    total_requests: int
    success_count: int
    failure_count: int
    avg_latency_ms: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# AI Request Schemas
# ──────────────────────────────────────────────

class AIRequestCreate(BaseModel):
    robot_id: str
    task_type: TaskType
    priority: Priority = Priority.NORMAL
    payload: Optional[dict] = None
    metadata: Optional[dict] = None


class AIRequestResponse(BaseModel):
    request_id: str
    robot_id: str
    task_type: str
    priority: str
    status: str
    created_at: datetime
    message: str = "Request accepted"

    model_config = {"from_attributes": True}


class AIRequestDetail(BaseModel):
    request_id: str
    robot_id: str
    task_type: str
    priority: str
    status: str
    selected_model: Optional[str]
    retry_count: int
    failure_reason: Optional[str]
    latency_ms: Optional[float]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    events: list[dict] = []
    result: Optional[dict] = None
    agent_decisions: list[dict] = []

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# System Schemas
# ──────────────────────────────────────────────

class SystemStatus(BaseModel):
    status: str = "operational"
    version: str
    environment: str
    uptime_seconds: float


class SystemMetrics(BaseModel):
    # Request metrics
    total_requests: int
    active_requests: int
    queued_requests: int
    completed_requests: int
    failed_requests: int
    avg_latency_ms: float
    # Robot metrics
    total_robots: int
    online_robots: int
    # Resource metrics (real from psutil where available)
    cpu_percent: float
    memory_percent: float
    gpu_percent: Optional[float]
    gpu_available: bool
    worker_utilization: float
    ai_utilization: float
    # Model health
    model_health: dict[str, str]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
