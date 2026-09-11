from __future__ import annotations
import asyncio
import heapq
from dataclasses import dataclass, field
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

PRIORITY_WEIGHTS = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}


@dataclass(order=True)
class PriorityQueueItem:
    sort_index: int
    sequence: int = field(compare=True)
    request_id: str = field(compare=False)
    priority: str = field(compare=False)
    created_at: float = field(compare=False)


class AgentPriorityQueue:
    """
    Thread-safe async priority queue for AI requests.
    CRITICAL > HIGH > NORMAL > LOW.
    Starvation prevention: low-priority requests are promoted after 60 seconds.
    """

    def __init__(self):
        self._heap: list[PriorityQueueItem] = []
        self._lock = asyncio.Lock()
        self._sequence = 0
        self._item_map: dict[str, PriorityQueueItem] = {}

    async def put(self, request_id: str, priority: str) -> None:
        async with self._lock:
            if request_id in self._item_map:
                return  # Already queued
            weight = PRIORITY_WEIGHTS.get(priority.lower(), 2)
            self._sequence += 1
            item = PriorityQueueItem(
                sort_index=weight,
                sequence=self._sequence,
                request_id=request_id,
                priority=priority,
                created_at=asyncio.get_event_loop().time(),
            )
            heapq.heappush(self._heap, item)
            self._item_map[request_id] = item
            logger.info({"event": "request_queued", "request_id": request_id,
                         "priority": priority, "queue_size": len(self._heap)})

    async def get(self) -> Optional[PriorityQueueItem]:
        async with self._lock:
            if not self._heap:
                return None
            item = heapq.heappop(self._heap)
            self._item_map.pop(item.request_id, None)
            return item

    async def get_state(self) -> dict:
        async with self._lock:
            counts: dict[str, int] = {"critical": 0, "high": 0, "normal": 0, "low": 0}
            for item in self._heap:
                counts[item.priority.lower()] = counts.get(item.priority.lower(), 0) + 1
            return {
                "total_queued": len(self._heap),
                "by_priority": counts,
                "top_request": self._heap[0].request_id if self._heap else None,
            }

    async def promote_starved_requests(self, max_wait_seconds: float = 60.0) -> int:
        """Promote LOW requests that have been waiting too long."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            promoted = 0
            for item in self._heap:
                if item.priority.lower() == "low" and (now - item.created_at) > max_wait_seconds:
                    item.sort_index = PRIORITY_WEIGHTS["normal"]
                    item.priority = "normal"
                    promoted += 1
            if promoted:
                heapq.heapify(self._heap)
                logger.info({"event": "starvation_prevention", "promoted": promoted})
            return promoted

    def size(self) -> int:
        return len(self._heap)
