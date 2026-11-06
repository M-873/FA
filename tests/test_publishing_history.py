"""
tests/test_publishing_history.py
================================
Unit tests for SQLite-backed PublishingHistoryManager:
- Database creation & table schema
- Record publication insertion
- Querying records by date and latest record
- Multiple records persistence
"""

import os
import pytest
from app.jobs.history import PublishingHistoryManager


def test_publishing_history_manager_crud(tmp_path):
    db_file = str(tmp_path / "test_pub_history.db")
    mgr = PublishingHistoryManager(db_path=db_file)

    assert os.path.exists(db_file)

    # Initially empty
    assert mgr.get_all_records() == []
    assert mgr.get_latest_record() is None

    # Insert a record
    rec_id = mgr.record_publication(
        date="2026-11-06",
        topic="এআই ও রোবট",
        clip_id="test_clip_123",
        provider="local",
        video_id="yt_video_abc",
        status="PUBLISHED",
        error=None,
    )
    assert rec_id == 1

    # Query latest record
    latest = mgr.get_latest_record()
    assert latest is not None
    assert latest["date"] == "2026-11-06"
    assert latest["topic"] == "এআই ও রোবট"
    assert latest["clip_id"] == "test_clip_123"
    assert latest["provider"] == "local"
    assert latest["video_id"] == "yt_video_abc"
    assert latest["status"] == "PUBLISHED"
    assert latest["error"] is None

    # Query by date
    by_date = mgr.get_records_by_date("2026-11-06")
    assert len(by_date) == 1
    assert by_date[0]["video_id"] == "yt_video_abc"

    # Insert another record with error
    mgr.record_publication(
        date="2026-11-06",
        topic="ব্যর্থ চেষ্টা",
        clip_id=None,
        provider="stock_edit",
        video_id=None,
        status="FAILED",
        error="API quota exceeded",
    )
    all_recs = mgr.get_all_records()
    assert len(all_recs) == 2
    assert all_recs[0]["status"] == "FAILED"
    assert all_recs[0]["error"] == "API quota exceeded"


def test_duplicate_guard_prevents_same_day_upload():
    """Verifies that DailyCartoonAutomationPipeline blocks re-uploading on the same day if already published."""
    from unittest.mock import MagicMock, patch
    from app.jobs.recovery import DailyCartoonAutomationPipeline
    from app.jobs.state import DailyJobState, JobStatus
    from app.jobs.manager import DailyJobManager

    mock_job = DailyJobState(
        date="2026-11-06",
        job_id="2026-11-06-main",
        status=JobStatus.PUBLISHED,
        video_path="output/final.mp4",
        youtube_status="SUCCESS",
        youtube_video_id="already_uploaded_id",
    )

    mock_mgr = MagicMock(spec=DailyJobManager)
    mock_mgr.get_or_create_today_job.return_value = mock_job
    mock_mgr.get_today_job.return_value = mock_job

    pipeline = DailyCartoonAutomationPipeline(job_manager=mock_mgr)

    # 1. run_daily_pipeline must short-circuit without uploading
    with patch("app.youtube.publisher.YouTubeShortsPublisher.publish_short") as mock_pub:
        res = pipeline.run_daily_pipeline()
        assert res["success"] is True
        assert res["job_status"] == JobStatus.PUBLISHED
        assert "Already published" in res["reason"]
        mock_pub.assert_not_called()

    # 2. approve_job must also reject approval if status is PUBLISHED
    with patch("app.youtube.publisher.YouTubeShortsPublisher.publish_short") as mock_pub:
        approve_res = pipeline.approve_job()
        assert approve_res["success"] is False
        assert "Cannot approve" in approve_res["reason"]
        mock_pub.assert_not_called()
