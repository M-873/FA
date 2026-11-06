"""
app/content/base.py
===================
Abstract base classes and schemas for pluggable ContentSource implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.hardware.profiles import RenderSettings
from app.utils.cleanup import TempFileManager


class ContentRenderResult(BaseModel):
    """Result returned after a ContentSource generates the master video file."""

    video_path: str = Field(description="Path to the generated master MP4 file")
    content_source: str = Field(description="Name of the content source that produced the video")
    duration_sec: float = Field(default=0.0, description="Video duration in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata e.g. stock license info")


class BaseContentSource(ABC):
    """Abstract interface for video content generation sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name identifier of the content source (e.g. 'cartoon', 'stock_edit')."""
        pass

    @abstractmethod
    def generate_video(
        self,
        topic: Dict[str, Any],
        script: Dict[str, Any],
        scene_plan: Dict[str, Any],
        tts_audio_path: Optional[str],
        music_path: Optional[str],
        render_settings: RenderSettings,
        temp_mgr: TempFileManager,
        output_mp4_path: str = "output/final.mp4",
    ) -> ContentRenderResult:
        """
        Generates the master video file for today's job.
        Returns a ContentRenderResult.
        """
        pass

