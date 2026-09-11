from __future__ import annotations
import time
import base64
import tempfile
import os
from app.inference.base import BaseModelService, InferenceRequest, InferenceResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class SpeechProcessingService(BaseModelService):
    """
    Real speech-to-text using OpenAI Whisper (tiny model).
    Falls back to mock adapter if whisper is not installed.
    """
    name = "whisper_tiny_speech"
    task_type = "speech_processing"

    def __init__(self, model_size: str = "tiny"):
        self.model_size = model_size
        self._model = None
        self.is_fallback = False

    async def warm_up(self) -> None:
        try:
            import whisper
            self._model = whisper.load_model(self.model_size)
            self.is_available = True
            logger.info({"event": "model_loaded", "model": self.name, "size": self.model_size})
        except ImportError:
            logger.warning({"event": "model_fallback", "model": self.name,
                            "reason": "openai-whisper not installed — using mock adapter"})
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
            audio_b64 = request.payload.get("audio_base64", "")
            if not audio_b64:
                raise ValueError("No audio_base64 in payload")

            audio_bytes = base64.b64decode(audio_b64)
            # Write to temp file for whisper to process
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name

            try:
                result = self._model.transcribe(tmp_path)
            finally:
                os.unlink(tmp_path)

            elapsed = (time.monotonic() - t0) * 1000
            text = result.get("text", "").strip()
            language = result.get("language", "en")
            segments = [
                {"start": s["start"], "end": s["end"], "text": s["text"]}
                for s in result.get("segments", [])
            ]
            return InferenceResponse(
                request_id=request.request_id,
                model_name=self.name,
                result={"transcript": text, "language": language, "segments": segments},
                confidence=None,
                processing_time_ms=round(elapsed, 2),
                is_fallback=False,
            )
        except Exception as e:
            logger.error({"event": "inference_error", "model": self.name, "error": str(e)})
            return self._mock_infer(request, t0, error=str(e))

    def _mock_infer(self, request: InferenceRequest, t0: float,
                    error: str | None = None) -> InferenceResponse:
        import random
        time.sleep(random.uniform(0.08, 0.25))
        elapsed = (time.monotonic() - t0) * 1000
        transcripts = [
            "Robot arm, move to position delta seven.",
            "Warning: obstacle detected in sector four.",
            "Initiate scanning sequence for target object.",
            "Return to charging station immediately.",
            "Pick and place operation complete.",
        ]
        text = random.choice(transcripts)
        return InferenceResponse(
            request_id=request.request_id,
            model_name="whisper_tiny_mock",
            result={"transcript": text, "language": "en", "segments": [],
                    "note": "mock_adapter_active"},
            confidence=round(random.uniform(0.80, 0.97), 4),
            processing_time_ms=round(elapsed, 2),
            is_fallback=True,
            error=error,
        )
