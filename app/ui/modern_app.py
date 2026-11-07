"""
app/ui/modern_app.py
====================
Primary Desktop Application for FA Automation Studio.
Built with CustomTkinter for high-DPI Windows displays:
- Modern Sidebar navigation (Home, Today's Video, History, Accounts, Settings, Logs, Wizard)
- Always-visible Emergency Kill Switch in Sidebar
- Light / Dark theme switching with consistent typography (Nirmala UI with Bengali OpenType support)
- 1366x768 responsive layout (default 1120x720, minimum 960x600)
- Asynchronous worker integration: UI never freezes
"""

import sys
import os
import customtkinter as ctk
from typing import Optional

from app.ui.theme import get_font, COLORS
from app.ui.controller import UIController
from app.ui.views.home_view import HomeView
from app.ui.views.today_view import TodayVideoView
from app.ui.views.history_view import HistoryView
from app.ui.views.accounts_view import AccountsView
from app.ui.views.settings_view import SettingsView
from app.ui.views.logs_view import LogsView
from app.ui.views.wizard_view import WizardView
from app.utils.logging import logger


class ModernDesktopApp(ctk.CTk):
    """
    Main Application Window providing the desktop interface.
    """

    def __init__(self, controller: Optional[UIController] = None):
        super().__init__()

        self.controller = controller if controller is not None else UIController()

        # Appearance setup
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Window configuration
        self.title("FA Video Automation Studio")
        self.geometry("1120x720")
        self.minsize(960, 600)

        # Main Layout: 2 Columns (Sidebar + Content Container)
        self.grid_columnconfigure(0, weight=0)  # Sidebar fixed
        self.grid_columnconfigure(1, weight=1)  # Content fills
        self.grid_rowconfigure(0, weight=1)

        self._current_view_name = ""
        self._current_view_widget = None

        self._build_sidebar()
        self._build_content_area()

        # Show Home view by default
        self.navigate_to("home")

        # Start periodic state refresh loop (every 3 seconds)
        self._schedule_periodic_refresh()

    def _build_sidebar(self):
        """Constructs left navigation sidebar."""
        self.sidebar = ctk.CTkFrame(
            self,
            width=210,
            corner_radius=0,
            fg_color=COLORS["sidebar_bg"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(8, weight=1)  # Spacer row

        # Brand / Title
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=15, pady=(20, 15), sticky="w")

        lbl_logo = ctk.CTkLabel(
            brand_frame,
            text="FA STUDIO",
            font=get_font(20, weight="bold"),
            text_color=COLORS["primary"],
        )
        lbl_logo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            brand_frame,
            text="v2.0 • Autonomous Automation",
            font=get_font(10),
            text_color=COLORS["text_muted"],
        )
        lbl_sub.pack(anchor="w")

        # Navigation Buttons
        self.nav_buttons = {}
        nav_items = [
            ("home", "🏠 Home"),
            ("today_video", "🎬 Today's Video"),
            ("history", "📜 History"),
            ("accounts", "🔑 Accounts"),
            ("settings", "⚙️ Settings"),
            ("logs", "📋 System Logs"),
            ("wizard", "🚀 Setup Wizard"),
        ]

        for idx, (route_key, label_text) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label_text,
                font=get_font(13),
                anchor="w",
                fg_color="transparent",
                hover_color=COLORS["button_secondary_hover"],
                text_color=COLORS["text_main"],
                height=38,
                corner_radius=8,
                command=lambda r=route_key: self.navigate_to(r),
            )
            btn.grid(row=idx, column=0, padx=12, pady=3, sticky="ew")
            self.nav_buttons[route_key] = btn

        # Row 8 is expanding spacer

        # Emergency Kill Switch (Always Visible at Sidebar Bottom)
        self.btn_kill_switch = ctk.CTkButton(
            self.sidebar,
            text="🛑 KILL SWITCH: OFF",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["card_bg"],
            border_width=2,
            border_color=COLORS["danger"][1],
            text_color=COLORS["danger"][1],
            hover_color=COLORS["danger_hover"],
            height=38,
            corner_radius=8,
            command=self._on_toggle_kill_switch,
        )
        self.btn_kill_switch.grid(row=9, column=0, padx=12, pady=(10, 8), sticky="ew")

        # Theme selector (Dark / Light)
        theme_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_frame.grid(row=10, column=0, padx=12, pady=(0, 15), sticky="ew")
        theme_frame.grid_columnconfigure(1, weight=1)

        lbl_theme = ctk.CTkLabel(theme_frame, text="Theme:", font=get_font(11), text_color=COLORS["text_muted"])
        lbl_theme.grid(row=0, column=0, padx=(5, 5), sticky="w")

        self.theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Dark", "Light", "System"],
            font=get_font(11),
            width=90,
            height=26,
            command=self._on_change_theme,
        )
        self.theme_menu.set("Dark")
        self.theme_menu.grid(row=0, column=1, sticky="e")

    def _build_content_area(self):
        """Constructs right-side view host container."""
        self.content_container = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=COLORS["main_bg"],
        )
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

    # -------------------------------------------------------------------------
    # Navigation & Routing
    # -------------------------------------------------------------------------
    def navigate_to(self, route_key: str):
        """Switches active view and updates sidebar highlight."""
        if self._current_view_widget:
            self._current_view_widget.destroy()

        self._current_view_name = route_key

        # Update button highlights
        for k, btn in self.nav_buttons.items():
            if k == route_key:
                btn.configure(
                    fg_color=COLORS["primary"],
                    text_color="#FFFFFF",
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS["text_main"],
                )

        # Instantiate requested view
        if route_key == "home":
            view = HomeView(self.content_container, controller=self.controller, on_navigate=self.navigate_to)
        elif route_key == "today_video":
            view = TodayVideoView(self.content_container, controller=self.controller, on_status_changed=self._on_subview_status_changed)
        elif route_key == "history":
            view = HistoryView(self.content_container, controller=self.controller)
        elif route_key == "accounts":
            view = AccountsView(self.content_container, controller=self.controller, on_account_changed=self._on_subview_status_changed)
        elif route_key == "settings":
            view = SettingsView(self.content_container, controller=self.controller, on_settings_saved=self._on_subview_status_changed)
        elif route_key == "logs":
            view = LogsView(self.content_container, controller=self.controller)
        elif route_key == "wizard":
            view = WizardView(self.content_container, controller=self.controller)
        else:
            view = HomeView(self.content_container, controller=self.controller)

        view.grid(row=0, column=0, sticky="nsew")
        self._current_view_widget = view

        self._update_kill_switch_button()

    def _on_subview_status_changed(self):
        self._update_kill_switch_button()

    # -------------------------------------------------------------------------
    # Controls & State
    # -------------------------------------------------------------------------
    def _on_toggle_kill_switch(self):
        new_val = self.controller.toggle_kill_switch()
        self._update_kill_switch_button()
        # If current view has refresh, call it
        if hasattr(self._current_view_widget, "refresh"):
            self._current_view_widget.refresh()

    def _update_kill_switch_button(self):
        is_active = getattr(self.controller.project_cfg, "kill_switch", False)
        if is_active:
            self.btn_kill_switch.configure(
                text="⚠️ KILL SWITCH ACTIVE",
                fg_color=COLORS["danger"][1],
                hover_color=COLORS["danger_hover"],
                text_color="#FFFFFF",
            )
        else:
            self.btn_kill_switch.configure(
                text="🛑 KILL SWITCH: OFF",
                fg_color=COLORS["card_bg"],
                hover_color=COLORS["danger_hover"],
                text_color=COLORS["danger"][1],
            )

    def _on_change_theme(self, mode: str):
        ctk.set_appearance_mode(mode)

    def _schedule_periodic_refresh(self):
        """Refreshes active view every 3000ms if idle."""
        try:
            if hasattr(self._current_view_widget, "refresh") and not self.controller.is_pipeline_running():
                self._current_view_widget.refresh()
            self._update_kill_switch_button()
        except Exception:
            pass
        self.after(3000, self._schedule_periodic_refresh)


def launch_modern_gui() -> None:
    """Entry point for running the CustomTkinter desktop interface."""
    app = ModernDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    launch_modern_gui()
