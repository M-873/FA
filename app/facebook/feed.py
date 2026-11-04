import os
import httpx
from typing import Dict, Any
from app.utils.config import get_env_settings
from app.utils.logging import logger
from app.utils.retry import with_retry


class FacebookFeedPublisher:
    """Publishes daily images and captions to Facebook Page Feed via Meta Graph API."""

    def __init__(self, access_token: str = None, page_id: str = None, api_version: str = None):
        env = get_env_settings()
        self.access_token = access_token or env.META_ACCESS_TOKEN
        self.page_id = page_id or env.META_PAGE_ID
        self.api_version = api_version or env.META_API_VERSION
        self.graph_url = f"https://graph.facebook.com/{self.api_version}"
        self.dry_run = env.DRY_RUN


    @with_retry(max_retries=3)
    def publish_image_post(self, image_path: str, caption: str) -> Dict[str, Any]:
        """
        Uploads photo and publishes post on Facebook Page timeline.
        """
        logger.info(f"Preparing to publish daily image post to Facebook Page feed (ID: {self.page_id})...")

        if self.dry_run:
            logger.info("[DRY_RUN MODE] Skipping actual Meta API post request.")
            logger.info(f"[DRY_RUN POST CAPTION]\n{caption}")
            logger.info(f"[DRY_RUN IMAGE PATH] {image_path}")
            return {
                "success": True,
                "dry_run": True,
                "post_id": "DRY_RUN_FEED_POST_ID_12345",
            }

        if not self.access_token or not self.page_id:
            raise ValueError("META_ACCESS_TOKEN and META_PAGE_ID are required for live publishing.")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        url = f"{self.graph_url}/{self.page_id}/photos"
        payload = {
            "caption": caption,
            "access_token": self.access_token,
            "published": "true",
        }

        with open(image_path, "rb") as img_file:
            files = {"source": (os.path.basename(image_path), img_file, "image/jpeg")}
            logger.info(f"POST {url}...")
            response = httpx.post(url, data=payload, files=files, timeout=60)

        if response.status_code in (200, 201):
            res_data = response.json()
            post_id = res_data.get("post_id", res_data.get("id"))
            logger.info(f"Successfully published Facebook Feed post! Post ID: {post_id}")
            return {
                "success": True,
                "post_id": post_id,
                "response": res_data,
            }
        else:
            logger.error(f"Failed to publish Facebook Feed post: {response.status_code} - {response.text}")
            response.raise_for_status()
            return {"success": False, "error": response.text}
