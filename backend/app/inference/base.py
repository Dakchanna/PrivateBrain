from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import time


@dataclass
class InferenceRequest:
    request_id: str
    task_type: str
    payload: dict
    metadata: dict | None = None


@dataclass
class InferenceResponse:
    request_id: str
    model_name: str
    result: dict
    confidence: Optional[float]
    processing_time_ms: float
    is_fallback: bool = False
    error: Optional[str] = None


class BaseModelService(ABC):
    """Abstract base for all AI model service adapters."""

    name: str = "base"
    task_type: str = "unknown"
    is_available: bool = False
    is_fallback: bool = False

    @abstractmethod
    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        """Run inference and return structured result."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if this model service is healthy."""
        ...

    async def warm_up(self) -> None:
        """Optional warm-up called at startup."""
        self.is_available = await self.health_check()
