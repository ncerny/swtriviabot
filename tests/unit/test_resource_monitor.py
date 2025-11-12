"""Unit tests for the resource monitor utility."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.utils import resource_monitor


class _LoggerSpy:
    """Capture logger calls for assertions."""

    def __init__(self) -> None:
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.criticals: list[str] = []
        self.debugs: list[str] = []

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def critical(self, message: str) -> None:
        self.criticals.append(message)

    def debug(self, message: str) -> None:
        self.debugs.append(message)

    def error(self, message: str, exc_info: bool | None = None) -> None:  # pragma: no cover - defensive only
        self.warnings.append(f"error:{message}")


@pytest.fixture(autouse=True)
def reset_resource_monitor():
    """Ensure singleton does not leak between tests."""

    previous = resource_monitor._monitor
    resource_monitor._monitor = None
    yield
    resource_monitor._monitor = previous


def test_resource_monitor_reports_memory_and_fd(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resource monitor returns memory and FD statistics when psutil is available."""

    fake_process = MagicMock()
    fake_process.memory_info.return_value = SimpleNamespace(rss=104857600, vms=209715200)
    fake_process.num_fds.return_value = 42

    spy = _LoggerSpy()
    monkeypatch.setattr(resource_monitor, "logger", spy)
    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", True)
    monkeypatch.setattr(resource_monitor.psutil, "Process", lambda pid: fake_process)

    monitor = resource_monitor.ResourceMonitor()

    memory = monitor.get_memory_usage()
    assert memory["rss_mb"] == pytest.approx(100.0, rel=1e-3)
    assert memory["vms_mb"] == pytest.approx(200.0, rel=1e-3)

    fd_count = monitor.get_fd_count()
    assert fd_count == 42

    monitor.log_stats(context="test")
    assert any("Resource usage (test)" in entry for entry in spy.infos)

    fake_process.memory_info.return_value = SimpleNamespace(rss=130 * 1024 * 1024, vms=0)
    monitor.check_memory_threshold(warning_mb=100.0, critical_mb=120.0)
    assert any("CRITICAL" in entry for entry in spy.criticals)


def test_resource_monitor_fd_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Monitor falls back to open_files when num_fds is unavailable."""

    class _Process:
        def __init__(self) -> None:
            self._files = [object(), object()]

        def memory_info(self):  # noqa: D401 - simple stub
            return SimpleNamespace(rss=0, vms=0)

        def open_files(self):  # noqa: D401 - simple stub
            return self._files

    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", True)
    monkeypatch.setattr(resource_monitor.psutil, "Process", lambda pid: _Process())

    monitor = resource_monitor.ResourceMonitor()

    assert monitor.get_fd_count() == 2


def test_resource_monitor_handles_missing_psutil(monkeypatch: pytest.MonkeyPatch) -> None:
    """When psutil is missing the monitor returns zeroed statistics."""

    spy = _LoggerSpy()
    monkeypatch.setattr(resource_monitor, "logger", spy)
    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", False)

    monitor = resource_monitor.ResourceMonitor()

    assert monitor.get_memory_usage() == {"rss_mb": 0.0, "vms_mb": 0.0}
    assert monitor.get_fd_count() == 0

    monitor.log_stats(context="disabled")
    assert any("Resource monitoring disabled" in entry for entry in spy.debugs)

    monitor.check_memory_threshold()
    # Initialization logs a warning once when psutil is unavailable
    assert spy.warnings == ["psutil not available - resource monitoring disabled"]
    assert not spy.criticals


def test_resource_monitor_memory_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gracefully handles memory_info exceptions."""

    class _Process:
        def memory_info(self):
            raise RuntimeError("boom")

    spy = _LoggerSpy()
    monkeypatch.setattr(resource_monitor, "logger", spy)
    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", True)
    monkeypatch.setattr(resource_monitor.psutil, "Process", lambda pid: _Process())

    monitor = resource_monitor.ResourceMonitor()

    mem = monitor.get_memory_usage()
    assert mem == {"rss_mb": 0.0, "vms_mb": 0.0}
    assert any("Failed to get memory usage" in entry for entry in spy.warnings)


def test_resource_monitor_fd_error_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """FD counting failures default to zero."""

    class _Process:
        def memory_info(self):
            return SimpleNamespace(rss=0, vms=0)

        def num_fds(self):
            raise RuntimeError("nope")

    spy = _LoggerSpy()
    monkeypatch.setattr(resource_monitor, "logger", spy)
    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", True)
    monkeypatch.setattr(resource_monitor.psutil, "Process", lambda pid: _Process())

    monitor = resource_monitor.ResourceMonitor()
    assert monitor.get_fd_count() == 0
    assert any("Could not get FD count" in entry for entry in spy.debugs)


def test_resource_monitor_log_stats_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """log_stats swallows exceptions and reports errors."""

    spy = _LoggerSpy()
    monkeypatch.setattr(resource_monitor, "logger", spy)
    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", True)

    monitor = resource_monitor.ResourceMonitor()

    def _raise() -> dict[str, float]:
        raise RuntimeError("fail")

    monkeypatch.setattr(monitor, "get_memory_usage", _raise)

    monitor.log_stats(context="ctx")
    assert any("Failed to log resource stats" in entry for entry in spy.warnings)


def test_resource_monitor_threshold_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Threshold checker logs errors when stats retrieval fails."""

    spy = _LoggerSpy()
    monkeypatch.setattr(resource_monitor, "logger", spy)
    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", True)

    monitor = resource_monitor.ResourceMonitor()

    def _raise() -> dict[str, float]:
        raise RuntimeError("fail")

    monkeypatch.setattr(monitor, "get_memory_usage", _raise)

    monitor.check_memory_threshold()
    assert any("Failed to check memory threshold" in entry for entry in spy.warnings)


def test_get_resource_monitor_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_resource_monitor returns a singleton instance."""

    monkeypatch.setattr(resource_monitor, "PSUTIL_AVAILABLE", False)
    resource_monitor._monitor = None

    first = resource_monitor.get_resource_monitor()
    second = resource_monitor.get_resource_monitor()

    assert first is second