"""
app/ui/theme.py
===============
Design System, Color Palette, and Bengali-capable Typography for the FA Studio Desktop UI.
Standardized for 1366x768 screens with crisp scaling, high-contrast states, and responsive hierarchy.
"""

from typing import Tuple, Dict, Any
import customtkinter as ctk

# -----------------------------------------------------------------------------
# Font Family Selection
# Windows provides 'Nirmala UI' natively with full OpenType Bengali ligature shaping.
# Fallback to Segoe UI and Arial.
# -----------------------------------------------------------------------------
FONT_FAMILY = "Nirmala UI"
FONT_FAMILY_FALLBACK = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"


def get_font(size: int = 13, weight: str = "normal", slant: str = "roman") -> ctk.CTkFont:
    """Returns a standardized CTkFont using Nirmala UI for perfect English and Bengali rendering."""
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight, slant=slant)


def get_mono_font(size: int = 12) -> ctk.CTkFont:
    """Returns monospaced CTkFont for code/log output."""
    return ctk.CTkFont(family=FONT_FAMILY_MONO, size=size)


# -----------------------------------------------------------------------------
# Color Palette
# (Light Mode, Dark Mode) tuples for CustomTkinter dynamic theming
# -----------------------------------------------------------------------------
COLORS = {
    # Brand & Accents
    "primary": ("#2563EB", "#3B82F6"),         # Royal Blue
    "primary_hover": ("#1D4ED8", "#1D4ED8"),
    "accent": ("#4F46E5", "#6366F1"),          # Indigo

    # Status Indicators
    "success": ("#059669", "#10B981"),         # Emerald Green
    "warning": ("#D97706", "#F59E0B"),         # Amber
    "danger": ("#DC2626", "#EF4444"),          # Crimson Red
    "danger_hover": ("#B91C1C", "#DC2626"),
    "info": ("#0284C7", "#38BDF8"),            # Sky Blue

    # Surfaces & Containers
    "sidebar_bg": ("#F1F5F9", "#181825"),      # Deep Navy / Soft Slate
    "main_bg": ("#F8FAFC", "#11111B"),         # Modern Background
    "card_bg": ("#FFFFFF", "#1E1E2E"),         # Card surface
    "card_border": ("#E2E8F0", "#313244"),     # Subtle border
    "header_bg": ("#FFFFFF", "#1E1E2E"),

    # Typography
    "text_main": ("#0F172A", "#F8FAFC"),       # High contrast
    "text_muted": ("#64748B", "#94A3B8"),      # Secondary text
    "text_subtle": ("#94A3B8", "#64748B"),     # Dim labels

    # Controls
    "button_secondary": ("#E2E8F0", "#313244"),
    "button_secondary_hover": ("#CBD5E1", "#45475A"),
    "input_bg": ("#FFFFFF", "#181825"),
    "input_border": ("#CBD5E1", "#45475A"),
}
