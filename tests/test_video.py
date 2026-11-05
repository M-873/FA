import os
import pytest
from app.hardware.profiles import RenderSettings, HardwareProfileManager
from app.video.music import MusicManager
from app.video.processor import FFmpegProcessor


def test_music_manager():
    mgr = MusicManager(music_dir="assets/music")
    tracks = mgr.get_music_tracks()
    assert isinstance(tracks, list)


def test_ffmpeg_processor_availability():
    processor = FFmpegProcessor()
    # Should safely return boolean True/False without crashing
    avail = processor.is_ffmpeg_available()
    assert isinstance(avail, bool)


def test_render_settings_crf_attribute():
    """Verify that RenderSettings includes a crf field with sensible defaults across profiles."""
    settings = RenderSettings()
    assert hasattr(settings, "crf")
    assert isinstance(settings.crf, int)
    assert 0 <= settings.crf <= 51

    # Verify per-profile CRF values
    legacy_settings = HardwareProfileManager._get_render_settings_for_profile("LEGACY_2GB")
    assert legacy_settings.crf == 28

    medium_settings = HardwareProfileManager._get_render_settings_for_profile("MEDIUM")
    assert medium_settings.crf == 23

    high_settings = HardwareProfileManager._get_render_settings_for_profile("HIGH")
    assert high_settings.crf == 20
