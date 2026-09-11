from __future__ import annotations
from typing import Optional
from app.inference.base import BaseModelService, InferenceRequest, InferenceResponse
from app.inference.object_detection import ObjectDetectionService
from app.inference.image_classification import ImageClassificationService
from app.inference.speech import SpeechProcessingService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ModelRouter:
    """
    Routes incoming inference requests to the correct model service.
    Tracks health/availability of all model services.
    """

    def __init__(self):
        self._services: dict[str, list[BaseModelService]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Warm up all model services at startup."""
        object_detection = ObjectDetectionService(settings.object_detection_model)
        image_classification = ImageClassificationService(settings.image_classification_model)
        speech = SpeechProcessingService(settings.speech_model)

        await object_detection.warm_up()
        await image_classification.warm_up()
        await speech.warm_up()

        self._services = {
            "object_detection": [object_detection],
            "image_classification": [image_classification],
            "speech_processing": [speech],
        }
        self._initialized = True
        logger.info({"event": "model_router_initialized", "services": list(self._services.keys())})

    def get_available_models(self) -> dict:
        """Return health status for all registered model services."""
        status = {}
        for task_type, services in self._services.items():
            for svc in services:
                status[svc.name] = {
                    "task_type": task_type,
                    "available": svc.is_available,
                    "is_fallback": svc.is_fallback,
                    "status": "AVAILABLE" if svc.is_available else "UNAVAILABLE",
                }
        return status

    def get_service_for_task(self, task_type: str) -> Optional[BaseModelService]:
        """Select an available service for the given task type."""
        services = self._services.get(task_type, [])
        for svc in services:
            if svc.is_available:
                return svc
        return None

    async def route(self, request: InferenceRequest) -> InferenceResponse:
        """Route an inference request to the appropriate model service."""
        if not self._initialized:
            raise RuntimeError("ModelRouter not initialized")

        service = self.get_service_for_task(request.task_type)
        if not service:
            raise ValueError(f"No available model service for task: {request.task_type}")

        logger.info({
            "event": "inference_routed",
            "request_id": request.request_id,
            "task_type": request.task_type,
            "model": service.name,
        })
        return await service.infer(request)

    async def force_failure(self, task_type: str) -> None:
        """Mark a model service as unavailable (for failure/recovery scenarios)."""
        for svc in self._services.get(task_type, []):
            svc.is_available = False
            logger.warning({"event": "model_forced_offline", "model": svc.name})

    async def restore(self, task_type: str) -> None:
        """Restore a model service to available state."""
        for svc in self._services.get(task_type, []):
            svc.is_available = True
            logger.info({"event": "model_restored", "model": svc.name})


# Global singleton
model_router = ModelRouter()
