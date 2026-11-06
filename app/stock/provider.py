"""
app/stock/provider.py
=====================
Unified stock video provider for vertical shorts.
Waterfall search strategy:
1. Pexels Video API (Free commercial license, portrait orientation)
2. Pixabay Video API (Free license, filtered for duration and aspect ratio)
3. Local Stock Library (assets/stock_videos/*.mp4)
If no matching clip is found across all providers, raises NoClipFoundError.
"""

import glob
import math
import os
import shutil
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from app.hardware.profiles import RenderSettings
from app.stock.license_log import StockLicenseManager
from app.utils.config import get_env_settings
from app.utils.logging import logger
from app.video.quality import VideoQualityChecker


class NoClipFoundError(RuntimeError):
    """Raised when no suitable stock video clip is found across any provider."""
    pass


class StockClipCandidate(BaseModel):
    """Metadata for a candidate stock footage clip."""

    clip_id: str = Field(description="Unique provider-scoped clip ID")
    provider: str = Field(description="Source provider: pexels, pixabay, or local")
    download_url: Optional[str] = Field(default=None, description="Remote download URL")
    local_path: Optional[str] = Field(default=None, description="Local downloaded file path")
    width: int = Field(default=720, description="Video width in pixels")
    height: int = Field(default=1280, description="Video height in pixels")
    duration: float = Field(default=15.0, description="Clip duration in seconds")
    source_url: str = Field(default="", description="Webpage or asset source path")
    license_note: str = Field(default="", description="Legal license terms")


class StockVideoProvider:
    """Orchestrates stock video clip retrieval with waterfall fallback and caching."""

    DEFAULT_CACHE_DIR = "output/stock_cache"
    DEFAULT_LOCAL_DIR = "assets/stock_videos"
    MAX_CACHE_BYTES = 300 * 1024 * 1024  # 300 MB

    def __init__(
        self,
        cache_dir: str = DEFAULT_CACHE_DIR,
        local_dir: str = DEFAULT_LOCAL_DIR,
        license_manager: Optional[StockLicenseManager] = None,
    ):
        self.cache_dir = cache_dir
        self.local_dir = local_dir
        self.license_mgr = license_manager or StockLicenseManager()
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.local_dir, exist_ok=True)

    def find_and_prepare_clip(
        self,
        keyword: str,
        render_settings: Optional[RenderSettings] = None,
        min_duration: float = 8.0,
        max_duration: float = 30.0,
    ) -> StockClipCandidate:
        """
        Executes waterfall search for a matching clip.
        Downloads remote clip to cache if needed, and returns candidate with populated local_path.
        Raises NoClipFoundError if all providers fail to yield a usable clip.
        """
        env = get_env_settings()
        target_w = render_settings.resolution_width if render_settings else 720
        target_h = render_settings.resolution_height if render_settings else 1280

        # 1. Pexels Video API
        pexels_key = getattr(env, "PEXELS_API_KEY", "")
        if pexels_key and pexels_key.strip():
            candidate = self._search_pexels(
                keyword=keyword,
                api_key=pexels_key.strip(),
                min_duration=min_duration,
                max_duration=max_duration,
                target_w=target_w,
                target_h=target_h,
            )
            if candidate:
                return self._download_if_needed(candidate)
        else:
            logger.debug("Pexels API key not configured. Skipping Pexels.")

        # 2. Pixabay Video API
        pixabay_key = getattr(env, "PIXABAY_API_KEY", "")
        if pixabay_key and pixabay_key.strip():
            candidate = self._search_pixabay(
                keyword=keyword,
                api_key=pixabay_key.strip(),
                min_duration=min_duration,
                max_duration=max_duration,
                target_w=target_w,
                target_h=target_h,
            )
            if candidate:
                return self._download_if_needed(candidate)
        else:
            logger.debug("Pixabay API key not configured. Skipping Pixabay.")

        # 3. Local Library Fallback (assets/stock_videos)
        candidate = self._search_local(
            min_duration=min_duration,
            max_duration=max_duration,
            target_w=target_w,
            target_h=target_h,
        )
        if candidate:
            return candidate

        # 4. Strict Failure: No clip found
        raise NoClipFoundError(
            f"No suitable stock video clip found for keyword '{keyword}' "
            f"across Pexels, Pixabay, and local assets directory ('{self.local_dir}')."
        )

    def _search_pexels(
        self,
        keyword: str,
        api_key: str,
        min_duration: float,
        max_duration: float,
        target_w: int,
        target_h: int,
    ) -> Optional[StockClipCandidate]:
        """Queries Pexels Video API for portrait clips."""
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key}
        params = {"query": keyword, "orientation": "portrait", "per_page": 15}

        try:
            logger.info(f"Querying Pexels Video API for keyword: '{keyword}'...")
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=headers, params=params)

            if res.status_code == 429:
                logger.warning("Pexels API rate limit reached (HTTP 429). Falling back to next provider.")
                return None
            if res.status_code != 200:
                logger.warning(f"Pexels API returned status {res.status_code}. Skipping Pexels.")
                return None

            data = res.json()
            videos = data.get("videos", [])
            for v in videos:
                vid_id = f"pexels_{v.get('id')}"
                if self.license_mgr.is_clip_used(vid_id):
                    continue

                duration = float(v.get("duration", 0))
                if not (min_duration <= duration <= max_duration):
                    continue

                # Filter video files for portrait orientation and nearest resolution
                files = v.get("video_files", [])
                portrait_files = [f for f in files if int(f.get("width", 0)) < int(f.get("height", 0))]
                if not portrait_files:
                    continue

                # Sort by distance to target resolution
                def _res_distance(f):
                    w = int(f.get("width", 0))
                    h = int(f.get("height", 0))
                    return abs(w - target_w) + abs(h - target_h)

                best_file = min(portrait_files, key=_res_distance)
                download_link = best_file.get("link")
                if not download_link:
                    continue

                logger.info(f"Selected Pexels clip: {vid_id} ({best_file.get('width')}x{best_file.get('height')}, {duration}s)")
                return StockClipCandidate(
                    clip_id=vid_id,
                    provider="pexels",
                    download_url=download_link,
                    width=int(best_file.get("width", target_w)),
                    height=int(best_file.get("height", target_h)),
                    duration=duration,
                    source_url=v.get("url", f"https://www.pexels.com/video/{v.get('id')}/"),
                    license_note="Pexels Free License (Commercial allowed, No attribution required)",
                )
        except Exception as e:
            logger.warning(f"Pexels API search failed: {e}. Skipping Pexels.")
            return None

    def _search_pixabay(
        self,
        keyword: str,
        api_key: str,
        min_duration: float,
        max_duration: float,
        target_w: int,
        target_h: int,
    ) -> Optional[StockClipCandidate]:
        """Queries Pixabay Video API."""
        url = "https://pixabay.com/api/videos/"
        params = {"key": api_key, "q": keyword, "video_type": "film", "per_page": 15}

        try:
            logger.info(f"Querying Pixabay Video API for keyword: '{keyword}'...")
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, params=params)

            if res.status_code == 429:
                logger.warning("Pixabay API rate limit reached (HTTP 429). Falling back to next provider.")
                return None
            if res.status_code != 200:
                logger.warning(f"Pixabay API returned status {res.status_code}. Skipping Pixabay.")
                return None

            data = res.json()
            hits = data.get("hits", [])
            for hit in hits:
                vid_id = f"pixabay_{hit.get('id')}"
                if self.license_mgr.is_clip_used(vid_id):
                    continue

                duration = float(hit.get("duration", 0))
                if not (min_duration <= duration <= max_duration):
                    continue

                video_variants = hit.get("videos", {})
                # Look for medium, small, or large
                candidates = []
                for variant_name, vdata in video_variants.items():
                    w = int(vdata.get("width", 0))
                    h = int(vdata.get("height", 0))
                    link = vdata.get("url")
                    if link and w > 0 and h > 0:
                        candidates.append((w, h, link))

                if not candidates:
                    continue

                # Prefer portrait (w < h), else pick closest resolution
                portrait_cands = [c for c in candidates if c[0] < c[1]]
                chosen_pool = portrait_cands if portrait_cands else candidates

                def _dist(c):
                    return abs(c[0] - target_w) + abs(c[1] - target_h)

                best_w, best_h, best_url = min(chosen_pool, key=_dist)
                logger.info(f"Selected Pixabay clip: {vid_id} ({best_w}x{best_h}, {duration}s)")
                return StockClipCandidate(
                    clip_id=vid_id,
                    provider="pixabay",
                    download_url=best_url,
                    width=best_w,
                    height=best_h,
                    duration=duration,
                    source_url=hit.get("pageURL", f"https://pixabay.com/videos/id-{hit.get('id')}/"),
                    license_note="Pixabay Content License (Free for commercial use, No attribution required)",
                )
        except Exception as e:
            logger.warning(f"Pixabay API search failed: {e}. Skipping Pixabay.")
            return None

    def _search_local(
        self,
        min_duration: float,
        max_duration: float,
        target_w: int,
        target_h: int,
    ) -> Optional[StockClipCandidate]:
        """Scans local stock assets directory for available, unused vertical video files."""
        patterns = [os.path.join(self.local_dir, "*.mp4"), os.path.join(self.local_dir, "*.mov")]
        local_files = []
        for pat in patterns:
            local_files.extend(glob.glob(pat))

        for file_path in local_files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            clip_id = f"local_{base_name}"
            if self.license_mgr.is_clip_used(clip_id):
                continue

            # Probe video metadata
            meta = VideoQualityChecker.probe_video_metadata(file_path)
            if not meta.get("has_video"):
                continue

            dur = meta.get("duration_sec", 0.0)
            if not (min_duration <= dur <= max_duration):
                continue

            w = meta.get("width", target_w)
            h = meta.get("height", target_h)

            logger.info(f"Selected Local Stock clip: {clip_id} ({w}x{h}, {dur}s) from {file_path}")
            return StockClipCandidate(
                clip_id=clip_id,
                provider="local",
                local_path=file_path,
                width=w,
                height=h,
                duration=dur,
                source_url=file_path,
                license_note="Local Royalty-Free Stock Asset",
            )
        return None

    def _download_if_needed(self, candidate: StockClipCandidate) -> StockClipCandidate:
        """Downloads remote clip to local cache directory with size cap enforcement."""
        if candidate.local_path and os.path.exists(candidate.local_path):
            return candidate

        if not candidate.download_url:
            return candidate

        dest_file = os.path.join(self.cache_dir, f"{candidate.provider}_{candidate.clip_id}.mp4")
        if os.path.exists(dest_file) and os.path.getsize(dest_file) > 1024:
            candidate.local_path = dest_file
            return candidate

        self._enforce_cache_size_cap()

        logger.info(f"Downloading stock clip {candidate.clip_id} to {dest_file}...")
        try:
            with httpx.Client(timeout=30.0) as client:
                with client.stream("GET", candidate.download_url) as resp:
                    resp.raise_for_status()
                    with open(dest_file, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
            candidate.local_path = dest_file
            logger.info(f"Successfully downloaded stock clip ({os.path.getsize(dest_file)} bytes).")
            return candidate
        except Exception as e:
            logger.error(f"Failed to download stock clip {candidate.clip_id}: {e}")
            if os.path.exists(dest_file):
                try:
                    os.remove(dest_file)
                except Exception:
                    pass
            raise RuntimeError(f"Could not download stock clip: {e}")

    def _enforce_cache_size_cap(self):
        """Purges oldest cached clips if total cache exceeds MAX_CACHE_BYTES."""
        try:
            cached_files = [
                os.path.join(self.cache_dir, f)
                for f in os.listdir(self.cache_dir)
                if os.path.isfile(os.path.join(self.cache_dir, f))
            ]
            total_size = sum(os.path.getsize(f) for f in cached_files)
            if total_size > self.MAX_CACHE_BYTES:
                # Sort oldest modified first
                cached_files.sort(key=lambda f: os.path.getmtime(f))
                while total_size > self.MAX_CACHE_BYTES and cached_files:
                    oldest = cached_files.pop(0)
                    sz = os.path.getsize(oldest)
                    try:
                        os.remove(oldest)
                        total_size -= sz
                        logger.info(f"Purged cached stock clip to preserve disk limit: {oldest}")
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Cache size enforcement error: {e}")

    def cleanup_clip(self, local_path: Optional[str]):
        """Removes a downloaded stock clip file from cache after video rendering."""
        if not local_path or not os.path.exists(local_path):
            return
        # Only delete files located in the cache directory, never delete files in local assets
        cache_abs = os.path.abspath(self.cache_dir)
        file_abs = os.path.abspath(local_path)
        if file_abs.startswith(cache_abs):
            try:
                os.remove(file_abs)
                logger.info(f"Cleaned up cached stock clip: {local_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up cached clip {local_path}: {e}")

