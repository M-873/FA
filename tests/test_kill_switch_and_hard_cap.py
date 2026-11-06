"""
tests/test_kill_switch_and_hard_cap.py
======================================
Tests for:
- Emergency Kill Switch (config and env override)
- Hard cap of 1 publish per day (enforced via state & SQLite publishing history)
"""

from unittest.mock import MagicMock, patch
import pytest

from app.jobs.manager import DailyJobManager
from app.jobs.history import PublishingHistoryManager
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import DailyJobState, JobStatus


def test_kill_switch_blocks_pipeline_run():
    pipeline = DailyCartoonAutomationPipeline()
    pipeline.project_cfg.kill_switch = True
    pipeline.env_cfg.KILL_SWITCH = None

    res = pipeline.run_daily_pipeline()
    assert res["success"] is False
    assert "kill switch" in res["reason"].lower()


def test_kill_switch_env_override_blocks_pipeline():
    pipeline = DailyCartoonAutomationPipeline()
    pipeline.project_cfg.kill_switch = False
    pipeline.env_cfg.KILL_SWITCH = True

    res = pipeline.run_daily_pipeline()
    assert res["success"] is False
    assert "kill switch" in res["reason"].lower()


def test_kill_switch_blocks_approval():
    pipeline = DailyCartoonAutomationPipeline()
    pipeline.project_cfg.kill_switch = True
    pipeline.env_cfg.KILL_SWITCH = None

    res = pipeline.approve_job()
    assert res["success"] is False
    assert "kill switch" in res["reason"].lower()


def test_hard_cap_blocks_pipeline_when_published_in_history(tmp_path):
    job_mgr = DailyJobManager()
    history_mgr = PublishingHistoryManager()

    history_mgr.record_publication(
        date="2026-11-06",
        topic="Prior Video Today",
        clip_id="clip_1",
        provider="local",
        video_id="yt_already_done",
        status="PUBLISHED",
        error=None,
    )

    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr, history_manager=history_mgr)
    pipeline.project_cfg.kill_switch = False
    pipeline.env_cfg.KILL_SWITCH = False

    res = pipeline.run_daily_pipeline()
    assert res["success"] is False
    assert "hard cap" in res["reason"].lower()


def test_hard_cap_blocks_approval_when_published_in_history(tmp_path):
    job_mgr = DailyJobManager()
    dummy_mp4 = tmp_path / "final.mp4"
    dummy_mp4.write_bytes(b"DATA")

    job = DailyJobState(
        date="2026-11-06",
        job_id="2026-11-06-test",
        status=JobStatus.AWAITING_APPROVAL,
        video_path=str(dummy_mp4),
        topic_title="Awaiting Video",
    )
    job_mgr.save_job(job)

    history_mgr = PublishingHistoryManager()
    history_mgr.record_publication(
        date="2026-11-06",
        topic="Prior Video Today",
        clip_id="clip_1",
        provider="local",
        video_id="yt_already_done",
        status="PUBLISHED",
        error=None,
    )

    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr, history_manager=history_mgr)
    pipeline.project_cfg.kill_switch = False
    pipeline.env_cfg.KILL_SWITCH = False

    res = pipeline.approve_job()
    assert res["success"] is False
    assert "hard cap" in res["reason"].lower()
