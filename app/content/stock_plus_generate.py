"""
app/content/stock_plus_generate.py
==================================
StockPlusGenerateContentSource: Hybrid content source for high-end hardware.
In this milestone, generative visual enhancement is stubbed and falls back cleanly
to StockEditContentSource.
"""

from typing import Any, Dict, Optional
from app.content.base import BaseContentSource, ContentRenderResult
from app.content.stock_edit import StockEditContentSource
from app.hardware.profiles import RenderSettings
from app.utils.cleanup import TempFileManager
from app.utils.logging import logger


class StockPlusGenerateContentSource(BaseContentSource):
    """
    High-end content pipeline stub: intended to composite locally generated AI visuals
    on top of stock footage. Falls back cleanly to StockEditContentSource.
    """

    def __init__(self, stock_edit_source: Optional[StockEditContentSource] = None):
        self._delegate = stock_edit_source or StockEditContentSource()

    @property
    def name(self) -> str:
        return "stock_plus_generate"

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
    ) -> ContentRenderResult:
        logger.info(
            "[stock_plus_generate] Local generative visuals stub active. "
            "Falling back to StockEditContentSource single-pass streaming compilation."
        )
        res = self._delegate.generate_video(
            topic=topic,
            script=script,
            scene_plan=scene_plan,
            tts_audio_path=tts_audio_path,
            music_path=music_path,
            render_settings=render_settings,
            temp_mgr=temp_mgr,
            output_mp4_path=output_mp4_path,
            music_source_url=music_source_url,
        )
        res.content_source = self.name
        return res

