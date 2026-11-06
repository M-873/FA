"""
app/video/ffmpeg_helper.py
==========================
Unified locator and runner for FFmpeg and FFprobe binaries.
Resolution strategy:
1. System PATH via shutil.which
2. Bundled imageio_ffmpeg binary (fallback for ffmpeg)
3. Sibling binary in ffmpeg directory (fallback for ffprobe)
Handles missing binaries gracefully without crashing.
"""

import os
import shutil
import subprocess
from typing import Optional
from app.utils.logging import logger


def get_ffmpeg_binary() -> Optional[str]:
    """
    Locates the FFmpeg executable.
    Checks system PATH first, then falls back to imageio_ffmpeg bundled binary.
    Returns executable path if found and existing, or None.
    """
    # 1. Check system PATH
    path_cmd = shutil.which("ffmpeg")
    if path_cmd:
        return path_cmd

    # 2. Check imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception as e:
        logger.debug(f"imageio_ffmpeg lookup failed: {e}")

    return None


def get_ffprobe_binary() -> Optional[str]:
    """
    Locates the FFprobe executable.
    Checks system PATH first, then checks adjacent directory to FFmpeg.
    Returns executable path if found, or None if unavailable.
    """
    # 1. Check system PATH
    path_cmd = shutil.which("ffprobe")
    if path_cmd:
        return path_cmd

    # 2. Check directory adjacent to resolved FFmpeg binary
    ffmpeg_bin = get_ffmpeg_binary()
    if ffmpeg_bin:
        ffmpeg_dir = os.path.dirname(ffmpeg_bin)
        for name in ("ffprobe.exe", "ffprobe"):
            candidate = os.path.join(ffmpeg_dir, name)
            if os.path.exists(candidate):
                return candidate

    return None


def is_ffmpeg_available() -> bool:
    """Checks if a valid, runnable FFmpeg binary is available on the host."""
    bin_path = get_ffmpeg_binary()
    if not bin_path:
        return False
    try:
        res = subprocess.run(
            [bin_path, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False


def is_ffprobe_available() -> bool:
    """Checks if a valid, runnable FFprobe binary is available on the host."""
    bin_path = get_ffprobe_binary()
    if not bin_path:
        return False
    try:
        res = subprocess.run(
            [bin_path, "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False
