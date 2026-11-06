import os
import pytest
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import DailyJobState, JobStatus
from app.jobs.manager import DailyJobManager
from app.utils.config import get_env_settings


def test_cartoon_workflow_dry_run():
    env = get_env_settings()
    env.DRY_RUN = True

    pipeline = DailyCartoonAutomationPipeline()
    pipeline.project_cfg.facebook_enabled = True
    pipeline.project_cfg.youtube_enabled = True
    res = pipeline.run_daily_pipeline()

    assert "success" in res
    assert res["success"] is True
    assert res["job_status"] == JobStatus.DRY_RUN_COMPLETE


from unittest.mock import patch
from app.facebook.reels import FacebookReelPublisher
from app.facebook.stories import FacebookStoryPublisher
from app.youtube.publisher import YouTubeShortsPublisher


def test_dry_run_does_not_block_same_day_real_run(tmp_path):
    """
    Verifies that a job marked DRY_RUN_COMPLETE does not get treated as 'Already published'
    and allows a subsequent real run on the same day.
    Mocks platform publishers so NO real network calls are made during the live run simulation.
    """
    env = get_env_settings()
    dummy_video = tmp_path / "final.mp4"
    dummy_video.write_bytes(b"DUMMY_MP4_CONTENT")

    pipeline = DailyCartoonAutomationPipeline()
    pipeline.project_cfg.facebook_enabled = True
    pipeline.project_cfg.youtube_enabled = True

    # Step 1: Simulate completed dry run
    env.DRY_RUN = True
    job = DailyJobState(
        date="2026-11-05",
        job_id="test-same-day-job",
        status=JobStatus.READY_TO_UPLOAD,
        video_path=str(dummy_video),
        topic_title="Dry Run Story",
    )
    res_dry = pipeline._resume_uploads(job, str(dummy_video), metadata={"title": "Dry Run Story"})
    assert res_dry["success"] is True
    assert res_dry["job_status"] == JobStatus.DRY_RUN_COMPLETE
    assert job.status == JobStatus.DRY_RUN_COMPLETE

    # Step 2: Now switch to live run (DRY_RUN = False)
    # Ensure that DRY_RUN_COMPLETE is not blocked as JobStatus.PUBLISHED
    assert job.status != JobStatus.PUBLISHED

    env.DRY_RUN = False
    job.facebook_reel = "PENDING"
    job.youtube_status = "PENDING"

    # Mock all publishers so real network calls are never attempted
    with patch.object(FacebookReelPublisher, "publish_reel", return_value={"success": True, "reel_id": "MOCK_LIVE_REEL_123"}), \
         patch.object(FacebookStoryPublisher, "publish_story", return_value={"success": True, "story_id": "MOCK_LIVE_STORY_123"}), \
         patch.object(YouTubeShortsPublisher, "publish_short", return_value={"success": True, "video_id": "MOCK_LIVE_YT_123"}):
        res_live = pipeline._resume_uploads(job, str(dummy_video), metadata={"title": "Live Run Story"})

    assert res_live["success"] is True
    assert res_live["job_status"] == JobStatus.PUBLISHED
    assert job.status == JobStatus.PUBLISHED
    assert job.facebook_reel == "SUCCESS"
    assert job.youtube_status == "SUCCESS"


def test_partial_recovery_resumes_upload_without_rerender(tmp_path):
    """
    Simulates a pending/partial upload recovery scenario where video rendering
    previously succeeded, but an upload failed or was interrupted.
    Verifies that _resume_uploads correctly handles metadata dict or string title
    and updates the job status to DRY_RUN_COMPLETE in DRY_RUN mode without re-rendering.
    """
    env = get_env_settings()
    env.DRY_RUN = True

    # Create dummy master mp4
    dummy_video = tmp_path / "final.mp4"
    dummy_video.write_bytes(b"DUMMY_MP4_CONTENT")

    pipeline = DailyCartoonAutomationPipeline()
    pipeline.project_cfg.facebook_enabled = True
    pipeline.project_cfg.youtube_enabled = True

    # Create job in PARTIALLY_PUBLISHED state (e.g. Facebook succeeded, YouTube pending)
    job = DailyJobState(
        date="2026-11-05",
        job_id="test-partial-recovery-job",
        status=JobStatus.PARTIALLY_PUBLISHED,
        video_path=str(dummy_video),
        topic_title="AI Robot Test Story",
        facebook_reel="SUCCESS",
        youtube_status="PENDING",
    )

    # 1. Test recovery with dictionary metadata
    res = pipeline._resume_uploads(job, str(dummy_video), metadata={"title": "Custom Title"})
    assert res["success"] is True
    assert job.youtube_status == "SUCCESS"
    assert job.status == JobStatus.DRY_RUN_COMPLETE

    # 2. Test recovery with string metadata (ensuring no AttributeError)
    job2 = DailyJobState(
        date="2026-11-05",
        job_id="test-partial-recovery-job-2",
        status=JobStatus.PARTIALLY_PUBLISHED,
        video_path=str(dummy_video),
        topic_title="AI Robot Test Story 2",
        facebook_reel="SUCCESS",
        youtube_status="PENDING",
    )
    res2 = pipeline._resume_uploads(job2, str(dummy_video), metadata="Custom String Title")
    assert res2["success"] is True
    assert job2.youtube_status == "SUCCESS"
    assert job2.status == JobStatus.DRY_RUN_COMPLETE
