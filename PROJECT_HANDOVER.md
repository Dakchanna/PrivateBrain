# PrivateBrain - Project Handover Document

This document serves as a memory and technical handover state for the **PrivateBrain** project, an AI-powered robotics orchestration platform. It is designed to help you quickly resume work from another account or environment.

---

## 🏗️ Project Overview
**PrivateBrain** is an API-first orchestration platform that manages AI workloads for external robot simulators. 
Instead of hard-coded rules, it uses a real **AI Reasoning Agent (Ollama + Qwen2.5 / LLaMA)** connected to a series of deterministic Python tools. It features a priority-based task scheduler (`CRITICAL`, `HIGH`, `NORMAL`, `LOW`) and routes requests to corresponding AI services (YOLOv8, MobileNetV2, Whisper-tiny) which have automatic simulated fallbacks.

The frontend is a futuristic command center built with **React + TypeScript + Vite**.

---

## ✅ What Has Been Completed 

### 1. Backend Core & Infrastructure (Python / FastAPI)
- **Database Architecture**: Supabase (PostgreSQL) integrated with async SQLAlchemy. Schema (`schema.sql`) and ORM models exist for Robots, AI Requests, System Events, and Agent Decisions.
- **Queue System**: Built an asynchronous priority queue with built-in starvation prevention algorithms.
- **WebSockets**: Live system event emitter integrated across all major request lifecycle events.
- **Testing**: A comprehensive pytest suite (`tests/test_privatebrain.py`) was created, run, and all tests successfully pass.
- **Fixed Issues**: Addressed fragile module imports (`__init__.py` files added) and resolved `DATABASE_URL` runtime parsing bugs.

### 2. AI Implementation
- **Integration**: Replaced logic branches with a true Ollama-compatible Agentic reasoning loop.
- **Model Routers**: Created structural service classes for Object Detection (YOLOv8), Classification (MobileNetV2), and Speech.
- **Isolated Simulation**: The models gracefully downgrade to local mock outputs if GPU/libraries aren't present.

### 3. Frontend Command Center (React)
- **UI System**: Futuristic dark-themed layout built in `index.css`.
- **Components**: Developed dynamic `RobotFleet.tsx`, `RequestMonitor.tsx`, `EventStream.tsx`, and `SystemHealth.tsx` widgets.
- **WebSocket Hooks**: `useWebSocket.ts` natively auto-reconnects and pushes state changes into the UI in real-time.

### 4. Developer Tools
- **Mock Robot**: Created `mock_robot/client.py`, which is capable of executing 5 complex lifecycle scenarios targeting the API endpoints directly.
- **Documentation**: Generated `SETUP.md`, `AI_MODELS.md`, `ROBOT_API_INTEGRATION.md`, and `README.md`.

---

## 🛠️ Outstanding / Pending Tasks

To fully spin up the environment on the new account/system, the following manual steps and environment configuration tasks remain:

1. **Deploy your PostgreSQL Database**
   * **Missing Component:** The application requires a PostgreSQL server containing the tables from `backend/app/database/schema.sql`.
   * **Action:** Either use Supabase to host this (as documented in `SETUP.md`) OR use Docker by running `docker compose up -d db`.

2. **Supply Global Environment Variables**
   * **Missing Component:** Real environment keys are missing.
   * **Action:** Copy `.env.example` to `.env` (in the root and/or `backend/` directory) and add the true PostgreSQL `DATABASE_URL`.

3. **Install Ollama Locally (Optional, but required for the "Real AI" requirement)**
   * **Missing Component:** The AI orchestration loop will fall back to deterministic if-else rules if Ollama cannot be reached.
   * **Action:** Install Ollama (`ollama pull qwen2.5:3b`) so the endpoint `http://localhost:11434` answers the agent's requests.

4. **Launch the Full Stack**
   * **Action:** Once the DB is online, you need to spin up the servers:
     - Term 1: `cd backend && python -m uvicorn app.main:app --port 8000`
     - Term 2: `cd frontend && npm run dev`
     - Term 3: `python mock_robot/client.py --scenario all` 

5. **Fix Python Constraints (If building locally on Windows)**
   * Note that `asyncpg` and certain `pydantic` binaries currently experience Rust compilation issues when running on the beta release of **Python 3.14**. 
   * **Action:** Ensure you're running Python 3.11 or Python 3.12, or just deploy purely through Docker using `docker compose up --build`.
