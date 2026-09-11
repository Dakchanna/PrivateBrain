from __future__ import annotations
import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Text, Integer, Float, DateTime, Enum as SAEnum,
    ForeignKey, JSON, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class RobotStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class TaskType(str, enum.Enum):
    OBJECT_DETECTION = "object_detection"
    IMAGE_CLASSIFICATION = "image_classification"
    SPEECH_PROCESSING = "speech_processing"


class Priority(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class RequestStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    AUTHENTICATING = "AUTHENTICATING"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    RETRYING = "RETRYING"
    RECOVERING = "RECOVERING"
    ERROR = "ERROR"
    FAILED = "FAILED"


class AgentAction(str, enum.Enum):
    QUEUE = "QUEUE"
    SCHEDULE = "SCHEDULE"
    PROCESS = "PROCESS"
    RETRY = "RETRY"
    FALLBACK = "FALLBACK"
    REJECT = "REJECT"
    WAIT = "WAIT"


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────

class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    robot_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[RobotStatus] = mapped_column(
        SAEnum(RobotStatus), default=RobotStatus.OFFLINE, nullable=False
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    requests: Mapped[list["AIRequest"]] = relationship("AIRequest", back_populates="robot")


class AIRequest(Base):
    __tablename__ = "ai_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    request_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    robot_id: Mapped[str] = mapped_column(String(64), ForeignKey("robots.robot_id"), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(SAEnum(TaskType), nullable=False)
    priority: Mapped[Priority] = mapped_column(SAEnum(Priority), default=Priority.NORMAL, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        SAEnum(RequestStatus), default=RequestStatus.RECEIVED, nullable=False, index=True
    )
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    selected_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    robot: Mapped["Robot"] = relationship("Robot", back_populates="requests")
    events: Mapped[list["RequestEvent"]] = relationship("RequestEvent", back_populates="request")
    result: Mapped[Optional["InferenceResult"]] = relationship(
        "InferenceResult", back_populates="request", uselist=False
    )
    agent_decisions: Mapped[list["AgentDecision"]] = relationship(
        "AgentDecision", back_populates="request"
    )


class RequestEvent(Base):
    __tablename__ = "request_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    request_id: Mapped[str] = mapped_column(String(32), ForeignKey("ai_requests.request_id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    request: Mapped["AIRequest"] = relationship("AIRequest", back_populates="events")


class InferenceResult(Base):
    __tablename__ = "inference_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    request_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("ai_requests.request_id"), unique=True, nullable=False
    )
    model_used: Mapped[str] = mapped_column(String(128), nullable=False)
    result_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    request: Mapped["AIRequest"] = relationship("AIRequest", back_populates="result")


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    request_id: Mapped[str] = mapped_column(String(32), ForeignKey("ai_requests.request_id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    selected_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    request: Mapped["AIRequest"] = relationship("AIRequest", back_populates="agent_decisions")


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    robot_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info")
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
