"""
tests/test_hardware_detection.py
================================
Comprehensive automated test suite for Phase 2:
- MX110 + 2 GB VRAM + 8 GB RAM -> LEGACY_2GB (local Ollama strictly disabled)
- Low-memory systems
- Medium hardware
- High GPU with insufficient system RAM (downgraded, GPU alone never qualifies)
- Unknown GPU or unavailable VRAM (conservative provisional classification)
- Missing NVIDIA utilities (graceful fallback, no crash)
- Missing PowerShell/WMI (safe fallbacks, no crash)
- Detection timeouts (timeout handling, no hang)
- Profile selection with insufficient data
- Settings persistence (caching, retain last known result with timestamp)
- Regression tests for Phase 1 toggles, URL validation, and mock job queue
"""

import json
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
import pytest

from app.hardware.detector import HardwareDetector, HardwareSpecs
from app.hardware.profiles import (
    HardwareProfileManager,
    HardwareProfileLevel,
    HardwareProfileResult,
)
from app.hardware.thresholds import PROFILE_THRESHOLDS
from app.ui.settings import (
    load_settings,
    save_settings,
    get_hardware_report,
    save_hardware_report,
)
from app.facebook.reels import ReelsWorkflowService


# ==============================================================================
# 1. HARDWARE PROFILES DETERMINISTIC SELECTION TESTS
# ==============================================================================

def test_mx110_target_profile():
    """
    Primary Target Hardware:
    - NVIDIA GeForce MX110
    - 2 GB dedicated VRAM
    - 8 GB system RAM
    - Intel Core i5 7th gen
    Must classify as LEGACY_2GB, local_ai_eligible=False, heavy local AI disabled.
    """
    specs = HardwareSpecs(
        gpu_name="NVIDIA GeForce MX110",
        gpu_vendor="NVIDIA",
        vram_mb=2048,
        ram_total_gb=7.89,
        ram_available_gb=1.5,
        cpu_name="Intel(R) Core(TM) i5-7200U CPU @ 2.50GHz",
        cpu_cores=2,
        cpu_threads=4,
        cpu_arch="AMD64",
        windows_version="Windows 10 Home (Build 19045)",
        disk_total_gb=237.7,
        disk_free_gb=80.0,
        driver_version="531.79",
        cuda_available=True,
        nvidia_gpu_present=True,
        detection_status="DETECTED",
    )

    result = HardwareProfileManager.determine_profile(specs)

    assert result.profile == HardwareProfileLevel.LEGACY_2GB.value
    assert result.local_ai_eligible is False
    assert result.is_provisional is False
    assert "LEGACY_2GB" in result.reason
    assert "Ollama" in result.reason or "disabled" in result.reason.lower()
    # Check bottlenecks identified
    assert any("VRAM" in b for b in result.bottlenecks)
    assert any("RAM" in b for b in result.bottlenecks)


def test_low_memory_system():
    """
    Low memory systems (e.g., 4GB RAM, integrated GPU or low VRAM)
    must select LEGACY_2GB and have local AI strictly disabled.
    """
    specs = HardwareSpecs(
        gpu_name="Intel(R) HD Graphics 620",
        gpu_vendor="Intel",
        vram_mb=128,
        ram_total_gb=4.0,
        ram_available_gb=0.8,
        cpu_name="Intel(R) Core(TM) i3-7100U",
        cpu_cores=2,
        cpu_threads=4,
        disk_free_gb=15.0,
        detection_status="DETECTED",
    )

    result = HardwareProfileManager.determine_profile(specs)

    assert result.profile == HardwareProfileLevel.LEGACY_2GB.value
    assert result.local_ai_eligible is False
    assert len(result.bottlenecks) > 0


def test_medium_hardware():
    """
    Medium hardware:
    - 6 GB VRAM
    - 16 GB system RAM
    - 8 logical threads
    - CUDA confirmed
    Must qualify for MEDIUM profile.
    """
    specs = HardwareSpecs(
        gpu_name="NVIDIA GeForce RTX 2060",
        gpu_vendor="NVIDIA",
        vram_mb=6144,
        ram_total_gb=16.0,
        ram_available_gb=9.5,
        cpu_name="AMD Ryzen 5 3600",
        cpu_cores=6,
        cpu_threads=12,
        disk_free_gb=120.0,
        driver_version="546.17",
        cuda_available=True,
        nvidia_gpu_present=True,
        detection_status="DETECTED",
    )

    result = HardwareProfileManager.determine_profile(specs)

    assert result.profile == HardwareProfileLevel.MEDIUM.value
    assert result.local_ai_eligible is True
    assert result.is_provisional is False


def test_high_gpu_with_insufficient_system_ram():
    """
    POLICY: GPU model alone must NEVER qualify a system for a high profile.
    High GPU (RTX 4080 with 16GB VRAM) but only 8 GB system RAM.
    Must be downgraded and disqualified from HIGH/ULTRA.
    """
    specs = HardwareSpecs(
        gpu_name="NVIDIA GeForce RTX 4080",
        gpu_vendor="NVIDIA",
        vram_mb=16384,
        ram_total_gb=8.0,  # Insufficient for HIGH (requires 32 GB) or ULTRA (requires 64 GB)
        ram_available_gb=2.0,
        cpu_name="Intel Core i7-13700K",
        cpu_cores=8,
        cpu_threads=16,
        disk_free_gb=200.0,
        driver_version="551.23",
        cuda_available=True,
        nvidia_gpu_present=True,
        detection_status="DETECTED",
    )

    result = HardwareProfileManager.determine_profile(specs)

    # Must NOT be HIGH or ULTRA
    assert result.profile not in [HardwareProfileLevel.HIGH.value, HardwareProfileLevel.ULTRA.value]
    # Rationale or bottlenecks must document the RAM bottleneck
    assert any("RAM bottleneck" in b or "system RAM" in b for b in result.bottlenecks)


def test_unknown_gpu_or_unavailable_vram():
    """
    When GPU is Unknown or dedicated VRAM is None, classification must be
    provisional (is_provisional=True) and select a conservative profile.
    """
    specs = HardwareSpecs(
        gpu_name="Unknown",
        gpu_vendor="Unknown",
        vram_mb=None,
        ram_total_gb=8.0,
        ram_available_gb=3.0,
        cpu_name="Intel Core i5",
        cpu_threads=4,
        disk_free_gb=40.0,
        detection_status="PARTIAL",
    )

    result = HardwareProfileManager.determine_profile(specs)

    assert result.is_provisional is True
    assert result.profile in [HardwareProfileLevel.LEGACY_2GB.value, HardwareProfileLevel.LOW.value]
    assert "Provisional" in result.reason
    assert any("VRAM" in b for b in result.bottlenecks)


def test_profile_selection_with_insufficient_data():
    """
    When detection fails or telemetry is completely missing,
    must choose a conservative fallback profile safely.
    """
    specs = HardwareSpecs(
        gpu_name="Unknown",
        vram_mb=None,
        ram_total_gb=0.0,
        ram_available_gb=0.0,
        cpu_threads=1,
        disk_free_gb=0.0,
        detection_status="FAILED",
    )

    result = HardwareProfileManager.determine_profile(specs)

    assert result.profile == HardwareProfileLevel.LEGACY_2GB.value
    assert result.is_provisional is True
    assert result.local_ai_eligible is False


# ==============================================================================
# 2. HARDWARE DETECTOR COMMAND HANDLING & SAFE FALLBACKS
# ==============================================================================

def test_missing_nvidia_utilities():
    """
    When nvidia-smi is missing (FileNotFoundError or non-zero exit),
    HardwareDetector must not crash and must return clean specs.
    """
    def mock_runner_no_nvidia(cmd: List[str], timeout: float = 3.0) -> Tuple[int, str, str]:
        if "nvidia-smi" in cmd[0]:
            raise FileNotFoundError("nvidia-smi not found in PATH")
        return 0, "", ""

    detector = HardwareDetector(command_runner=mock_runner_no_nvidia)
    specs = detector.detect()

    # Must complete without unhandled exception
    assert isinstance(specs, HardwareSpecs)
    # Hardware specs must be populated safely
    assert specs.ram_total_gb >= 0.0
    assert specs.detection_status in ["DETECTED", "PARTIAL"]


def test_missing_powershell_and_wmi():
    """
    When PowerShell or WMI are completely unavailable or fail,
    HardwareDetector must fall back to standard library / ctypes.
    """
    def mock_runner_no_ps(cmd: List[str], timeout: float = 3.0) -> Tuple[int, str, str]:
        raise subprocess.SubprocessError("PowerShell is disabled by policy")

    detector = HardwareDetector(command_runner=mock_runner_no_ps)
    specs = detector.detect()

    assert isinstance(specs, HardwareSpecs)
    # RAM and CPU should still be detected via ctypes / os.cpu_count
    assert specs.cpu_threads >= 1
    assert specs.ram_total_gb > 0.0


def test_detection_timeout_handling():
    """
    When an external command hangs or exceeds the 3-second timeout,
    HardwareDetector must cleanly abort the command and continue.
    """
    def mock_runner_timeout(cmd: List[str], timeout: float = 3.0) -> Tuple[int, str, str]:
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    detector = HardwareDetector(command_runner=mock_runner_timeout)
    specs = detector.detect()

    assert isinstance(specs, HardwareSpecs)
    assert any("timed out" in note.lower() for note in specs.detection_notes)


def test_mock_profiles_support():
    """
    Verify HardwareDetector's deterministic mock profile loader.
    """
    mx110_detector = HardwareDetector(mock_profile="MX110_2GB")
    specs = mx110_detector.detect()
    assert specs.gpu_name == "NVIDIA GeForce MX110"
    assert specs.vram_mb == 2048
    assert specs.ram_total_gb == 8.0

    high_detector = HardwareDetector(mock_profile="HIGH_8GB")
    specs_high = high_detector.detect()
    assert specs_high.gpu_name == "NVIDIA GeForce RTX 3070"
    assert specs_high.vram_mb == 8192


# ==============================================================================
# 3. SETTINGS PERSISTENCE & HARDWARE REPORT CACHING
# ==============================================================================

def test_settings_persistence_and_hardware_report():
    """
    Verify that save_hardware_report properly persists telemetry to JSON
    without corrupting daily_auto_post or link_to_reels settings.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        # Initial save with Phase 1 toggles
        initial_data = {
            "daily_auto_post": {"enabled": True, "status": "ON"},
            "link_to_reels": {"enabled": False, "status": "OFF"},
            "mock_reels_jobs": [{"id": "job_1", "status": "QUEUED"}],
        }
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        mock_specs = {
            "gpu_name": "NVIDIA GeForce MX110",
            "vram_mb": 2048,
            "ram_total_gb": 8.0,
            "detection_status": "DETECTED",
        }
        mock_profile = {
            "profile": "LEGACY_2GB",
            "reason": "Target low-end configuration",
            "is_provisional": False,
        }

        # Save hardware report
        saved = save_hardware_report(mock_specs, mock_profile, settings_path=temp_path)
        assert saved is True

        # Read back
        loaded = get_hardware_report(settings_path=temp_path)
        assert loaded is not None
        assert loaded["specs"]["gpu_name"] == "NVIDIA GeForce MX110"
        assert loaded["specs"]["vram_mb"] == 2048
        assert loaded["profile"]["profile"] == "LEGACY_2GB"

        # Verify Phase 1 settings were NOT altered
        all_settings = load_settings(temp_path)
        assert all_settings["daily_auto_post"]["enabled"] is True
        assert all_settings["link_to_reels"]["enabled"] is False
        assert len(all_settings["mock_reels_jobs"]) == 1
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ==============================================================================
# 4. REGRESSION TESTS: PHASE 1 TOGGLES, URL VALIDATION & JOB QUEUE
# ==============================================================================

def test_phase1_independent_toggles():
    """
    Verify Daily Auto Post and Link to Reels toggles operate independently.
    """
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        settings = load_settings(temp_path)
        assert settings["daily_auto_post"]["enabled"] is False
        assert settings["link_to_reels"]["enabled"] is False

        # Toggle DAP ON
        settings["daily_auto_post"]["enabled"] = True
        settings["daily_auto_post"]["status"] = "ON"
        save_settings(settings, temp_path)

        reloaded = load_settings(temp_path)
        assert reloaded["daily_auto_post"]["enabled"] is True
        assert reloaded["link_to_reels"]["enabled"] is False

        # Toggle LTR ON
        reloaded["link_to_reels"]["enabled"] = True
        save_settings(reloaded, temp_path)

        reloaded2 = load_settings(temp_path)
        assert reloaded2["daily_auto_post"]["enabled"] is True
        assert reloaded2["link_to_reels"]["enabled"] is True
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_phase1_url_validation():
    """
    Verify video URL validation rules for Link to Reels.
    """
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://vimeo.com/76979871",
        "http://example.com/video.mp4",
    ]
    for url in valid_urls:
        valid, msg = ReelsWorkflowService.validate_video_url(url)
        assert valid is True, f"Expected {url} to be valid, got: {msg}"

    invalid_urls = [
        "",
        "   ",
        "not-a-url",
        "ftp://example.com/file",
        "www.youtube.com/watch",  # Missing scheme
    ]
    for url in invalid_urls:
        valid, msg = ReelsWorkflowService.validate_video_url(url)
        assert valid is False, f"Expected {url} to be invalid"


def test_phase1_mock_job_queue():
    """
    Verify adding mock jobs and job queue integrity.
    """
    service = ReelsWorkflowService()
    job = service.create_job("https://www.youtube.com/watch?v=sample123")

    assert job is not None
    assert job["id"].startswith("reel_job_")
    assert job["status"] == "QUEUED"
    assert job["progress"] == 0

    all_jobs = service.get_all_jobs()
    assert any(j["id"] == job["id"] for j in all_jobs)
