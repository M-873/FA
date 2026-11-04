"""
Hardware detection, performance profile, and safety monitor package.
"""
from app.hardware.detector import HardwareSpecs, HardwareDetector
from app.hardware.thresholds import PROFILE_THRESHOLDS, ProfileThresholdCriteria
from app.hardware.profiles import (
    HardwareProfileLevel,
    HardwareProfileResult,
    HardwareProfileManager,
    PerformanceProfileLevel,
    PerformanceProfileManager,
    RenderSettings,
)
from app.hardware.monitor import HardwareSafetyMonitor

__all__ = [
    "HardwareSpecs",
    "HardwareDetector",
    "HardwareProfileLevel",
    "HardwareProfileResult",
    "HardwareProfileManager",
    "PerformanceProfileLevel",
    "PerformanceProfileManager",
    "RenderSettings",
    "HardwareSafetyMonitor",
    "PROFILE_THRESHOLDS",
    "ProfileThresholdCriteria",
]
