import os
import shutil
import subprocess
from typing import Optional
from app.utils.config import get_env_settings
from app.utils.logging import logger
from app.video.ffmpeg_helper import get_ffmpeg_binary, is_ffmpeg_available


class FFmpegProcessor:
    """Processes AI generated video into Facebook Reel compliant format (9:16, MP4, H.264, AAC)."""

    def __init__(self):
        env = get_env_settings()
        self.min_duration = 3
        self.max_duration = 15
        self.ffmpeg_cmd = get_ffmpeg_binary() or "ffmpeg"

    def is_ffmpeg_available(self) -> bool:
        """Checks if FFmpeg executable is present and functional."""
        return is_ffmpeg_available()

    def process_video_for_reel(
        self,
        input_video_path: str,
        output_video_path: str,
        audio_path: Optional[str] = None,
    ) -> str:
        """
        Formats input video into 9:16 vertical MP4 (1080x1920), crops/pads appropriately,
        trims duration, and overlays low-volume background audio.
        """
        if not self.is_ffmpeg_available():
            logger.warning("FFmpeg executable not found in system PATH! Skipping FFmpeg processing step.")
            logger.warning("Please install FFmpeg on your production runtime (e.g. `apt-get install ffmpeg` or `brew install ffmpeg`).")
            # If FFmpeg is missing, copy input video directly to output
            shutil.copy(input_video_path, output_video_path)
            return output_video_path

        logger.info(f"Processing video {input_video_path} -> 9:16 vertical format using FFmpeg...")

        # FFmpeg command builder for 9:16 scaling & audio overlay
        cmd = [self.ffmpeg_cmd, "-y", "-i", input_video_path]

        if audio_path and os.path.exists(audio_path):
            logger.info(f"Mixing background audio from {audio_path} at -20dB volume...")
            cmd.extend(["-i", audio_path])
            filter_complex = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[v];"
                f"[1:a]volume=0.1,atrim=0:{self.max_duration}[a]"
            )
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "[a]",
            ])
        else:
            filter_complex = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
            cmd.extend([
                "-vf", filter_complex,
                "-an",  # no audio
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-t", str(self.max_duration),
            output_video_path,
        ])

        try:
            logger.info("Running FFmpeg encoding command...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"FFmpeg processing complete. Output saved to {output_video_path}")
            return output_video_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e.stderr}")
            # Fallback copy
            shutil.copy(input_video_path, output_video_path)
            return output_video_path
