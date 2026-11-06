"""
tests/test_stock_provider.py
============================
Automated tests for StockVideoProvider and StockLicenseManager.
Mocks all HTTP requests:
- Waterfall execution: Pexels (429) -> Pixabay -> Local library -> NoClipFoundError
- Strict failure when nothing is found (NoClipFoundError)
- Clip deduplication via StockLicenseManager
- License audit logging with verifiable music source
- Cache management and cleanup
No external network calls.
"""

import json
import os
import subprocess
from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.hardware.profiles import RenderSettings
from app.stock.license_log import StockLicenseManager, StockLicenseRecord
from app.stock.provider import (
    NoClipFoundError,
    StockClipCandidate,
    StockVideoProvider,
)
from app.video.ffmpeg_helper import get_ffmpeg_binary


@pytest.fixture
def temp_dirs(tmp_path):
    cache_d = str(tmp_path / "cache")
    local_d = str(tmp_path / "local_stock")
    log_f = str(tmp_path / "license_log.json")
    os.makedirs(cache_d, exist_ok=True)
    os.makedirs(local_d, exist_ok=True)
    return cache_d, local_d, log_f


def test_license_log_record_and_deduplication(temp_dirs):
    cache_d, local_d, log_f = temp_dirs
    mgr = StockLicenseManager(log_path=log_f)

    assert mgr.is_clip_used("pexels_1001") is False

    # Record usage
    record = mgr.record_usage(
        clip_id="pexels_1001",
        provider="pexels",
        source_url="https://www.pexels.com/video/1001/",
        license_note="Pexels Free License",
        music_source="https://freemusicarchive.org/music/track1",
        topic="AI in 2026",
    )

    assert record.clip_id == "pexels_1001"
    assert record.music_source == "https://freemusicarchive.org/music/track1"
    assert mgr.is_clip_used("pexels_1001") is True
    assert mgr.is_clip_used("pexels_1002") is False

    # Verify JSON structure on disk
    with open(log_f, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["clip_id"] == "pexels_1001"
        assert data[0]["music_source"] == "https://freemusicarchive.org/music/track1"


def test_license_log_unverified_music_source_default(temp_dirs):
    cache_d, local_d, log_f = temp_dirs
    mgr = StockLicenseManager(log_path=log_f)

    record = mgr.record_usage(
        clip_id="local_clip",
        provider="local",
        source_url="assets/stock_videos/clip.mp4",
        license_note="Local Royalty Free",
        music_source="",  # Empty
    )
    assert record.music_source == "UNVERIFIED"


def test_provider_skips_when_api_keys_missing(temp_dirs):
    """Missing API keys must silently skip remote providers and check local library."""
    cache_d, local_d, log_f = temp_dirs
    mgr = StockLicenseManager(log_path=log_f)
    provider = StockVideoProvider(cache_dir=cache_d, local_dir=local_d, license_manager=mgr)

    with patch("app.stock.provider.get_env_settings") as mock_env:
        mock_env.return_value.PEXELS_API_KEY = ""
        mock_env.return_value.PIXABAY_API_KEY = ""

        # Local library is empty, must raise NoClipFoundError
        with pytest.raises(NoClipFoundError) as exc_info:
            provider.find_and_prepare_clip(keyword="robot")
        assert "No suitable stock video clip found" in str(exc_info.value)


def test_provider_waterfall_pexels_429_to_pixabay(temp_dirs):
    """When Pexels returns 429 rate limit, waterfall must seamlessly try Pixabay."""
    cache_d, local_d, log_f = temp_dirs
    mgr = StockLicenseManager(log_path=log_f)
    provider = StockVideoProvider(cache_dir=cache_d, local_dir=local_d, license_manager=mgr)

    with patch("app.stock.provider.get_env_settings") as mock_env:
        mock_env.return_value.PEXELS_API_KEY = "test_pexels_key"
        mock_env.return_value.PIXABAY_API_KEY = "test_pixabay_key"

        # Mock Pexels returning 429
        mock_pexels_resp = MagicMock(status_code=429)

        # Mock Pixabay returning valid portrait clip
        mock_pixabay_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "hits": [
                    {
                        "id": 999,
                        "duration": 14.0,
                        "pageURL": "https://pixabay.com/videos/id-999/",
                        "videos": {
                            "medium": {
                                "width": 720,
                                "height": 1280,
                                "url": "https://pixabay.com/download/999.mp4",
                            }
                        },
                    }
                ]
            },
        )

        def mock_get(url, **kwargs):
            if "pexels" in url:
                return mock_pexels_resp
            return mock_pixabay_resp

        with patch("httpx.Client.get", side_effect=mock_get):
            with patch.object(provider, "_download_if_needed", side_effect=lambda cand: cand):
                candidate = provider.find_and_prepare_clip(keyword="technology")
                assert candidate.provider == "pixabay"
                assert candidate.clip_id == "pixabay_999"
                assert candidate.duration == 14.0
                assert candidate.width == 720
                assert candidate.height == 1280


def test_provider_waterfall_to_local_library(temp_dirs):
    """When remote providers fail, local video asset in assets/stock_videos is selected."""
    cache_d, local_d, log_f = temp_dirs
    mgr = StockLicenseManager(log_path=log_f)
    provider = StockVideoProvider(cache_dir=cache_d, local_dir=local_d, license_manager=mgr)

    # Generate a real tiny 10-second vertical video in local_d
    local_mp4 = os.path.join(local_d, "sample_clip.mp4")
    ffmpeg_bin = get_ffmpeg_binary()
    assert ffmpeg_bin is not None
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "color=c=navy:s=720x1280:d=10",
        "-f", "lavfi", "-i", "sine=f=440:d=10",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-shortest",
        local_mp4,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    with patch("app.stock.provider.get_env_settings") as mock_env:
        mock_env.return_value.PEXELS_API_KEY = ""
        mock_env.return_value.PIXABAY_API_KEY = ""

        candidate = provider.find_and_prepare_clip(keyword="anything")
        assert candidate.provider == "local"
        assert candidate.clip_id == "local_sample_clip"
        assert candidate.local_path == local_mp4


def test_provider_deduplication_skips_used_clip(temp_dirs):
    """Clips already registered in StockLicenseManager must be skipped."""
    cache_d, local_d, log_f = temp_dirs
    mgr = StockLicenseManager(log_path=log_f)
    mgr.record_usage(clip_id="pexels_101", provider="pexels", source_url="url1", license_note="note")

    provider = StockVideoProvider(cache_dir=cache_d, local_dir=local_d, license_manager=mgr)

    with patch("app.stock.provider.get_env_settings") as mock_env:
        mock_env.return_value.PEXELS_API_KEY = "dummy_key"
        mock_env.return_value.PIXABAY_API_KEY = ""

        # Pexels returns two videos: #101 (used) and #102 (unused)
        mock_pexels_resp = MagicMock(
            status_code=200,
            json=lambda: {
                "videos": [
                    {
                        "id": 101,
                        "duration": 12.0,
                        "video_files": [{"width": 720, "height": 1280, "link": "http://vid101"}],
                    },
                    {
                        "id": 102,
                        "duration": 15.0,
                        "video_files": [{"width": 720, "height": 1280, "link": "http://vid102"}],
                    },
                ]
            },
        )

        with patch("httpx.Client.get", return_value=mock_pexels_resp):
            with patch.object(provider, "_download_if_needed", side_effect=lambda cand: cand):
                candidate = provider.find_and_prepare_clip(keyword="tech")
                # 101 was skipped, 102 was picked
                assert candidate.clip_id == "pexels_102"


def test_provider_cleanup_only_removes_cache(temp_dirs):
    """cleanup_clip must remove cache files but never delete local library assets."""
    cache_d, local_d, log_f = temp_dirs
    provider = StockVideoProvider(cache_dir=cache_d, local_dir=local_d)

    # 1. Cache file
    cached_file = os.path.join(cache_d, "test.mp4")
    with open(cached_file, "w") as f:
        f.write("cached data")
    assert os.path.exists(cached_file)

    provider.cleanup_clip(cached_file)
    assert not os.path.exists(cached_file)

    # 2. Local asset file
    local_file = os.path.join(local_d, "permanent.mp4")
    with open(local_file, "w") as f:
        f.write("permanent asset")
    assert os.path.exists(local_file)

    provider.cleanup_clip(local_file)
    # Must still exist!
    assert os.path.exists(local_file)
