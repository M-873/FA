"""
app/hardware/profiles.py
========================
Deterministic Hardware Profile Selection Service.
Evaluates multi-attribute hardware telemetry and assigns one of:
- LEGACY_2GB
- LOW
- MEDIUM
- HIGH
- ULTRA

Strict Policies:
1. MX110 with ~2GB dedicated VRAM and 8GB RAM must be classified as LEGACY_2GB.
2. LEGACY_2GB must explicitly disable local Ollama installation and heavy local AI video generation.
3. GPU model alone must never qualify a system for a high profile.
   System RAM, CPU threads, and dedicated VRAM are all strictly enforced.
4. If hardware data is incomplete, a conservative profile is chosen and flagged as provisional.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.hardware.detector import HardwareSpecs
from app.hardware.thresholds import PROFILE_THRESHOLDS, ProfileThresholdCriteria
from app.utils.logging import logger


class HardwareProfileLevel(str, Enum):
    LEGACY_2GB = "LEGACY_2GB"
    LEGACY_LOW = "LEGACY_2GB"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    ULTRA = "ULTRA"


# Backward compatibility aliases
PerformanceProfileLevel = HardwareProfileLevel


class RenderSettings(BaseModel):
    """Rendering configuration parameters derived from performance profile."""
    resolution_width: int = Field(default=720, description="Video width in pixels")
    resolution_height: int = Field(default=1280, description="Video height in pixels")
    fps: int = Field(default=24, description="Target frames per second")
    codec_preset: str = Field(default="ultrafast", description="FFmpeg encoding speed preset")
    crf: int = Field(default=26, description="Constant Rate Factor for x264 video quality")
    max_duration_seconds: int = Field(default=15, description="Maximum video animation duration ceiling in seconds")
    sequential_processing: bool = Field(default=True, description="Strict single-job sequential processing")


class HardwareProfileResult(BaseModel):
    """Detailed profile classification result with explanatory rationale."""

    profile: str = Field(description="Selected profile level e.g. LEGACY_2GB, LOW, MEDIUM, HIGH, ULTRA")
    reason: str = Field(description="Clear, human-readable rationale explaining why this profile was chosen")
    is_provisional: bool = Field(default=False, description="True if classification is based on incomplete telemetry")
    local_ai_eligible: bool = Field(default=False, description="Whether host is eligible for local Ollama in future phases")
    recommended_mode: str = Field(description="Recommended execution architecture: Cloud API or Local")
    bottlenecks: List[str] = Field(default_factory=list, description="Identified hardware bottlenecks")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic threshold details")
    render_settings: Optional[RenderSettings] = Field(default=None, description="Rendering parameters derived from profile")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class HardwareProfileManager:
    """
    Evaluates HardwareSpecs against deterministic criteria and assigns profiles.
    """

    @classmethod
    def _get_render_settings_for_profile(cls, profile_name: str) -> RenderSettings:
        prof_upper = str(profile_name).upper()
        if "LEGACY" in prof_upper or prof_upper == "LOW":
            return RenderSettings(resolution_width=720, resolution_height=1280, fps=24, codec_preset="ultrafast", crf=28)
        elif prof_upper == "MEDIUM":
            return RenderSettings(resolution_width=1080, resolution_height=1920, fps=30, codec_preset="medium", crf=23)
        elif prof_upper == "HIGH":
            return RenderSettings(resolution_width=1080, resolution_height=1920, fps=30, codec_preset="fast", crf=20)
        else:  # ULTRA
            return RenderSettings(resolution_width=1080, resolution_height=1920, fps=60, codec_preset="fast", crf=20)

    @classmethod
    def determine_profile(
        cls,
        specs: HardwareSpecs,
        override_profile: str = "AUTO",
    ) -> HardwareProfileResult:
        """
        Classifies host hardware and returns a HardwareProfileResult.
        """
        if override_profile and override_profile.upper() != "AUTO":
            try:
                prof_enum = HardwareProfileLevel(override_profile.upper())
                crit = PROFILE_THRESHOLDS[prof_enum.value]
                return HardwareProfileResult(
                    profile=prof_enum.value,
                    reason=f"Manual configuration override forced profile to '{prof_enum.value}'.",
                    is_provisional=False,
                    local_ai_eligible=crit.local_ai_eligible,
                    recommended_mode=crit.recommended_mode,
                    bottlenecks=[],
                    details={"manual_override": True},
                    render_settings=cls._get_render_settings_for_profile(prof_enum.value),
                )
            except ValueError:
                logger.warning(f"Invalid override profile '{override_profile}'. Falling back to AUTO.")

        result = cls._classify(specs)
        if not result.render_settings:
            result.render_settings = cls._get_render_settings_for_profile(result.profile)
        return result

    @classmethod
    def _classify(cls, specs: HardwareSpecs) -> HardwareProfileResult:
        bottlenecks: List[str] = []
        is_provisional = False

        # Extract telemetry
        vram = specs.vram_mb
        ram_total = specs.ram_total_gb
        ram_avail = specs.ram_available_gb
        cpu_threads = specs.cpu_threads
        disk_free = specs.disk_free_gb
        gpu_name = specs.gpu_name
        gpu_lower = gpu_name.lower()
        cuda_ok = specs.cuda_available and specs.nvidia_gpu_present

        # ----------------------------------------------------------------------
        # Rule 1: Missing or Incomplete Hardware Telemetry (Provisional)
        # ----------------------------------------------------------------------
        if vram is None or specs.detection_status == "FAILED" or gpu_name == "Unknown":
            is_provisional = True
            bottlenecks.append("Dedicated GPU VRAM could not be confirmed.")

            # Conservative assignment based solely on confirmed system RAM
            if ram_total <= 8.5:
                prof = HardwareProfileLevel.LEGACY_2GB.value
                reason = (
                    f"Provisional classification: Dedicated VRAM unavailable. "
                    f"Conservatively assigned to '{prof}' based on {ram_total:.1f} GB system RAM "
                    "to prevent system instability."
                )
            else:
                prof = HardwareProfileLevel.LOW.value
                reason = (
                    f"Provisional classification: Dedicated VRAM unavailable. "
                    f"Assigned to '{prof}' based on {ram_total:.1f} GB system RAM. "
                    "Cloud-first pipeline recommended."
                )

            crit = PROFILE_THRESHOLDS[prof]
            return HardwareProfileResult(
                profile=prof,
                reason=reason,
                is_provisional=True,
                local_ai_eligible=crit.local_ai_eligible,
                recommended_mode=crit.recommended_mode,
                bottlenecks=bottlenecks,
                details={"provisional_reason": "Missing VRAM / GPU data"},
            )

        # ----------------------------------------------------------------------
        # Rule 2: Target Hardware MX110 with ~2GB VRAM + ~8GB RAM -> LEGACY_2GB
        # ----------------------------------------------------------------------
        is_mx110_target = (
            ("mx110" in gpu_lower or "mx130" in gpu_lower or "mx150" in gpu_lower or "920m" in gpu_lower or "940m" in gpu_lower)
            or (vram <= 2048)
            or (ram_total <= 8.5 and vram <= 4096)
        )

        if is_mx110_target:
            prof = HardwareProfileLevel.LEGACY_2GB.value
            crit = PROFILE_THRESHOLDS[prof]

            reasons: List[str] = []
            if "mx110" in gpu_lower:
                reasons.append("NVIDIA GeForce MX110 target GPU detected")
            if vram <= 2048:
                reasons.append(f"{vram} MB dedicated VRAM")
                bottlenecks.append(f"Low dedicated VRAM ({vram} MB)")
            if ram_total <= 8.5:
                reasons.append(f"{ram_total:.1f} GB system RAM")
                bottlenecks.append(f"Limited system RAM ({ram_total:.1f} GB)")
            if ram_avail < 2.0:
                bottlenecks.append(f"Low currently available RAM ({ram_avail:.1f} GB)")

            joined_reasons = ", ".join(reasons) if reasons else f"{gpu_name} ({vram} MB VRAM)"
            reason = (
                f"Target Low-Resource Hardware ({joined_reasons}). "
                "Classified as LEGACY_2GB. Local Ollama and heavy AI video rendering strictly disabled."
            )

            return HardwareProfileResult(
                profile=prof,
                reason=reason,
                is_provisional=False,
                local_ai_eligible=False,
                recommended_mode=crit.recommended_mode,
                bottlenecks=bottlenecks,
                details={"target_match": "MX110_2GB"},
            )

        # ----------------------------------------------------------------------
        # Rule 3: Multi-attribute Deterministic Classification (ULTRA -> HIGH -> MEDIUM -> LOW)
        # GPU model alone NEVER qualifies a system. System RAM, CPU, and Disk are enforced.
        # ----------------------------------------------------------------------
        levels = [
            ("ULTRA", PROFILE_THRESHOLDS["ULTRA"]),
            ("HIGH", PROFILE_THRESHOLDS["HIGH"]),
            ("MEDIUM", PROFILE_THRESHOLDS["MEDIUM"]),
            ("LOW", PROFILE_THRESHOLDS["LOW"]),
        ]

        for lvl_name, crit in levels:
            rejection_reasons: List[str] = []

            # Check VRAM
            if vram < crit.min_vram_mb:
                rejection_reasons.append(f"VRAM {vram}MB < {crit.min_vram_mb}MB")

            # Check System RAM (Critical: GPU alone must not qualify!)
            if ram_total < crit.min_system_ram_gb:
                rejection_reasons.append(f"System RAM {ram_total:.1f}GB < {crit.min_system_ram_gb:.1f}GB")

            # Check Available RAM
            if ram_avail < crit.min_available_ram_gb:
                rejection_reasons.append(f"Available RAM {ram_avail:.1f}GB < {crit.min_available_ram_gb:.1f}GB")

            # Check CPU Logical Threads
            if cpu_threads < crit.min_cpu_threads:
                rejection_reasons.append(f"CPU Threads {cpu_threads} < {crit.min_cpu_threads}")

            # Check Free Disk Space
            if disk_free < crit.min_disk_free_gb:
                rejection_reasons.append(f"Free Disk {disk_free:.1f}GB < {crit.min_disk_free_gb:.1f}GB")

            # Check CUDA if required
            if crit.requires_cuda and not cuda_ok:
                rejection_reasons.append("CUDA/NVIDIA support required")

            if not rejection_reasons:
                # All criteria satisfied!
                reason = (
                    f"Qualified for {lvl_name}: {gpu_name} ({vram} MB VRAM), "
                    f"{ram_total:.1f} GB RAM ({ram_avail:.1f} GB free), {cpu_threads} CPU threads, "
                    f"and {disk_free:.1f} GB free disk space."
                )
                return HardwareProfileResult(
                    profile=lvl_name,
                    reason=reason,
                    is_provisional=False,
                    local_ai_eligible=crit.local_ai_eligible,
                    recommended_mode=crit.recommended_mode,
                    bottlenecks=[],
                    details={"matched_criteria": lvl_name},
                )
            else:
                # Log bottleneck causing disqualification from this tier
                if vram >= crit.min_vram_mb and ram_total < crit.min_system_ram_gb:
                    bottlenecks.append(
                        f"System RAM bottleneck: GPU qualifies for {lvl_name} ({vram} MB), "
                        f"but system RAM ({ram_total:.1f} GB) is below the {crit.min_system_ram_gb:.1f} GB threshold."
                    )

        # ----------------------------------------------------------------------
        # Fallback to LOW if VRAM > 2048 but missed other constraints
        # ----------------------------------------------------------------------
        crit_low = PROFILE_THRESHOLDS["LOW"]
        prof = HardwareProfileLevel.LOW.value
        bottleneck_summary = "; ".join(bottlenecks) if bottlenecks else "Entry-level hardware configuration."
        reason = (
            f"Assigned to {prof}: {gpu_name} ({vram} MB VRAM, {ram_total:.1f} GB RAM). "
            f"Stability prioritized. {bottleneck_summary}"
        )

        return HardwareProfileResult(
            profile=prof,
            reason=reason,
            is_provisional=False,
            local_ai_eligible=crit_low.local_ai_eligible,
            recommended_mode=crit_low.recommended_mode,
            bottlenecks=bottlenecks,
            details={"fallback": "LOW"},
        )


# Backward compatibility alias
PerformanceProfileManager = HardwareProfileManager
