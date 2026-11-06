from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "PENDING"
    GENERATING_TOPIC = "GENERATING_TOPIC"
    GENERATING_SCRIPT = "GENERATING_SCRIPT"
    GENERATING_VOICE = "GENERATING_VOICE"
    ANIMATING = "ANIMATING"
    RENDERING = "RENDERING"
    QUALITY_CHECK = "QUALITY_CHECK"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    READY_TO_UPLOAD = "READY_TO_UPLOAD"
    UPLOADING_FACEBOOK = "UPLOADING_FACEBOOK"
    UPLOADING_YOUTUBE = "UPLOADING_YOUTUBE"
    PUBLISHED = "PUBLISHED"
    PARTIALLY_PUBLISHED = "PARTIALLY_PUBLISHED"
    DRY_RUN_COMPLETE = "DRY_RUN_COMPLETE"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class DailyJobState(BaseModel):
    """Minimal daily job state model saved to local JSON file (daily_job.json)."""

    date: str = Field(description="Date string in YYYY-MM-DD format")
    job_id: str = Field(description="Unique job identifier e.g. 2026-08-11-main")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Overall current job status")
    video_path: Optional[str] = Field(default=None, description="Path to rendered master final.mp4")
    topic_title: Optional[str] = Field(default=None, description="Selected daily topic headline")
    content_source: str = Field(default="cartoon", description="Content source used: cartoon, stock_edit, etc.")

    # Facebook Status
    facebook_reel: str = Field(default="PENDING", description="Status: PENDING, SUCCESS, FAILED, SKIPPED")
    facebook_story: str = Field(default="PENDING", description="Status: PENDING, SUCCESS, FAILED, SKIPPED")
    facebook_post_id: Optional[str] = Field(default=None, description="Returned Facebook Post/Reel ID")

    # YouTube Status
    youtube_status: str = Field(default="PENDING", description="Status: PENDING, SUCCESS, FAILED, SKIPPED")
    youtube_video_id: Optional[str] = Field(default=None, description="Returned YouTube Video ID")

    # Instagram Status
    instagram_status: str = Field(default="SKIPPED", description="Status: PENDING, SUCCESS, FAILED, SKIPPED")
    instagram_media_id: Optional[str] = Field(default=None, description="Returned Instagram Media ID")

    # Metadata & Diagnostics
    error_message: Optional[str] = Field(default=None, description="Detailed failure diagnostic message")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    def update_status(self, new_status: JobStatus, error: Optional[str] = None):
        self.status = new_status
        self.last_updated = datetime.now().isoformat()
        if error:
            self.error_message = error
