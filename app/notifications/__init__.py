"""
app/notifications
=================
Notification package for FA Video Automation.
"""

from app.notifications.service import (
    NotificationEvent,
    Notifier,
    get_notifier,
    set_global_notifier,
)

__all__ = [
    "NotificationEvent",
    "Notifier",
    "get_notifier",
    "set_global_notifier",
]
