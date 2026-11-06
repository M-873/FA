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


def get_bengali_font_path() -> Optional[str]:
    """
    Locates a Bengali-capable TrueType/OpenType font on the host system.
    Searches assets/fonts/, Windows Fonts (Nirmala UI, Vrinda), and Linux font paths.
    Returns the absolute path to the font file, or None if none found.
    """
    # 1. Project assets directory
    for candidate_dir in ("assets/fonts", "assets"):
        if os.path.exists(candidate_dir):
            for fname in ("NirmalaB.ttf", "Nirmala.ttf", "Kalpurush.ttf", "SiyamRupali.ttf", "SolaimanLipi.ttf"):
                p = os.path.join(candidate_dir, fname)
                if os.path.exists(p):
                    return os.path.abspath(p)

    # 2. Windows System Fonts
    windir = os.environ.get("WINDIR", r"C:\Windows")
    win_fonts = os.path.join(windir, "Fonts")
    if os.path.exists(win_fonts):
        for fname in ("NirmalaB.ttf", "Nirmala.ttf", "NirmalaS.ttf", "vrinda.ttf", "vrindab.ttf", "arial.ttf"):
            p = os.path.join(win_fonts, fname)
            if os.path.exists(p):
                return p.replace("\\", "/")

    # 3. Linux/Unix Font Paths
    linux_candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-bengali/Lohit-Bengali.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansBengali-Bold.otf",
    ]
    for p in linux_candidates:
        if os.path.exists(p):
            return p

    return None


def format_font_path_for_ffmpeg(font_path: Optional[str]) -> str:
    """Formats and escapes font path so FFmpeg drawtext filter doesn't choke on Windows colons."""
    if not font_path:
        return ""
    normalized = font_path.replace("\\", "/")
    return normalized.replace(":", r"\:")
