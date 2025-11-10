"""Resource monitoring utility for tracking bot memory and system usage."""

import logging
import os

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor process resource usage (memory, file descriptors)."""

    def __init__(self):
        """Initialize resource monitor."""
        if PSUTIL_AVAILABLE:
            self.process = psutil.Process(os.getpid())
        else:
            logger.warning("psutil not available - resource monitoring disabled")
            self.process = None

    def get_memory_usage(self) -> dict[str, float]:
        """Get current memory usage in MB.

        Returns:
            Dictionary with 'rss_mb' (Resident Set Size) and 'vms_mb' (Virtual Memory Size)
            Returns zeros if psutil not available.
        """
        if not self.process:
            return {"rss_mb": 0.0, "vms_mb": 0.0}

        try:
            mem = self.process.memory_info()
            return {
                "rss_mb": mem.rss / 1024 / 1024,  # Resident Set Size (actual RAM used)
                "vms_mb": mem.vms / 1024 / 1024,  # Virtual Memory Size
            }
        except Exception as e:
            logger.error(f"Failed to get memory usage: {e}", exc_info=True)
            return {"rss_mb": 0.0, "vms_mb": 0.0}

    def get_fd_count(self) -> int:
        """Get current file descriptor count.

        Returns:
            Number of open file descriptors, or 0 if not available
        """
        if not self.process:
            return 0

        try:
            # num_fds() is Linux/macOS only
            if hasattr(self.process, 'num_fds'):
                return self.process.num_fds()
            else:
                # Windows alternative - count handles
                return len(self.process.open_files())
        except Exception as e:
            logger.debug(f"Could not get FD count: {e}")
            return 0

    def log_stats(self, context: str = "") -> None:
        """Log current resource usage.

        Args:
            context: Optional context string for the log message
        """
        if not PSUTIL_AVAILABLE:
            logger.debug("Resource monitoring disabled (psutil not installed)")
            return

        try:
            mem = self.get_memory_usage()
            fd_count = self.get_fd_count()

            context_str = f" ({context})" if context else ""
            logger.info(
                f"Resource usage{context_str}: "
                f"RSS={mem['rss_mb']:.1f}MB, "
                f"VMS={mem['vms_mb']:.1f}MB, "
                f"FDs={fd_count}"
            )
        except Exception as e:
            logger.error(f"Failed to log resource stats: {e}", exc_info=True)

    def check_memory_threshold(self, warning_mb: float = 100.0, critical_mb: float = 120.0) -> None:
        """Check if memory usage exceeds thresholds and log warnings.

        Args:
            warning_mb: Warning threshold in MB (default: 100MB)
            critical_mb: Critical threshold in MB (default: 120MB)
        """
        if not PSUTIL_AVAILABLE:
            return

        try:
            mem = self.get_memory_usage()
            rss_mb = mem['rss_mb']

            if rss_mb > critical_mb:
                logger.critical(
                    f"CRITICAL: Memory usage {rss_mb:.1f}MB exceeds critical threshold {critical_mb}MB! "
                    f"Bot may be killed by host."
                )
            elif rss_mb > warning_mb:
                logger.warning(
                    f"WARNING: Memory usage {rss_mb:.1f}MB exceeds warning threshold {warning_mb}MB"
                )
        except Exception as e:
            logger.error(f"Failed to check memory threshold: {e}", exc_info=True)


# Singleton instance
_monitor = None


def get_resource_monitor() -> ResourceMonitor:
    """Get the singleton ResourceMonitor instance.

    Returns:
        ResourceMonitor instance
    """
    global _monitor
    if _monitor is None:
        _monitor = ResourceMonitor()
    return _monitor
