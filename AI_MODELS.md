# AI Models — PrivateBrain

PrivateBrain uses two categories of AI models:

1. **AI Reasoning Model** — powers the orchestration agent
2. **Task-Specific Models** — perform actual inference on robot requests

---

## 1. AI Reasoning Model: qwen2.5:3b (via Ollama)

| Property | Value |
|---|---|
| Model | Qwen 2.5 3B Instruct |
| Provider | Alibaba / Ollama |
| Size | ~2GB |
| Hardware | CPU-capable (no GPU required) |
| Runtime | Ollama |

**Why qwen2.5:3b?**
- Runs comfortably on a CPU-only development machine
- Excellent instruction following and JSON output
- Small enough for rapid response in an agentic loop
- Supports tool-calling patterns

**Install:**
```bash
# Install Ollama: https://ollama.com/download
ollama pull qwen2.5:3b

# Alternative: llama3.2:3b
ollama pull llama3.2:3b
# Then set: AGENT_MODEL=llama3.2:3b in .env
```

**Verify:**
```bash
ollama run qwen2.5:3b "Respond: { \"action\": \"SCHEDULE\" }"
```

**Configure:**
```env
AGENT_MODEL=qwen2.5:3b
MODEL_BASE_URL=http://localhost:11434
```

**Fallback behavior:**
If Ollama is offline, PrivateBrain automatically switches to deterministic rule-based orchestration. All backend features remain fully functional — only the LLM reasoning is replaced by rules.

---

## 2. Object Detection: YOLOv8-nano (ultralytics)

| Property | Value |
|---|---|
| Model | YOLOv8n |
| Provider | Ultralytics |
| Weight Size | ~6MB |
| Hardware | CPU-capable |
| Task | Object detection (COCO 80 classes) |

**Why YOLOv8n?**
- Smallest YOLOv8 variant — fast on CPU
- Industry-standard detection model
- Relevant for robotics (obstacle detection, object picking)

**Install:**
```bash
pip install ultralytics Pillow
# Weights (yolov8n.pt) auto-download on first inference
```

**Configure:**
```env
OBJECT_DETECTION_MODEL=yolov8n.pt
```

**Verify:**
```python
from ultralytics import YOLO
model = YOLO("yolov8n.pt")
print("Loaded:", model.model_name)
```

**Payload format** (in robot request):
```json
{
  "task_type": "object_detection",
  "payload": {
    "image_base64": "<base64-encoded PNG or JPEG>"
  }
}
```

---

## 3. Image Classification: MobileNetV2 (PyTorch)

| Property | Value |
|---|---|
| Model | MobileNetV2 |
| Provider | PyTorch / torchvision |
| Weight Size | ~14MB |
| Hardware | CPU-capable |
| Task | ImageNet-1000 classification |

**Why MobileNetV2?**
- Extremely lightweight — designed for mobile/edge
- Ships in torchvision — zero additional download
- CPU inference is fast enough for demo

**Install:**
```bash
pip install torch torchvision Pillow
# MobileNet_V2_Weights.IMAGENET1K_V1 auto-downloads (~14MB)
```

**Configure:**
```env
IMAGE_CLASSIFICATION_MODEL=mobilenet_v2
```

**Payload format:**
```json
{
  "task_type": "image_classification",
  "payload": {
    "image_base64": "<base64-encoded PNG or JPEG>"
  }
}
```

---

## 4. Speech Processing: Whisper-tiny (openai-whisper)

| Property | Value |
|---|---|
| Model | Whisper tiny |
| Provider | OpenAI |
| Weight Size | ~75MB |
| Hardware | CPU-capable |
| Task | Speech-to-text transcription |

**Why Whisper-tiny?**
- Smallest Whisper variant — fast on CPU
- High-quality transcription for simple speech
- Relevant for voice-commanded robotics

**Install:**
```bash
pip install openai-whisper
pip install ffmpeg-python  # optional, for non-WAV audio
# Model weights auto-download on first inference
```

**Configure:**
```env
SPEECH_MODEL=tiny
```

**Payload format:**
```json
{
  "task_type": "speech_processing",
  "payload": {
    "audio_base64": "<base64-encoded WAV file>"
  }
}
```

---

## Mock Adapters

If any real model is not installed, PrivateBrain automatically activates its mock adapter. The mock:
- Returns realistic dummy data (fake detections, classifications, transcripts)
- Clearly labels results with `"note": "mock_adapter_active"` and `"is_fallback": true`
- Simulates realistic processing delay

This means the full system always runs without any GPU or large model downloads.

---

## Switching Models

All model configuration is through environment variables in `.env`:

```env
# Reasoning (Ollama model name)
AGENT_MODEL=qwen2.5:3b

# Task-specific (file path or name)
OBJECT_DETECTION_MODEL=yolov8n.pt
IMAGE_CLASSIFICATION_MODEL=mobilenet_v2
SPEECH_MODEL=tiny
```

No code changes are required to switch models.

---

## Resource Requirements (Approximate)

| Model | RAM | CPU | GPU | Notes |
|---|---|---|---|---|
| qwen2.5:3b | 4GB | Moderate | Optional | Ollama handles loading |
| YOLOv8n | 256MB | Low | Optional | Very fast on CPU |
| MobileNetV2 | 128MB | Very Low | Optional | Extremely lightweight |
| Whisper-tiny | 512MB | Moderate | Optional | Slowest on CPU |
| **Total (all)** | **~5GB** | **Moderate** | **Not required** | |

PrivateBrain is usable on a standard development laptop with 8GB RAM.
