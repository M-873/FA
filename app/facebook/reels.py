import os
import httpx
from typing import Dict, Any
from app.utils.config import get_env_settings
from app.utils.logging import logger
from app.utils.retry import with_retry


class FacebookReelPublisher:
    """Publishes weekly AI video reels to Facebook Page via official Meta Reels Graph API."""

    def __init__(self, access_token: str = None, page_id: str = None, api_version: str = None):
        env = get_env_settings()
        self.access_token = access_token or env.META_ACCESS_TOKEN
        self.page_id = page_id or env.META_PAGE_ID
        self.api_version = api_version or env.META_API_VERSION
        self.graph_url = f"https://graph.facebook.com/{self.api_version}"
        self.dry_run = env.DRY_RUN


    @with_retry(max_retries=3)
    def publish_reel(self, video_path: str, caption: str) -> Dict[str, Any]:
        """
        Publishes video as a Facebook Reel using 3-step Reels Upload Session API.
        """
        logger.info(f"Preparing to publish weekly Reel to Facebook Page (ID: {self.page_id})...")

        if self.dry_run:
            logger.info("[DRY_RUN MODE] Skipping actual Meta Reel publishing API calls.")
            logger.info(f"[DRY_RUN REEL CAPTION]\n{caption}")
            logger.info(f"[DRY_RUN VIDEO PATH] {video_path}")
            return {
                "success": True,
                "dry_run": True,
                "reel_id": "DRY_RUN_REEL_ID_67890",
            }

        if not self.access_token or not self.page_id:
            logger.info("Facebook META_ACCESS_TOKEN or META_PAGE_ID not configured yet. Skipping Facebook upload.")
            return {"success": False, "skipped": True, "reason": "Facebook credentials not configured"}

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        file_size = os.path.getsize(video_path)

        # Step 1: Initialize Reel Upload Session
        init_url = f"{self.graph_url}/{self.page_id}/video_reels"
        init_params = {
            "upload_phase": "start",
            "access_token": self.access_token,
        }

        logger.info("Initializing Reel upload session with Meta Graph API...")
        init_res = httpx.post(init_url, params=init_params, timeout=30)
        if init_res.status_code not in (200, 201):
            logger.error(f"Reel upload initialization failed: {init_res.status_code} - {init_res.text}")
            init_res.raise_for_status()

        init_data = init_res.json()
        video_id = init_data.get("video_id")
        upload_url = init_data.get("upload_url")

        logger.info(f"Reel session initialized. Video ID: {video_id}. Uploading binary video...")

        # Step 2: Upload Binary Video File
        upload_headers = {
            "Authorization": f"OAuth {self.access_token}",
            "file_offset": "0",
        }
        with open(video_path, "rb") as video_file:
            upload_res = httpx.post(upload_url, headers=upload_headers, content=video_file.read(), timeout=120)

        if upload_res.status_code not in (200, 201):
            logger.error(f"Reel video file upload failed: {upload_res.status_code} - {upload_res.text}")
            upload_res.raise_for_status()

        # Step 3: Finish and Publish Reel
        finish_params = {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": self.access_token,
        }
        logger.info("Finalizing Reel publishing...")
        finish_res = httpx.post(init_url, params=finish_params, timeout=30)

        if finish_res.status_code in (200, 201):
            result_data = finish_res.json()
            logger.info(f"Successfully published Facebook Reel! Reel ID: {video_id}")
            return {
                "success": True,
                "reel_id": video_id,
                "response": result_data,
            }
        else:
            logger.error(f"Reel publish finalization failed: {finish_res.status_code} - {finish_res.text}")
            finish_res.raise_for_status()
            return {"success": False, "error": finish_res.text}
