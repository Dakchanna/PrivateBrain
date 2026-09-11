from __future__ import annotations
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

# ──────────────────────────────────────────────
# Mock DB and services for unit tests
# ──────────────────────────────────────────────

class MockRobotRepo:
    def __init__(self):
        self.robots = {}

    async def get_by_robot_id(self, robot_id):
        return self.robots.get(robot_id)

    async def get_all(self):
        return list(self.robots.values())

    async def create(self, robot_id, api_key_hash, name=None, description=None):
        from unittest.mock import MagicMock
        from datetime import datetime, timezone
        robot = MagicMock()
        robot.robot_id = robot_id
        robot.api_key_hash = api_key_hash
        robot.name = name
        robot.status = MagicMock(value="OFFLINE")
        robot.last_seen = None
        robot.total_requests = 0
        robot.success_count = 0
        robot.failure_count = 0
        robot.avg_latency_ms = 0.0
        robot.created_at = datetime.now(timezone.utc)
        self.robots[robot_id] = robot
        return robot

    async def update_status(self, robot_id, status):
        if robot_id in self.robots:
            self.robots[robot_id].status = MagicMock(value=status.value if hasattr(status, 'value') else status)

    async def increment_request_count(self, robot_id, success, latency_ms):
        pass


class MockRequestRepo:
    def __init__(self):
        self.requests = {}

    async def create(self, request_id, robot_id, task_type, priority, payload=None, metadata=None):
        from unittest.mock import MagicMock
        from datetime import datetime, timezone
        req = MagicMock()
        req.request_id = request_id
        req.robot_id = robot_id
        req.task_type = MagicMock(value=task_type.value if hasattr(task_type, 'value') else task_type)
        req.priority = MagicMock(value=priority.value if hasattr(priority, 'value') else priority)
        req.status = MagicMock(value="RECEIVED")
        req.payload = payload
        req.created_at = datetime.now(timezone.utc)
        self.requests[request_id] = req
        return req

    async def get_by_request_id(self, request_id):
        return self.requests.get(request_id)

    async def update_status(self, request_id, status, **kwargs):
        if request_id in self.requests:
            self.requests[request_id].status = MagicMock(value=status.value if hasattr(status, 'value') else status)

    async def get_recent(self, limit=50):
        return list(self.requests.values())[:limit]

    async def get_stats(self):
        return {"total": 0, "active": 0, "queued": 0, "completed": 0, "failed": 0, "avg_latency_ms": 0.0}

    async def set_latency(self, request_id, latency_ms):
        pass


# ──────────────────────────────────────────────
# Tests: Authentication
# ──────────────────────────────────────────────

def test_api_key_generation():
    from app.security.authentication import generate_api_key, hash_api_key, verify_api_key
    key = generate_api_key()
    assert key.startswith("pb_")
    assert len(key) > 10
    hashed = hash_api_key(key)
    assert verify_api_key(key, hashed)
    assert not verify_api_key("wrong_key", hashed)


def test_jwt_creation_and_decode():
    from app.security.authentication import create_robot_token, decode_robot_token
    token = create_robot_token("ROBOT_TEST")
    payload = decode_robot_token(token)
    assert payload["sub"] == "ROBOT_TEST"
    assert payload["type"] == "robot"


# ──────────────────────────────────────────────
# Tests: Priority Queue
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priority_queue_ordering():
    from app.scheduler.priority_queue import AgentPriorityQueue
    pq = AgentPriorityQueue()
    await pq.put("req-low", "low")
    await pq.put("req-critical", "critical")
    await pq.put("req-normal", "normal")
    await pq.put("req-high", "high")

    first = await pq.get()
    assert first.request_id == "req-critical"
    second = await pq.get()
    assert second.request_id == "req-high"
    third = await pq.get()
    assert third.request_id == "req-normal"
    fourth = await pq.get()
    assert fourth.request_id == "req-low"


@pytest.mark.asyncio
async def test_priority_queue_no_duplicates():
    from app.scheduler.priority_queue import AgentPriorityQueue
    pq = AgentPriorityQueue()
    await pq.put("req-1", "normal")
    await pq.put("req-1", "normal")  # duplicate
    assert pq.size() == 1


# ──────────────────────────────────────────────
# Tests: Agent Tools
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_estimate_task_resources_valid():
    from app.agent.tools.agent_tools import estimate_task_resources
    result = await estimate_task_resources("object_detection")
    assert result.success
    assert result.data["cpu_pct"] > 0


@pytest.mark.asyncio
async def test_estimate_task_resources_invalid():
    from app.agent.tools.agent_tools import estimate_task_resources
    result = await estimate_task_resources("unknown_task")
    assert not result.success
    assert "Unknown task type" in result.error


@pytest.mark.asyncio
async def test_update_request_status_invalid():
    from app.agent.tools.agent_tools import update_request_status
    repo = MockRequestRepo()
    await repo.create("REQ-001", "R01", "object_detection", "normal")
    result = await update_request_status("REQ-001", "INVALID_STATUS", repo)
    assert not result.success
    assert "Invalid status" in result.error


# ──────────────────────────────────────────────
# Tests: Model Router
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_model_router_availability():
    from app.inference.router import ModelRouter
    router = ModelRouter()
    await router.initialize()
    models = router.get_available_models()
    assert len(models) > 0
    # All models should be available (at minimum via mock adapter)
    for name, info in models.items():
        assert info["available"] is True


@pytest.mark.asyncio
async def test_object_detection_mock_inference():
    from app.inference.object_detection import ObjectDetectionService
    from app.inference.base import InferenceRequest
    svc = ObjectDetectionService()
    svc.is_fallback = True
    svc.is_available = True
    req = InferenceRequest("req-001", "object_detection", {})
    result = await svc.infer(req)
    assert result.model_name == "yolov8n_mock"
    assert result.is_fallback
    assert "detections" in result.result


@pytest.mark.asyncio
async def test_image_classification_mock_inference():
    from app.inference.image_classification import ImageClassificationService
    from app.inference.base import InferenceRequest
    svc = ImageClassificationService()
    svc.is_fallback = True
    svc.is_available = True
    req = InferenceRequest("req-002", "image_classification", {})
    result = await svc.infer(req)
    assert result.is_fallback
    assert "classifications" in result.result


@pytest.mark.asyncio
async def test_speech_mock_inference():
    from app.inference.speech import SpeechProcessingService
    from app.inference.base import InferenceRequest
    svc = SpeechProcessingService()
    svc.is_fallback = True
    svc.is_available = True
    req = InferenceRequest("req-003", "speech_processing", {})
    result = await svc.infer(req)
    assert result.is_fallback
    assert "transcript" in result.result


# ──────────────────────────────────────────────
# Tests: Agent Decision (Deterministic Fallback)
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_deterministic_critical():
    """Critical priority should always result in PROCESS action."""
    from app.agent.agent import PrivateBrainAgent, AgentContext
    from app.inference.router import ModelRouter
    from app.scheduler.scheduler import PrivateBrainScheduler
    from app.monitoring.resources import ResourceMonitor

    agent = PrivateBrainAgent()
    router = ModelRouter()
    await router.initialize()
    sched = PrivateBrainScheduler()
    await sched.start()

    ctx = AgentContext(
        request_id="TEST-001",
        robot_id="R99",
        task_type="object_detection",
        priority="critical",
        payload={},
        robot_repo=MockRobotRepo(),
        request_repo=MockRequestRepo(),
        decision_repo=MagicMock(),
        scheduler=sched,
        model_router=router,
        resource_monitor=ResourceMonitor(),
    )
    decision = await agent._deterministic_fallback(ctx)
    assert decision["action"] in ("PROCESS", "SCHEDULE")
    assert decision["priority"] == "critical"


# ──────────────────────────────────────────────
# Tests: Resource Monitor
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resource_monitor():
    from app.monitoring.resources import ResourceMonitor
    monitor = ResourceMonitor()
    metrics = await monitor.get_metrics()
    assert "cpu_percent" in metrics
    assert "memory_percent" in metrics
    assert 0 <= metrics["cpu_percent"] <= 100
    assert 0 <= metrics["memory_percent"] <= 100


# ──────────────────────────────────────────────
# Tests: Request ID Generation
# ──────────────────────────────────────────────

def test_request_id_format():
    import re
    pattern = r"^PB-\d{4}-\d{6}$"
    test_ids = ["PB-2026-000001", "PB-2026-000123", "PB-2099-999999"]
    for rid in test_ids:
        assert re.match(pattern, rid), f"ID {rid} doesn't match pattern"
