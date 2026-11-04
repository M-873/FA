import os
from typing import Dict, Any
from app.utils.config import get_env_settings
from app.utils.logging import logger
from app.utils.retry import with_retry
from app.youtube.auth import YouTubeAuthManager


class YouTubeShortsPublisher:
    """Publishes the SAME master final.mp4 video file to YouTube Shorts via YouTube Data API v3."""

    def __init__(self):
        self.env = get_env_settings()
        self.auth_mgr = YouTubeAuthManager()

    @with_retry(max_retries=3)
    def publish_short(
        self,
        video_path: str,
        title: str,
        description: str,
        hashtags: list,
    ) -> Dict[str, Any]:
        """
        Uploads master video file to YouTube Shorts.
        Guarantees SAME video file is uploaded without re-rendering.
        """
        logger.info(f"Preparing YouTube Shorts upload for master file: {video_path}...")

        if self.env.DRY_RUN:
            logger.info("[DRY_RUN MODE] Skipping actual YouTube API upload.")
            logger.info(f"[DRY_RUN YOUTUBE TITLE] {title} #Shorts")
            logger.info(f"[DRY_RUN MASTER VIDEO PATH] {video_path}")
            return {
                "success": True,
                "dry_run": True,
                "video_id": "DRY_RUN_YOUTUBE_VIDEO_ID_99999",
            }

        service = self.auth_mgr.get_authenticated_service()
        if not service:
            logger.warning("YouTube service not authenticated. Skipping live upload.")
            return {"success": False, "reason": "Unauthenticated YouTube OAuth"}

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Master video file not found: {video_path}")

        # Format title to include #Shorts tag
        full_title = f"{title} #Shorts"[:100]
        tags_list = [t.replace("#", "") for t in hashtags] + ["Shorts", "Short"]

        body = {
            "snippet": {
                "title": full_title,
                "description": f"{description}\n\n{' '.join(hashtags)}",
                "tags": tags_list,
                "categoryId": "28",  # Science & Technology
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
            from googleapiclient.http import MediaFileUpload

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
            request = service.videos().insert(part="snippet,status", body=body, media_body=media)

            logger.info("Uploading video stream to YouTube...")
            response = request.execute()
            video_id = response.get("id")

            logger.info(f"Successfully uploaded YouTube Short! Video ID: {video_id}")
            return {
                "success": True,
                "video_id": video_id,
                "response": response,
            }
        except Exception as e:
            logger.error(f"YouTube Shorts upload failed: {e}")
            raise e
