"""Low-overhead local CPU, memory, and process monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

import psutil


class PerformanceMonitor:
    """Collect the resource snapshot used by the dashboard and detection logic.

    The monitor intentionally collects only aggregate host metrics and public
    process metadata (PID, executable name, CPU percentage, and memory use).
    It never reads process arguments, windows, files, or application content.
    """

    def __init__(self, refresh_interval: float = 1.0, process_limit: int = 30) -> None:
        if isinstance(refresh_interval, bool) or not isinstance(refresh_interval, (int, float)):
            raise ValueError("Refresh interval must be a positive number.")
        if not math.isfinite(refresh_interval) or refresh_interval <= 0:
            raise ValueError("Refresh interval must be a positive number.")
        if isinstance(process_limit, bool) or not isinstance(process_limit, int) or process_limit < 1:
            raise ValueError("Process limit must be a positive integer.")

        self.refresh_interval = float(refresh_interval)
        self.process_limit = process_limit
        self.is_monitoring = False
        self.started_at: str | None = None

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()

    def start_monitoring(self) -> dict[str, str]:
        """Start local monitoring and prime psutil's non-blocking CPU counter."""
        if self.is_monitoring:
            raise RuntimeError("Monitoring is already running.")
        psutil.cpu_percent(interval=None)
        self.is_monitoring = True
        self.started_at = self._timestamp()
        return {"status": "started", "started_at": self.started_at}

    def stop_monitoring(self) -> dict[str, str | None]:
        if not self.is_monitoring:
            raise RuntimeError("Monitoring is not currently running.")
        self.is_monitoring = False
        return {"status": "stopped", "started_at": self.started_at, "stopped_at": self._timestamp()}

    def collect_snapshot(self) -> dict[str, Any]:
        """Return a sanitized resource snapshot while monitoring is active."""
        if not self.is_monitoring:
            raise RuntimeError("Start monitoring before collecting a performance snapshot.")

        processes: list[dict[str, Any]] = []
        for process in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = process.info
                pid = info.get("pid")
                name = info.get("name")
                memory_info = info.get("memory_info")
                if not isinstance(pid, int) or not isinstance(name, str) or not name.strip():
                    continue
                memory_mb = (getattr(memory_info, "rss", 0) or 0) / (1024 * 1024)
                processes.append({
                    "pid": pid,
                    "name": name.strip(),
                    "cpu_percent": max(0.0, float(process.cpu_percent(interval=None))),
                    "memory_mb": max(0.0, memory_mb),
                    "memory_percent": max(0.0, min(100.0, float(process.memory_percent()))),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        processes.sort(key=lambda item: (item["cpu_percent"], item["memory_mb"]), reverse=True)
        virtual_memory = psutil.virtual_memory()
        return {
            "timestamp": self._timestamp(),
            "cpu_percent": max(0.0, min(100.0, float(psutil.cpu_percent(interval=None)))),
            "memory_percent": max(0.0, min(100.0, float(virtual_memory.percent))),
            "processes": processes[: self.process_limit],
        }
