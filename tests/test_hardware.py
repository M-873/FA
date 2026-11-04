from app.hardware.detector import HardwareDetector
from app.hardware.profiles import PerformanceProfileManager, PerformanceProfileLevel
from app.hardware.monitor import HardwareSafetyMonitor


def test_hardware_detector_mock_mx110():
    detector = HardwareDetector(mock_profile="MX110_2GB")
    specs = detector.detect()
    assert specs.gpu_name == "NVIDIA GeForce MX110"
    assert specs.vram_mb == 2048
    assert specs.ram_gb == 8.0


def test_profile_classification_mx110():
    detector = HardwareDetector(mock_profile="MX110_2GB")
    specs = detector.detect()
    res = PerformanceProfileManager.determine_profile(specs)
    assert res["profile"] == PerformanceProfileLevel.LEGACY_LOW.value
    assert res["render_settings"].resolution_width == 720
    assert res["render_settings"].resolution_height == 1280
    assert res["render_settings"].fps == 24


def test_profile_classification_high():
    detector = HardwareDetector(mock_profile="HIGH_8GB")
    specs = detector.detect()
    res = PerformanceProfileManager.determine_profile(specs)
    assert res["profile"] == PerformanceProfileLevel.HIGH.value
    assert res["render_settings"].resolution_width == 1080
    assert res["render_settings"].resolution_height == 1920
    assert res["render_settings"].fps == 60


def test_hardware_memory_monitor():
    mem_health = HardwareSafetyMonitor.check_memory_health()
    assert "available_mb" in mem_health
    assert "is_critical" in mem_health
