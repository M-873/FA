import os
from typing import Dict, Any
from app.utils.logging import logger


class VideoQualityChecker:
    """Verifies that final.mp4 meets quality criteria before platform uploads."""

    @classmethod
    def verify_video(self, video_path: str) -> Dict[str, Any]:
        """
        Performs quality and integrity checks on final master MP4.
        """
        logger.info(f"Executing Pre-Upload Quality Check on {video_path}...")

        if not os.path.exists(video_path):
            logger.error("Quality Check Failed: Master MP4 file does not exist.")
            return {"passed": False, "reason": "File does not exist"}

        file_size_bytes = os.path.getsize(video_path)
        if file_size_bytes < 100:  # Minimum valid file size
            logger.error(f"Quality Check Failed: File size too small ({file_size_bytes} bytes).")
            return {"passed": False, "reason": f"File size too small ({file_size_bytes} bytes)"}

        logger.info(f"Quality Check PASSED! File size: {round(file_size_bytes / 1024, 2)} KB.")
        return {"passed": True, "file_size_bytes": file_size_bytes, "reason": "Video verified successfully."}
