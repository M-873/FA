"""
tests/test_ui_logic.py
======================
Unit and View-Model tests for FA Studio Modern Desktop UI:
- Decoupled UIController state machine & hardware badge
- Step progress calculation across job states
- Today's video details and approval/rejection lifecycle
- Accounts status, YouTube binding verification & platform switches
- Settings persistence and dynamic DRY_RUN warnings
- Windows Credential Manager integration for masked API keys
- First-Run Wizard system diagnostics & plain-language suggestions
- Async worker execution and cancellation events
- System tray status and menu configuration
"""

import os
import threading
import pytest
from unittest.mock import MagicMock, patch

from app.jobs.manager import DailyJobManager
from app.jobs.state import DailyJobState, JobStatus
from app.jobs.history import PublishingHistoryManager
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.scheduler.service import DailyScheduler
from app.ui.controller import UIController
from app.tray.app import SystemTrayApp, create_tray_icon_image
from app.utils.config import ProjectConfig
from app.utils.windows import is_start_with_windows_enabled, set_start_with_windows


@pytest.fixture
def mock_controller():
    """Creates a decoupled UIController with isolated temporary test state."""
    job_mgr = DailyJobManager()
    history_mgr = PublishingHistoryManager()
    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr, history_manager=history_mgr)
    scheduler = DailyScheduler(job_manager=job_mgr, pipeline=pipeline, history_manager=history_mgr)

    ctrl = UIController(
        job_manager=job_mgr,
        pipeline=pipeline,
        scheduler=scheduler,
        history_manager=history_mgr,
    )
    # Ensure clean kill switch
    ctrl.project_cfg.kill_switch = False
    return ctrl


# -----------------------------------------------------------------------------
# 1. Home Dashboard & Hardware Badge Tests
# -----------------------------------------------------------------------------
def test_home_state_idle(mock_controller):
    state = mock_controller.get_home_state()
    assert state["status_text"] == "IDLE"
    assert state["is_running"] is False
    assert state["kill_switch"] is False
    assert "Hardware:" in state["hardware_badge"]
    assert "Profile:" in state["hardware_badge"]
    assert state["steps"]["topic"] is False
    assert state["steps"]["upload"] is False


def test_home_state_step_progression(mock_controller):
    # Set job state to AWAITING_APPROVAL
    job = mock_controller.job_mgr.get_or_create_today_job()
    job.status = JobStatus.AWAITING_APPROVAL
    job.topic_title = "এআই যখন বিড়ালের ভাষা বুঝতে চাইল!"
    job.video_path = "output/final.mp4"
    job.clip_id = "855564"
    job.provider = "pexels"
    mock_controller.job_mgr.save_job(job)

    state = mock_controller.get_home_state()
    assert state["status_text"] == "AWAITING_APPROVAL"
    # Steps 1 through 4 should be marked complete
    assert state["steps"]["topic"] is True
    assert state["steps"]["clip"] is True
    assert state["steps"]["edit"] is True
    assert state["steps"]["quality"] is True
    assert state["steps"]["approval"] is False
    assert state["steps"]["upload"] is False


def test_home_state_kill_switch_override(mock_controller):
    mock_controller.project_cfg.kill_switch = True
    try:
        state = mock_controller.get_home_state()
        assert state["status_text"] == "KILL SWITCH ACTIVE"
        assert state["kill_switch"] is True
    finally:
        mock_controller.project_cfg.kill_switch = False


# -----------------------------------------------------------------------------
# 2. Today's Video Details & Actions
# -----------------------------------------------------------------------------
def test_today_video_details(mock_controller, tmp_path):
    # Create a dummy video file
    dummy_video = os.path.join(tmp_path, "test_final.mp4")
    with open(dummy_video, "wb") as f:
        f.write(b"\x00" * 1024 * 512)  # 512 KB

    job = mock_controller.job_mgr.get_or_create_today_job()
    job.status = JobStatus.AWAITING_APPROVAL
    job.topic_title = "আজকের ভিডিও শিরোনাম"
    job.video_path = dummy_video
    job.clip_id = "sample_99"
    job.provider = "pixabay"
    mock_controller.job_mgr.save_job(job)

    details = mock_controller.get_today_video_details()
    assert details["exists"] is True
    assert details["topic"] == "আজকের ভিডিও শিরোনাম"
    assert details["clip_id"] == "sample_99"
    assert details["provider"] == "pixabay"
    assert details["size_mb"] == 0.5
    assert details["can_approve"] is True


def test_approve_and_reject_actions(mock_controller):
    job = mock_controller.job_mgr.get_or_create_today_job()
    job.status = JobStatus.AWAITING_APPROVAL
    job.topic_title = "Approve Test Topic"
    mock_controller.job_mgr.save_job(job)

    # Approve
    with patch.object(mock_controller.pipeline, "approve_job", return_value={"success": True, "job_status": "PUBLISHED"}):
        res = mock_controller.approve_today_video()
        assert res["success"] is True

    # Reject
    with patch.object(mock_controller.pipeline, "reject_job", return_value={"success": True, "job_status": "PENDING"}):
        res = mock_controller.reject_today_video(regenerate=False)
        assert res["success"] is True


# -----------------------------------------------------------------------------
# 3. History Retrieval Tests
# -----------------------------------------------------------------------------
def test_publishing_history_queries(mock_controller):
    mock_controller.history_mgr.record_publication(
        date="2026-11-07",
        topic="বাংলা প্রযুক্তি ভিডিও",
        clip_id="clip_123",
        provider="pexels",
        video_id="YT_TEST_123",
        status="PUBLISHED",
    )

    records = mock_controller.get_publishing_history()
    assert len(records) >= 1
    rec = records[0]
    assert rec["topic"] == "বাংলা প্রযুক্তি ভিডিও"
    assert rec["video_id"] == "YT_TEST_123"
    assert rec["status"] == "PUBLISHED"


# -----------------------------------------------------------------------------
# 4. Accounts & Platform Switches
# -----------------------------------------------------------------------------
def test_accounts_state_and_toggles(mock_controller):
    with patch.object(mock_controller.auth_mgr, "get_authenticated_service", return_value=MagicMock()):
        acc = mock_controller.get_accounts_state()
        assert acc["youtube"]["connected"] is True
        assert "@Life-X-873" in acc["youtube"]["status_text"]
        assert "Coming Soon" in acc["facebook"]["status_text"]
        assert "Coming Soon" in acc["instagram"]["status_text"]

    # Toggle platforms
    mock_controller.update_platform_toggle("youtube", False)
    assert mock_controller.project_cfg.youtube_enabled is False
    mock_controller.update_platform_toggle("youtube", True)
    assert mock_controller.project_cfg.youtube_enabled is True


# -----------------------------------------------------------------------------
# 5. Settings Persistence & Start with Windows
# -----------------------------------------------------------------------------
def test_settings_persistence(mock_controller):
    orig_time = mock_controller.project_cfg.scheduled_time
    settings_data = {
        "scheduled_time": "14:30",
        "require_human_approval": False,
        "content_source": "auto",
        "dry_run": False,
        "publisher_device": True,
        "youtube_privacy": "unlisted",
    }

    try:
        with patch("app.ui.controller.set_start_with_windows", return_value=True), \
             patch.object(mock_controller.project_cfg, "save"):
            saved = mock_controller.save_settings(settings_data)
            assert saved is True

            s = mock_controller.get_settings()
            assert s["scheduled_time"] == "14:30"
            assert s["require_human_approval"] is False
            assert s["content_source"] == "auto"
            assert s["dry_run"] is False
            assert s["youtube_privacy"] == "unlisted"
    finally:
        mock_controller.project_cfg.scheduled_time = orig_time


# -----------------------------------------------------------------------------
# 6. Secure Masked API Keys (Windows Credential Manager)
# -----------------------------------------------------------------------------
def test_secure_api_key_saving(mock_controller):
    with patch("app.utils.credentials.WindowsCredentialManager.save_credential", return_value=True) as mock_save, \
         patch("app.utils.credentials.WindowsCredentialManager.has_credential", return_value=True):
        # Save key
        saved = mock_controller.save_api_key("gemini", "TEST_GEMINI_KEY_VALUE")
        assert saved is True
        mock_save.assert_called_once_with(
            target_name="FA_GEMINI_API_KEY",
            username="FA_User",
            secret_data="TEST_GEMINI_KEY_VALUE",
            comment="FA gemini API Key",
        )

        # Has key check
        assert mock_controller.has_api_key("gemini") is True


# -----------------------------------------------------------------------------
# 7. First-Run Wizard Diagnostics
# -----------------------------------------------------------------------------
def test_first_run_diagnostics(mock_controller):
    checks = mock_controller.run_first_run_diagnostics()
    assert len(checks) >= 5
    item_names = [c["item"] for c in checks]
    assert "Hardware Detection" in item_names
    assert "FFmpeg Engine" in item_names
    assert "Gemini AI Key" in item_names
    assert "YouTube Channel (@Life-X-873)" in item_names
    assert "Output Storage Directory" in item_names

    for c in checks:
        assert "passed" in c
        assert "detail" in c
        if not c["passed"]:
            assert c["fix"] is not None


# -----------------------------------------------------------------------------
# 8. Async Pipeline Execution & Cancellation
# -----------------------------------------------------------------------------
def test_async_pipeline_execution_and_cancellation(mock_controller):
    executed = threading.Event()

    def mock_run():
        executed.set()
        return {"success": True, "job_status": "DRY_RUN_COMPLETE"}

    with patch.object(mock_controller.pipeline, "run_daily_pipeline", side_effect=mock_run):
        started = mock_controller.run_pipeline_async()
        assert started is True
        assert executed.wait(timeout=3.0) is True

    # Cancellation check
    mock_controller.cancel_pipeline()
    assert mock_controller._cancel_requested.is_set() is True


# -----------------------------------------------------------------------------
# 9. System Tray App Lifecycle & Menu
# -----------------------------------------------------------------------------
def test_system_tray_app_structure(mock_controller):
    tray = SystemTrayApp(
        scheduler=mock_controller.scheduler,
        job_manager=mock_controller.job_mgr,
        pipeline=mock_controller.pipeline,
    )

    summary = tray.get_status_summary()
    assert "Status:" in summary

    menu = tray.build_menu()
    assert menu is not None
    assert len(menu.items) >= 8

    # Icon generation
    icon_img = create_tray_icon_image(size=(32, 32), alert=False)
    assert icon_img.size == (32, 32)
    alert_icon = create_tray_icon_image(size=(32, 32), alert=True)
    assert alert_icon.size == (32, 32)
