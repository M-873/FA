"""
Video generation and processing package.
"""
from app.video.huggingface import HuggingFaceVideoGenerator
from app.video.processor import FFmpegProcessor
from app.video.music import MusicManager
from app.video.ffmpeg_helper import (
    get_ffmpeg_binary,
    get_ffprobe_binary,
    is_ffmpeg_available,
    is_ffprobe_available,
)

__all__ = [
    "HuggingFaceVideoGenerator",
    "FFmpegProcessor",
    "MusicManager",
    "get_ffmpeg_binary",
    "get_ffprobe_binary",
    "is_ffmpeg_available",
    "is_ffprobe_available",
]
