"""
app/content/factory.py
======================
Factory resolving the appropriate ContentSource for today's job based on
configuration and hardware profile.
Rules:
- Manual choice wins (CONTENT_SOURCE_OVERRIDE env var or non-'auto' project_config.json)
- Auto:
    - LEGACY_2GB / LOW -> stock_edit
    - MEDIUM / HIGH / ULTRA -> stock_plus_generate
- Until stock sources exist, stock_edit and stock_plus_generate fall back to 'cartoon'
  with an explicit warning log.
"""

from typing import Optional
from app.content.base import BaseContentSource
from app.content.cartoon import CartoonContentSource
from app.hardware.detector import HardwareSpecs
from app.hardware.profiles import HardwareProfileManager
from app.utils.config import get_env_settings, get_project_config
from app.utils.logging import logger


class ContentSourceFactory:
    """Instantiates ContentSource based on configuration and host telemetry."""

    VALID_SOURCES = {"auto", "stock_edit", "stock_plus_generate", "cartoon"}

    @classmethod
    def resolve_source_name(
        cls,
        specs: Optional[HardwareSpecs] = None,
        configured_source: Optional[str] = None,
    ) -> str:
        """Determines the target source string according to resolution rules."""
        env = get_env_settings()

        # 1. Environment variable override takes highest precedence
        env_override = getattr(env, "CONTENT_SOURCE_OVERRIDE", None)
        if env_override and str(env_override).strip().lower() in cls.VALID_SOURCES:
            candidate = str(env_override).strip().lower()
            if candidate != "auto":
                return candidate

        # 2. Manual setting in project_config.json
        if not configured_source:
            project_cfg = get_project_config()
            configured_source = getattr(project_cfg, "content_source", "auto")

        source_clean = str(configured_source).strip().lower()
        if source_clean in cls.VALID_SOURCES and source_clean != "auto":
            return source_clean

        # 3. Auto derivation based on hardware profile
        if specs is None:
            from app.hardware.detector import HardwareDetector
            specs = HardwareDetector().detect()

        profile_res = HardwareProfileManager.determine_profile(specs)
        prof_name = str(profile_res.profile).upper()

        if "LEGACY" in prof_name or prof_name == "LOW":
            return "stock_edit"
        else:
            return "stock_plus_generate"

    @classmethod
    def get_source(
        cls,
        specs: Optional[HardwareSpecs] = None,
        configured_source: Optional[str] = None,
    ) -> BaseContentSource:
        """
        Returns a concrete BaseContentSource implementation.
        Falls back to CartoonContentSource with a warning if the requested source
        is not yet implemented.
        """
        source_name = cls.resolve_source_name(specs, configured_source)

        if source_name == "cartoon":
            return CartoonContentSource()

        if source_name in ("stock_edit", "stock_plus_generate"):
            logger.warning(
                f"Content source '{source_name}' is not implemented yet. "
                f"Falling back to 'cartoon' content source with procedural animation."
            )
            return CartoonContentSource()

        logger.warning(f"Unknown content source '{source_name}'. Defaulting to 'cartoon'.")
        return CartoonContentSource()
