"""
Video generation and processing package.
"""
from app.video.huggingface import HuggingFaceVideoGenerator
from app.video.processor import FFmpegProcessor
from app.video.music import MusicManager

__all__ = [
    "HuggingFaceVideoGenerator",
    "FFmpegProcessor",
    "MusicManager",
]
