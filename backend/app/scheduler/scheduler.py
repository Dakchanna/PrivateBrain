from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable

from app.scheduler.priority_queue import AgentPriorityQueue
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PrivateBrainScheduler:
    """
    Async worker pool scheduler for AI requests.
    Routes completed items to a registered process_fn callback.
    """

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or settings.max_workers
        self.queue = AgentPriorityQueue()
        self._active_workers: set[str] = set()
        self._process_fn: Optional[Callable] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._processed_count = 0
        self._failed_count = 0

    def set_process_fn(self, fn: Callable[..., Awaitable]) -> None:
        """Register the async function that processes each queued request."""
        self._process_fn = fn

    async def enqueue(self, request_id: str, priority: str) -> None:
        """Add a request to the priority queue."""
        await self.queue.put(request_id, priority)

    def get_queue_state(self) -> dict:
        """Return queue state synchronously (safe from async context)."""
        return {
            "total_queued": self.queue.size(),
            "active_workers": len(self._active_workers),
            "max_workers": self.max_workers,
            "worker_utilization": len(self._active_workers) / self.max_workers,
            "processed_total": self._processed_count,
            "failed_total": self._failed_count,
        }

    async def start(self) -> None:
        """Start the background worker dispatch loop."""
        self._running = True
        self._semaphore = asyncio.Semaphore(self.max_workers)
        logger.info({"event": "scheduler_started", "max_workers": self.max_workers})
        # Start dispatch task
        asyncio.create_task(self._dispatch_loop())
        # Start anti-starvation task
        asyncio.create_task(self._starvation_loop())

    async def stop(self) -> None:
        """Stop the dispatcher."""
        self._running = False
        logger.info({"event": "scheduler_stopped"})

    async def _dispatch_loop(self) -> None:
        """Continuously dequeue and dispatch requests to workers."""
        while self._running:
            item = await self.queue.get()
            if item:
                await self._semaphore.acquire()
                self._active_workers.add(item.request_id)
                task = asyncio.create_task(self._run_worker(item))
                self._tasks.append(task)
            else:
                await asyncio.sleep(0.1)

    async def _starvation_loop(self) -> None:
        """Periodically promote starved LOW requests."""
        while self._running:
            await asyncio.sleep(30)
            await self.queue.promote_starved_requests()

    async def _run_worker(self, item) -> None:
        """Execute a single request through the process_fn."""
        try:
            if self._process_fn:
                await asyncio.wait_for(
                    self._process_fn(item.request_id, item.priority),
                    timeout=settings.request_timeout,
                )
                self._processed_count += 1
        except asyncio.TimeoutError:
            logger.error({"event": "worker_timeout", "request_id": item.request_id})
            self._failed_count += 1
        except Exception as e:
            logger.error({"event": "worker_error", "request_id": item.request_id, "error": str(e)})
            self._failed_count += 1
        finally:
            self._active_workers.discard(item.request_id)
            self._semaphore.release()


# Global singleton
scheduler = PrivateBrainScheduler()
