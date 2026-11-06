"""
app/stock/license_log.py
========================
Audit log and deduplication registry for stock footage and music assets.
Persists records in JSON to ensure every clip is tracked and no clip is reused.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from app.utils.logging import logger


class StockLicenseRecord(BaseModel):
    """Schema for a stock footage licensing record."""

    clip_id: str = Field(description="Unique clip identifier e.g. pexels_123456")
    provider: str = Field(description="Provider name: pexels, pixabay, or local")
    source_url: str = Field(description="Direct URL to stock page or asset path")
    license_note: str = Field(description="License terms e.g. Pexels Free License")
    music_source: str = Field(
        default="UNVERIFIED",
        description="Verifiable source URL for background music, or 'UNVERIFIED'"
    )
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    topic: str = Field(default="", description="Topic or headline of the short")
    video_path: str = Field(default="output/final.mp4", description="Master output video path")


class StockLicenseManager:
    """Manages audit logging and reuse blocking for stock assets."""

    DEFAULT_LOG_PATH = "output/stock_license_log.json"

    def __init__(self, log_path: str = DEFAULT_LOG_PATH):
        self.log_path = log_path
        self._used_ids_cache: Optional[Set[str]] = None

    def _ensure_dir(self):
        log_dir = os.path.dirname(self.log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    def load_records(self) -> List[StockLicenseRecord]:
        """Loads all logged license records from disk."""
        if not os.path.exists(self.log_path):
            return []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [StockLicenseRecord.model_validate(item) for item in data]
        except Exception as e:
            logger.warning(f"Could not read stock license log from {self.log_path}: {e}")
        return []

    def get_used_clip_ids(self) -> Set[str]:
        """Returns set of all clip IDs that have already been used."""
        records = self.load_records()
        self._used_ids_cache = {r.clip_id for r in records}
        return self._used_ids_cache

    def is_clip_used(self, clip_id: str) -> bool:
        """Checks if a clip ID has already been utilized in a published or rendered job."""
        if self._used_ids_cache is None:
            self.get_used_clip_ids()
        return clip_id in self._used_ids_cache

    def record_usage(
        self,
        clip_id: str,
        provider: str,
        source_url: str,
        license_note: str,
        music_source: Optional[str] = None,
        date: Optional[str] = None,
        topic: str = "",
        video_path: str = "output/final.mp4",
    ) -> StockLicenseRecord:
        """
        Appends a license record to the audit log and updates the in-memory deduplication set.
        """
        self._ensure_dir()
        music_val = music_source.strip() if music_source and music_source.strip() else "UNVERIFIED"
        record = StockLicenseRecord(
            clip_id=clip_id,
            provider=provider,
            source_url=source_url,
            license_note=license_note,
            music_source=music_val,
            date=date or datetime.now().strftime("%Y-%m-%d"),
            topic=topic,
            video_path=video_path,
        )

        records = self.load_records()
        records.append(record)

        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([r.model_dump() for r in records], f, indent=2, ensure_ascii=False)
            if self._used_ids_cache is not None:
                self._used_ids_cache.add(clip_id)
            logger.info(f"Recorded stock license log: {clip_id} ({provider}) -> {self.log_path}")
        except Exception as e:
            logger.error(f"Failed to write stock license log: {e}")

        return record

