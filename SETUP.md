# PrivateBrain Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- Redis (for queue state, optional but recommended)
- Supabase account (free tier works)
- Ollama (for real AI agent) — optional but strongly recommended

---

## Step 1: Supabase Database Setup

1. Go to https://supabase.com and create a free project
2. In your Supabase dashboard → SQL Editor → paste the contents of `backend/app/database/schema.sql`
3. Click **Run** — all tables will be created
4. Go to **Project Settings → Database → Connection String (URI mode)**
5. Copy the connection string (it looks like `postgresql://postgres:PASSWORD@db.PROJECTREF.supabase.co:5432/postgres`)

---

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_REF.supabase.co:5432/postgres
API_SECRET=any_long_random_string_at_least_32_chars
JWT_SECRET=another_long_random_string
```

---

## Step 3: Install Ollama (AI Reasoning Model)

```bash
# Download Ollama from https://ollama.com
# Then pull the agent model:
ollama pull qwen2.5:3b

# Verify it runs:
ollama run qwen2.5:3b "Hello, reply in one sentence."
```

Ollama runs at `http://localhost:11434` by default (matches `.env.example`).

If you can't install Ollama, PrivateBrain automatically falls back to deterministic orchestration — the system still works correctly, it just won't use an LLM for decisions.

---

## Step 4: Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # macOS/Linux

# Install core dependencies
pip install -r requirements.txt

# Install Redis (optional — improves queue reliability in multi-process mode)
# Windows: download from https://github.com/microsoftarchive/redis/releases
# Or use Docker: docker run -d -p 6379:6379 redis:7-alpine

# Start Redis if you have it:
# redis-server

# Start backend
uvicorn app.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

---

## Step 5: Frontend

```bash
cd frontend

npm install

# Create local env
echo "VITE_API_BASE_URL=http://localhost:8000" > .env
echo "VITE_WS_URL=ws://localhost:8000" >> .env

npm run dev
```

Dashboard: `http://localhost:5173`

---

## Step 6: Install AI Models (Optional — for real inference)

```bash
# Object Detection (YOLOv8-nano, ~6MB)
pip install ultralytics

# Image Classification (MobileNetV2 via PyTorch)
pip install torch torchvision
# Weights auto-download on first use (~14MB)

# Speech Processing (Whisper-tiny, ~75MB)
pip install openai-whisper
# Model downloads on first use
```

Without these, PrivateBrain uses intelligent mock adapters automatically.
See [AI_MODELS.md](AI_MODELS.md) for details.

---

## Step 7: Run the Mock Robot Client

The mock robot client is the testing harness that triggers PrivateBrain via API.

```bash
# From the project root:
pip install httpx

# Run all 5 demonstration scenarios:
python mock_robot/client.py --scenario all

# Or individual scenarios:
python mock_robot/client.py --scenario concurrent
python mock_robot/client.py --scenario critical
python mock_robot/client.py --scenario failure
python mock_robot/client.py --scenario disconnect

# Register a single robot manually:
python mock_robot/client.py --register --robot-id MY_ROBOT
```

Watch the dashboard at `http://localhost:5173` while the mock client runs.

---

## Step 8: Run Tests

```bash
cd backend
pytest tests/ -v
```

---

## Docker (Alternative to manual setup)

```bash
cp .env.example .env
# Edit .env with your DATABASE_URL

docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- Redis: localhost:6379

> **Note**: You still need to run the Supabase SQL schema separately, and Ollama must be available at the configured MODEL_BASE_URL.
