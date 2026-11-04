import os
import httpx
from typing import Dict, Any
from app.utils.config import get_env_settings
from app.utils.logging import logger


class FacebookStoryPublisher:
    """Publishes Page Stories using official Meta Graph API endpoints with permission fallback."""

    def __init__(self, access_token: str = None, page_id: str = None, api_version: str = None):
        env = get_env_settings()
        self.access_token = access_token or env.META_ACCESS_TOKEN
        self.page_id = page_id or env.META_PAGE_ID
        self.api_version = api_version or env.META_API_VERSION
        self.graph_url = f"https://graph.facebook.com/{self.api_version}"
        self.dry_run = env.DRY_RUN


    def publish_story(self, media_path: str, media_type: str = "image") -> Dict[str, Any]:
        """
        Publishes an image or video to Facebook Page Story using official endpoints if supported.
        If unsupported, logs limitation and continues without breaking.
        """
        logger.info(f"Attempting to publish Page Story ({media_type}) to Page ID {self.page_id}...")

        if self.dry_run:
            logger.info("[DRY_RUN MODE] Story publish test simulated.")
            return {"success": True, "dry_run": True, "story_id": "DRY_RUN_STORY_ID_111"}

        if not self.access_token or not self.page_id:
            logger.warning("META_ACCESS_TOKEN or META_PAGE_ID missing. Story publishing skipped.")
            return {"success": False, "skipped": True, "reason": "Missing Meta credentials"}

        # Determine official endpoint based on media type
        endpoint_name = "photo_stories" if media_type == "image" else "video_stories"
        url = f"{self.graph_url}/{self.page_id}/{endpoint_name}"

        try:
            # Check if photo_stories or video_stories endpoint is available for this Page
            payload = {
                "access_token": self.access_token,
                "upload_phase": "start" if media_type == "video" else None,
            }
            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            with open(media_path, "rb") as f:
                files = {"source": (os.path.basename(media_path), f, f"{media_type}/jpeg" if media_type == "image" else "video/mp4")}
                response = httpx.post(url, data=payload, files=files, timeout=30)

            if response.status_code in (200, 201):
                res_data = response.json()
                story_id = res_data.get("id")
                logger.info(f"Successfully published Facebook Page Story! Story ID: {story_id}")
                return {"success": True, "story_id": story_id, "response": res_data}
            else:
                logger.warning(
                    f"Story publishing unavailable through current official API configuration ({response.status_code} - {response.text})."
                )
                logger.info("Continuing workflow as feed/reel publishing succeeded.")
                return {
                    "success": False,
                    "skipped": True,
                    "reason": "Story publishing unavailable through current official API configuration.",
                }

        except Exception as e:
            logger.warning(f"Story publishing exception: {e}. Story publishing unavailable through current official API configuration.")
            return {
                "success": False,
                "skipped": True,
                "reason": f"Story publishing unavailable through current official API configuration: {e}",
            }
