import pytest
from app.hardware.detector import HardwareDetector, HardwareSpecs
from app.hardware.profiles import (
    PerformanceProfileManager,
    PerformanceProfileLevel,
    HardwareProfileManager,
    HardwareProfileLevel,
)
from app.hardware.monitor import HardwareSafetyMonitor
from app.ui.settings import SettingsManager


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
    assert res["render_settings"].crf == 28


def test_profile_classification_high():
    detector = HardwareDetector(mock_profile="HIGH_8GB")
    specs = detector.detect()
    res = PerformanceProfileManager.determine_profile(specs)
    assert res["profile"] == PerformanceProfileLevel.HIGH.value
    assert res["render_settings"].resolution_width == 1080
    assert res["render_settings"].resolution_height == 1920
    assert res["render_settings"].fps == 60
    assert res["render_settings"].crf == 20


def test_hardware_memory_monitor():
    mem_health = HardwareSafetyMonitor.check_memory_health()
    assert "available_mb" in mem_health
    assert "is_critical" in mem_health


@pytest.mark.parametrize(
    "vram_mb,expected_profile",
    [
        (2048, "LEGACY_2GB"),
        (4096, "LOW"),
        (7900, "HIGH"),
        (8151, "HIGH"),
        (12288, "ULTRA"),
    ],
)
def test_tolerant_vram_thresholds_simulation(vram_mb, expected_profile):
    """
    Simulates various VRAM values (2048, 4096, 7900, 8151, 12288) to verify
    tolerant classification, ensuring real-world GPUs like RTX 5060 (8151 MB)
    qualify for HIGH rather than falling back to MEDIUM.
    """
    specs = HardwareSpecs(
        gpu_name="Simulated GPU",
        gpu_vendor="NVIDIA",
        vram_mb=vram_mb,
        ram_total_gb=32.0,
        ram_available_gb=16.0,
        cpu_name="Simulated Fast CPU",
        cpu_cores=8,
        cpu_threads=16,
        disk_total_gb=500.0,
        disk_free_gb=100.0,
        cuda_available=True,
        nvidia_gpu_present=True,
        detection_status="DETECTED",
    )
    result = HardwareProfileManager.determine_profile(specs)
    assert result.profile == expected_profile


def test_manual_profile_override_in_settings(tmp_path):
    """
    Verifies that the manual override setting defaults to 'auto' and can force
    low, medium, high, or ultra regardless of detected hardware.
    """
    test_settings_path = str(tmp_path / "app_settings.json")
    mgr = SettingsManager(filepath=test_settings_path)

    # Default override must be 'auto'
    assert mgr.get_hardware_profile_override() == "auto"

    # Simulated high-end specs (would normally qualify for HIGH)
    specs = HardwareSpecs(
        gpu_name="NVIDIA GeForce RTX 5060",
        gpu_vendor="NVIDIA",
        vram_mb=8151,
        ram_total_gb=32.0,
        ram_available_gb=16.0,
        cpu_threads=16,
        disk_free_gb=100.0,
        cuda_available=True,
        nvidia_gpu_present=True,
        detection_status="DETECTED",
    )

    # 1. AUTO mode -> HIGH (due to tolerant threshold)
    auto_res = HardwareProfileManager.determine_profile(specs, override_profile=mgr.get_hardware_profile_override())
    assert auto_res.profile == "HIGH"

    # 2. Manual override: LOW
    mgr.set_hardware_profile_override("low")
    assert mgr.get_hardware_profile_override() == "low"
    low_res = HardwareProfileManager.determine_profile(specs, override_profile=mgr.get_hardware_profile_override())
    assert low_res.profile == "LOW"
    assert low_res.details.get("manual_override") is True
    assert low_res.render_settings.resolution_width == 720

    # 3. Manual override: MEDIUM
    mgr.set_hardware_profile_override("medium")
    med_res = HardwareProfileManager.determine_profile(specs, override_profile=mgr.get_hardware_profile_override())
    assert med_res.profile == "MEDIUM"
    assert med_res.render_settings.fps == 30

    # 4. Manual override: HIGH
    mgr.set_hardware_profile_override("high")
    high_res = HardwareProfileManager.determine_profile(specs, override_profile=mgr.get_hardware_profile_override())
    assert high_res.profile == "HIGH"
    assert high_res.render_settings.fps == 60
