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
    res = pipeline.run_daily_pipeline()

    assert "success" in res
    assert res["success"] is True


def test_partial_recovery_resumes_upload_without_rerender(tmp_path):
    """
    Simulates a pending/partial upload recovery scenario where video rendering
    previously succeeded, but an upload failed or was interrupted.
    Verifies that _resume_uploads correctly handles metadata dict or string title
    and updates the job status to PUBLISHED in DRY_RUN mode without re-rendering.
    """
    env = get_env_settings()
    env.DRY_RUN = True

    # Create dummy master mp4
    dummy_video = tmp_path / "final.mp4"
    dummy_video.write_bytes(b"DUMMY_MP4_CONTENT")

    pipeline = DailyCartoonAutomationPipeline()

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
    assert job.status == JobStatus.PUBLISHED

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
    assert job2.status == JobStatus.PUBLISHED
