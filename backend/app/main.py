from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.database.session import engine, create_tables
from app.database.models import Base
from app.inference.router import model_router
from app.scheduler.scheduler import scheduler
from app.monitoring.resources import resource_monitor
from app.websocket.manager import ws_manager
from app.websocket import events as ws_events
from app.api.v1 import robots, requests, system

setup_logging()
logger = get_logger("privatebrain.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info({"event": "startup", "version": settings.app_version})

    # Auto-create DB tables (SQLite dev or Postgres)
    await create_tables()

    # Initialize AI model services
    await model_router.initialize()

    # Start scheduler
    await scheduler.start()

    # Start background resource broadcaster
    async def broadcast_resources():
        while True:
            await asyncio.sleep(5)
            metrics = await resource_monitor.get_metrics()
            await ws_events.emit_resource_updated(metrics)

    resource_task = asyncio.create_task(broadcast_resources())

    logger.info({"event": "ready", "message": "PrivateBrain is operational"})
    yield

    # Shutdown
    resource_task.cancel()
    await scheduler.stop()
    logger.info({"event": "shutdown"})


app = FastAPI(
    title="PrivateBrain",
    description="AI-Powered Private Robotics Workload Orchestration Platform",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(robots.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


# WebSocket endpoint for live dashboard
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — dashboard only receives
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


# Health endpoint at root level
@app.get("/health", tags=["Infrastructure"])
async def health():
    return {"status": "ok", "service": "PrivateBrain", "version": settings.app_version}


@app.get("/", tags=["Infrastructure"])
async def root():
    return {
        "service": "PrivateBrain",
        "version": settings.app_version,
        "docs": "/docs",
        "websocket": "/ws",
    }
