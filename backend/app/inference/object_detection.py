from __future__ import annotations
import time
import base64
import io
from app.inference.base import BaseModelService, InferenceRequest, InferenceResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────
# Real YOLOv8 Object Detection Service
# ──────────────────────────────────────────────────────────────

class ObjectDetectionService(BaseModelService):
    """
    Real object detection using Ultralytics YOLOv8-nano.
    Falls back to mock adapter if ultralytics is not installed.
    """
    name = "yolov8n_object_detection"
    task_type = "object_detection"

    def __init__(self, model_path: str = "yolov8n.pt"):
        self.model_path = model_path
        self._model = None
        self.is_fallback = False

    async def warm_up(self) -> None:
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
            self.is_available = True
            logger.info({"event": "model_loaded", "model": self.name})
        except ImportError:
            logger.warning({"event": "model_fallback", "model": self.name,
                            "reason": "ultralytics not installed — using mock adapter"})
            self.is_fallback = True
            self.is_available = True  # mock is always available
        except Exception as e:
            logger.error({"event": "model_load_failed", "model": self.name, "error": str(e)})
            self.is_fallback = True
            self.is_available = True

    async def health_check(self) -> bool:
        return self.is_available

    async def infer(self, request: InferenceRequest) -> InferenceResponse:
        t0 = time.monotonic()

        if self.is_fallback or self._model is None:
            return self._mock_infer(request, t0)

        try:
            # Decode base64 image from payload
            img_b64 = request.payload.get("image_base64", "")
            if not img_b64:
                raise ValueError("No image_base64 in payload")

            image_bytes = base64.b64decode(img_b64)
            from PIL import Image
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            results = self._model(image, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = self._model.names.get(cls_id, str(cls_id))
                    xyxy = box.xyxy[0].tolist()
                    detections.append({
                        "label": label,
                        "confidence": round(conf, 4),
                        "bbox": [round(v, 2) for v in xyxy],
                    })

            elapsed = (time.monotonic() - t0) * 1000
            avg_conf = sum(d["confidence"] for d in detections) / max(len(detections), 1)
            return InferenceResponse(
                request_id=request.request_id,
                model_name=self.name,
                result={"detections": detections, "count": len(detections)},
                confidence=round(avg_conf, 4),
                processing_time_ms=round(elapsed, 2),
                is_fallback=False,
            )
        except Exception as e:
            logger.error({"event": "inference_error", "model": self.name, "error": str(e)})
            return self._mock_infer(request, t0, error=str(e))

    def _mock_infer(self, request: InferenceRequest, t0: float,
                    error: str | None = None) -> InferenceResponse:
        import random, asyncio
        time.sleep(random.uniform(0.05, 0.15))  # simulate processing
        elapsed = (time.monotonic() - t0) * 1000
        detections = [
            {"label": "robot_arm", "confidence": round(random.uniform(0.75, 0.97), 4),
             "bbox": [120.0, 80.0, 340.0, 290.0]},
            {"label": "obstacle", "confidence": round(random.uniform(0.60, 0.88), 4),
             "bbox": [450.0, 200.0, 620.0, 380.0]},
        ]
        return InferenceResponse(
            request_id=request.request_id,
            model_name="yolov8n_mock",
            result={"detections": detections, "count": len(detections),
                    "note": "mock_adapter_active"},
            confidence=round(sum(d["confidence"] for d in detections) / len(detections), 4),
            processing_time_ms=round(elapsed, 2),
            is_fallback=True,
            error=error,
        )
