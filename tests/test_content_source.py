"""
tests/test_content_source.py
============================
Automated tests for ContentSource abstraction, Factory resolution rules,
and DailyJobState backwards compatibility.
"""

from unittest.mock import patch, MagicMock
import pytest

from app.content.base import BaseContentSource, ContentRenderResult
from app.content.cartoon import CartoonContentSource
from app.content.factory import ContentSourceFactory
from app.hardware.detector import HardwareSpecs
from app.jobs.state import DailyJobState, JobStatus


def test_daily_job_state_content_source_backward_compatibility():
    """Existing serialized daily_job json without content_source must default to 'cartoon'."""
    legacy_data = {
        "date": "2026-11-06",
        "job_id": "2026-11-06-test",
        "status": "PENDING",
    }
    state = DailyJobState.model_validate(legacy_data)
    assert hasattr(state, "content_source")
    assert state.content_source == "cartoon"


def test_factory_resolves_manual_choice():
    """Manual selection in project_config or argument strictly overrides auto."""
    assert ContentSourceFactory.resolve_source_name(configured_source="cartoon") == "cartoon"
    assert ContentSourceFactory.resolve_source_name(configured_source="stock_edit") == "stock_edit"
    assert ContentSourceFactory.resolve_source_name(configured_source="stock_plus_generate") == "stock_plus_generate"


def test_factory_env_override_takes_precedence():
    """CONTENT_SOURCE_OVERRIDE in environment variables takes highest precedence."""
    with patch("app.content.factory.get_env_settings") as mock_env:
        mock_env.return_value.CONTENT_SOURCE_OVERRIDE = "stock_edit"
        resolved = ContentSourceFactory.resolve_source_name(configured_source="cartoon")
        assert resolved == "stock_edit"


def test_factory_auto_derivation_low_end():
    """Auto mode on LEGACY_2GB / LOW hardware derives stock_edit."""
    low_specs = HardwareSpecs(
        gpu_name="NVIDIA GeForce MX110",
        nvidia_gpu_present=True,
        vram_mb=2048,
        ram_total_gb=8.0,
        ram_available_gb=1.5,
        cpu_threads=4,
        disk_free_gb=50.0,
        detection_status="DETECTED",
    )
    resolved = ContentSourceFactory.resolve_source_name(specs=low_specs, configured_source="auto")
    assert resolved == "stock_edit"


def test_factory_auto_derivation_high_end():
    """Auto mode on HIGH hardware derives stock_plus_generate."""
    high_specs = HardwareSpecs(
        gpu_name="NVIDIA GeForce RTX 4060",
        nvidia_gpu_present=True,
        vram_mb=8192,
        ram_total_gb=32.0,
        ram_available_gb=24.0,
        cpu_threads=16,
        cuda_available=True,
        disk_free_gb=100.0,
        detection_status="DETECTED",
    )
    resolved = ContentSourceFactory.resolve_source_name(specs=high_specs, configured_source="auto")
    assert resolved == "stock_plus_generate"


def test_factory_fallback_to_cartoon_for_unimplemented_sources(caplog):
    """stock_edit and stock_plus_generate fall back to CartoonContentSource with warning log."""
    source = ContentSourceFactory.get_source(configured_source="stock_edit")
    assert isinstance(source, CartoonContentSource)
    assert source.name == "cartoon"
    assert any("not implemented yet" in record.message for record in caplog.records)


def test_cartoon_content_source_properties():
    source = CartoonContentSource()
    assert source.name == "cartoon"
    assert isinstance(source, BaseContentSource)
