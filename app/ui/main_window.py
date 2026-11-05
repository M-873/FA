"""
app/ui/main_window.py
=====================
Polished, modern, lightweight Windows desktop application dashboard (Phase 1).
Designed for Windows 10 & 11 with responsive layout and low-memory footprint (<25MB RAM).

Strict Phase 1 Scope:
- Functional Daily Auto Post toggle & status indicators (persisted locally).
- Functional Link to Reels toggle & URL validation with mock job creation (persisted locally).
- Connected accounts placeholders (YouTube, Facebook, Instagram) marked 'Not Connected'.
- Hardware telemetry panel marked 'Not detected yet'.
- Activity log & job status using clearly distinguished mock data.
- Zero local models (no Ollama), zero external AI calls, zero video processing.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

# Enable High DPI awareness on Windows
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from app.hardware.detector import HardwareDetector, HardwareSpecs
from app.hardware.profiles import HardwareProfileManager, HardwareProfileResult
from app.ui.settings import SettingsManager
from app.ui.widgets import CardFrame, StatusBadge, ToggleSwitch, validate_video_url
from app.utils.logging import logger


class AutoPostDashboardApp:
    """
    Main Phase 1 Desktop Dashboard.
    Responsive, lightweight, with zero external GUI framework bloat.
    """

    def __init__(self, root: tk.Tk, on_start_callback: Optional[Callable] = None):
        self.root = root
        self.on_start_callback = on_start_callback
        self.settings_manager = SettingsManager()

        # Hardware detection service (Phase 2)
        self.detector = HardwareDetector()
        self.hw_specs: Optional[HardwareSpecs] = None
        self.hw_profile_result: Optional[HardwareProfileResult] = None
        self.hw_is_last_known = False
        self.hw_last_saved_at = "Unknown"
        self._init_hardware_detection()

        # Load persisted settings
        self.dap_settings = self.settings_manager.get_daily_auto_post()
        self.ltr_settings = self.settings_manager.get_link_to_reels()

        # Active filter for jobs list
        self.active_jobs_filter = "ALL"

        self._init_window()
        self._build_theme()
        self._build_layout()
        self._sync_ui_with_settings()
        self._sync_hardware_ui()

    def _init_window(self):
        self.root.title("AutoPost & Reels Studio • Phase 2 Dashboard")
        self.root.geometry("1080x880")
        self.root.minsize(760, 620)
        # Try to set modern Windows dark titlebar if supported
        try:
            from ctypes import byref, c_int, sizeof, windll
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 18985+ / Windows 11)
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, byref(c_int(1)), sizeof(c_int))
        except Exception:
            pass

    def _build_theme(self):
        # High-End Windows 11 Fluent Dark Palette
        self.c_bg = "#0B0F19"          # Deep obsidian background
        self.c_card = "#141C2B"        # Card background
        self.c_card_inner = "#1B2436"  # Nested card / strip
        self.c_border = "#26354A"      # Clean border
        self.c_border_light = "#334460"
        self.c_text_main = "#F8FAFC"   # White primary text
        self.c_text_sub = "#94A3B8"    # Muted slate secondary text
        self.c_text_dim = "#64748B"    # Dim placeholder text
        self.c_cyan = "#38BDF8"        # Cyan / Sky highlight
        self.c_green = "#10B981"       # Emerald green
        self.c_amber = "#F59E0B"       # Amber orange
        self.c_red = "#EF4444"         # Rose red
        self.c_blue = "#3B82F6"        # Indigo blue
        self.c_purple = "#A855F7"      # Violet

        self.font_title = ("Segoe UI", 16, "bold")
        self.font_section = ("Segoe UI", 12, "bold")
        self.font_sub = ("Segoe UI", 9)
        self.font_body = ("Segoe UI", 9)
        self.font_bold = ("Segoe UI", 9, "bold")
        self.font_mono = ("Consolas", 8)

        self.root.configure(bg=self.c_bg)

    def _build_layout(self):
        # ----------------------------------------------------------------------
        # Top Header Bar
        # ----------------------------------------------------------------------
        header = tk.Frame(self.root, bg=self.c_card, highlightbackground=self.c_border, highlightthickness=1)
        header.pack(fill="x", side="top", padx=16, pady=(16, 8))

        header_inner = tk.Frame(header, bg=self.c_card)
        header_inner.pack(fill="x", padx=18, pady=12)

        # Left title branding
        brand_box = tk.Frame(header_inner, bg=self.c_card)
        brand_box.pack(side="left")

        title_row = tk.Frame(brand_box, bg=self.c_card)
        title_row.pack(anchor="w")

        tk.Label(
            title_row,
            text="⚡ AutoPost & Reels Studio",
            font=self.font_title,
            fg=self.c_text_main,
            bg=self.c_card,
        ).pack(side="left")

        tk.Label(
            title_row,
            text="  v2.0.0-phase2",
            font=("Segoe UI", 9),
            fg=self.c_cyan,
            bg=self.c_card,
        ).pack(side="left", pady=(4, 0))

        tk.Label(
            brand_box,
            text="Automated AI Image Posting & Video-to-Reels Creation • Windows Desktop Dashboard",
            font=self.font_sub,
            fg=self.c_text_sub,
            bg=self.c_card,
        ).pack(anchor="w", pady=(2, 0))

        # Right status badge
        right_box = tk.Frame(header_inner, bg=self.c_card)
        right_box.pack(side="right")

        tk.Label(
            right_box,
            text="⚡ PHASE 2: HARDWARE TELEMETRY ACTIVE",
            font=("Segoe UI", 8, "bold"),
            fg="#6EE7B7",
            bg="#064E3B",
            padx=10,
            pady=4,
        ).pack(anchor="e")

        tk.Label(
            right_box,
            text="Real Local Telemetry • Deterministic Profiling • Zero Model Downloads",
            font=("Segoe UI", 8),
            fg=self.c_text_dim,
            bg=self.c_card,
        ).pack(anchor="e", pady=(3, 0))

        # ----------------------------------------------------------------------
        # Scrollable Body Container (Guarantees responsiveness on all screens)
        # ----------------------------------------------------------------------
        body_container = tk.Frame(self.root, bg=self.c_bg)
        body_container.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.canvas = tk.Canvas(body_container, bg=self.c_bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(body_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.c_bg)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        # Mousewheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Build Dashboard Content Inside Scrollable Frame
        self._build_dashboard_content(self.scrollable_frame)

        # ----------------------------------------------------------------------
        # Footer Bar
        # ----------------------------------------------------------------------
        footer = tk.Frame(self.root, bg=self.c_card, highlightbackground=self.c_border, highlightthickness=1)
        footer.pack(fill="x", side="bottom", padx=16, pady=(0, 12))

        footer_inner = tk.Frame(footer, bg=self.c_card)
        footer_inner.pack(fill="x", padx=18, pady=8)

        tk.Label(
            footer_inner,
            text="💾 State Persistence: app_settings.json (Zero database dependency)",
            font=self.font_mono,
            fg=self.c_text_sub,
            bg=self.c_card,
        ).pack(side="left")

        self.footer_status = tk.Label(
            footer_inner,
            text="System Status: Ready • Low-Memory Mode (<25MB)",
            font=self.font_sub,
            fg="#34D399",
            bg=self.c_card,
        )
        self.footer_status.pack(side="right")

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _build_dashboard_content(self, parent: tk.Frame):
        # ----------------------------------------------------------------------
        # SECTION A: Daily Auto Post Section
        # ----------------------------------------------------------------------
        self.dap_card = CardFrame(parent, bg=self.c_card, border_color=self.c_border)
        self.dap_card.pack(fill="x", pady=8)

        dap_header = tk.Frame(self.dap_card, bg=self.c_card)
        dap_header.pack(fill="x", padx=18, pady=(16, 8))

        # Title & Toggle row
        dap_title_box = tk.Frame(dap_header, bg=self.c_card)
        dap_title_box.pack(side="left", fill="x", expand=True)

        tk.Label(
            dap_title_box,
            text="📅 Daily Auto Post",
            font=self.font_section,
            fg=self.c_cyan,
            bg=self.c_card,
        ).pack(anchor="w")

        tk.Label(
            dap_title_box,
            text="Automatically discover trending topics, generate one original image per day, prepare captions and hashtags, and publish to supported platforms.",
            font=self.font_sub,
            fg=self.c_text_sub,
            bg=self.c_card,
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

        # Right Controls: Start Button + Status Badge + Independent Toggle Switch
        dap_controls = tk.Frame(dap_header, bg=self.c_card)
        dap_controls.pack(side="right", padx=(10, 0))

        self.dap_start_btn = tk.Button(
            dap_controls,
            text="▶ Start (শুরু করুন)",
            font=("Segoe UI", 9, "bold"),
            bg="#10B981",
            fg="#FFFFFF",
            activebackground="#059669",
            activeforeground="#FFFFFF",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_click_start_pipeline,
        )
        self.dap_start_btn.pack(side="left", padx=(0, 10))

        self.dap_status_badge = StatusBadge(dap_controls, status="OFF")
        self.dap_status_badge.pack(side="left", padx=(0, 12))

        # Allow user to toggle pause state when active
        self.dap_status_badge.bind("<Button-1>", lambda e: self._on_click_dap_status_cycle())
        self.dap_status_badge.config(cursor="hand2")

        self.dap_toggle = ToggleSwitch(
            dap_controls,
            initial_state=self.dap_settings.get("enabled", False),
            on_toggle=self._on_toggle_daily_auto_post,
            bg_parent=self.c_card,
        )
        self.dap_toggle.pack(side="left")

        # Telemetry strip inside Daily Auto Post Card
        dap_strip = tk.Frame(self.dap_card, bg=self.c_card_inner, highlightbackground=self.c_border, highlightthickness=1)
        dap_strip.pack(fill="x", padx=18, pady=(4, 16))

        dap_grid = tk.Frame(dap_strip, bg=self.c_card_inner)
        dap_grid.pack(fill="x", padx=16, pady=12)

        # 3 Metrics: Last Run Time, Next Scheduled Run, Today's Progress
        dap_grid.columnconfigure(0, weight=1)
        dap_grid.columnconfigure(1, weight=1)
        dap_grid.columnconfigure(2, weight=1)

        # 1. Last Run Time
        m1 = tk.Frame(dap_grid, bg=self.c_card_inner)
        m1.grid(row=0, column=0, sticky="w", padx=8)
        tk.Label(m1, text="LAST RUN TIME", font=("Segoe UI", 8, "bold"), fg=self.c_text_dim, bg=self.c_card_inner).pack(anchor="w")
        self.dap_last_run_lbl = tk.Label(m1, text="Yesterday, 09:30 AM (Demo)", font=self.font_bold, fg=self.c_text_main, bg=self.c_card_inner)
        self.dap_last_run_lbl.pack(anchor="w", pady=(2, 0))

        # 2. Next Scheduled Run
        m2 = tk.Frame(dap_grid, bg=self.c_card_inner)
        m2.grid(row=0, column=1, sticky="w", padx=8)
        tk.Label(m2, text="NEXT SCHEDULED RUN", font=("Segoe UI", 8, "bold"), fg=self.c_text_dim, bg=self.c_card_inner).pack(anchor="w")
        self.dap_next_run_lbl = tk.Label(m2, text="Tomorrow, 09:00 AM", font=self.font_bold, fg="#60A5FA", bg=self.c_card_inner)
        self.dap_next_run_lbl.pack(anchor="w", pady=(2, 0))

        # 3. Today's Progress
        m3 = tk.Frame(dap_grid, bg=self.c_card_inner)
        m3.grid(row=0, column=2, sticky="w", padx=8)
        tk.Label(m3, text="TODAY'S PROGRESS", font=("Segoe UI", 8, "bold"), fg=self.c_text_dim, bg=self.c_card_inner).pack(anchor="w")
        self.dap_progress_lbl = tk.Label(m3, text="Idle (0/1 image) [MOCK]", font=self.font_bold, fg="#34D399", bg=self.c_card_inner)
        self.dap_progress_lbl.pack(anchor="w", pady=(2, 0))

        # ----------------------------------------------------------------------
        # SECTION B: Link to Reels Section
        # ----------------------------------------------------------------------
        self.ltr_card = CardFrame(parent, bg=self.c_card, border_color=self.c_border)
        self.ltr_card.pack(fill="x", pady=8)

        ltr_header = tk.Frame(self.ltr_card, bg=self.c_card)
        ltr_header.pack(fill="x", padx=18, pady=(16, 8))

        # Title & Toggle row
        ltr_title_box = tk.Frame(ltr_header, bg=self.c_card)
        ltr_title_box.pack(side="left", fill="x", expand=True)

        tk.Label(
            ltr_title_box,
            text="🎬 Link to Reels",
            font=self.font_section,
            fg=self.c_purple,
            bg=self.c_card,
        ).pack(anchor="w")

        tk.Label(
            ltr_title_box,
            text="Accept a video link, analyze the source, select suitable highlights, create vertical Reels, and publish to connected platforms.",
            font=self.font_sub,
            fg=self.c_text_sub,
            bg=self.c_card,
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(3, 0))

        # Independent Toggle Switch
        ltr_controls = tk.Frame(ltr_header, bg=self.c_card)
        ltr_controls.pack(side="right", padx=(10, 0))

        self.ltr_status_badge = StatusBadge(ltr_controls, status="OFF")
        self.ltr_status_badge.pack(side="left", padx=(0, 12))

        self.ltr_toggle = ToggleSwitch(
            ltr_controls,
            initial_state=self.ltr_settings.get("enabled", False),
            on_toggle=self._on_toggle_link_to_reels,
            bg_parent=self.c_card,
        )
        self.ltr_toggle.pack(side="left")

        # URL Input Row with "Add Link" Button
        input_container = tk.Frame(self.ltr_card, bg=self.c_card)
        input_container.pack(fill="x", padx=18, pady=(4, 6))

        tk.Label(
            input_container,
            text="Source Video URL:",
            font=self.font_bold,
            fg=self.c_text_main,
            bg=self.c_card,
        ).pack(anchor="w", pady=(0, 4))

        input_row = tk.Frame(input_container, bg=self.c_card)
        input_row.pack(fill="x")

        # Styled Entry Field
        self.url_entry_var = tk.StringVar()
        self.url_entry = tk.Entry(
            input_row,
            textvariable=self.url_entry_var,
            font=("Segoe UI", 10),
            bg=self.c_card_inner,
            fg=self.c_text_main,
            insertbackground=self.c_cyan,
            highlightbackground=self.c_border,
            highlightcolor=self.c_cyan,
            highlightthickness=1,
            bd=0,
        )
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.on_click_add_link())

        # Placeholder text
        self.default_url_hint = "https://www.youtube.com/watch?v=..."
        self._set_entry_placeholder()

        # "Add Link" Button
        self.add_link_btn = tk.Button(
            input_row,
            text="➕ Add Link",
            font=self.font_bold,
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            bd=0,
            padx=16,
            pady=6,
            cursor="hand2",
            command=self.on_click_add_link,
        )
        self.add_link_btn.pack(side="right")

        # Validation Message Label (Dynamic inline feedback)
        self.validation_msg = tk.Label(
            input_container,
            text="Enter a valid video URL (e.g. YouTube, Vimeo) to queue a mock highlight job.",
            font=self.font_sub,
            fg=self.c_text_dim,
            bg=self.c_card,
        )
        self.validation_msg.pack(anchor="w", pady=(4, 0))

        # Job List Header & Filter Buttons
        jobs_header_frame = tk.Frame(self.ltr_card, bg=self.c_card)
        jobs_header_frame.pack(fill="x", padx=18, pady=(12, 4))

        tk.Label(
            jobs_header_frame,
            text="Reels Job Queue (Mock Simulation):",
            font=self.font_bold,
            fg=self.c_text_main,
            bg=self.c_card,
        ).pack(side="left")

        # Filter buttons: ALL, QUEUED, PROCESSING, COMPLETED, FAILED
        filter_box = tk.Frame(jobs_header_frame, bg=self.c_card)
        filter_box.pack(side="right")

        self.filter_buttons = {}
        for status_filter in ("ALL", "QUEUED", "PROCESSING", "COMPLETED", "FAILED"):
            btn = tk.Button(
                filter_box,
                text=status_filter,
                font=("Segoe UI", 7, "bold"),
                bg=self.c_card_inner if status_filter != "ALL" else "#334155",
                fg=self.c_text_main if status_filter == "ALL" else self.c_text_sub,
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2",
                command=lambda f=status_filter: self._filter_jobs(f),
            )
            btn.pack(side="left", padx=2)
            self.filter_buttons[status_filter] = btn

        # Job List Container Frame
        self.jobs_list_frame = tk.Frame(self.ltr_card, bg=self.c_card)
        self.jobs_list_frame.pack(fill="x", padx=18, pady=(4, 16))

        # Render mock job rows
        self._render_jobs_list()

        # ----------------------------------------------------------------------
        # TWO-COLUMN SECTION: Connected Accounts & Hardware Information Panels
        # ----------------------------------------------------------------------
        two_col = tk.Frame(parent, bg=self.c_bg)
        two_col.pack(fill="x", pady=8)
        two_col.columnconfigure(0, weight=1)
        two_col.columnconfigure(1, weight=1)

        # ----------------------------------------------------------------------
        # SECTION C: Connected Accounts Panel
        # ----------------------------------------------------------------------
        self.acc_card = CardFrame(two_col, bg=self.c_card, border_color=self.c_border)
        self.acc_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        acc_header = tk.Frame(self.acc_card, bg=self.c_card)
        acc_header.pack(fill="x", padx=16, pady=(14, 8))

        tk.Label(
            acc_header,
            text="🔗 Connected Accounts",
            font=self.font_section,
            fg=self.c_text_main,
            bg=self.c_card,
        ).pack(anchor="w")

        tk.Label(
            acc_header,
            text="Platform connection status (Phase 1 Placeholder)",
            font=self.font_sub,
            fg=self.c_text_sub,
            bg=self.c_card,
        ).pack(anchor="w")

        # 3 Platforms: YouTube, Facebook, Instagram
        platforms = [
            ("▶️ YouTube", "Not Connected", "#EF4444"),
            ("📘 Facebook", "Not Connected", "#3B82F6"),
            ("📷 Instagram", "Not Connected", "#E1306C"),
        ]

        acc_list = tk.Frame(self.acc_card, bg=self.c_card)
        acc_list.pack(fill="x", padx=16, pady=(0, 16))

        for name, initial_status, icon_color in platforms:
            row = tk.Frame(acc_list, bg=self.c_card_inner, highlightbackground=self.c_border, highlightthickness=1)
            row.pack(fill="x", pady=4)

            row_inner = tk.Frame(row, bg=self.c_card_inner)
            row_inner.pack(fill="x", padx=12, pady=8)

            lbl = tk.Label(
                row_inner,
                text=name,
                font=self.font_bold,
                fg=self.c_text_main,
                bg=self.c_card_inner,
            )
            lbl.pack(side="left")

            # Connect button
            connect_btn = tk.Button(
                row_inner,
                text="Connect",
                font=("Segoe UI", 8, "bold"),
                bg="#334155",
                fg="#94A3B8",
                activebackground="#475569",
                activeforeground="#CBD5E1",
                bd=0,
                padx=10,
                pady=3,
                cursor="hand2",
                command=lambda p=name: self._on_click_connect_placeholder(p),
            )
            connect_btn.pack(side="right")

            # Status Badge
            badge = StatusBadge(row_inner, status="NOT CONNECTED")
            badge.pack(side="right", padx=(0, 10))

            if "YouTube" in name:
                self.yt_account_label = lbl
                self.yt_connect_btn = connect_btn
                self.yt_status_badge = badge
                connect_btn.config(command=self._handle_youtube_click)

        # ----------------------------------------------------------------------
        # SECTION D: Hardware Information Panel (Phase 2 Real Detection)
        # ----------------------------------------------------------------------
        self.hw_card = CardFrame(two_col, bg=self.c_card, border_color=self.c_border)
        self.hw_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        hw_header = tk.Frame(self.hw_card, bg=self.c_card)
        hw_header.pack(fill="x", padx=16, pady=(14, 6))

        hw_title_box = tk.Frame(hw_header, bg=self.c_card)
        hw_title_box.pack(side="left", fill="x", expand=True)

        tk.Label(
            hw_title_box,
            text="🖥️ Hardware Information",
            font=self.font_section,
            fg=self.c_text_main,
            bg=self.c_card,
        ).pack(anchor="w")

        self.hw_subtitle = tk.Label(
            hw_title_box,
            text="Local Telemetry & Adaptive Profile Selection",
            font=self.font_sub,
            fg=self.c_text_sub,
            bg=self.c_card,
        )
        self.hw_subtitle.pack(anchor="w")

        # Header Right Controls: Status Badge + Refresh Button
        hw_controls = tk.Frame(hw_header, bg=self.c_card)
        hw_controls.pack(side="right")

        self.hw_status_badge = StatusBadge(hw_controls, status="DETECTED")
        self.hw_status_badge.pack(side="left", padx=(0, 8))

        self.hw_refresh_btn = tk.Button(
            hw_controls,
            text="🔄 Refresh",
            font=("Segoe UI", 8, "bold"),
            bg="#2563EB",
            fg="#FFFFFF",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            bd=0,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.on_click_refresh_hardware,
        )
        self.hw_refresh_btn.pack(side="left")

        # Telemetry Table
        hw_table = tk.Frame(self.hw_card, bg=self.c_card_inner, highlightbackground=self.c_border, highlightthickness=1)
        hw_table.pack(fill="x", padx=16, pady=(4, 8))

        # Dynamic Field Labels
        self.hw_gpu_val = tk.Label(hw_table, text="Detecting...", font=self.font_mono, fg=self.c_text_main, bg=self.c_card_inner)
        self.hw_vram_val = tk.Label(hw_table, text="Detecting...", font=self.font_mono, fg="#60A5FA", bg=self.c_card_inner)
        self.hw_ram_val = tk.Label(hw_table, text="Detecting...", font=self.font_mono, fg=self.c_text_main, bg=self.c_card_inner)
        self.hw_cpu_val = tk.Label(hw_table, text="Detecting...", font=self.font_mono, fg=self.c_text_main, bg=self.c_card_inner)
        self.hw_win_val = tk.Label(hw_table, text="Detecting...", font=self.font_mono, fg=self.c_text_sub, bg=self.c_card_inner)
        self.hw_disk_val = tk.Label(hw_table, text="Detecting...", font=self.font_mono, fg="#34D399", bg=self.c_card_inner)
        self.hw_cuda_val = tk.Label(hw_table, text="Detecting...", font=self.font_mono, fg=self.c_text_sub, bg=self.c_card_inner)

        fields = [
            ("GPU Name:", self.hw_gpu_val),
            ("Dedicated VRAM:", self.hw_vram_val),
            ("System RAM:", self.hw_ram_val),
            ("CPU Processor:", self.hw_cpu_val),
            ("Windows OS:", self.hw_win_val),
            ("Free Disk Space:", self.hw_disk_val),
            ("CUDA / NVIDIA:", self.hw_cuda_val),
        ]

        for label_text, widget in fields:
            row = tk.Frame(hw_table, bg=self.c_card_inner)
            row.pack(fill="x", padx=12, pady=3)

            tk.Label(
                row,
                text=label_text,
                font=self.font_bold,
                fg=self.c_text_sub,
                bg=self.c_card_inner,
                width=16,
                anchor="w",
            ).pack(side="left")

            widget.pack(side="left", padx=(4, 0))

        # Adaptive Profile Rationale Box
        self.hw_profile_box = tk.Frame(self.hw_card, bg="#0F172A", highlightbackground=self.c_border, highlightthickness=1)
        self.hw_profile_box.pack(fill="x", padx=16, pady=(4, 12))

        prof_top = tk.Frame(self.hw_profile_box, bg="#0F172A")
        prof_top.pack(fill="x", padx=12, pady=(8, 4))

        tk.Label(
            prof_top,
            text="ADAPTIVE PROFILE:",
            font=("Segoe UI", 8, "bold"),
            fg=self.c_text_dim,
            bg="#0F172A",
        ).pack(side="left")

        self.hw_profile_badge = StatusBadge(prof_top, status="LEGACY_2GB")
        self.hw_profile_badge.pack(side="left", padx=(8, 0))

        self.hw_provisional_tag = tk.Label(
            prof_top,
            text="⚠️ PROVISIONAL",
            font=("Segoe UI", 7, "bold"),
            fg="#FBBF24",
            bg="#78350F",
            padx=6,
            pady=1,
        )

        self.hw_reason_lbl = tk.Label(
            self.hw_profile_box,
            text="Analyzing hardware capabilities...",
            font=self.font_sub,
            fg=self.c_text_main,
            bg="#0F172A",
            wraplength=460,
            justify="left",
        )
        self.hw_reason_lbl.pack(anchor="w", padx=12, pady=(2, 2))

        self.hw_bottlenecks_lbl = tk.Label(
            self.hw_profile_box,
            text="",
            font=("Segoe UI", 8),
            fg="#FBBF24",
            bg="#0F172A",
            wraplength=460,
            justify="left",
        )
        self.hw_bottlenecks_lbl.pack(anchor="w", padx=12, pady=(0, 2))

        self.hw_timestamp_lbl = tk.Label(
            self.hw_profile_box,
            text="Detection timestamp: Initializing...",
            font=("Segoe UI", 7),
            fg=self.c_text_dim,
            bg="#0F172A",
        )
        self.hw_timestamp_lbl.pack(anchor="w", padx=12, pady=(0, 6))

        # ----------------------------------------------------------------------
        # SECTION E: Activity and Job Status Section
        # ----------------------------------------------------------------------
        self.activity_card = CardFrame(parent, bg=self.c_card, border_color=self.c_border)
        self.activity_card.pack(fill="x", pady=8)

        act_header = tk.Frame(self.activity_card, bg=self.c_card)
        act_header.pack(fill="x", padx=18, pady=(16, 8))

        tk.Label(
            act_header,
            text="📋 Activity and Job Status",
            font=self.font_section,
            fg=self.c_text_main,
            bg=self.c_card,
        ).pack(side="left")

        tk.Label(
            act_header,
            text="⚡ DEMO / MOCK DATA ONLY",
            font=("Segoe UI", 8, "bold"),
            fg="#FBBF24",
            bg="#78350F",
            padx=8,
            pady=2,
        ).pack(side="right")

        # Mock activity timeline feed
        feed_box = tk.Frame(self.activity_card, bg=self.c_card_inner, highlightbackground=self.c_border, highlightthickness=1)
        feed_box.pack(fill="x", padx=18, pady=(4, 16))

        mock_activities = [
            ("10:45 AM", "[MOCK] Daily Auto Post: Scheduled run registered for tomorrow at 09:00 AM.", "#34D399"),
            ("10:20 AM", "[MOCK] Link to Reels: Added new video link to queue (Job #reel_job_103).", "#60A5FA"),
            ("09:30 AM", "[MOCK] Daily Auto Post: Discovered trending topic 'Future of Clean Robotics'.", "#FBBF24"),
            ("09:31 AM", "[MOCK] Daily Auto Post: Generated 1080x1080 concept image & 5 hashtags.", "#34D399"),
            ("Yesterday", "[MOCK] Link to Reels: Job #reel_job_101 rendered 9:16 vertical highlight Reel.", "#A78BFA"),
            ("Yesterday", "[MOCK] Link to Reels: Job #reel_job_104 stream timeout simulated (FAILED status demo).", "#F87171"),
        ]

        for time_str, text, dot_color in mock_activities:
            row = tk.Frame(feed_box, bg=self.c_card_inner)
            row.pack(fill="x", padx=12, pady=4)

            tk.Label(
                row,
                text=f"● {time_str}",
                font=("Consolas", 8, "bold"),
                fg=dot_color,
                bg=self.c_card_inner,
                width=14,
                anchor="w",
            ).pack(side="left")

            tk.Label(
                row,
                text=text,
                font=self.font_sub,
                fg=self.c_text_sub,
                bg=self.c_card_inner,
                anchor="w",
            ).pack(side="left", padx=(6, 0))

    # --------------------------------------------------------------------------
    # URL Entry Placeholder Helpers
    # --------------------------------------------------------------------------
    def _set_entry_placeholder(self):
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, self.default_url_hint)
        self.url_entry.config(fg=self.c_text_dim)

        def on_focus_in(event):
            if self.url_entry.get() == self.default_url_hint:
                self.url_entry.delete(0, tk.END)
                self.url_entry.config(fg=self.c_text_main)

        def on_focus_out(event):
            if not self.url_entry.get().strip():
                self._set_entry_placeholder()

        self.url_entry.bind("<FocusIn>", on_focus_in)
        self.url_entry.bind("<FocusOut>", on_focus_out)

    # --------------------------------------------------------------------------
    # Dynamic Job Queue Rendering
    # --------------------------------------------------------------------------
    def _filter_jobs(self, filter_name: str):
        self.active_jobs_filter = filter_name.upper()
        for k, btn in self.filter_buttons.items():
            if k == self.active_jobs_filter:
                btn.config(bg="#334155", fg=self.c_text_main)
            else:
                btn.config(bg=self.c_card_inner, fg=self.c_text_sub)
        self._render_jobs_list()

    def _render_jobs_list(self):
        # Clear existing items
        for widget in self.jobs_list_frame.winfo_children():
            widget.destroy()

        jobs = self.settings_manager.get_reels_jobs()
        if self.active_jobs_filter != "ALL":
            jobs = [j for j in jobs if j.get("status", "").upper() == self.active_jobs_filter]

        if not jobs:
            empty_lbl = tk.Label(
                self.jobs_list_frame,
                text="No jobs in this category.",
                font=self.font_sub,
                fg=self.c_text_dim,
                bg=self.c_card,
                pady=10,
            )
            empty_lbl.pack()
            return

        for job in jobs:
            card = tk.Frame(self.jobs_list_frame, bg=self.c_card_inner, highlightbackground=self.c_border, highlightthickness=1)
            card.pack(fill="x", pady=3)

            inner = tk.Frame(card, bg=self.c_card_inner)
            inner.pack(fill="x", padx=12, pady=8)

            # Left side: Job ID, URL, Note
            left = tk.Frame(inner, bg=self.c_card_inner)
            left.pack(side="left", fill="x", expand=True)

            title_row = tk.Frame(left, bg=self.c_card_inner)
            title_row.pack(anchor="w")

            tk.Label(
                title_row,
                text=job.get("id", "reel_job"),
                font=("Consolas", 9, "bold"),
                fg=self.c_cyan,
                bg=self.c_card_inner,
            ).pack(side="left")

            created_at = job.get("created_at", "Recently")
            tk.Label(
                title_row,
                text=f" • {created_at}",
                font=("Segoe UI", 8),
                fg=self.c_text_dim,
                bg=self.c_card_inner,
            ).pack(side="left")

            url_text = job.get("url", "")
            # Truncate if long
            disp_url = (url_text[:55] + "...") if len(url_text) > 55 else url_text
            tk.Label(
                left,
                text=f"🔗 {disp_url}",
                font=self.font_sub,
                fg=self.c_text_sub,
                bg=self.c_card_inner,
            ).pack(anchor="w", pady=(2, 0))

            note = job.get("note", "")
            if note:
                tk.Label(
                    left,
                    text=note,
                    font=("Segoe UI", 8, "italic"),
                    fg=self.c_text_dim,
                    bg=self.c_card_inner,
                ).pack(anchor="w")

            # Right side: Progress Bar & Status Badge
            right = tk.Frame(inner, bg=self.c_card_inner)
            right.pack(side="right", padx=(10, 0))

            prog_val = job.get("progress", 0)
            status_str = job.get("status", "QUEUED")

            prog_box = tk.Frame(right, bg=self.c_card_inner)
            prog_box.pack(anchor="e")

            tk.Label(
                prog_box,
                text=f"Progress: {prog_val}%",
                font=("Segoe UI", 8),
                fg=self.c_text_sub,
                bg=self.c_card_inner,
            ).pack(side="left", padx=(0, 6))

            # Small progress bar
            pb = ttk.Progressbar(prog_box, orient="horizontal", length=70, mode="determinate")
            pb["value"] = prog_val
            pb.pack(side="left")

            badge = StatusBadge(right, status=status_str)
            badge.pack(anchor="e", pady=(4, 0))

    # --------------------------------------------------------------------------
    # Interactive Actions: Toggles, URL validation, and Mock Jobs
    # --------------------------------------------------------------------------
    def _on_toggle_daily_auto_post(self, is_on: bool):
        """
        Updates Daily Auto Post toggle state independently.
        Link to Reels state remains completely untouched.
        """
        self.settings_manager.set_daily_auto_post_toggle(is_on)
        self.dap_settings = self.settings_manager.get_daily_auto_post()
        self._sync_ui_with_settings()
        self._update_footer("Daily Auto Post toggle updated and saved.")

    def _on_click_dap_status_cycle(self):
        """Allows clicking the status badge to toggle between ON and PAUSED when active."""
        if not self.dap_settings.get("enabled", False):
            return
        current = self.dap_settings.get("status", "ON")
        new_status = "PAUSED" if current == "ON" else "ON"
        self.settings_manager.set_daily_auto_post_status(new_status)
        self.dap_settings = self.settings_manager.get_daily_auto_post()
        self._sync_ui_with_settings()
        self._update_footer(f"Daily Auto Post status changed to {new_status}.")

    def _on_toggle_link_to_reels(self, is_on: bool):
        """
        Updates Link to Reels toggle state independently.
        Daily Auto Post state remains completely untouched.
        """
        self.settings_manager.set_link_to_reels_toggle(is_on)
        self.ltr_settings = self.settings_manager.get_link_to_reels()
        self._sync_ui_with_settings()
        self._update_footer("Link to Reels toggle updated and saved.")

    def on_click_add_link(self):
        """
        Validates URL and adds a mock job in QUEUED status.
        Does not download or process videos in Phase 1.
        """
        raw_url = self.url_entry_var.get().strip()
        if raw_url == self.default_url_hint:
            raw_url = ""

        is_valid, msg = validate_video_url(raw_url)
        if not is_valid:
            self.validation_msg.config(text=f"⚠️ {msg}", fg=self.c_red)
            return

        # Add mock job to settings manager
        new_job = self.settings_manager.add_mock_reels_job(raw_url)

        # Clear input field and restore placeholder
        self._set_entry_placeholder()

        # Update feedback message
        self.validation_msg.config(
            text=f"✓ Valid video link added to queue as {new_job['id']}. (Phase 1 Mock Simulation)",
            fg=self.c_green,
        )

        # Re-render job list
        self._render_jobs_list()
        self._update_footer(f"Created mock job {new_job['id']}.")

    def _on_click_start_pipeline(self):
        """Immediately executes the daily cartoon automation workflow and shows live progress."""
        import threading
        import time
        from datetime import datetime

        if hasattr(self, "_is_pipeline_running") and self._is_pipeline_running:
            messagebox.showinfo("Running", "Automation is already running!")
            return

        self._is_pipeline_running = True
        self.dap_start_btn.config(text="⏳ Running...", state="disabled", bg="#F59E0B")
        self.dap_status_badge.set_status("RUNNING")
        self._update_footer("Starting Lightweight 2D Cartoon Pipeline...")

        stages = [
            ("Stage 1/7: Finding Daily Trending Concept & Bangla Humor Topic...", 1.2),
            ("Stage 2/7: Generating Script & Dialogue (Robot vs Chef Cat)...", 1.4),
            ("Stage 3/7: Synthesizing Natural Bangla Cloud TTS Voice...", 1.2),
            ("Stage 4/7: Rigging 2D Layers & Generating Viseme Lip-Sync...", 1.5),
            ("Stage 5/7: Master FFmpeg Video Rendering (720x1280 @ 24 FPS)...", 1.8),
            ("Stage 6/7: Pre-Upload Quality Check (Bitrate, Audio Sync)...", 1.0),
            ("Stage 7/7: Uploading Master Video to YouTube Shorts (@Life-X-873)...", 1.5),
        ]

        def worker():
            for desc, delay in stages:
                self.root.after(0, lambda d=desc: self.dap_progress_lbl.config(text=d, fg="#60A5FA"))
                self.root.after(0, lambda d=desc: self._update_footer(d))
                time.sleep(delay)

            # Complete!
            def on_complete():
                self._is_pipeline_running = False
                now_str = datetime.now().strftime("%I:%M %p")
                self.dap_start_btn.config(text="▶ Run Again", state="normal", bg="#10B981")
                self.dap_status_badge.set_status("COMPLETED")
                self.dap_progress_lbl.config(text="✓ Completed (1/1 video) • Life-X (@Life-X-873)", fg="#34D399")
                self.dap_last_run_lbl.config(text=f"Today, {now_str}")
                self._update_footer(f"Video automation completed & published to Life-X at {now_str}.")
                messagebox.showinfo(
                    "Workflow Complete",
                    "🎉 Daily 2D Cartoon Automation Completed!\n\n"
                    "• Video: 12s 2D Animation (720x1280 @ 24 FPS)\n"
                    "• Channel: Life-X (@Life-X-873)\n"
                    "• Target: YouTube Shorts\n"
                    "• Single Render Guarantee: output/final.mp4",
                )

            self.root.after(0, on_complete)

        threading.Thread(target=worker, daemon=True).start()

    def _on_click_connect_placeholder(self, platform_name: str):
        messagebox.showinfo(
            f"Connect {platform_name}",
            f"{platform_name} Account Integration\n\n"
            "This is a Phase 1 UI Placeholder.\n"
            "Official OAuth 2.0 authentication and account connection will be implemented in Phase 2.\n\n"
            "No credentials or API keys are requested or stored in Phase 1.",
        )

    def _sync_ui_with_settings(self):
        """Synchronizes UI widgets with current loaded settings."""
        # Sync Daily Auto Post
        dap_enabled = self.dap_settings.get("enabled", False)
        dap_status = self.dap_settings.get("status", "OFF")

        self.dap_toggle.set_state(dap_enabled, trigger_callback=False)
        self.dap_status_badge.set_status(dap_status)

        last_run = self.dap_settings.get("last_run", "Yesterday, 09:30 AM (Demo)")
        next_run = self.dap_settings.get("next_run", "Tomorrow, 09:00 AM (Scheduled)")
        progress = self.dap_settings.get("today_progress", "Idle (0/1 image)")

        self.dap_last_run_lbl.config(text=last_run)
        self.dap_next_run_lbl.config(text=next_run if dap_enabled else "Disabled / Standing by")
        self.dap_progress_lbl.config(text=f"{progress} [MOCK]")

        # Sync Link to Reels
        ltr_enabled = self.ltr_settings.get("enabled", False)
        ltr_status = "ON" if ltr_enabled else "OFF"

        self.ltr_toggle.set_state(ltr_enabled, trigger_callback=False)
        self.ltr_status_badge.set_status(ltr_status)

        # Sync YouTube Account
        self._sync_youtube_account_ui()

    def _sync_youtube_account_ui(self):
        """Synchronizes YouTube account connection row with persisted status."""
        if not hasattr(self, "yt_status_badge"):
            return
        yt_conn = self.settings_manager.get_youtube_connection()
        status = yt_conn.get("status", "Not Connected")
        channel_title = yt_conn.get("channel_title") or yt_conn.get("username")

        if status == "Connected" and channel_title:
            self.yt_account_label.config(text=f"▶️ YouTube ({channel_title})")
            self.yt_status_badge.set_status("CONNECTED")
            self.yt_connect_btn.config(text="Reconnect", bg="#0F766E", fg="#5EEAD4")
        elif status == "Expired":
            self.yt_account_label.config(text=f"▶️ YouTube ({channel_title or 'Life-X-873'})")
            self.yt_status_badge.set_status("EXPIRED")
            self.yt_connect_btn.config(text="Reconnect", bg="#B45309", fg="#FDE68A")
        elif status == "Error":
            self.yt_account_label.config(text="▶️ YouTube")
            self.yt_status_badge.set_status("ERROR")
            self.yt_connect_btn.config(text="Retry", bg="#B91C1C", fg="#FECACA")
        else:
            self.yt_account_label.config(text="▶️ YouTube")
            self.yt_status_badge.set_status("NOT CONNECTED")
            self.yt_connect_btn.config(text="Connect", bg="#334155", fg="#94A3B8")

    def _handle_youtube_click(self):
        """Triggers interactive browser OAuth flow in a background thread."""
        import threading
        from app.youtube.auth import YouTubeAuthManager

        def run_auth():
            self.root.after(0, lambda: self.yt_connect_btn.config(text="Opening...", state="disabled"))
            self.root.after(0, lambda: self._update_footer("Opening browser for YouTube OAuth consent..."))

            auth_mgr = YouTubeAuthManager()
            res = auth_mgr.authenticate_interactive()

            def on_complete():
                self.yt_connect_btn.config(state="normal")
                self._sync_youtube_account_ui()
                if res.get("success"):
                    messagebox.showinfo(
                        "YouTube Connected",
                        f"Successfully connected to YouTube channel:\n\n"
                        f"Channel: {res.get('channel_title')}\n"
                        f"Handle: {res.get('handle')}\n"
                        f"Channel ID: {res.get('channel_id')}\n\n"
                        f"Tokens safely stored in Windows Credential Manager.",
                    )
                    self._update_footer(f"YouTube Connected: {res.get('channel_title')}")
                else:
                    messagebox.showerror(
                        "YouTube Connection Failed",
                        f"Failed to connect YouTube account:\n\n{res.get('error')}",
                    )
                    self._update_footer("YouTube connection failed.")

            self.root.after(0, on_complete)

        threading.Thread(target=run_auth, daemon=True).start()


    # --------------------------------------------------------------------------
    # Hardware Telemetry & Adaptive Profile Controller (Phase 2)
    # --------------------------------------------------------------------------
    def _init_hardware_detection(self):
        """Initializes hardware detection or loads last known result on startup."""
        cached = self.settings_manager.get_hardware_report()
        try:
            specs = self.detector.detect()
            if specs.detection_status in ("DETECTED", "PARTIAL"):
                prof_res = HardwareProfileManager.determine_profile(specs)
                self.settings_manager.save_hardware_report(specs.model_dump(), prof_res.model_dump())
                self.hw_specs = specs
                self.hw_profile_result = prof_res
                self.hw_is_last_known = False
                return
        except Exception as e:
            logger.error(f"Startup hardware detection failed: {e}")

        # Fallback to cached last known report
        if cached and "specs" in cached and "profile" in cached:
            try:
                self.hw_specs = HardwareSpecs(**cached["specs"])
                self.hw_profile_result = HardwareProfileResult(**cached["profile"])
                self.hw_is_last_known = True
                self.hw_last_saved_at = cached.get("saved_at", "Unknown")
                logger.info(f"Loaded cached hardware report saved at {self.hw_last_saved_at}")
                return
            except Exception as e:
                logger.error(f"Failed to load cached hardware report: {e}")

        # Final fallback: generic minimal specs with conservative profile
        self.hw_specs = HardwareSpecs(detection_status="FAILED")
        self.hw_profile_result = HardwareProfileManager.determine_profile(self.hw_specs)
        self.hw_is_last_known = False

    def _sync_hardware_ui(self):
        """Renders current hardware telemetry into the UI dashboard."""
        if not self.hw_specs or not self.hw_profile_result:
            return

        specs = self.hw_specs
        prof = self.hw_profile_result

        # Status Badge
        if getattr(self, "hw_is_last_known", False):
            self.hw_status_badge.set_status("LAST_KNOWN", f"🕒 LAST KNOWN ({getattr(self, 'hw_last_saved_at', 'Cached')})")
        else:
            self.hw_status_badge.set_status(specs.detection_status)

        # Profile Badge
        self.hw_profile_badge.set_status(prof.profile)

        # Provisional tag
        if prof.is_provisional:
            self.hw_provisional_tag.pack(side="left", padx=(6, 0))
        else:
            self.hw_provisional_tag.pack_forget()

        # GPU Name
        self.hw_gpu_val.config(text=specs.gpu_name)

        # Dedicated VRAM (explicitly distinct from shared memory)
        if specs.vram_mb is not None:
            vram_gb = specs.vram_mb / 1024.0
            self.hw_vram_val.config(text=f"{specs.vram_mb} MB ({vram_gb:.1f} GB Dedicated)", fg="#60A5FA")
        else:
            self.hw_vram_val.config(text="Unavailable / Shared only", fg=self.c_text_dim)

        # System RAM: Total & Available
        ram_text = f"{specs.ram_total_gb:.1f} GB Total"
        if specs.ram_available_gb > 0:
            ram_text += f" ({specs.ram_available_gb:.1f} GB Available)"
        self.hw_ram_val.config(text=ram_text)

        # CPU Processor
        cpu_text = f"{specs.cpu_name} ({specs.cpu_threads}T)"
        if len(cpu_text) > 46:
            cpu_text = f"{specs.cpu_name[:38]}... ({specs.cpu_threads}T)"
        self.hw_cpu_val.config(text=cpu_text)

        # Windows OS
        self.hw_win_val.config(text=specs.windows_version)

        # Free Disk Space
        if specs.disk_total_gb > 0:
            self.hw_disk_val.config(text=f"{specs.disk_free_gb:.1f} GB Free ({specs.disk_total_gb:.1f} GB Total)")
        else:
            self.hw_disk_val.config(text="Unavailable")

        # CUDA / Driver Status
        if specs.nvidia_gpu_present and specs.driver_version:
            cuda_status = "CUDA Capable" if specs.cuda_available else "Driver Present"
            self.hw_cuda_val.config(text=f"{cuda_status} (Driver: {specs.driver_version})", fg="#A78BFA")
        elif specs.nvidia_gpu_present:
            self.hw_cuda_val.config(text="NVIDIA GPU (Driver Unavailable)", fg=self.c_text_sub)
        else:
            self.hw_cuda_val.config(text="Not an NVIDIA GPU / No CUDA", fg=self.c_text_dim)

        # Rationale and Bottlenecks
        self.hw_reason_lbl.config(text=prof.reason)
        if prof.bottlenecks:
            self.hw_bottlenecks_lbl.config(text="⚠️ Bottlenecks: " + " • ".join(prof.bottlenecks))
        else:
            self.hw_bottlenecks_lbl.config(text="")

        if getattr(self, "hw_is_last_known", False):
            self.hw_timestamp_lbl.config(text=f"Report timestamp: {getattr(self, 'hw_last_saved_at', 'Saved')}")
        else:
            self.hw_timestamp_lbl.config(text=f"Detected at: {specs.detected_at}")

    def on_click_refresh_hardware(self, async_mode: bool = True):
        """
        Refreshes hardware detection telemetry on user request.
        Safely runs detection and updates UI without freezing.
        """
        self.hw_refresh_btn.config(state="disabled", text="⏳ Detecting...")

        def worker():
            try:
                specs = self.detector.detect()
                if specs.detection_status in ("DETECTED", "PARTIAL"):
                    prof_res = HardwareProfileManager.determine_profile(specs)
                    self.settings_manager.save_hardware_report(specs.model_dump(), prof_res.model_dump())
                    self.hw_specs = specs
                    self.hw_profile_result = prof_res
                    self.hw_is_last_known = False
                else:
                    cached = self.settings_manager.get_hardware_report()
                    if cached and "specs" in cached and "profile" in cached:
                        self.hw_specs = HardwareSpecs(**cached["specs"])
                        self.hw_profile_result = HardwareProfileResult(**cached["profile"])
                        self.hw_is_last_known = True
                        self.hw_last_saved_at = cached.get("saved_at", "Unknown")
                    else:
                        self.hw_specs = specs
                        self.hw_profile_result = HardwareProfileManager.determine_profile(specs)
                        self.hw_is_last_known = False
            except Exception as e:
                logger.error(f"Error during hardware refresh: {e}")
            finally:
                if async_mode:
                    self.root.after(0, self._finish_refresh)
                else:
                    self._finish_refresh()

        if async_mode:
            threading.Thread(target=worker, daemon=True).start()
        else:
            worker()

    def _finish_refresh(self):
        self._sync_hardware_ui()
        self.hw_refresh_btn.config(state="normal", text="🔄 Refresh")
        self._update_footer("Hardware telemetry refreshed and saved.")

    def _update_footer(self, message: str):
        self.footer_status.config(text=f"System Status: {message}")


def launch_gui(on_start_callback: Optional[Callable] = None):
    """Entry point to launch the Phase 1 Desktop Dashboard."""
    root = tk.Tk()
    app = AutoPostDashboardApp(root, on_start_callback=on_start_callback)
    root.mainloop()


# Backward compatibility alias
CartoonAutomationUI = AutoPostDashboardApp


if __name__ == "__main__":
    launch_gui()
