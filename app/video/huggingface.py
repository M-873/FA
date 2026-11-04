import os
import time
from typing import Optional
from huggingface_hub import InferenceClient

from app.utils.config import get_env_settings
from app.utils.logging import logger
from app.utils.retry import with_retry


class HuggingFaceVideoGenerator:
    """Weekly AI Video Generator using Hugging Face Inference API."""

    def __init__(self, token: str = None, model: str = None, provider: str = None):
        env = get_env_settings()
        self.token = token or env.HF_TOKEN
        self.model = model or env.HF_VIDEO_MODEL
        self.provider = provider or env.HF_PROVIDER
        self.max_retries = env.MAX_RETRIES


    @with_retry(max_retries=3)
    def generate_video(self, prompt: str, output_path: str) -> str:
        """
        Generates 3-10 second AI video from text prompt using Hugging Face Inference API.
        """
        logger.info(f"Initiating Hugging Face video generation with model '{self.model}' (provider: '{self.provider}')...")

        if not self.token:
            logger.warning("HF_TOKEN is missing. Creating fallback sample video for testing.")
            return self._create_placeholder_video(output_path)

        try:
            client = InferenceClient(
                provider=self.provider if self.provider else None,
                api_key=self.token,
            )

            logger.info("Sending text_to_video request to Hugging Face...")
            video_bytes = client.text_to_video(
                prompt,
                model=self.model,
            )

            with open(output_path, "wb") as f:
                f.write(video_bytes)

            logger.info(f"Successfully generated and downloaded HF video to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Hugging Face video generation failed: {e}")
            raise e

    def _create_placeholder_video(self, output_path: str) -> str:
        """Creates a mock/synthetic video file for dry run mode or when HF token is missing."""
        # Create a simple synthetic video file using OpenCV/Pillow if available, or write a dummy file structure
        try:
            import subprocess
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", "color=c=0x121826:s=1080x1920:d=5",
                "-vf", "drawtext=text='AI WEEKLY REEL':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Generated sample FFmpeg placeholder video at {output_path}")
            return output_path
        except Exception:
            # If FFmpeg isn't installed yet, write a placeholder byte file for structural testing
            with open(output_path, "wb") as f:
                f.write(b"MOCK_MP4_HEADER_AI_VIDEO_CONTENT")
            logger.info(f"Generated fallback raw placeholder file at {output_path}")
            return output_path
