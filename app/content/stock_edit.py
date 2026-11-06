"""
app/content/stock_edit.py
=========================
StockEditContentSource: Generates 10-15s vertical shorts from free stock video +
dialogue voiceover + background music + on-screen Bengali typography.
Uses a single-pass streaming FFmpeg pipeline (low memory footprint, < 60 MB RAM).
"""

import os
import re
import subprocess
from typing import Any, Dict, List, Optional
from app.content.base import BaseContentSource, ContentRenderResult
from app.hardware.profiles import RenderSettings
from app.stock.license_log import StockLicenseManager
from app.stock.provider import NoClipFoundError, StockClipCandidate, StockVideoProvider
from app.utils.cleanup import TempFileManager
from app.utils.logging import logger
from app.video.ffmpeg_helper import (
    format_font_path_for_ffmpeg,
    get_bengali_font_path,
    get_ffmpeg_binary,
)


class StockEditContentSource(BaseContentSource):
    """
    Assembles professional 9:16 vertical shorts from stock footage with voiceover,
    royalty-free background music, and Bengali text overlays via streaming FFmpeg.
    """

    DEFAULT_KEYWORDS_LIST = [
        ["artificial intelligence", "robot technology", "futuristic tech", "coding computer screen"],
        ["cyberpunk city", "server room", "digital network abstract", "science laboratory"],
        ["space galaxy universe", "astronomy stars", "quantum computer", "hologram technology"],
        ["microchip processor", "neural network brain", "virtual reality", "modern technology laboratory"],
    ]

    def __init__(
        self,
        stock_provider: Optional[StockVideoProvider] = None,
        license_manager: Optional[StockLicenseManager] = None,
    ):
        self.provider = stock_provider or StockVideoProvider()
        self.license_mgr = license_manager or StockLicenseManager()

    @property
    def name(self) -> str:
        return "stock_edit"

    @classmethod
    def extract_visual_keywords(
        cls,
        topic: Dict[str, Any],
        script: Dict[str, Any],
    ) -> List[str]:
        """
        Extracts 3-5 visual search keywords for stock footage.
        Extracts from AI metadata if available, else derives from topic title or fallback list.
        """
        # 1. Check topic/script metadata
        for obj in (topic, script):
            if isinstance(obj, dict):
                kws = obj.get("visual_keywords") or obj.get("keywords")
                if isinstance(kws, list) and kws:
                    valid_kws = [str(k).strip() for k in kws if str(k).strip()]
                    if valid_kws:
                        return valid_kws[:5]
                elif isinstance(kws, str) and kws.strip():
                    valid_kws = [k.strip() for k in kws.split(",") if k.strip()]
                    if valid_kws:
                        return valid_kws[:5]

        # 2. Derive keyword from topic title or niche
        title = str(topic.get("topic_title", "")).lower()
        if any(w in title for w in ("ai", "রোবট", "robot", "কৃত্রিম", "কম্পিউটার", "code")):
            return ["artificial intelligence", "robot technology", "coding computer screen", "futuristic technology"]
        if any(w in title for w in ("মহাকাশ", "space", "নক্ষত্র", "তারা", "গ্রহ", "galaxy")):
            return ["space galaxy", "astronomy stars", "futuristic science", "hologram technology"]
        if any(w in title for w in ("সাইবার", "হ্যাক", "নিরাপত্তা", "security", "data", "নেটওয়ার্ক")):
            return ["digital network", "server room", "cyberpunk city", "data stream"]

        # 3. Deterministic rotation through built-in tech/science keywords
        title_hash = sum(ord(c) for c in title) if title else 0
        idx = title_hash % len(cls.DEFAULT_KEYWORDS_LIST)
        return cls.DEFAULT_KEYWORDS_LIST[idx]

    @staticmethod
    def _sanitize_drawtext(text: str) -> str:
        """Escapes characters that break FFmpeg drawtext filter string syntax."""
        if not text:
            return ""
        # Escape backslashes, colons, single quotes, percent signs
        text = text.replace("\\", "\\\\")
        text = text.replace("'", "\u2019")  # Replace single quote with typographic apostrophe
        text = text.replace(":", r"\:")
        text = text.replace("%", r"\%")
        return text.strip()

    @classmethod
    def create_ass_file(
        cls,
        ass_path: str,
        w: int,
        h: int,
        duration: float,
        title_text: str,
        subtitle_text: str,
        font_name: str = "Nirmala UI",
    ) -> str:
        """
        Creates an Advanced SubStation Alpha (.ass) subtitle file.
        Provides native OpenType / HarfBuzz text shaping via libass,
        rendering Bengali matras, conjuncts, and vowel signs accurately.
        """
        title_size = max(24, int(w * 0.048))
        sub_size = max(20, int(w * 0.036))
        title_margin_v = int(h * 0.14)
        sub_margin_v = int(h * 0.18)

        dur_h = int(duration // 3600)
        dur_m = int((duration % 3600) // 60)
        dur_s = int(duration % 60)
        dur_cs = int((duration * 100) % 100)
        end_ts = f"{dur_h}:{dur_m:02d}:{dur_s:02d}.{dur_cs:02d}"

        # Clean any raw newlines from text
        title_text = title_text.replace("\n", " ").replace("\r", "").strip()
        subtitle_text = subtitle_text.replace("\n", " ").replace("\r", "").strip()

        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{font_name},{title_size},&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,8,20,20,{title_margin_v},1
Style: Subtitle,{font_name},{sub_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,20,20,{sub_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{end_ts},Title,,0,0,0,,{title_text}
Dialogue: 0,0:00:00.00,{end_ts},Subtitle,,0,0,0,,{subtitle_text}
"""
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)
        return ass_path

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
        """
        Executes single-pass streaming FFmpeg video composition from stock video.
        Uses libass for typography to ensure 100% correct Bengali glyph shaping.
        """
        ffmpeg_bin = get_ffmpeg_binary()
        if not ffmpeg_bin:
            raise RuntimeError("FFmpeg executable is required for stock_edit video composition.")

        # 1. Visual Keyword Extraction
        keywords = self.extract_visual_keywords(topic, script)
        logger.info(f"[stock_edit] Visual keywords for stock search: {keywords}")

        # 2. Stock Clip Waterfall Retrieval
        candidate: Optional[StockClipCandidate] = None
        for kw in keywords:
            try:
                candidate = self.provider.find_and_prepare_clip(
                    keyword=kw,
                    render_settings=render_settings,
                    min_duration=8.0,
                    max_duration=30.0,
                )
                if candidate:
                    break
            except NoClipFoundError:
                continue
            except Exception as e:
                logger.warning(f"[stock_edit] Search attempt for keyword '{kw}' failed: {e}")

        if not candidate:
            raise NoClipFoundError(
                f"No suitable stock video clip found for keywords {keywords} across all stock providers."
            )

        logger.info(
            f"[stock_edit] Selected clip: {candidate.clip_id} ({candidate.provider}) -> {candidate.local_path}"
        )

        try:
            # 3. Typography & Bengali Font Setup via libass
            w = render_settings.resolution_width
            h = render_settings.resolution_height
            max_duration = min(float(render_settings.max_duration_seconds or 15.0), 15.0)

            hook_title = topic.get("topic_title", "প্রযুক্তির বিস্ময়")
            dialogue_lines = [d.get("text", "") for d in script.get("dialogues", []) if d.get("text")]
            subtitle_line = dialogue_lines[0] if dialogue_lines else hook_title

            # Generate ASS subtitle for flawless Bengali text shaping (HarfBuzz)
            ass_path = temp_mgr.get_path("typography_overlay.ass")
            self.create_ass_file(
                ass_path=ass_path,
                w=w,
                h=h,
                duration=max_duration,
                title_text=hook_title,
                subtitle_text=subtitle_line,
                font_name="Nirmala UI",
            )
            escaped_ass = ass_path.replace("\\", "/").replace(":", r"\:")

            # 4. Construct Single-Pass Streaming FFmpeg Command
            os.makedirs(os.path.dirname(output_mp4_path) or ".", exist_ok=True)

            cmd = [
                ffmpeg_bin, "-y",
                "-ss", "00:00:01",
                "-i", candidate.local_path,
            ]

            has_tts = tts_audio_path and os.path.exists(tts_audio_path)
            has_music = music_path and os.path.exists(music_path)

            if has_tts:
                cmd.extend(["-i", tts_audio_path])
            if has_music:
                cmd.extend(["-i", music_path])

            # Video Filtergraph
            # Scale & 9:16 Crop, then apply ASS overlay
            vf_string = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,ass='{escaped_ass}'"

            # Audio Mixing Filtergraph
            if has_tts and has_music:
                filter_complex = f"[0:v]{vf_string}[v];[1:a]volume=1.0[atmp];[2:a]volume=0.15[amusic];[atmp][amusic]amix=inputs=2:duration=first:dropout_transition=2[a]"
                cmd.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"])
            elif has_tts:
                filter_complex = f"[0:v]{vf_string}[v];[1:a]volume=1.0[a]"
                cmd.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"])
            elif has_music:
                filter_complex = f"[0:v]{vf_string}[v];[1:a]volume=0.3[a]"
                cmd.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"])
            else:
                cmd.extend(["-vf", vf_string, "-an"])

            cmd.extend([
                "-c:v", "libx264",
                "-preset", render_settings.codec_preset or "ultrafast",
                "-crf", str(render_settings.crf or 28),
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-t", str(max_duration),
                "-shortest",
                output_mp4_path,
            ])

            logger.info(f"[stock_edit] Executing FFmpeg streaming composition -> {output_mp4_path}...")
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
            logger.info(f"[stock_edit] Video composition completed: {output_mp4_path}")

            # 5. Record Audit Licensing
            self.license_mgr.record_usage(
                clip_id=candidate.clip_id,
                provider=candidate.provider,
                source_url=candidate.source_url,
                license_note=candidate.license_note,
                music_source=music_source_url,
                topic=topic.get("topic_title", ""),
                video_path=output_mp4_path,
            )

            return ContentRenderResult(
                video_path=output_mp4_path,
                content_source=self.name,
                duration_sec=max_duration,
                metadata={
                    "clip_id": candidate.clip_id,
                    "provider": candidate.provider,
                    "source_url": candidate.source_url,
                    "license_note": candidate.license_note,
                },
            )

        finally:
            # 6. Clean up temporary downloaded clip
            if candidate and candidate.local_path:
                self.provider.cleanup_clip(candidate.local_path)
