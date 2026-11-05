"""
app/hardware/thresholds.py
==========================
Configurable hardware profile thresholds and classification policies.
Defines criteria for:
- LEGACY_2GB
- LOW
- MEDIUM
- HIGH
- ULTRA

Key Policy Rules:
1. MX110 with ~2GB dedicated VRAM and 8GB RAM must be classified as LEGACY_2GB.
2. LEGACY_2GB explicitly disables local Ollama and heavy local AI video generation.
3. GPU model alone must never qualify a system for a high profile.
   System RAM, CPU threads, and dedicated VRAM must all satisfy profile requirements.
4. If hardware data is incomplete (e.g. VRAM unknown), a conservative provisional
   profile is selected.
5. VRAM thresholds use tolerant values to accommodate binary/WDDM reporting disparities
   (e.g. 8GB GPUs reporting ~8151 MB, 12GB GPUs reporting ~12000 MB, etc.).
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class ProfileThresholdCriteria:
    """Threshold constraints required to achieve a hardware profile level."""
    min_vram_mb: int
    min_system_ram_gb: float
    min_available_ram_gb: float
    min_cpu_threads: int
    min_disk_free_gb: float
    requires_cuda: bool
    local_ai_eligible: bool
    recommended_mode: str
    description: str


# Threshold specifications for deterministic classification
# Tolerant VRAM thresholds account for WDDM / binary MB reporting variations
PROFILE_THRESHOLDS: Dict[str, ProfileThresholdCriteria] = {
    "ULTRA": ProfileThresholdCriteria(
        min_vram_mb=11500,         # 12 GB+ dedicated VRAM (e.g. RTX 4080, 4090, 3090, often reported as ~12100-12288 MB)
        min_system_ram_gb=32.0,    # 32 GB system RAM
        min_available_ram_gb=16.0, # At least 16 GB currently free
        min_cpu_threads=12,        # 12+ logical cores
        min_disk_free_gb=50.0,     # 50 GB free disk
        requires_cuda=True,
        local_ai_eligible=True,
        recommended_mode="Local High-Precision AI & Ultra 60fps Master Rendering",
        description="High-end workstation capable of local large LLMs and unconstrained rendering.",
    ),
    "HIGH": ProfileThresholdCriteria(
        min_vram_mb=7500,          # 8 GB dedicated VRAM (e.g. RTX 5060, 4060, 4070, 3070, reported as ~8151-8192 MB)
        min_system_ram_gb=16.0,    # 16 GB system RAM
        min_available_ram_gb=8.0,  # At least 8 GB currently free
        min_cpu_threads=8,         # 8+ logical cores
        min_disk_free_gb=30.0,     # 30 GB free disk
        requires_cuda=True,
        local_ai_eligible=True,
        recommended_mode="Local Standard AI & High-Definition 30/60fps Rendering",
        description="Modern gaming/creator PC capable of medium local models and parallel processing.",
    ),
    "MEDIUM": ProfileThresholdCriteria(
        min_vram_mb=5500,          # 6 GB dedicated VRAM (RTX 2060, RTX 3060 6GB, reported as ~5800-6144 MB)
        min_system_ram_gb=14.0,    # 14-16 GB system RAM
        min_available_ram_gb=5.0,  # 5 GB free
        min_cpu_threads=6,         # 6+ logical cores
        min_disk_free_gb=20.0,     # 20 GB free disk
        requires_cuda=False,       # Can run on capable AMD/Apple or NVIDIA
        local_ai_eligible=True,
        recommended_mode="Hybrid Local/Cloud AI & Balanced 1080p Rendering",
        description="Mid-tier system suitable for quantized small models and sequential rendering.",
    ),
    "LOW": ProfileThresholdCriteria(
        min_vram_mb=2800,          # 3-4 GB dedicated VRAM (GTX 1050Ti, GTX 1650, etc., reported as ~3000-4096 MB)
        min_system_ram_gb=8.0,     # 8 GB system RAM
        min_available_ram_gb=2.5,  # 2.5 GB free
        min_cpu_threads=4,         # 4 logical cores
        min_disk_free_gb=10.0,     # 10 GB free disk
        requires_cuda=False,
        local_ai_eligible=False,   # Local AI disabled to prevent memory exhaustion
        recommended_mode="Cloud-First AI & Lightweight 720p Rendering",
        description="Entry-level discrete GPU or high-end iGPU. Cloud generation recommended for stability.",
    ),
    "LEGACY_2GB": ProfileThresholdCriteria(
        min_vram_mb=0,             # <= 2048 MB VRAM (GeForce MX110, MX130, iGPUs)
        min_system_ram_gb=0,       # Typically ~8 GB RAM
        min_available_ram_gb=0,    # Low available RAM
        min_cpu_threads=2,         # 2-4 threads (e.g. i5-7200U)
        min_disk_free_gb=5.0,      # Low disk allowance
        requires_cuda=False,
        local_ai_eligible=False,   # Strictly disabled: No Ollama, no heavy models
        recommended_mode="Strict Cloud API Pipeline & Ultrafast Sequential Processing",
        description="Legacy hardware (NVIDIA MX110 2GB, 8GB RAM). Zero local model execution for stability.",
    ),
}
