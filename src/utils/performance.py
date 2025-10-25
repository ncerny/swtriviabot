"""Performance monitoring utilities for the Discord Trivia Bot."""

import logging
import time
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)


def monitor_performance(command_name: str) -> Callable:
    """Decorator to monitor command execution time.

    Args:
        command_name: Name of the command being monitored

    Returns:
        Decorated function that logs execution time
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
                logger.info(
                    f"Command '{command_name}' completed in {elapsed_time:.2f}ms"
                )
                return result
            except Exception as e:
                elapsed_time = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Command '{command_name}' failed after {elapsed_time:.2f}ms: {e}"
                )
                raise
        return wrapper
    return decorator


class PerformanceMetrics:
    """Track performance metrics for bot operations."""

    def __init__(self):
        """Initialize performance metrics tracker."""
        self.metrics = {
            "command_counts": {},
            "command_times": {},
            "errors": {},
        }

    def record_command(self, command_name: str, execution_time_ms: float, success: bool) -> None:
        """Record a command execution metric.

        Args:
            command_name: Name of the executed command
            execution_time_ms: Execution time in milliseconds
            success: Whether the command completed successfully
        """
        # Track counts
        if command_name not in self.metrics["command_counts"]:
            self.metrics["command_counts"][command_name] = {"total": 0, "success": 0, "errors": 0}
        
        self.metrics["command_counts"][command_name]["total"] += 1
        if success:
            self.metrics["command_counts"][command_name]["success"] += 1
        else:
            self.metrics["command_counts"][command_name]["errors"] += 1

        # Track execution times
        if command_name not in self.metrics["command_times"]:
            self.metrics["command_times"][command_name] = []
        
        self.metrics["command_times"][command_name].append(execution_time_ms)

    def get_stats(self, command_name: str) -> dict[str, Any]:
        """Get performance statistics for a specific command.

        Args:
            command_name: Name of the command

        Returns:
            Dictionary with performance statistics
        """
        if command_name not in self.metrics["command_times"]:
            return {}

        times = self.metrics["command_times"][command_name]
        counts = self.metrics["command_counts"][command_name]
        
        sorted_times = sorted(times)
        n = len(sorted_times)
        
        return {
            "total_executions": counts["total"],
            "successful": counts["success"],
            "errors": counts["errors"],
            "avg_time_ms": sum(times) / n if n > 0 else 0,
            "min_time_ms": sorted_times[0] if n > 0 else 0,
            "max_time_ms": sorted_times[-1] if n > 0 else 0,
            "p50_time_ms": sorted_times[n // 2] if n > 0 else 0,
            "p95_time_ms": sorted_times[int(n * 0.95)] if n > 0 else 0,
            "p99_time_ms": sorted_times[int(n * 0.99)] if n > 0 else 0,
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get performance statistics for all commands.

        Returns:
            Dictionary mapping command names to their statistics
        """
        stats = {}
        for command_name in self.metrics["command_counts"].keys():
            stats[command_name] = self.get_stats(command_name)
        return stats


# Global metrics instance
_metrics = PerformanceMetrics()


def get_metrics() -> PerformanceMetrics:
    """Get the global performance metrics instance.

    Returns:
        Global PerformanceMetrics instance
    """
    return _metrics
