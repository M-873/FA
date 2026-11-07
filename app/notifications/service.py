"""
app/notifications/service.py
============================
Lightweight Notification System for FA Video Automation.
Supports Windows desktop notifications (tray balloon / Windows toast)
with automatic structured logging fallback.
Covers:
- Awaiting Approval
- Success
- No Clip Found
- Gemini Failure
- FFmpeg Failure
- YouTube Quota Error
- YouTube Token Expired / Re-login Required
"""

import sys
import subprocess
from enum import Enum
from typing import Optional, Any, Callable, List, Dict
from datetime import datetime
from app.utils.logging import logger


class NotificationEvent(str, Enum):
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUCCESS = "SUCCESS"
    NO_CLIP_FOUND = "NO_CLIP_FOUND"
    GEMINI_FAILURE = "GEMINI_FAILURE"
    FFMPEG_FAILURE = "FFMPEG_FAILURE"
    YOUTUBE_QUOTA_ERROR = "YOUTUBE_QUOTA_ERROR"
    YOUTUBE_TOKEN_EXPIRED = "YOUTUBE_TOKEN_EXPIRED"


class Notifier:
    """
    Central notification manager.
    Dispatches to tray icon if available, Windows system toast/balloon,
    and always records to logger and in-memory notification history.
    """

    def __init__(self, tray_icon: Optional[Any] = None):
        self._tray_icon = tray_icon
        self._custom_handler: Optional[Callable[[NotificationEvent, str, str], None]] = None
        self._history: List[Dict[str, Any]] = []

    def set_tray_icon(self, tray_icon: Optional[Any]):
        self._tray_icon = tray_icon

    def set_custom_handler(self, handler: Optional[Callable[[NotificationEvent, str, str], None]]):
        self._custom_handler = handler

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return list(reversed(self._history[-limit:]))

    def clear_history(self):
        self._history.clear()

    def notify(self, event: NotificationEvent, title: str, message: str) -> bool:
        """
        Main dispatch method. Never crashes; falls back cleanly.
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "event": event.value,
            "title": title,
            "message": message,
        }
        self._history.append(record)

        # 1. Structured log
        if event in (NotificationEvent.SUCCESS, NotificationEvent.AWAITING_APPROVAL):
            logger.info(f"[{event.value}] {title}: {message}")
        elif event in (NotificationEvent.NO_CLIP_FOUND, NotificationEvent.GEMINI_FAILURE):
            logger.warning(f"[{event.value}] {title}: {message}")
        else:
            logger.error(f"[{event.value}] {title}: {message}")

        # 2. Custom listener callback (e.g. for UI or test assertions)
        if self._custom_handler:
            try:
                self._custom_handler(event, title, message)
            except Exception as e:
                logger.debug(f"Custom notification handler error: {e}")

        # 3. Tray icon notification if attached and active
        if self._tray_icon and hasattr(self._tray_icon, "notify"):
            try:
                self._tray_icon.notify(message, title)
                return True
            except Exception as e:
                logger.debug(f"Tray icon notify failed: {e}")

        # 4. Windows Desktop Toast / Balloon (best-effort, non-blocking)
        if sys.platform == "win32":
            self._send_windows_toast(title, message)

        return True

    def _send_windows_toast(self, title: str, message: str):
        """Attempts a light non-blocking PowerShell notification on Windows."""
        try:
            safe_title = title.replace('"', '`"').replace("'", "''")
            safe_msg = message.replace('"', '`"').replace("'", "''")
            ps_cmd = (
                "[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null; "
                "$n = New-Object System.Windows.Forms.NotifyIcon; "
                "$n.Icon = [System.Drawing.SystemIcons]::Information; "
                "$n.Visible = $true; "
                f"$n.ShowBalloonTip(3000, '{safe_title}', '{safe_msg}', [System.Windows.Forms.ToolTipIcon]::Info); "
                "Start-Sleep -Milliseconds 100; $n.Dispose()"
            )
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception as e:
            logger.debug(f"Windows desktop toast delivery omitted: {e}")

    # Specific event helpers
    def notify_awaiting_approval(self, topic: str, video_path: str) -> bool:
        return self.notify(
            NotificationEvent.AWAITING_APPROVAL,
            "Video Ready - Approval Required",
            f"Topic: {topic}\nRendered to: {video_path}\nRun --approve to publish.",
        )

    def notify_success(self, video_id: str, platform: str = "YouTube Shorts") -> bool:
        return self.notify(
            NotificationEvent.SUCCESS,
            "Video Published Successfully!",
            f"Published to {platform} (ID: {video_id}).",
        )

    def notify_no_clip_found(self, reason: str = "No clip found") -> bool:
        return self.notify(
            NotificationEvent.NO_CLIP_FOUND,
            "No Video Clip Found",
            f"Stock waterfall found no matching clip: {reason}",
        )

    def notify_gemini_failure(self, reason: str) -> bool:
        return self.notify(
            NotificationEvent.GEMINI_FAILURE,
            "AI Generation Warning",
            f"Gemini API issue ({reason}). System engaged fallback.",
        )

    def notify_ffmpeg_failure(self, reason: str) -> bool:
        return self.notify(
            NotificationEvent.FFMPEG_FAILURE,
            "FFmpeg Render Failure",
            f"Video encoding failed: {reason}",
        )

    def notify_youtube_quota_error(self, reason: str = "YouTube daily quota exceeded") -> bool:
        return self.notify(
            NotificationEvent.YOUTUBE_QUOTA_ERROR,
            "YouTube Quota Exceeded",
            f"YouTube API quota limit reached: {reason}",
        )

    def notify_youtube_token_expired(self, reason: str = "Re-login required") -> bool:
        return self.notify(
            NotificationEvent.YOUTUBE_TOKEN_EXPIRED,
            "YouTube Re-login Required",
            f"OAuth token expired or refresh failed: {reason}",
        )


_notifier_instance: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """Returns singleton Notifier instance."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = Notifier()
    return _notifier_instance


def set_global_notifier(notifier: Notifier):
    """Sets singleton Notifier instance (useful for tests or custom DI)."""
    global _notifier_instance
    _notifier_instance = notifier
