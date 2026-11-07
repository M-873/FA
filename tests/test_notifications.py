"""
tests/test_notifications.py
============================
Automated tests for the notification subsystem:
- Awaiting approval, success, no clip found, Gemini failure,
  FFmpeg failure, YouTube quota error, YouTube token expired ("Re-login required")
- Tray icon notification dispatch
- Clean logger fallback when tray icon or desktop toast is unavailable (never crashes)
- In-memory notification history
"""

from unittest.mock import MagicMock, patch
import pytest

from app.notifications.service import (
    NotificationEvent,
    Notifier,
    get_notifier,
    set_global_notifier,
)


@pytest.fixture
def test_notifier():
    notifier = Notifier()
    return notifier


def test_notifier_all_events_record_to_history(test_notifier):
    # 1. Awaiting approval
    test_notifier.notify_awaiting_approval("Test Topic", "output/final.mp4")

    # 2. Success
    test_notifier.notify_success("yt_video_123", "YouTube Shorts")

    # 3. No clip found
    test_notifier.notify_no_clip_found("Waterfall exhausted")

    # 4. Gemini failure
    test_notifier.notify_gemini_failure("API 404 model not found")

    # 5. FFmpeg failure
    test_notifier.notify_ffmpeg_failure("Invalid pixel format")

    # 6. YouTube quota error
    test_notifier.notify_youtube_quota_error("403 quotaExceeded")

    # 7. YouTube token expired ("Re-login required")
    test_notifier.notify_youtube_token_expired("Token refresh failed: invalid_grant")

    history = test_notifier.get_history()
    assert len(history) == 7

    events = [item["event"] for item in history]
    assert NotificationEvent.AWAITING_APPROVAL.value in events
    assert NotificationEvent.SUCCESS.value in events
    assert NotificationEvent.NO_CLIP_FOUND.value in events
    assert NotificationEvent.GEMINI_FAILURE.value in events
    assert NotificationEvent.FFMPEG_FAILURE.value in events
    assert NotificationEvent.YOUTUBE_QUOTA_ERROR.value in events
    assert NotificationEvent.YOUTUBE_TOKEN_EXPIRED.value in events

    # Verify message contents
    token_item = next(i for i in history if i["event"] == NotificationEvent.YOUTUBE_TOKEN_EXPIRED.value)
    assert "re-login required" in token_item["title"].lower() or "re-login required" in token_item["message"].lower()


def test_notifier_dispatches_to_tray_icon(test_notifier):
    mock_tray = MagicMock()
    mock_tray.notify = MagicMock()
    test_notifier.set_tray_icon(mock_tray)

    test_notifier.notify_awaiting_approval("Approval Topic", "output/final.mp4")
    mock_tray.notify.assert_called_once()
    args, _ = mock_tray.notify.call_args
    assert "output/final.mp4" in args[0]
    assert "Approval Required" in args[1]


def test_notifier_custom_handler_callback(test_notifier):
    received = []

    def custom_handler(event, title, message):
        received.append((event, title, message))

    test_notifier.set_custom_handler(custom_handler)
    test_notifier.notify_success("vid_456")

    assert len(received) == 1
    assert received[0][0] == NotificationEvent.SUCCESS
    assert "vid_456" in received[0][2]


def test_notifier_never_crashes_on_tray_error(test_notifier):
    mock_tray = MagicMock()
    mock_tray.notify.side_effect = RuntimeError("Tray icon disconnected!")
    test_notifier.set_tray_icon(mock_tray)

    # Should not raise exception
    res = test_notifier.notify_youtube_quota_error("Quota test")
    assert res is True


def test_notifier_never_crashes_on_toast_error(test_notifier, monkeypatch):
    test_notifier.set_tray_icon(None)

    def broken_popen(*args, **kwargs):
        raise OSError("PowerShell execution policy blocked")

    monkeypatch.setattr("subprocess.Popen", broken_popen)

    res = test_notifier.notify_ffmpeg_failure("Render crashed")
    assert res is True
