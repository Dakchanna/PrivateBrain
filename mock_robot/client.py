"""
PrivateBrain Mock Robot Client

External testing harness that communicates ONLY through the public PrivateBrain API.
This is NOT the real robot simulator — it is for testing PrivateBrain standalone.

Usage:
  python mock_robot/client.py --scenario all
  python mock_robot/client.py --scenario concurrent
  python mock_robot/client.py --scenario critical
  python mock_robot/client.py --scenario failure
  python mock_robot/client.py --register --robot-id ROBOT_01

API env:
  PRIVATEBRAIN_URL=http://localhost:8000
"""
from __future__ import annotations
import asyncio
import argparse
import json
import base64
import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    print("ERROR: Install httpx first: pip install httpx")
    sys.exit(1)

BASE_URL = os.getenv("PRIVATEBRAIN_URL", "http://localhost:8000")

# ──────────────────────────────────────────────
# Client class
# ──────────────────────────────────────────────

class RobotClient:
    def __init__(self, robot_id: str, api_key: str | None = None, token: str | None = None):
        self.robot_id = robot_id
        self.api_key = api_key
        self.token = token
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    async def close(self):
        await self._client.aclose()

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    async def register(self, name: str | None = None) -> dict:
        r = await self._client.post("/api/v1/robots/register", json={
            "robot_id": self.robot_id,
            "name": name or self.robot_id,
            "description": f"Mock robot client — {self.robot_id}",
        })
        if r.status_code == 409:
            print(f"  [!] Robot {self.robot_id} already registered")
            return {}
        r.raise_for_status()
        data = r.json()
        self.api_key = data["api_key"]
        print(f"  [✓] Robot registered: {self.robot_id}")
        print(f"  [KEY] API Key: {self.api_key}  ← store this!")
        return data

    async def authenticate(self) -> str:
        if not self.api_key:
            raise ValueError(f"No API key for {self.robot_id}")
        r = await self._client.post("/api/v1/robots/authenticate", json={
            "robot_id": self.robot_id,
            "api_key": self.api_key,
        })
        r.raise_for_status()
        self.token = r.json()["token"]
        print(f"  [✓] Authenticated: {self.robot_id}")
        return self.token

    async def submit_request(self, task_type: str, priority: str = "normal",
                              payload: dict | None = None) -> str:
        r = await self._client.post("/api/v1/requests",
            headers=self._auth_headers,
            json={
                "robot_id": self.robot_id,
                "task_type": task_type,
                "priority": priority,
                "payload": payload or {},
                "metadata": {"sent_at": datetime.now(timezone.utc).isoformat()},
            }
        )
        r.raise_for_status()
        data = r.json()
        req_id = data["request_id"]
        print(f"  [→] Submitted {task_type} [{priority}] → {req_id}")
        return req_id

    async def poll_result(self, request_id: str, timeout: int = 60) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = await self._client.get(f"/api/v1/requests/{request_id}/result",
                                        headers=self._auth_headers)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status", "UNKNOWN")
                if status in ("COMPLETED", "FAILED", "ERROR"):
                    return data
            await asyncio.sleep(1)
        return {"status": "TIMEOUT", "request_id": request_id}

    async def get_status(self, request_id: str) -> dict:
        r = await self._client.get(f"/api/v1/requests/{request_id}",
                                    headers=self._auth_headers)
        r.raise_for_status()
        return r.json()

    async def disconnect(self):
        if not self.token:
            return
        await self._client.post(f"/api/v1/robots/{self.robot_id}/disconnect",
                                  headers=self._auth_headers)
        print(f"  [✓] Disconnected: {self.robot_id}")


# ──────────────────────────────────────────────
# Test payloads
# ──────────────────────────────────────────────

def _dummy_image_b64() -> str:
    # 1x1 white PNG in base64
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

def _dummy_audio_b64() -> str:
    # Minimal WAV header (44 bytes) in base64
    import struct
    header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36, b'WAVE', b'fmt ', 16, 1, 1, 16000, 32000, 2, 16, b'data', 0)
    return base64.b64encode(header).decode()


# ──────────────────────────────────────────────
# Scenarios
# ──────────────────────────────────────────────

async def setup_robots(*robot_ids: str) -> dict[str, RobotClient]:
    """Register and authenticate a set of robots. Persists API keys to .keys file."""
    keys_file = Path("mock_robot/.robot_keys.json")
    stored: dict = {}
    if keys_file.exists():
        stored = json.loads(keys_file.read_text())

    clients: dict[str, RobotClient] = {}
    for rid in robot_ids:
        key = stored.get(rid)
        client = RobotClient(rid, api_key=key)
        if not key:
            result = await client.register(name=f"Mock {rid}")
            if "api_key" in result:
                stored[rid] = result["api_key"]
                client.api_key = result["api_key"]
        await client.authenticate()
        clients[rid] = client

    keys_file.parent.mkdir(exist_ok=True)
    keys_file.write_text(json.dumps(stored, indent=2))
    return clients


async def scenario_concurrent():
    """Scenario 1: Three robots send concurrent requests."""
    print("\n══════ SCENARIO 1: Concurrent Requests ══════")
    clients = await setup_robots("ROBOT_01", "ROBOT_02", "ROBOT_03")
    try:
        r1 = asyncio.create_task(
            clients["ROBOT_01"].submit_request("object_detection", "normal",
                                                {"image_base64": _dummy_image_b64()})
        )
        r2 = asyncio.create_task(
            clients["ROBOT_02"].submit_request("image_classification", "high",
                                                {"image_base64": _dummy_image_b64()})
        )
        r3 = asyncio.create_task(
            clients["ROBOT_03"].submit_request("speech_processing", "normal",
                                                {"audio_base64": _dummy_audio_b64()})
        )
        ids = await asyncio.gather(r1, r2, r3)
        print("\n  Polling for results…")
        results = await asyncio.gather(*[
            clients[rid].poll_result(rid_val)
            for rid, rid_val in zip(["ROBOT_01","ROBOT_02","ROBOT_03"], ids)
        ])
        for i, (rid, result) in enumerate(zip(["ROBOT_01","ROBOT_02","ROBOT_03"], results)):
            print(f"  [{rid}] Status: {result.get('status')} | Model: {result.get('model','?')}")
    finally:
        for c in clients.values():
            await c.close()


async def scenario_critical():
    """Scenario 2: Critical priority request from ROBOT_03."""
    print("\n══════ SCENARIO 2: Critical Priority ══════")
    clients = await setup_robots("ROBOT_01", "ROBOT_03")
    try:
        # Submit a normal request first
        rid_norm = await clients["ROBOT_01"].submit_request("image_classification", "low",
                                                              {"image_base64": _dummy_image_b64()})
        await asyncio.sleep(0.2)
        # Now submit critical — should jump the queue
        rid_crit = await clients["ROBOT_03"].submit_request("object_detection", "critical",
                                                              {"image_base64": _dummy_image_b64()})
        print("  [!] Critical job submitted — watching priority scheduling…")
        result = await clients["ROBOT_03"].poll_result(rid_crit)
        print(f"  [ROBOT_03 CRITICAL] Status: {result.get('status')} | Latency: {result.get('processing_time_ms','?')}ms")
    finally:
        for c in clients.values():
            await c.close()


async def scenario_resource_constrained():
    """Scenario 3: Multiple low-priority requests when resources may be constrained."""
    print("\n══════ SCENARIO 3: Resource Constrained ══════")
    clients = await setup_robots("ROBOT_01", "ROBOT_02")
    try:
        tasks = []
        for i in range(4):
            rid = "ROBOT_01" if i % 2 == 0 else "ROBOT_02"
            task_type = random.choice(["object_detection", "image_classification"])
            priority = "low" if i < 3 else "high"
            payload = {"image_base64": _dummy_image_b64()}
            req_id = await clients[rid].submit_request(task_type, priority, payload)
            tasks.append((rid, req_id))
            await asyncio.sleep(0.1)
        print(f"  Submitted {len(tasks)} requests — agent will prioritize…")
        for rid, req_id in tasks[-2:]:
            result = await clients[rid].poll_result(req_id, timeout=90)
            print(f"  [{rid} {req_id}] → {result.get('status')}")
    finally:
        for c in clients.values():
            await c.close()


async def scenario_failure_recovery():
    """Scenario 4: Speech request (fallback will trigger if Whisper not installed)."""
    print("\n══════ SCENARIO 4: Failure / Recovery ══════")
    clients = await setup_robots("ROBOT_03")
    try:
        req_id = await clients["ROBOT_03"].submit_request(
            "speech_processing", "high",
            {"audio_base64": _dummy_audio_b64()}
        )
        print("  [!] Watching for fallback / recovery…")
        result = await clients["ROBOT_03"].poll_result(req_id, timeout=60)
        detail = await clients["ROBOT_03"].get_status(req_id)
        print(f"  Status: {result.get('status')} | Fallback: {result.get('is_fallback', '?')}")
        events = detail.get("events", [])
        for e in events:
            print(f"    {e['event']:20} {e.get('message','')}")
    finally:
        for c in clients.values():
            await c.close()


async def scenario_disconnect():
    """Scenario 5: Robot disconnects — dashboard should show OFFLINE."""
    print("\n══════ SCENARIO 5: Robot Disconnect ══════")
    clients = await setup_robots("ROBOT_02")
    try:
        await asyncio.sleep(1)
        await clients["ROBOT_02"].disconnect()
        print("  [✓] Robot marked OFFLINE on dashboard")
    finally:
        for c in clients.values():
            await c.close()


async def run_all():
    """Run all 5 demonstration scenarios sequentially."""
    await scenario_concurrent()
    await asyncio.sleep(2)
    await scenario_critical()
    await asyncio.sleep(2)
    await scenario_resource_constrained()
    await asyncio.sleep(2)
    await scenario_failure_recovery()
    await asyncio.sleep(2)
    await scenario_disconnect()
    print("\n══════ All Scenarios Complete ══════")


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
def main():
    global BASE_URL
    parser = argparse.ArgumentParser(description="PrivateBrain Mock Robot Client")
    parser.add_argument("--scenario", choices=["all","concurrent","critical","resources","failure","disconnect"],
                        default="all", help="Scenario to run")
    parser.add_argument("--register", action="store_true", help="Register a robot by ID")
    parser.add_argument("--robot-id", default="ROBOT_01", help="Robot ID for --register")
    parser.add_argument("--url", default=BASE_URL, help="PrivateBrain base URL")
    args = parser.parse_args()

    BASE_URL = args.url

    print(f"PrivateBrain Mock Robot Client")
    print(f"Connecting to: {BASE_URL}\n")

    if args.register:
        async def do_register():
            client = RobotClient(args.robot_id)
            result = await client.register()
            await client.close()
            return result
        asyncio.run(do_register())
        return

    scenario_map = {
        "all": run_all,
        "concurrent": scenario_concurrent,
        "critical": scenario_critical,
        "resources": scenario_resource_constrained,
        "failure": scenario_failure_recovery,
        "disconnect": scenario_disconnect,
    }
    asyncio.run(scenario_map[args.scenario]())


if __name__ == "__main__":
    main()
