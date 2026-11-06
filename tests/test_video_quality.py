"""
tests/test_video_quality.py
===========================
Automated quality verification tests for VideoQualityChecker.
Tests real video samples generated via FFmpeg in tmp_path:
- Valid 9:16 vertical shorts with audio
- Aspect ratio rejection (e.g. landscape 16:9)
- Duration bounds (too short / too long)
- Audio stream requirement (rejects silent/video-only)
- Black frame ratio rejection
- Configurable limits
No network calls.
"""

import os
import subprocess
import pytest

from app.video.ffmpeg_helper import get_ffmpeg_binary
from app.video.quality import VideoQualityChecker


@pytest.fixture(scope="module")
def ffmpeg_bin():
    binary = get_ffmpeg_binary()
    assert binary is not None, "FFmpeg binary must be available for quality tests"
    return binary


def _create_sample_video(
    ffmpeg_bin: str,
    output_path: str,
    width: int = 720,
    height: int = 1280,
    duration: float = 3.0,
    color: str = "blue",
    include_audio: bool = True,
) -> str:
    """Helper creating tiny test videos with precise synthetic parameters."""
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:d={duration}",
    ]
    if include_audio:
        cmd.extend(["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"])
        cmd.extend(["-c:a", "aac", "-b:a", "64k"])
    else:
        cmd.extend(["-an"])

    cmd.extend([
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-t", str(duration),
        output_path,
    ])
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return output_path


def test_verify_nonexistent_file():
    res = VideoQualityChecker.verify_video("non_existent_file.mp4")
    assert res["passed"] is False
    assert "does not exist" in res["reason"]


def test_verify_file_too_small(tmp_path):
    small_file = tmp_path / "tiny.mp4"
    small_file.write_bytes(b"Too small")
    res = VideoQualityChecker.verify_video(str(small_file), min_file_size_bytes=1024)
    assert res["passed"] is False
    assert "too small" in res["reason"]


def test_verify_valid_vertical_video(ffmpeg_bin, tmp_path):
    vid = str(tmp_path / "valid_vertical.mp4")
    _create_sample_video(ffmpeg_bin, vid, width=720, height=1280, duration=3.5, color="green", include_audio=True)

    res = VideoQualityChecker.verify_video(vid, min_duration=3.0, max_duration=15.0)
    assert res["passed"] is True
    assert res["details"]["width"] == 720
    assert res["details"]["height"] == 1280
    assert res["details"]["has_audio"] is True
    assert res["details"]["has_video"] is True


def test_verify_rejects_landscape_video(ffmpeg_bin, tmp_path):
    vid = str(tmp_path / "landscape.mp4")
    _create_sample_video(ffmpeg_bin, vid, width=1280, height=720, duration=3.0, color="red", include_audio=True)

    res = VideoQualityChecker.verify_video(vid)
    assert res["passed"] is False
    assert "Invalid aspect ratio" in res["reason"]


def test_verify_rejects_too_short_video(ffmpeg_bin, tmp_path):
    vid = str(tmp_path / "short.mp4")
    _create_sample_video(ffmpeg_bin, vid, width=720, height=1280, duration=1.0, color="blue", include_audio=True)

    res = VideoQualityChecker.verify_video(vid, min_duration=3.0)
    assert res["passed"] is False
    assert "Duration" in res["reason"]


def test_verify_rejects_too_long_video(ffmpeg_bin, tmp_path):
    vid = str(tmp_path / "long.mp4")
    _create_sample_video(ffmpeg_bin, vid, width=720, height=1280, duration=6.0, color="blue", include_audio=True)

    res = VideoQualityChecker.verify_video(vid, max_duration=4.0)
    assert res["passed"] is False
    assert "Duration" in res["reason"]


def test_verify_rejects_video_without_audio(ffmpeg_bin, tmp_path):
    vid = str(tmp_path / "no_audio.mp4")
    _create_sample_video(ffmpeg_bin, vid, width=720, height=1280, duration=3.0, color="yellow", include_audio=False)

    res = VideoQualityChecker.verify_video(vid)
    assert res["passed"] is False
    assert "No audio stream detected" in res["reason"]


def test_verify_rejects_black_frames(ffmpeg_bin, tmp_path):
    vid = str(tmp_path / "all_black.mp4")
    _create_sample_video(ffmpeg_bin, vid, width=720, height=1280, duration=3.0, color="black", include_audio=True)

    res = VideoQualityChecker.verify_video(vid, max_black_frame_ratio=0.25)
    assert res["passed"] is False
    assert "Black frame ratio" in res["reason"]


def test_verify_configurable_limits(ffmpeg_bin, tmp_path):
    # An all-black 2.0s video would normally fail, but with custom limits it can be permitted
    vid = str(tmp_path / "custom_limits.mp4")
    _create_sample_video(ffmpeg_bin, vid, width=720, height=1280, duration=2.0, color="black", include_audio=True)

    res = VideoQualityChecker.verify_video(
        vid,
        min_duration=1.5,
        max_duration=10.0,
        max_black_frame_ratio=1.0,  # allow black frames
    )
    assert res["passed"] is True
