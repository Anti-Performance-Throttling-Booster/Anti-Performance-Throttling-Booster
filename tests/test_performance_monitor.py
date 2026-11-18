from types import SimpleNamespace

import pytest

from monitoring.performance_monitor import PerformanceMonitor


class FakeProcess:
    def __init__(self, pid, name, cpu, memory):
        self.info = {"pid": pid, "name": name, "memory_info": SimpleNamespace(rss=memory)}
        self.cpu = cpu

    def cpu_percent(self, interval=None):
        return self.cpu

    def memory_percent(self):
        return 3.5


def test_monitor_starts_collects_sanitized_snapshot_and_stops(monkeypatch):
    cpu_values = iter([0.0, 42.5])
    monkeypatch.setattr("monitoring.performance_monitor.psutil.cpu_percent", lambda interval=None: next(cpu_values))
    monkeypatch.setattr("monitoring.performance_monitor.psutil.virtual_memory", lambda: SimpleNamespace(percent=61.2))
    monkeypatch.setattr("monitoring.performance_monitor.psutil.process_iter", lambda attrs: [
        FakeProcess(2, "Low.exe", 1.0, 100 * 1024 * 1024),
        FakeProcess(1, "High.exe", 8.0, 200 * 1024 * 1024),
    ])

    monitor = PerformanceMonitor(process_limit=1)
    assert monitor.start_monitoring()["status"] == "started"
    snapshot = monitor.collect_snapshot()

    assert snapshot["cpu_percent"] == 42.5
    assert snapshot["memory_percent"] == 61.2
    assert snapshot["processes"] == [{"pid": 1, "name": "High.exe", "cpu_percent": 8.0, "memory_mb": 200.0, "memory_percent": 3.5}]
    assert monitor.stop_monitoring()["status"] == "stopped"


def test_monitor_requires_active_session():
    with pytest.raises(RuntimeError):
        PerformanceMonitor().collect_snapshot()


@pytest.mark.parametrize("interval, limit", [(0, 10), (-1, 10), (True, 10), (1, 0), (1, True)])
def test_invalid_configuration_is_rejected(interval, limit):
    with pytest.raises(ValueError):
        PerformanceMonitor(interval, limit)
