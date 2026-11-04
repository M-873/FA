import gc
import sys
from typing import Dict, Any
from app.utils.logging import logger


class HardwareSafetyMonitor:
    """Monitors system memory pressure and enforces hardware safety for low-spec systems."""

    @classmethod
    def check_memory_health(self) -> Dict[str, Any]:
        """Checks available RAM and logs warnings if memory pressure is critical."""
        available_mb = 1024  # Default fallback assumption (1GB available)
        try:
            import psutil
            mem = psutil.virtual_memory()
            available_mb = mem.available // (1024 * 1024)
        except Exception:
            pass

        is_critical = available_mb < 500
        if is_critical:
            logger.warning(f"[MEMORY WARNING] Low system RAM detected! Available: {available_mb}MB. Purging garbage collector...")
            self.purge_resources()

        return {
            "available_mb": available_mb,
            "is_critical": is_critical,
        }

    @classmethod
    def purge_resources(self):
        """Triggers Python garbage collection to release unreferenced memory."""
        gc.collect()
        logger.info("Executed system resource cleanup and garbage collection.")
