# Robot API Integration Guide

This guide explains how to connect a separately developed robot simulator to PrivateBrain.

## Overview

PrivateBrain exposes a versioned REST API at `/api/v1/`. Any robot simulator that can make HTTP requests can integrate without modifying PrivateBrain's internal agent.

---

## Step 1: Start PrivateBrain

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Set base URL in your simulator:
```
PRIVATEBRAIN_URL=http://localhost:8000
```

---

## Step 2: Register Your Robot

**POST** `/api/v1/robots/register`

```bash
curl -X POST http://localhost:8000/api/v1/robots/register \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "MY_ROBOT_01",
    "name": "Simulation Robot 1",
    "description": "Connected from ROS2 simulator"
  }'
```

**Response:**
```json
{
  "robot_id": "MY_ROBOT_01",
  "api_key": "pb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "message": "Robot registered. Store the API key — it cannot be retrieved again."
}
```

> ⚠️ **Store the `api_key` securely.** It is only returned once.

---

## Step 3: Authenticate

**POST** `/api/v1/robots/authenticate`

```bash
curl -X POST http://localhost:8000/api/v1/robots/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "MY_ROBOT_01",
    "api_key": "pb_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }'
```

**Response:**
```json
{
  "robot_id": "MY_ROBOT_01",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400
}
```

Use this `token` as a Bearer token in all subsequent requests. Re-authenticate after 24 hours.

---

## Step 4: Submit an AI Request

**POST** `/api/v1/requests`

Headers: `Authorization: Bearer <token>`

### Object Detection

```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "MY_ROBOT_01",
    "task_type": "object_detection",
    "priority": "high",
    "payload": {
      "image_base64": "<base64-encoded PNG or JPEG>"
    },
    "metadata": {
      "frame_id": "camera_front_001",
      "timestamp": "2026-09-11T00:00:00Z"
    }
  }'
```

### Image Classification

```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "MY_ROBOT_01",
    "task_type": "image_classification",
    "priority": "normal",
    "payload": {
      "image_base64": "<base64-encoded PNG or JPEG>"
    }
  }'
```

### Speech Processing

```bash
curl -X POST http://localhost:8000/api/v1/requests \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "MY_ROBOT_01",
    "task_type": "speech_processing",
    "priority": "normal",
    "payload": {
      "audio_base64": "<base64-encoded WAV file>"
    }
  }'
```

**Priority values:** `critical` | `high` | `normal` | `low`

**Response (all request types):**
```json
{
  "request_id": "PB-2026-000001",
  "robot_id": "MY_ROBOT_01",
  "task_type": "object_detection",
  "priority": "high",
  "status": "QUEUED",
  "created_at": "2026-09-11T00:00:01Z",
  "message": "Request accepted and queued for AI agent processing"
}
```

---

## Step 5: Track Request Status

**GET** `/api/v1/requests/{request_id}`

```bash
curl http://localhost:8000/api/v1/requests/PB-2026-000001
```

**Response includes full lifecycle:**
```json
{
  "request_id": "PB-2026-000001",
  "status": "PROCESSING",
  "events": [
    {"event": "RECEIVED", "message": "Request received", "timestamp": "..."},
    {"event": "VALIDATED", "message": "Request validated", "timestamp": "..."},
    {"event": "QUEUED", "message": "Queued with high priority", "timestamp": "..."},
    {"event": "SCHEDULED", "message": "Request scheduled for processing", "timestamp": "..."},
    {"event": "PROCESSING", "message": "Running inference...", "timestamp": "..."}
  ],
  "agent_decisions": [
    {"action": "SCHEDULE", "reason": "High priority with sufficient resources", "model": "yolov8n_object_detection"}
  ]
}
```

**Request statuses:**
`RECEIVED → VALIDATED → QUEUED → SCHEDULED → PROCESSING → COMPLETED`

Failure path: `... → ERROR → RETRYING → RECOVERING → COMPLETED` (or `FAILED`)

---

## Step 6: Retrieve Result

**GET** `/api/v1/requests/{request_id}/result`

```bash
curl http://localhost:8000/api/v1/requests/PB-2026-000001/result
```

**Response (object detection):**
```json
{
  "request_id": "PB-2026-000001",
  "status": "COMPLETED",
  "model": "yolov8n_object_detection",
  "result": {
    "detections": [
      {"label": "person", "confidence": 0.92, "bbox": [120, 80, 340, 290]},
      {"label": "chair", "confidence": 0.85, "bbox": [450, 200, 620, 380]}
    ],
    "count": 2
  },
  "confidence": 0.885,
  "is_fallback": false,
  "processing_time_ms": 187.4
}
```

**Response (classification):**
```json
{
  "result": {
    "classifications": [
      {"class": "robot", "confidence": 0.94},
      {"class": "tool", "confidence": 0.45}
    ],
    "top_class": "robot"
  }
}
```

**Response (speech):**
```json
{
  "result": {
    "transcript": "Move to position delta seven immediately.",
    "language": "en",
    "segments": [...]
  }
}
```

---

## Step 7: Handle Errors

```json
{
  "status": "FAILED",
  "error": "...",
  "detail": "..."
}
```

Standard HTTP codes: `400` validation, `401` auth, `403` forbidden, `404` not found, `409` conflict, `422` schema error.

---

## Step 8: Real-Time Events (WebSocket)

Connect to `ws://localhost:8000/ws` to receive live events:

```python
import websockets, asyncio, json

async def watch():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        async for msg in ws:
            event = json.loads(msg)
            if event.get("request_id") == "PB-2026-000001":
                print(event["type"], event.get("message"))

asyncio.run(watch())
```

**Event types:** `REQUEST_RECEIVED`, `REQUEST_QUEUED`, `REQUEST_SCHEDULED`, `REQUEST_STARTED`, `REQUEST_COMPLETED`, `REQUEST_FAILED`, `RETRY_STARTED`, `FALLBACK_SELECTED`, `RECOVERY_COMPLETED`, `AGENT_DECISION`, `ROBOT_CONNECTED`, `ROBOT_DISCONNECTED`, `RESOURCE_UPDATED`

---

## API Contract Stability

All APIs are versioned under `/api/v1/`. The robot API contract will remain stable. Future improvements will be additive and versioned under `/api/v2/` if breaking changes are required.
