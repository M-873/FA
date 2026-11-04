"""
app/ui/widgets.py
=================
Modern, lightweight Windows UI components for Tkinter.
Includes:
- Modern Canvas-rendered ToggleSwitch (Win11 Fluent style)
- StatusBadge / StatusPill with semantic colors
- CardFrame container with rounded dark aesthetics
- URL validation helper
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import Callable, Optional
from urllib.parse import urlparse


def validate_video_url(url: str) -> tuple[bool, str]:
    """
    Validates that the input is a well-formed video URL.
    Returns (is_valid, error_or_success_message).
    """
    cleaned = (url or "").strip()
    if not cleaned:
        return False, "URL cannot be empty. Please enter a video link."

    try:
        parsed = urlparse(cleaned)
    except Exception:
        return False, "Failed to parse URL syntax."

    if parsed.scheme.lower() not in ("http", "https"):
        return False, "Invalid protocol. URL must start with http:// or https://"

    netloc = parsed.netloc.lower()
    if not netloc or "." not in netloc:
        return False, "Invalid domain name. Please enter a complete web address."

    # Verify recognized video platforms or valid web links
    return True, "Valid video URL"


class ToggleSwitch(tk.Canvas):
    """
    Modern pill-shaped toggle switch modeled after Windows 11 Fluent Design.
    Supports keyboard accessibility, hover effects, and independent callbacks.
    """

    def __init__(
        self,
        parent: tk.Widget,
        initial_state: bool = False,
        on_toggle: Optional[Callable[[bool], None]] = None,
        width: int = 54,
        height: int = 28,
        bg_parent: str = "#161F30",
        active_color: str = "#10B981",    # Emerald Green
        inactive_color: str = "#334155",  # Slate
        thumb_color: str = "#FFFFFF",
        cursor: str = "hand2",
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=bg_parent,
            highlightthickness=0,
            cursor=cursor,
        )
        self.width = width
        self.height = height
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.thumb_color = thumb_color
        self.on_toggle = on_toggle
        self.is_on = bool(initial_state)

        # Bindings
        self.bind("<Button-1>", self._on_click)
        self.bind("<KeyPress-space>", self._on_keypress)
        self.bind("<KeyPress-Return>", self._on_keypress)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_leave)

        self._draw()

    def _draw(self):
        self.delete("all")
        r = self.height / 2
        track_color = self.active_color if self.is_on else self.inactive_color

        # Draw rounded pill track (two circles and a rectangle)
        self.create_oval(1, 1, self.height - 1, self.height - 1, fill=track_color, outline="", tags="track")
        self.create_oval(self.width - self.height + 1, 1, self.width - 1, self.height - 1, fill=track_color, outline="", tags="track")
        self.create_rectangle(r, 1, self.width - r, self.height - 1, fill=track_color, outline="", tags="track")

        # Draw knob/thumb circle
        padding = 3
        thumb_diameter = self.height - (padding * 2)
        if self.is_on:
            thumb_x1 = self.width - padding - thumb_diameter
            thumb_x2 = self.width - padding
        else:
            thumb_x1 = padding
            thumb_x2 = padding + thumb_diameter

        thumb_y1 = padding
        thumb_y2 = self.height - padding
        self.create_oval(
            thumb_x1, thumb_y1, thumb_x2, thumb_y2,
            fill=self.thumb_color, outline="#CBD5E1", width=1, tags="thumb"
        )

    def _on_click(self, event=None):
        self.toggle()

    def _on_keypress(self, event=None):
        self.toggle()

    def _on_hover(self, event=None):
        self.config(cursor="hand2")

    def _on_leave(self, event=None):
        pass

    def toggle(self):
        self.is_on = not self.is_on
        self._draw()
        if self.on_toggle:
            self.on_toggle(self.is_on)

    def set_state(self, is_on: bool, trigger_callback: bool = False):
        self.is_on = bool(is_on)
        self._draw()
        if trigger_callback and self.on_toggle:
            self.on_toggle(self.is_on)


class StatusBadge(tk.Label):
    """
    Pill-shaped status badge with modern palette.
    """

    COLOR_MAP = {
        "ON": ("#065F46", "#34D399", "● ON"),          # bg, fg, text
        "OFF": ("#1E293B", "#94A3B8", "○ OFF"),
        "PAUSED": ("#78350F", "#FBBF24", "⏸ PAUSED"),
        "QUEUED": ("#1E3A8A", "#60A5FA", "⏳ QUEUED"),
        "PROCESSING": ("#78350F", "#FBBF24", "🔄 PROCESSING"),
        "COMPLETED": ("#065F46", "#34D399", "✓ COMPLETED"),
        "FAILED": ("#7F1D1D", "#F87171", "✕ FAILED"),
        "NOT CONNECTED": ("#1E293B", "#94A3B8", "Not Connected"),
        "NOT DETECTED YET": ("#1E293B", "#94A3B8", "Not detected yet"),
        "DETECTED": ("#064E3B", "#34D399", "● DETECTED"),
        "PARTIAL": ("#78350F", "#FBBF24", "◐ PARTIAL"),
        "LAST_KNOWN": ("#1E293B", "#94A3B8", "🕒 LAST KNOWN RESULT"),
        "LEGACY_2GB": ("#374151", "#E5E7EB", "⚡ LEGACY_2GB"),
        "LOW": ("#1E3A8A", "#93C5FD", "⚡ LOW"),
        "MEDIUM": ("#065F46", "#6EE7B7", "⚡ MEDIUM"),
        "HIGH": ("#581C87", "#D8B4FE", "⚡ HIGH"),
        "ULTRA": ("#831843", "#F472B6", "⚡ ULTRA"),
    }

    def __init__(self, parent: tk.Widget, status: str = "OFF", **kwargs):
        bg, fg, label = self._get_style(status)
        font = ("Segoe UI", 9, "bold")
        super().__init__(
            parent,
            text=f"  {label}  ",
            bg=bg,
            fg=fg,
            font=font,
            padx=8,
            pady=3,
            relief="flat",
            **kwargs,
        )
        self.current_status = status

    def _get_style(self, status: str):
        key = status.upper().strip()
        if key in self.COLOR_MAP:
            return self.COLOR_MAP[key]
        return ("#1E293B", "#94A3B8", status)

    def set_status(self, status: str, custom_text: Optional[str] = None):
        self.current_status = status
        bg, fg, default_text = self._get_style(status)
        display_text = custom_text if custom_text is not None else default_text
        self.config(text=f"  {display_text}  ", bg=bg, fg=fg)


class CardFrame(tk.Frame):
    """
    Styled card container with consistent border and dark background.
    """

    def __init__(
        self,
        parent: tk.Widget,
        bg: str = "#161F30",
        border_color: str = "#283548",
        border_width: int = 1,
        **kwargs,
    ):
        super().__init__(
            parent,
            bg=bg,
            highlightbackground=border_color,
            highlightthickness=border_width,
            **kwargs,
        )
