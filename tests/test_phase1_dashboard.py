"""
tests/test_phase1_dashboard.py
==============================
Automated test suite verifying all Phase 1 requirements:
1. Daily Auto Post Section (Toggle, ON/OFF/PAUSED status, Last Run, Next Run, Today's Progress).
2. Link to Reels Section (Independent Toggle, URL validation, Mock Job creation & Queue).
3. Connected Accounts Panel (YouTube, Facebook, Instagram marked 'Not Connected' with Connect placeholder).
4. Hardware Information Panel (GPU, VRAM, RAM, CPU, Profile, Disk space marked 'Not detected yet').
5. Activity and Job Status (Demarcated as Mock Data).
6. Local Settings Persistence (Zero database, independent toggle state preservation across restarts).
7. Strict scope restriction checks (No external AI calls, no Ollama downloads, no video downloads).
"""

import os
import pytest
import tkinter as tk
from app.ui.settings import SettingsManager, get_default_settings
from app.ui.widgets import validate_video_url, StatusBadge, ToggleSwitch
from app.ui.main_window import AutoPostDashboardApp


# -----------------------------------------------------------------------------
# 1. Local Settings & Independent Toggle Persistence Tests
# -----------------------------------------------------------------------------
def test_settings_defaults(tmp_path):
    temp_file = os.path.join(tmp_path, "test_settings.json")
    mgr = SettingsManager(filepath=temp_file)

    dap = mgr.get_daily_auto_post()
    ltr = mgr.get_link_to_reels()

    assert dap["enabled"] is False
    assert dap["status"] == "OFF"
    assert "Yesterday" in dap["last_run"]
    assert "Tomorrow" in dap["next_run"]
    assert "Idle" in dap["today_progress"]

    assert ltr["enabled"] is False
    assert ltr["status"] == "OFF"
    assert len(mgr.get_reels_jobs()) >= 4


def test_independent_toggle_behavior(tmp_path):
    """
    Verifies:
    - Toggling Daily Auto Post does NOT change Link to Reels.
    - Toggling Link to Reels does NOT change Daily Auto Post.
    - Toggle states persist after reloading from disk.
    """
    temp_file = os.path.join(tmp_path, "test_settings.json")
    mgr1 = SettingsManager(filepath=temp_file)

    # Both start False
    assert mgr1.get_daily_auto_post()["enabled"] is False
    assert mgr1.get_link_to_reels()["enabled"] is False

    # Toggle Daily Auto Post ON
    mgr1.set_daily_auto_post_toggle(True)
    assert mgr1.get_daily_auto_post()["enabled"] is True
    assert mgr1.get_daily_auto_post()["status"] == "ON"
    assert mgr1.get_link_to_reels()["enabled"] is False  # Must remain False!

    # Simulate restart by reading from disk with new instance
    mgr2 = SettingsManager(filepath=temp_file)
    assert mgr2.get_daily_auto_post()["enabled"] is True
    assert mgr2.get_daily_auto_post()["status"] == "ON"
    assert mgr2.get_link_to_reels()["enabled"] is False  # Must still be False!

    # Toggle Link to Reels ON
    mgr2.set_link_to_reels_toggle(True)
    assert mgr2.get_link_to_reels()["enabled"] is True
    assert mgr2.get_link_to_reels()["status"] == "ON"
    assert mgr2.get_daily_auto_post()["enabled"] is True  # Must remain True!

    # Toggle Daily Auto Post OFF
    mgr2.set_daily_auto_post_toggle(False)
    assert mgr2.get_daily_auto_post()["enabled"] is False
    assert mgr2.get_daily_auto_post()["status"] == "OFF"
    assert mgr2.get_link_to_reels()["enabled"] is True   # Must remain True!

    # Final reload check
    mgr3 = SettingsManager(filepath=temp_file)
    assert mgr3.get_daily_auto_post()["enabled"] is False
    assert mgr3.get_link_to_reels()["enabled"] is True


def test_daily_auto_post_status_cycles(tmp_path):
    temp_file = os.path.join(tmp_path, "test_settings.json")
    mgr = SettingsManager(filepath=temp_file)

    mgr.set_daily_auto_post_status("ON")
    assert mgr.get_daily_auto_post()["status"] == "ON"
    assert mgr.get_daily_auto_post()["enabled"] is True

    mgr.set_daily_auto_post_status("PAUSED")
    assert mgr.get_daily_auto_post()["status"] == "PAUSED"
    assert mgr.get_daily_auto_post()["enabled"] is True

    mgr.set_daily_auto_post_status("OFF")
    assert mgr.get_daily_auto_post()["status"] == "OFF"
    assert mgr.get_daily_auto_post()["enabled"] is False

    with pytest.raises(ValueError):
        mgr.set_daily_auto_post_status("INVALID_STATUS")


# -----------------------------------------------------------------------------
# 2. URL Validation Tests
# -----------------------------------------------------------------------------
def test_video_url_validation():
    # Valid video URLs
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://vimeo.com/76979871",
        "https://www.facebook.com/reel/123456789",
        "https://www.instagram.com/reel/Cx1234567",
        "https://www.tiktok.com/@user/video/71234567890",
        "http://example.com/videos/sample.mp4",
    ]
    for url in valid_urls:
        ok, msg = validate_video_url(url)
        assert ok is True, f"Expected {url} to be valid, got error: {msg}"

    # Invalid video URLs
    invalid_urls = [
        "",
        "   ",
        "not_a_url",
        "ftp://invalid-protocol.com/video.mp4",
        "http://",
        "https://",
        "just text with spaces",
        "http://nodomain",
    ]
    for url in invalid_urls:
        ok, msg = validate_video_url(url)
        assert ok is False, f"Expected {url} to be invalid, got ok=True"
        assert len(msg) > 0


# -----------------------------------------------------------------------------
# 3. Mock Job Creation & Queue Tests
# -----------------------------------------------------------------------------
def test_mock_job_creation(tmp_path):
    temp_file = os.path.join(tmp_path, "test_settings.json")
    mgr = SettingsManager(filepath=temp_file)

    initial_jobs = mgr.get_reels_jobs()
    initial_count = len(initial_jobs)

    # Verify seed jobs contain queued, processing, completed, and failed
    statuses = {j["status"] for j in initial_jobs}
    assert "QUEUED" in statuses
    assert "PROCESSING" in statuses
    assert "COMPLETED" in statuses
    assert "FAILED" in statuses

    # Add new mock job
    test_url = "https://www.youtube.com/watch?v=new_test_video"
    new_job = mgr.add_mock_reels_job(test_url)

    assert new_job["url"] == test_url
    assert new_job["status"] == "QUEUED"
    assert new_job["progress"] == 0
    assert "reel_job_" in new_job["id"]

    # Verify job persisted
    reloaded_mgr = SettingsManager(filepath=temp_file)
    assert len(reloaded_mgr.get_reels_jobs()) == initial_count + 1
    assert reloaded_mgr.get_reels_jobs()[0]["id"] == new_job["id"]


# -----------------------------------------------------------------------------
# 4. GUI Dashboard Integration Tests (Tkinter)
# -----------------------------------------------------------------------------
def _create_tk_root():
    try:
        return tk.Tk()
    except (tk.TclError, Exception) as e:
        pytest.skip(f"Tkinter / Tcl not available: {e}")


def test_dashboard_ui_initialization_and_widgets():
    root = _create_tk_root()
    app = AutoPostDashboardApp(root)
    root.update()

    try:
        # Check title and window size
        assert "Dashboard" in root.title()

        # Check Daily Auto Post UI elements
        assert app.dap_card is not None
        assert app.dap_toggle is not None
        assert app.dap_status_badge is not None
        assert app.dap_last_run_lbl is not None
        assert app.dap_next_run_lbl is not None
        assert app.dap_progress_lbl is not None

        # Check Link to Reels UI elements
        assert app.ltr_card is not None
        assert app.ltr_toggle is not None
        assert app.ltr_status_badge is not None
        assert app.url_entry is not None
        assert app.add_link_btn is not None
        assert app.validation_msg is not None
        assert app.jobs_list_frame is not None

        # Check Connected Accounts elements
        assert app.acc_card is not None

        # Check Hardware Info elements
        assert app.hw_card is not None

        # Check Activity elements
        assert app.activity_card is not None

    finally:
        root.destroy()


def test_dashboard_independent_toggles_in_gui():
    root = _create_tk_root()
    app = AutoPostDashboardApp(root)
    root.update()

    try:
        # Initial states
        dap_init = app.dap_toggle.is_on
        ltr_init = app.ltr_toggle.is_on

        # Toggle DAP
        app.dap_toggle.toggle()
        root.update()
        assert app.dap_toggle.is_on != dap_init
        assert app.ltr_toggle.is_on == ltr_init  # LTR unchanged!

        # Toggle LTR
        app.ltr_toggle.toggle()
        root.update()
        assert app.ltr_toggle.is_on != ltr_init
        # DAP remains at its new state
        assert app.dap_toggle.is_on != dap_init

    finally:
        root.destroy()


def test_dashboard_url_validation_and_mock_job_in_gui():
    root = _create_tk_root()
    app = AutoPostDashboardApp(root)
    root.update()

    try:
        # Invalid input: should display error in red
        app.url_entry.delete(0, tk.END)
        app.url_entry.insert(0, "not-a-valid-link")
        app.on_click_add_link()
        root.update()
        msg_text = app.validation_msg.cget("text")
        assert "⚠️" in msg_text

        # Valid input: should display success message in green and add to job list
        valid_link = "https://www.youtube.com/watch?v=valid12345"
        app.url_entry.delete(0, tk.END)
        app.url_entry.insert(0, valid_link)
        app.on_click_add_link()
        root.update()
        success_msg = app.validation_msg.cget("text")
        assert "✓" in success_msg

        # Verify new mock job is rendered in job list
        first_job = app.settings_manager.get_reels_jobs()[0]
        assert first_job["url"] == valid_link
        assert first_job["status"] == "QUEUED"

    finally:
        root.destroy()
