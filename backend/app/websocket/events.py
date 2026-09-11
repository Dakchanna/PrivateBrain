from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from app.websocket.manager import ws_manager


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


async def emit_robot_connected(robot_id: str) -> None:
    await ws_manager.broadcast({
        "type": "ROBOT_CONNECTED",
        "robot_id": robot_id,
        "timestamp": _ts(),
        "message": f"Robot {robot_id} connected",
    })


async def emit_robot_disconnected(robot_id: str) -> None:
    await ws_manager.broadcast({
        "type": "ROBOT_DISCONNECTED",
        "robot_id": robot_id,
        "timestamp": _ts(),
        "message": f"Robot {robot_id} disconnected",
    })


async def emit_request_received(request_id: str, robot_id: str,
                                task_type: str, priority: str) -> None:
    await ws_manager.broadcast({
        "type": "REQUEST_RECEIVED",
        "request_id": request_id,
        "robot_id": robot_id,
        "task_type": task_type,
        "priority": priority,
        "timestamp": _ts(),
        "message": f"{robot_id} → {task_type} [{priority.upper()}]",
    })


async def emit_request_queued(request_id: str, robot_id: str, priority: str) -> None:
    await ws_manager.broadcast({
        "type": "REQUEST_QUEUED",
        "request_id": request_id,
        "robot_id": robot_id,
        "priority": priority,
        "timestamp": _ts(),
        "message": f"Request {request_id} queued [{priority.upper()}]",
    })


async def emit_request_scheduled(request_id: str, selected_model: str) -> None:
    await ws_manager.broadcast({
        "type": "REQUEST_SCHEDULED",
        "request_id": request_id,
        "selected_model": selected_model,
        "timestamp": _ts(),
        "message": f"Scheduled on {selected_model}",
    })


async def emit_request_started(request_id: str, robot_id: str, model: str) -> None:
    await ws_manager.broadcast({
        "type": "REQUEST_STARTED",
        "request_id": request_id,
        "robot_id": robot_id,
        "model": model,
        "timestamp": _ts(),
        "message": f"Processing {request_id} on {model}",
    })


async def emit_request_completed(request_id: str, robot_id: str,
                                  latency_ms: float, model: str) -> None:
    await ws_manager.broadcast({
        "type": "REQUEST_COMPLETED",
        "request_id": request_id,
        "robot_id": robot_id,
        "latency_ms": latency_ms,
        "model": model,
        "timestamp": _ts(),
        "message": f"Completed {request_id} in {latency_ms:.0f}ms",
    })


async def emit_request_failed(request_id: str, robot_id: str, reason: str) -> None:
    await ws_manager.broadcast({
        "type": "REQUEST_FAILED",
        "request_id": request_id,
        "robot_id": robot_id,
        "reason": reason,
        "timestamp": _ts(),
        "message": f"FAILED {request_id}: {reason}",
    })


async def emit_retry_started(request_id: str, retry_count: int) -> None:
    await ws_manager.broadcast({
        "type": "RETRY_STARTED",
        "request_id": request_id,
        "retry_count": retry_count,
        "timestamp": _ts(),
        "message": f"Retrying {request_id} (attempt {retry_count})",
    })


async def emit_fallback_selected(request_id: str, reason: str) -> None:
    await ws_manager.broadcast({
        "type": "FALLBACK_SELECTED",
        "request_id": request_id,
        "reason": reason,
        "timestamp": _ts(),
        "message": f"Fallback activated for {request_id}",
    })


async def emit_recovery_completed(request_id: str) -> None:
    await ws_manager.broadcast({
        "type": "RECOVERY_COMPLETED",
        "request_id": request_id,
        "timestamp": _ts(),
        "message": f"Recovery completed for {request_id}",
    })


async def emit_resource_updated(metrics: dict) -> None:
    await ws_manager.broadcast({
        "type": "RESOURCE_UPDATED",
        "metrics": metrics,
        "timestamp": _ts(),
    })


async def emit_agent_decision(request_id: str, action: str, reason: str,
                               selected_model: Optional[str] = None) -> None:
    await ws_manager.broadcast({
        "type": "AGENT_DECISION",
        "request_id": request_id,
        "action": action,
        "selected_model": selected_model,
        "reason": reason,
        "timestamp": _ts(),
        "message": f"Agent: {action} → {selected_model or 'N/A'} — {reason}",
    })
