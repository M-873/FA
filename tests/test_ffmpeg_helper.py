"""
tests/test_ffmpeg_helper.py
===========================
Automated tests for unified FFmpeg / FFprobe locator and runner.
Tests PATH resolution, imageio_ffmpeg fallback, adjacent binary discovery,
and graceful failure when binaries are missing.
"""

import os
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from app.video.ffmpeg_helper import (
    get_ffmpeg_binary,
    get_ffprobe_binary,
    is_ffmpeg_available,
    is_ffprobe_available,
)


def test_get_ffmpeg_binary_prefers_path():
    """System PATH should take precedence if ffmpeg is found."""
    with patch("shutil.which", return_value="/usr/local/bin/ffmpeg"):
        result = get_ffmpeg_binary()
        assert result == "/usr/local/bin/ffmpeg"


def test_get_ffmpeg_binary_falls_back_to_imageio():
    """If ffmpeg is missing from PATH, fallback to imageio_ffmpeg bundled binary."""
    with patch("shutil.which", return_value=None):
        with patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="/opt/imageio/ffmpeg"):
            with patch("os.path.exists", return_value=True):
                result = get_ffmpeg_binary()
                assert result == "/opt/imageio/ffmpeg"


def test_get_ffmpeg_binary_returns_none_if_all_fail():
    """If neither PATH nor imageio provides ffmpeg, return None."""
    with patch("shutil.which", return_value=None):
        with patch("imageio_ffmpeg.get_ffmpeg_exe", side_effect=ImportError("No imageio")):
            result = get_ffmpeg_binary()
            assert result is None


def test_get_ffprobe_binary_prefers_path():
    """System PATH should take precedence if ffprobe is found."""
    with patch("shutil.which", return_value="/usr/local/bin/ffprobe"):
        result = get_ffprobe_binary()
        assert result == "/usr/local/bin/ffprobe"


def test_get_ffprobe_binary_checks_adjacent_to_ffmpeg():
    """If not in PATH, ffprobe in ffmpeg's parent directory should be detected."""
    with patch("shutil.which", return_value=None):
        with patch("app.video.ffmpeg_helper.get_ffmpeg_binary", return_value=r"C:\tools\ffmpeg\bin\ffmpeg.exe"):
            def fake_exists(path):
                return "ffprobe" in path
            with patch("os.path.exists", side_effect=fake_exists):
                result = get_ffprobe_binary()
                assert result is not None
                assert "ffprobe" in result.lower()


def test_get_ffprobe_binary_handles_missing_gracefully():
    """If ffprobe is nowhere to be found, return None without raising an exception."""
    with patch("shutil.which", return_value=None):
        with patch("app.video.ffmpeg_helper.get_ffmpeg_binary", return_value=None):
            result = get_ffprobe_binary()
            assert result is None


def test_is_ffmpeg_available_returns_true_on_success():
    """Checks that a 0 returncode evaluates is_ffmpeg_available to True."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    with patch("app.video.ffmpeg_helper.get_ffmpeg_binary", return_value="/bin/ffmpeg"):
        with patch("subprocess.run", return_value=mock_res):
            assert is_ffmpeg_available() is True


def test_is_ffmpeg_available_returns_false_on_error():
    """Checks that non-zero returncode or exception evaluates is_ffmpeg_available to False."""
    with patch("app.video.ffmpeg_helper.get_ffmpeg_binary", return_value="/bin/ffmpeg"):
        with patch("subprocess.run", side_effect=subprocess.SubprocessError("Failed")):
            assert is_ffmpeg_available() is False


def test_is_ffprobe_available_returns_false_when_none():
    """Checks that is_ffprobe_available returns False when get_ffprobe_binary is None."""
    with patch("app.video.ffmpeg_helper.get_ffprobe_binary", return_value=None):
        assert is_ffprobe_available() is False


def test_real_runtime_ffmpeg_resolution():
    """
    On this actual machine, get_ffmpeg_binary() must resolve either system ffmpeg
    or imageio_ffmpeg, and it must exist on disk.
    """
    binary = get_ffmpeg_binary()
    assert binary is not None, "Host must resolve a valid FFmpeg binary via imageio_ffmpeg or PATH"
    assert os.path.exists(binary), f"Resolved binary does not exist on disk: {binary}"
    assert is_ffmpeg_available() is True
