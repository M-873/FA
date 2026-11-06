"""
app/content/cartoon.py
======================
CartoonContentSource: 2D frame animation engine + Master FFmpeg Renderer.
Wraps existing CartoonAnimationEngine and CartoonMasterRenderer with zero behavioral changes.
"""

from typing import Any, Dict, Optional
from app.animation.engine import CartoonAnimationEngine
from app.content.base import BaseContentSource, ContentRenderResult
from app.hardware.monitor import HardwareSafetyMonitor
from app.hardware.profiles import RenderSettings
from app.utils.cleanup import TempFileManager
from app.video.renderer import CartoonMasterRenderer


class CartoonContentSource(BaseContentSource):
    """Generates 2D procedural cartoon video via PIL frame animation & FFmpeg."""

    @property
    def name(self) -> str:
        return "cartoon"

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
        music_source_url: str = "UNVERIFIED",
        **kwargs: Any,
    ) -> ContentRenderResult:
        # 1. 2D Frame Animation
        anim_engine = CartoonAnimationEngine(render_settings)
        frames_dir = temp_mgr.get_path("frames")
        anim_engine.render_scene_frames(script, scene_plan, frames_dir)

        HardwareSafetyMonitor.purge_resources()

        # 2. Master FFmpeg Render
        master_renderer = CartoonMasterRenderer(render_settings)
        final_mp4 = master_renderer.render_master_mp4(
            frame_dir=frames_dir,
            tts_audio_path=tts_audio_path,
            music_path=music_path,
            output_mp4_path=output_mp4_path,
        )

        return ContentRenderResult(
            video_path=final_mp4,
            content_source=self.name,
        )

