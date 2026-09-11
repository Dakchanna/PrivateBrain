from __future__ import annotations
import asyncio
import time
from typing import Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

_START_TIME = time.monotonic()


class ResourceMonitor:
    """
    Monitors hardware resource utilization using psutil where available.
    Labels simulated values clearly when real metrics cannot be obtained.
    """

    def __init__(self):
        self._psutil_available = False
        self._gpu_available = False
        self._try_init()

    def _try_init(self):
        try:
            import psutil
            self._psutil_available = True
        except ImportError:
            logger.warning({"event": "psutil_unavailable", "message": "CPU/memory metrics will be simulated"})
        try:
            import pynvml
            pynvml.nvmlInit()
            self._gpu_available = True
        except Exception:
            logger.info({"event": "gpu_unavailable", "message": "No GPU detected — GPU metrics unavailable"})

    async def get_metrics(self) -> dict:
        metrics: dict = {}

        if self._psutil_available:
            import psutil
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            metrics["memory_percent"] = psutil.virtual_memory().percent
            metrics["memory_available_mb"] = round(psutil.virtual_memory().available / 1024 / 1024, 1)
            metrics["source"] = "real"
        else:
            import random
            metrics["cpu_percent"] = round(30 + random.uniform(-10, 20), 1)
            metrics["memory_percent"] = round(45 + random.uniform(-5, 15), 1)
            metrics["memory_available_mb"] = round(4096 * (1 - metrics["memory_percent"] / 100), 1)
            metrics["source"] = "simulated"

        if self._gpu_available:
            try:
                import pynvml
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                metrics["gpu_percent"] = util.gpu
                metrics["gpu_available"] = True
            except Exception:
                metrics["gpu_percent"] = None
                metrics["gpu_available"] = False
        else:
            metrics["gpu_percent"] = None
            metrics["gpu_available"] = False

        metrics["uptime_seconds"] = round(time.monotonic() - _START_TIME, 1)
        return metrics

    def get_uptime(self) -> float:
        return round(time.monotonic() - _START_TIME, 1)


# Global singleton
resource_monitor = ResourceMonitor()
