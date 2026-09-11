from __future__ import annotations
import time
import base64
import io
from app.inference.base import BaseModelService, InferenceRequest, InferenceResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

# ImageNet class names (abbreviated — top-20 most robotic-context relevant)
_IMAGENET_LABELS = [
    "forklift", "conveyor_belt", "robot", "tool", "machine",
    "computer_monitor", "camera", "sensor", "cable", "container",
    "pallet", "motor", "gear", "circuit_board", "power_supply",
    "safety_helmet", "glove", "workbench", "drill", "wrench",
]


class ImageClassificationService(BaseModelService):
    """
    Real image classification using PyTorch MobileNetV2.
    Falls back to mock adapter if torch is not installed.
    """
    name = "mobilenet_v2_classification"
    task_type = "image_classification"

    def __init__(self, model_name: str = "mobilenet_v2"):
        self.model_name = model_name
        self._model = None
        self._transform = None
        self.is_fallback = False

    async def warm_up(self) -> None:
        try:
            import torch
            from torchvision import models, transforms
            self._model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
            self._model.eval()
            self._transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225]),
            ])
            self.is_available = True
            logger.info({"event": "model_loaded", "model": self.name})
        except ImportError:
            logger.warning({"event": "model_fallback", "model": self.name,
                            "reason": "torch/torchvision not installed — using mock adapter"})
            self.is_fallback = True
            self.is_available = True
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
            import torch
            from PIL import Image

            img_b64 = request.payload.get("image_base64", "")
            if not img_b64:
                raise ValueError("No image_base64 in payload")

            image_bytes = base64.b64decode(img_b64)
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            tensor = self._transform(image).unsqueeze(0)

            with torch.no_grad():
                output = self._model(tensor)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                top5_prob, top5_idx = torch.topk(probabilities, 5)

            classifications = [
                {"class_id": int(idx), "confidence": round(float(prob), 4)}
                for prob, idx in zip(top5_prob, top5_idx)
            ]

            elapsed = (time.monotonic() - t0) * 1000
            return InferenceResponse(
                request_id=request.request_id,
                model_name=self.name,
                result={"classifications": classifications, "top_class_id": int(top5_idx[0])},
                confidence=round(float(top5_prob[0]), 4),
                processing_time_ms=round(elapsed, 2),
                is_fallback=False,
            )
        except Exception as e:
            logger.error({"event": "inference_error", "model": self.name, "error": str(e)})
            return self._mock_infer(request, t0, error=str(e))

    def _mock_infer(self, request: InferenceRequest, t0: float,
                    error: str | None = None) -> InferenceResponse:
        import random
        time.sleep(random.uniform(0.04, 0.12))
        elapsed = (time.monotonic() - t0) * 1000
        top = random.choice(_IMAGENET_LABELS)
        classifications = [
            {"class": top, "confidence": round(random.uniform(0.72, 0.96), 4)},
            {"class": random.choice(_IMAGENET_LABELS), "confidence": round(random.uniform(0.30, 0.55), 4)},
        ]
        return InferenceResponse(
            request_id=request.request_id,
            model_name="mobilenet_v2_mock",
            result={"classifications": classifications, "top_class": top,
                    "note": "mock_adapter_active"},
            confidence=classifications[0]["confidence"],
            processing_time_ms=round(elapsed, 2),
            is_fallback=True,
            error=error,
        )
