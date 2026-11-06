"""
tests/test_stock_edit.py
========================
Automated tests for StockEditContentSource and StockPlusGenerateContentSource.
Tests:
- Bangla typography rendering via FFmpeg drawtext with Bengali font
- Visual keyword extraction from topic/script with curated fallback list
- Single-pass video composition, subtitle overlay, and licensing record
- Strict NoClipFoundError bubbling (no gradient fallback)
- StockPlusGenerateContentSource delegation stub
"""

import os
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from app.content.base import ContentRenderResult
from app.content.stock_edit import StockEditContentSource
from app.content.stock_plus_generate import StockPlusGenerateContentSource
from app.hardware.profiles import RenderSettings
from app.stock.license_log import StockLicenseManager
from app.stock.provider import NoClipFoundError, StockClipCandidate, StockVideoProvider
from app.utils.cleanup import TempFileManager
from app.video.ffmpeg_helper import (
    format_font_path_for_ffmpeg,
    get_bengali_font_path,
    get_ffmpeg_binary,
)
from app.video.quality import VideoQualityChecker


@pytest.fixture(scope="module")
def ffmpeg_bin():
    binary = get_ffmpeg_binary()
    assert binary is not None, "FFmpeg binary must be available for stock edit tests"
    return binary


def _create_sample_clip(ffmpeg_bin: str, output_path: str, duration: float = 10.0) -> str:
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", f"color=c=teal:s=720x1280:d={duration}",
        "-f", "lavfi", "-i", f"sine=f=440:d={duration}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-shortest",
        output_path,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path


def test_bangla_text_rendering_with_ffmpeg(ffmpeg_bin, tmp_path):
    """
    Renders Bengali Unicode typography via FFmpeg drawtext.
    Verifies that the generated video has valid aspect ratio and streams.
    """
    font_path = get_bengali_font_path()
    assert font_path is not None, "Host must provide a Bengali-capable font (Nirmala UI, Vrinda, etc.)"
    assert os.path.exists(font_path)

    out_mp4 = str(tmp_path / "bangla_render_test.mp4")
    escaped_font = format_font_path_for_ffmpeg(font_path)
    bangla_headline = "কৃত্রিম বুদ্ধিমত্তা ও রোবটিক্স"
    bangla_sub = "আজকের প্রযুক্তির বিস্ময়কর অগ্রগতি"

    vf = (
        f"scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        f"drawtext=fontfile='{escaped_font}':text='{bangla_headline}':fontcolor=yellow:fontsize=36:x=(w-text_w)/2:y=180:box=1:boxcolor=black@0.65:boxborderw=8,"
        f"drawtext=fontfile='{escaped_font}':text='{bangla_sub}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=h-260:box=1:boxcolor=black@0.65:boxborderw=8"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "color=c=teal:s=720x1280:d=3",
        "-f", "lavfi", "-i", "sine=f=440:d=3",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-shortest",
        out_mp4,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Validate generated Bangla video with VideoQualityChecker
    res = VideoQualityChecker.verify_video(out_mp4, min_duration=2.5, max_duration=5.0)
    assert res["passed"] is True
    assert res["details"]["has_video"] is True
    assert res["details"]["has_audio"] is True
    assert res["details"]["width"] == 720
    assert res["details"]["height"] == 1280


def test_extract_visual_keywords():
    """Verifies keyword extraction from metadata and curated tech fallbacks."""
    # From explicit metadata
    topic_with_meta = {"topic_title": "AI News", "visual_keywords": ["robotics lab", "cyberpunk"]}
    assert StockEditContentSource.extract_visual_keywords(topic_with_meta, {}) == ["robotics lab", "cyberpunk"]

    # Derived from title words
    topic_ai = {"topic_title": "রোবট ও কৃত্রিম বুদ্ধিমত্তা"}
    kws = StockEditContentSource.extract_visual_keywords(topic_ai, {})
    assert "artificial intelligence" in kws

    # Fallback rotation
    generic_topic = {"topic_title": "নতুন কিছু আবিষ্কার"}
    generic_kws = StockEditContentSource.extract_visual_keywords(generic_topic, {})
    assert len(generic_kws) >= 3


def test_stock_edit_generate_video_end_to_end(ffmpeg_bin, tmp_path):
    """Verifies StockEditContentSource single-pass streaming render and license logging."""
    cache_dir = str(tmp_path / "cache")
    log_path = str(tmp_path / "license_log.json")
    sample_clip = str(tmp_path / "raw_stock.mp4")
    _create_sample_clip(ffmpeg_bin, sample_clip, duration=10.0)

    # Audio files
    tts_mp3 = str(tmp_path / "dialogue.mp3")
    music_wav = str(tmp_path / "music.wav")
    subprocess.run([ffmpeg_bin, "-y", "-f", "lavfi", "-i", "sine=f=440:d=5", "-c:a", "libmp3lame", tts_mp3], check=True)
    subprocess.run([ffmpeg_bin, "-y", "-f", "lavfi", "-i", "sine=f=880:d=5", "-c:a", "pcm_s16le", music_wav], check=True)

    out_mp4 = str(tmp_path / "final.mp4")

    mock_candidate = StockClipCandidate(
        clip_id="mock_clip_777",
        provider="pexels",
        local_path=sample_clip,
        source_url="https://www.pexels.com/video/777/",
        license_note="Pexels Free License",
        duration=10.0,
        width=720,
        height=1280,
    )

    mock_provider = MagicMock(spec=StockVideoProvider)
    mock_provider.find_and_prepare_clip.return_value = mock_candidate

    license_mgr = StockLicenseManager(log_path=log_path)
    source = StockEditContentSource(stock_provider=mock_provider, license_manager=license_mgr)

    render_settings = RenderSettings(
        resolution_width=720,
        resolution_height=1280,
        fps=24,
        codec_preset="ultrafast",
        crf=28,
        max_duration_seconds=12,
    )

    with TempFileManager(prefix="test_stock_") as temp_mgr:
        topic = {"topic_title": "ভবিষ্যতের সুপারকম্পিউটার"}
        script = {"dialogues": [{"speaker": "narrator", "text": "কোয়ান্টাম প্রযুক্তির নতুন দিগন্ত"}]}

        res = source.generate_video(
            topic=topic,
            script=script,
            scene_plan={},
            tts_audio_path=tts_mp3,
            music_path=music_wav,
            render_settings=render_settings,
            temp_mgr=temp_mgr,
            output_mp4_path=out_mp4,
            music_source_url="https://freemusicarchive.org/music/test",
        )

        assert isinstance(res, ContentRenderResult)
        assert res.video_path == out_mp4
        assert res.content_source == "stock_edit"
        assert os.path.exists(out_mp4)

        # Verify quality of output video
        qual = VideoQualityChecker.verify_video(out_mp4, min_duration=3.0, max_duration=15.0)
        assert qual["passed"] is True
        assert qual["details"]["has_video"] is True
        assert qual["details"]["has_audio"] is True

        # Verify license log
        assert license_mgr.is_clip_used("mock_clip_777") is True
        records = license_mgr.load_records()
        assert len(records) == 1
        assert records[0].clip_id == "mock_clip_777"
        assert records[0].music_source == "https://freemusicarchive.org/music/test"

        # Verify cleanup called
        mock_provider.cleanup_clip.assert_called_once_with(sample_clip)


def test_stock_edit_raises_no_clip_found(tmp_path):
    """When provider raises NoClipFoundError, StockEditContentSource must raise it without gradient fallback."""
    mock_provider = MagicMock(spec=StockVideoProvider)
    mock_provider.find_and_prepare_clip.side_effect = NoClipFoundError("Nothing found")

    source = StockEditContentSource(stock_provider=mock_provider)
    render_settings = RenderSettings()

    with TempFileManager(prefix="test_fail_") as temp_mgr:
        with pytest.raises(NoClipFoundError) as exc_info:
            source.generate_video(
                topic={"topic_title": "Unknown Topic"},
                script={},
                scene_plan={},
                tts_audio_path=None,
                music_path=None,
                render_settings=render_settings,
                temp_mgr=temp_mgr,
            )
        assert "No suitable stock video clip found" in str(exc_info.value)


def test_stock_plus_generate_delegates_to_stock_edit():
    mock_stock_edit = MagicMock(spec=StockEditContentSource)
    mock_stock_edit.generate_video.return_value = ContentRenderResult(
        video_path="output/final.mp4",
        content_source="stock_edit",
        duration_sec=12.0,
    )

    hybrid = StockPlusGenerateContentSource(stock_edit_source=mock_stock_edit)
    assert hybrid.name == "stock_plus_generate"

    res = hybrid.generate_video(
        topic={},
        script={},
        scene_plan={},
        tts_audio_path=None,
        music_path=None,
        render_settings=RenderSettings(),
        temp_mgr=MagicMock(),
    )
    assert res.content_source == "stock_plus_generate"
    assert res.video_path == "output/final.mp4"
    mock_stock_edit.generate_video.assert_called_once()
