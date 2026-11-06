"""
tests/test_publisher_device.py
===============================
Tests for publisher_device authorization setting:
- When PUBLISHER_DEVICE=False, forces DRY_RUN behavior and logs warning even if DRY_RUN=False
- When PUBLISHER_DEVICE=True and DRY_RUN=False, allows real publication flow
- YouTubeShortsPublisher enforces publisher_device check
"""

from unittest.mock import MagicMock, patch
import pytest

from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import DailyJobState, JobStatus
from app.youtube.publisher import YouTubeShortsPublisher


def test_publisher_device_false_forces_dry_run_in_pipeline(tmp_path):
    """If publisher_device is False, pipeline must end in DRY_RUN_COMPLETE even if DRY_RUN is False."""
    pipeline = DailyCartoonAutomationPipeline()
    pipeline.env_cfg.DRY_RUN = False
    pipeline.project_cfg.dry_run = False
    pipeline.project_cfg.publisher_device = False
    pipeline.env_cfg.PUBLISHER_DEVICE = None
    pipeline.project_cfg.youtube_enabled = True
    pipeline.project_cfg.facebook_enabled = False
    pipeline.project_cfg.instagram_enabled = False

    job = DailyJobState(
        date="2026-11-06",
        job_id="2026-11-06-test",
        status=JobStatus.READY_TO_UPLOAD,
        video_path=str(tmp_path / "final.mp4"),
    )

    with patch.object(YouTubeShortsPublisher, "publish_short") as mock_yt:
        mock_yt.return_value = {
            "success": True,
            "dry_run": True,
            "video_id": "DRY_RUN_YOUTUBE_SHORTS_99999",
        }
        res = pipeline._resume_uploads(job, job.video_path, metadata={"title": "Test Title"})

        assert res["success"] is True
        assert res["job_status"] == JobStatus.DRY_RUN_COMPLETE.value
        assert job.status == JobStatus.DRY_RUN_COMPLETE


def test_publisher_device_env_override_takes_precedence(tmp_path):
    """PUBLISHER_DEVICE=False in env overrides project_config.publisher_device=True."""
    pipeline = DailyCartoonAutomationPipeline()
    pipeline.env_cfg.DRY_RUN = False
    pipeline.project_cfg.dry_run = False
    pipeline.project_cfg.publisher_device = True
    pipeline.env_cfg.PUBLISHER_DEVICE = False
    pipeline.project_cfg.youtube_enabled = True
    pipeline.project_cfg.facebook_enabled = False
    pipeline.project_cfg.instagram_enabled = False

    job = DailyJobState(
        date="2026-11-06",
        job_id="2026-11-06-test",
        status=JobStatus.READY_TO_UPLOAD,
        video_path=str(tmp_path / "final.mp4"),
    )

    with patch.object(YouTubeShortsPublisher, "publish_short") as mock_yt:
        mock_yt.return_value = {
            "success": True,
            "dry_run": True,
            "video_id": "DRY_RUN_YOUTUBE_SHORTS_99999",
        }
        res = pipeline._resume_uploads(job, job.video_path, metadata={"title": "Test Title"})

        assert res["job_status"] == JobStatus.DRY_RUN_COMPLETE.value
        assert job.status == JobStatus.DRY_RUN_COMPLETE


def test_publisher_device_false_in_youtube_publisher():
    """YouTubeShortsPublisher forces dry run when publisher_device is False."""
    publisher = YouTubeShortsPublisher()
    publisher.env.DRY_RUN = False
    publisher.project_cfg.dry_run = False
    publisher.project_cfg.publisher_device = False
    publisher.env.PUBLISHER_DEVICE = None

    res = publisher.publish_short(
        video_path="dummy.mp4",
        title="Test Short",
        description="Description",
    )

    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["video_id"] == "DRY_RUN_YOUTUBE_SHORTS_99999"


def test_publisher_device_true_allows_publication(tmp_path):
    """When publisher_device=True and DRY_RUN=False, pipeline transitions to PUBLISHED."""
    pipeline = DailyCartoonAutomationPipeline()
    pipeline.env_cfg.DRY_RUN = False
    pipeline.project_cfg.dry_run = False
    pipeline.project_cfg.publisher_device = True
    pipeline.env_cfg.PUBLISHER_DEVICE = None
    pipeline.project_cfg.youtube_enabled = True
    pipeline.project_cfg.facebook_enabled = False
    pipeline.project_cfg.instagram_enabled = False

    job = DailyJobState(
        date="2026-11-06",
        job_id="2026-11-06-test",
        status=JobStatus.READY_TO_UPLOAD,
        video_path=str(tmp_path / "final.mp4"),
    )

    with patch.object(YouTubeShortsPublisher, "publish_short") as mock_yt:
        mock_yt.return_value = {
            "success": True,
            "dry_run": False,
            "video_id": "REAL_YT_VIDEO_123",
        }
        res = pipeline._resume_uploads(job, job.video_path, metadata={"title": "Test Title"})

        assert res["success"] is True
        assert res["job_status"] == JobStatus.PUBLISHED.value
        assert job.status == JobStatus.PUBLISHED
