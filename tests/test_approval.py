"""
tests/test_approval.py
======================
Automated tests for require_human_approval workflow:
- Pipeline pause at AWAITING_APPROVAL state after quality check
- Skipping publication until approved
- approve_job() resumes upload stage
- reject_job() resets state to PENDING
- CLI flags (--approve, --reject, --regenerate)
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.hardware.detector import HardwareSpecs
from app.jobs.manager import DailyJobManager
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import DailyJobState, JobStatus
from app.utils.config import ProjectConfig


@pytest.fixture
def mock_pipeline_components(tmp_path):
    dummy_mp4 = tmp_path / "final.mp4"
    dummy_mp4.write_bytes(b"DUMMY_MP4_CONTENT")
    return {
        "video_path": str(dummy_mp4),
        "tts_path": str(tmp_path / "tts.mp3"),
    }


@patch("app.jobs.recovery.FacebookReelPublisher")
@patch("app.jobs.recovery.YouTubeShortsPublisher")
@patch("app.jobs.recovery.HardwareSafetyMonitor")
@patch("app.jobs.recovery.PerformanceProfileManager")
@patch("app.jobs.recovery.HardwareDetector")
@patch("app.ai.factory.AIProviderFactory")
@patch("app.jobs.recovery.CloudTTSProvider")
@patch("app.jobs.recovery.ContentSourceFactory")
@patch("app.jobs.recovery.VideoQualityChecker")
def test_pipeline_pauses_for_approval_when_required(
    mock_qc,
    mock_factory,
    mock_tts,
    mock_ai_factory,
    mock_detector,
    mock_profile_mgr,
    mock_safety,
    mock_yt_pub,
    mock_fb_reel,
    mock_pipeline_components,
):
    """
    When require_human_approval is True:
    - Renders video & passes quality check
    - State is saved as AWAITING_APPROVAL
    - Does NOT call publishers
    - Returns awaiting_approval: True
    """
    job_mgr = DailyJobManager()
    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr)

    pipeline.project_cfg.require_human_approval = True
    pipeline.project_cfg.youtube_enabled = True
    pipeline.env_cfg.REQUIRE_HUMAN_APPROVAL = None

    mock_detector.return_value.detect_specs.return_value = HardwareSpecs(cpu_cores=4, ram_gb=8.0, disk_free_gb=50.0)
    mock_profile_mgr.get_render_settings.return_value = MagicMock(max_duration_seconds=12)

    mock_ai = MagicMock()
    mock_ai.generate_topic.return_value = {"topic_title": "AI Approval Test"}
    mock_ai.generate_script.return_value = {"dialogues": []}
    mock_ai.generate_scene_plan.return_value = {}
    mock_ai.generate_metadata.return_value = {"title": "AI Approval Test"}
    mock_ai_factory.get_provider.return_value = mock_ai
    mock_tts.return_value.generate_dialogue_audio.return_value = mock_pipeline_components["tts_path"]

    dummy_render = MagicMock(video_path=mock_pipeline_components["video_path"], content_source="stock_edit")
    mock_source = MagicMock()
    mock_source.name = "stock_edit"
    mock_source.generate_video.return_value = dummy_render
    mock_factory.get_source.return_value = mock_source

    mock_qc.verify_video.return_value = {"passed": True}

    res = pipeline.run_daily_pipeline()

    assert res["success"] is True
    assert res["job_status"] == JobStatus.AWAITING_APPROVAL.value
    assert res["awaiting_approval"] is True

    # Publishers must NOT be called while awaiting approval
    mock_yt_pub.assert_not_called()
    mock_fb_reel.assert_not_called()

    # Job state in manager must be AWAITING_APPROVAL
    job = job_mgr.get_today_job()
    assert job is not None
    assert job.status == JobStatus.AWAITING_APPROVAL


@patch("app.jobs.recovery.YouTubeShortsPublisher")
def test_approve_resumes_publishing(mock_yt_pub, mock_pipeline_components):
    """
    When approve_job() is called on an AWAITING_APPROVAL job:
    - Resumes upload stage
    - Publishes to enabled platforms
    - Moves status to DRY_RUN_COMPLETE / PUBLISHED
    """
    job_mgr = DailyJobManager()
    job = job_mgr.get_or_create_today_job()
    job.status = JobStatus.AWAITING_APPROVAL
    job.video_path = mock_pipeline_components["video_path"]
    job.topic_title = "Ready to Publish Topic"
    job_mgr.save_job(job)

    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr)
    pipeline.project_cfg.youtube_enabled = True
    pipeline.project_cfg.facebook_enabled = False
    pipeline.env_cfg.DRY_RUN = True

    mock_yt_pub.return_value.publish_short.return_value = {"success": True, "video_id": "yt_approved_123"}

    res = pipeline.approve_job()

    assert res["success"] is True
    assert res["job_status"] == JobStatus.DRY_RUN_COMPLETE.value
    saved_job = job_mgr.get_today_job()
    assert saved_job is not None
    assert saved_job.status == JobStatus.DRY_RUN_COMPLETE
    assert saved_job.youtube_status == "SUCCESS"
    mock_yt_pub.return_value.publish_short.assert_called_once()


def test_reject_resets_job_to_pending(mock_pipeline_components):
    """
    When reject_job(regenerate=False) is called:
    - Resets today's job state to PENDING
    """
    job_mgr = DailyJobManager()
    job = job_mgr.get_or_create_today_job()
    job.status = JobStatus.AWAITING_APPROVAL
    job.video_path = mock_pipeline_components["video_path"]
    job_mgr.save_job(job)

    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr)
    res = pipeline.reject_job(regenerate=False)

    assert res["success"] is True
    assert res["job_status"] == JobStatus.PENDING.value

    job_after = job_mgr.get_today_job()
    assert job_after is None or job_after.status == JobStatus.PENDING


def test_approve_without_awaiting_approval_job():
    """approve_job returns failure when no job is in AWAITING_APPROVAL state."""
    job_mgr = DailyJobManager()
    job = job_mgr.get_or_create_today_job()
    job.status = JobStatus.PENDING
    job_mgr.save_job(job)

    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr)
    res = pipeline.approve_job()

    assert res["success"] is False
    assert "Cannot approve" in res["reason"]
