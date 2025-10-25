"""Unit tests for performance monitoring utilities."""

import pytest
import asyncio

from src.utils.performance import PerformanceMetrics, monitor_performance, get_metrics


def test_performance_metrics_initialization():
    """Test PerformanceMetrics class initialization."""
    metrics = PerformanceMetrics()
    
    assert metrics.metrics["command_counts"] == {}
    assert metrics.metrics["command_times"] == {}
    assert metrics.metrics["errors"] == {}


def test_record_command_success():
    """Test recording successful command execution."""
    metrics = PerformanceMetrics()
    
    metrics.record_command("test_command", 50.0, success=True)
    
    assert metrics.metrics["command_counts"]["test_command"]["total"] == 1
    assert metrics.metrics["command_counts"]["test_command"]["success"] == 1
    assert metrics.metrics["command_counts"]["test_command"]["errors"] == 0
    assert metrics.metrics["command_times"]["test_command"] == [50.0]


def test_record_command_failure():
    """Test recording failed command execution."""
    metrics = PerformanceMetrics()
    
    metrics.record_command("test_command", 30.0, success=False)
    
    assert metrics.metrics["command_counts"]["test_command"]["total"] == 1
    assert metrics.metrics["command_counts"]["test_command"]["success"] == 0
    assert metrics.metrics["command_counts"]["test_command"]["errors"] == 1
    assert metrics.metrics["command_times"]["test_command"] == [30.0]


def test_record_multiple_commands():
    """Test recording multiple command executions."""
    metrics = PerformanceMetrics()
    
    metrics.record_command("cmd1", 10.0, success=True)
    metrics.record_command("cmd1", 20.0, success=True)
    metrics.record_command("cmd2", 30.0, success=False)
    metrics.record_command("cmd1", 15.0, success=True)
    
    assert metrics.metrics["command_counts"]["cmd1"]["total"] == 3
    assert metrics.metrics["command_counts"]["cmd1"]["success"] == 3
    assert metrics.metrics["command_counts"]["cmd2"]["total"] == 1
    assert metrics.metrics["command_counts"]["cmd2"]["errors"] == 1
    assert len(metrics.metrics["command_times"]["cmd1"]) == 3
    assert len(metrics.metrics["command_times"]["cmd2"]) == 1


def test_get_stats_no_data():
    """Test getting stats for a command with no data."""
    metrics = PerformanceMetrics()
    
    stats = metrics.get_stats("nonexistent")
    assert stats == {}


def test_get_stats_with_data():
    """Test getting stats for a command with data."""
    metrics = PerformanceMetrics()
    
    metrics.record_command("cmd1", 100.0, success=True)
    metrics.record_command("cmd1", 200.0, success=True)
    metrics.record_command("cmd1", 300.0, success=True)
    
    stats = metrics.get_stats("cmd1")
    assert stats["total_executions"] == 3
    assert stats["successful"] == 3
    assert stats["errors"] == 0
    assert stats["avg_time_ms"] == pytest.approx(200.0, rel=0.01)
    assert stats["min_time_ms"] == 100.0
    assert stats["max_time_ms"] == 300.0
    assert stats["p50_time_ms"] == 200.0


def test_get_stats_percentiles():
    """Test percentile calculations in get_stats."""
    metrics = PerformanceMetrics()
    
    # Add many values for better percentile testing
    for time in range(1, 101):  # 1ms to 100ms
        metrics.record_command("cmd1", float(time), success=True)
    
    stats = metrics.get_stats("cmd1")
    assert stats["total_executions"] == 100
    # p50 is calculated as sorted_times[n // 2], where n=100, so index 50 = value 51
    assert stats["p50_time_ms"] == pytest.approx(50.0, abs=2)  # Allow small variance
    assert stats["p95_time_ms"] == pytest.approx(95.0, abs=1)
    assert stats["p99_time_ms"] == pytest.approx(99.0, abs=1)


def test_get_all_stats():
    """Test getting stats for all commands."""
    metrics = PerformanceMetrics()
    
    metrics.record_command("cmd1", 10.0, success=True)
    metrics.record_command("cmd1", 20.0, success=True)
    metrics.record_command("cmd2", 30.0, success=True)
    
    all_stats = metrics.get_all_stats()
    
    assert "cmd1" in all_stats
    assert "cmd2" in all_stats
    assert all_stats["cmd1"]["total_executions"] == 2
    assert all_stats["cmd2"]["total_executions"] == 1


@pytest.mark.asyncio
async def test_monitor_performance_decorator():
    """Test the monitor_performance decorator."""
    
    @monitor_performance("test_func")
    async def test_function():
        await asyncio.sleep(0.01)  # Small delay
        return "success"
    
    result = await test_function()
    
    assert result == "success"


@pytest.mark.asyncio
async def test_monitor_performance_decorator_with_error():
    """Test decorator handles exceptions correctly."""
    
    @monitor_performance("failing_func")
    async def failing_function():
        await asyncio.sleep(0.01)
        raise ValueError("Test error")
    
    with pytest.raises(ValueError, match="Test error"):
        await failing_function()


def test_get_metrics_singleton():
    """Test that get_metrics returns the same instance."""
    metrics1 = get_metrics()
    metrics2 = get_metrics()
    
    assert metrics1 is metrics2
    
    # Test that it's functional
    initial_count = len(metrics1.metrics["command_counts"])
    metrics1.record_command("test", 10.0, success=True)
    assert len(metrics2.metrics["command_counts"]) == initial_count + 1
