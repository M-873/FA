"""
tests/test_scheduler.py
========================
Automated tests for DailyScheduler:
- Configurable scheduled_time (HH:MM, default 10:00)
- Mocked clock evaluation (before vs after scheduled time)
- Catch-up run on startup or wake-from-sleep if missed
- Max 1 job per day enforcement (skips if PUBLISHED or DRY_RUN_COMPLETE)
- Skips if job in progress or AWAITING_APPROVAL
- Respects emergency kill switch
- tick() execution and callbacks
- Non-blocking worker thread lifecycle (start and stop)
"""

from datetime import datetime, date, time as dt_time, timedelta
from unittest.mock import MagicMock, patch
import pytest

from app.jobs.manager import DailyJobManager
from app.jobs.history import PublishingHistoryManager
from app.jobs.state import DailyJobState, JobStatus
from app.scheduler.service import DailyScheduler


@pytest.fixture
def test_setup(tmp_path):
    job_mgr = DailyJobManager()
    history_mgr = PublishingHistoryManager()
    mock_pipeline = MagicMock()
    mock_pipeline.run_daily_pipeline.return_value = {"success": True, "job_status": "AWAITING_APPROVAL"}

    scheduler = DailyScheduler(
        job_manager=job_mgr,
        pipeline=mock_pipeline,
        history_manager=history_mgr,
    )
    scheduler.project_cfg.kill_switch = False
    scheduler.env_cfg.KILL_SWITCH = None
    scheduler.project_cfg.scheduled_time = "10:00"
    scheduler.env_cfg.SCHEDULED_TIME = None

    return {
        "scheduler": scheduler,
        "job_mgr": job_mgr,
        "history_mgr": history_mgr,
        "mock_pipeline": mock_pipeline,
    }


def test_scheduler_default_time(test_setup):
    sched = test_setup["scheduler"]
    assert sched.get_scheduled_time_str() == "10:00"
    parsed = sched.parse_scheduled_time()
    assert parsed.hour == 10
    assert parsed.minute == 0


def test_scheduler_custom_configured_time(test_setup):
    sched = test_setup["scheduler"]
    sched.project_cfg.scheduled_time = "14:30"
    sched.env_cfg.SCHEDULED_TIME = None
    assert sched.get_scheduled_time_str() == "14:30"
    parsed = sched.parse_scheduled_time()
    assert parsed.hour == 14
    assert parsed.minute == 30


def test_scheduler_env_override_time(test_setup):
    sched = test_setup["scheduler"]
    sched.project_cfg.scheduled_time = "10:00"
    sched.env_cfg.SCHEDULED_TIME = "18:45"
    assert sched.get_scheduled_time_str() == "18:45"
    parsed = sched.parse_scheduled_time()
    assert parsed.hour == 18
    assert parsed.minute == 45


def test_scheduler_before_scheduled_time_does_not_catch_up(test_setup):
    sched = test_setup["scheduler"]
    sched.project_cfg.scheduled_time = "10:00"
    sched.env_cfg.SCHEDULED_TIME = None

    # Mock time at 09:30 AM
    mock_now = datetime(2026, 11, 7, 9, 30, 0)
    assert sched.should_catch_up(mock_now) is False

    next_run = sched.get_next_run_time(mock_now)
    assert next_run == datetime(2026, 11, 7, 10, 0, 0)


def test_scheduler_after_scheduled_time_triggers_catch_up(test_setup):
    sched = test_setup["scheduler"]
    sched.project_cfg.scheduled_time = "10:00"
    sched.env_cfg.SCHEDULED_TIME = None

    # Mock time at 11:15 AM (past 10:00, no job done today)
    mock_now = datetime(2026, 11, 7, 11, 15, 0)
    assert sched.should_catch_up(mock_now) is True

    next_run = sched.get_next_run_time(mock_now)
    assert next_run == mock_now


def test_scheduler_today_published_does_not_catch_up(test_setup):
    sched = test_setup["scheduler"]
    sched.project_cfg.scheduled_time = "10:00"
    sched.env_cfg.SCHEDULED_TIME = None

    today_str = "2026-11-07"
    job = DailyJobState(
        date=today_str,
        job_id=f"{today_str}-test",
        status=JobStatus.PUBLISHED,
    )
    test_setup["job_mgr"].save_job(job)

    mock_now = datetime(2026, 11, 7, 12, 0, 0)
    assert sched.should_catch_up(mock_now) is False

    next_run = sched.get_next_run_time(mock_now)
    # Next run must be tomorrow at 10:00
    assert next_run == datetime(2026, 11, 8, 10, 0, 0)


def test_scheduler_today_dry_run_complete_does_not_catch_up(test_setup):
    sched = test_setup["scheduler"]
    today_str = "2026-11-07"
    job = DailyJobState(
        date=today_str,
        job_id=f"{today_str}-test",
        status=JobStatus.DRY_RUN_COMPLETE,
    )
    test_setup["job_mgr"].save_job(job)

    mock_now = datetime(2026, 11, 7, 12, 0, 0)
    assert sched.should_catch_up(mock_now) is False
    assert sched.get_next_run_time(mock_now) == datetime(2026, 11, 8, 10, 0, 0)


def test_scheduler_today_awaiting_approval_does_not_catch_up(test_setup):
    sched = test_setup["scheduler"]
    today_str = "2026-11-07"
    job = DailyJobState(
        date=today_str,
        job_id=f"{today_str}-test",
        status=JobStatus.AWAITING_APPROVAL,
    )
    test_setup["job_mgr"].save_job(job)

    mock_now = datetime(2026, 11, 7, 12, 0, 0)
    assert sched.should_catch_up(mock_now) is False


def test_scheduler_kill_switch_blocks_catch_up(test_setup):
    sched = test_setup["scheduler"]
    sched.project_cfg.kill_switch = True
    try:
        mock_now = datetime(2026, 11, 7, 12, 0, 0)
        assert sched.should_catch_up(mock_now) is False
    finally:
        sched.project_cfg.kill_switch = False


def test_scheduler_tick_triggers_pipeline_and_callbacks(test_setup):
    sched = test_setup["scheduler"]
    started = []
    completed = []

    sched.on_job_started = lambda: started.append(True)
    sched.on_job_completed = lambda res: completed.append(res)

    mock_now = datetime(2026, 11, 7, 10, 30, 0)
    res = sched.tick(now=mock_now)

    assert res is not None
    assert res["success"] is True
    assert test_setup["mock_pipeline"].run_daily_pipeline.called
    assert len(started) == 1
    assert len(completed) == 1


def test_scheduler_worker_thread_lifecycle(test_setup):
    sched = test_setup["scheduler"]
    assert sched.is_running() is False

    sched.start(poll_interval_seconds=0.05)
    assert sched.is_running() is True

    sched.stop(timeout=1.0)
    assert sched.is_running() is False
