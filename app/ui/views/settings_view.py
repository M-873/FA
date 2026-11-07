"""
app/ui/views/settings_view.py
=============================
Settings & Configuration View for FA Studio:
- Daily schedule time entry (default 10:00)
- Human approval toggle
- Content source selector (auto / stock_edit / ai_cartoon)
- DRY_RUN toggle with prominent RED WARNING BANNER when OFF
- Publisher Device toggle (only designated PC uploads)
- Start with Windows toggle (HKCU Run registry key)
- YouTube privacy level selector (private / unlisted / public)
- Masked API key entries stored securely in Windows Credential Manager (never logged or shown)
"""

import customtkinter as ctk
from typing import Optional, Callable
from app.ui.theme import get_font, COLORS
from app.ui.controller import UIController
from app.utils.logging import logger


class SettingsView(ctk.CTkFrame):
    """View allowing users to configure pipeline timing, safety guardrails, and secure API keys."""

    def __init__(self, master, controller: UIController, on_settings_saved: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.on_settings_saved = on_settings_saved

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_warning_banner()
        self._build_scrollable_form()

        self.refresh()

    def _build_header(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        top.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top,
            text="Settings & Safety Guardrails",
            font=get_font(22, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title.grid(row=0, column=0, sticky="w")

        self.save_feedback_lbl = ctk.CTkLabel(
            top,
            text="",
            font=get_font(12, weight="bold"),
            text_color=COLORS["success"][1],
        )
        self.save_feedback_lbl.grid(row=0, column=1, sticky="e")

    def _build_warning_banner(self):
        """Dynamic warning banner. Changes to bright RED alert when DRY_RUN is OFF."""
        self.banner_frame = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=8,
        )
        self.banner_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        self.banner_frame.grid_columnconfigure(0, weight=1)

        self.banner_lbl = ctk.CTkLabel(
            self.banner_frame,
            text="DRY_RUN status",
            font=get_font(12, weight="bold"),
            padx=15,
            pady=8,
        )
        self.banner_lbl.pack(fill="x")

    def _build_scrollable_form(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(5, 10))
        self.scroll.grid_columnconfigure(0, weight=1)

        # ---------------------------------------------------------------------
        # Section 1: Scheduling & Guardrails
        # ---------------------------------------------------------------------
        sec1 = ctk.CTkFrame(
            self.scroll,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        sec1.pack(fill="x", pady=8)
        sec1.grid_columnconfigure(1, weight=1)

        lbl_s1 = ctk.CTkLabel(sec1, text="1. Scheduling & Automation Rules", font=get_font(14, weight="bold"), text_color=COLORS["text_main"])
        lbl_s1.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 10))

        # Schedule Time
        lbl_time = ctk.CTkLabel(sec1, text="Daily Scheduled Time (HH:MM):", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_time.grid(row=1, column=0, sticky="w", padx=15, pady=6)
        self.entry_time = ctk.CTkEntry(sec1, width=120, font=get_font(12))
        self.entry_time.grid(row=1, column=1, sticky="w", padx=15, pady=6)

        # Human Approval
        lbl_app = ctk.CTkLabel(sec1, text="Require Human Approval:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_app.grid(row=2, column=0, sticky="w", padx=15, pady=6)
        self.switch_approval = ctk.CTkSwitch(sec1, text="Pause at AWAITING_APPROVAL before upload", font=get_font(12))
        self.switch_approval.grid(row=2, column=1, sticky="w", padx=15, pady=6)

        # Publisher Device
        lbl_pub = ctk.CTkLabel(sec1, text="Publisher Device Designation:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_pub.grid(row=3, column=0, sticky="w", padx=15, pady=6)
        self.switch_publisher = ctk.CTkSwitch(sec1, text="Only this designated host machine may publish live", font=get_font(12))
        self.switch_publisher.grid(row=3, column=1, sticky="w", padx=15, pady=6)

        # Start with Windows
        lbl_win = ctk.CTkLabel(sec1, text="Launch with Windows:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_win.grid(row=4, column=0, sticky="w", padx=15, pady=(6, 12))
        self.switch_startup = ctk.CTkSwitch(sec1, text="Automatically start in system tray on login (HKCU Run)", font=get_font(12))
        self.switch_startup.grid(row=4, column=1, sticky="w", padx=15, pady=(6, 12))

        # ---------------------------------------------------------------------
        # Section 2: Pipeline Content & Distribution Mode
        # ---------------------------------------------------------------------
        sec2 = ctk.CTkFrame(
            self.scroll,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        sec2.pack(fill="x", pady=8)
        sec2.grid_columnconfigure(1, weight=1)

        lbl_s2 = ctk.CTkLabel(sec2, text="2. Content Generation & Privacy", font=get_font(14, weight="bold"), text_color=COLORS["text_main"])
        lbl_s2.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 10))

        # Content Source
        lbl_cs = ctk.CTkLabel(sec2, text="Content Source Mode:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_cs.grid(row=1, column=0, sticky="w", padx=15, pady=6)
        self.opt_source = ctk.CTkOptionMenu(
            sec2,
            values=["stock_edit", "auto", "ai_cartoon"],
            font=get_font(12),
            width=180,
        )
        self.opt_source.grid(row=1, column=1, sticky="w", padx=15, pady=6)

        # YouTube Privacy
        lbl_priv = ctk.CTkLabel(sec2, text="YouTube Upload Privacy:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_priv.grid(row=2, column=0, sticky="w", padx=15, pady=6)
        self.opt_privacy = ctk.CTkOptionMenu(
            sec2,
            values=["private", "unlisted", "public"],
            font=get_font(12),
            width=180,
        )
        self.opt_privacy.grid(row=2, column=1, sticky="w", padx=15, pady=6)

        # DRY_RUN Toggle
        lbl_dry = ctk.CTkLabel(sec2, text="DRY_RUN Simulation Mode:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_dry.grid(row=3, column=0, sticky="w", padx=15, pady=(6, 12))
        self.switch_dryrun = ctk.CTkSwitch(
            sec2,
            text="Simulate publishing (safe mode, no live uploads)",
            font=get_font(12),
            command=self._on_dry_run_toggled,
        )
        self.switch_dryrun.grid(row=3, column=1, sticky="w", padx=15, pady=(6, 12))

        # ---------------------------------------------------------------------
        # Section 3: Secure API Keys (Windows Credential Manager)
        # ---------------------------------------------------------------------
        sec3 = ctk.CTkFrame(
            self.scroll,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        sec3.pack(fill="x", pady=8)
        sec3.grid_columnconfigure(1, weight=1)

        lbl_s3 = ctk.CTkLabel(sec3, text="3. Secure API Keys (Encrypted in Windows Credential Manager)", font=get_font(14, weight="bold"), text_color=COLORS["text_main"])
        lbl_s3.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(12, 4))

        note_lbl = ctk.CTkLabel(
            sec3,
            text="API keys entered below are encrypted directly into native Windows Credential Manager. Values are never displayed, printed, or saved to plain-text files.",
            font=get_font(11),
            text_color=COLORS["text_muted"],
            wraplength=600,
            justify="left",
        )
        note_lbl.grid(row=1, column=0, columnspan=3, sticky="w", padx=15, pady=(0, 10))

        # Gemini API Key
        lbl_gk = ctk.CTkLabel(sec3, text="Google Gemini AI Key:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_gk.grid(row=2, column=0, sticky="w", padx=15, pady=6)
        self.entry_gemini = ctk.CTkEntry(sec3, width=280, show="*", placeholder_text="Enter new key to update", font=get_font(12))
        self.entry_gemini.grid(row=2, column=1, sticky="w", padx=15, pady=6)
        self.gemini_badge = ctk.CTkLabel(sec3, text="Checking...", font=get_font(11))
        self.gemini_badge.grid(row=2, column=2, sticky="w", padx=10, pady=6)

        # Pexels API Key
        lbl_pk = ctk.CTkLabel(sec3, text="Pexels Video Stock Key:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_pk.grid(row=3, column=0, sticky="w", padx=15, pady=6)
        self.entry_pexels = ctk.CTkEntry(sec3, width=280, show="*", placeholder_text="Enter new key to update", font=get_font(12))
        self.entry_pexels.grid(row=3, column=1, sticky="w", padx=15, pady=6)
        self.pexels_badge = ctk.CTkLabel(sec3, text="Checking...", font=get_font(11))
        self.pexels_badge.grid(row=3, column=2, sticky="w", padx=10, pady=6)

        # Pixabay API Key
        lbl_pxk = ctk.CTkLabel(sec3, text="Pixabay Video Stock Key:", font=get_font(12), text_color=COLORS["text_muted"])
        lbl_pxk.grid(row=4, column=0, sticky="w", padx=15, pady=6)
        self.entry_pixabay = ctk.CTkEntry(sec3, width=280, show="*", placeholder_text="Enter new key to update", font=get_font(12))
        self.entry_pixabay.grid(row=4, column=1, sticky="w", padx=15, pady=6)
        self.pixabay_badge = ctk.CTkLabel(sec3, text="Checking...", font=get_font(11))
        self.pixabay_badge.grid(row=4, column=2, sticky="w", padx=10, pady=6)

        btn_save_keys = ctk.CTkButton(
            sec3,
            text="💾 Save Keys to Credential Manager",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            command=self._save_api_keys,
        )
        btn_save_keys.grid(row=5, column=1, sticky="w", padx=15, pady=(10, 15))

        # Bottom Save All Settings Button
        btn_save_all = ctk.CTkButton(
            self.scroll,
            text="💾 Save All Settings",
            font=get_font(14, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=42,
            command=self._save_all_settings,
        )
        btn_save_all.pack(fill="x", pady=(15, 20))

    # -------------------------------------------------------------------------
    # Actions & Handlers
    # -------------------------------------------------------------------------
    def _on_dry_run_toggled(self):
        is_dry = bool(self.switch_dryrun.get())
        self._update_banner(is_dry)

    def _update_banner(self, is_dry: bool):
        if is_dry:
            self.banner_frame.configure(fg_color=COLORS["card_bg"], border_color=COLORS["card_border"])
            self.banner_lbl.configure(
                text="ℹ DRY_RUN is ON: Safe simulation mode active. Videos will NOT be published to YouTube.",
                text_color=COLORS["info"][1],
            )
        else:
            self.banner_frame.configure(fg_color=COLORS["danger"][1], border_color=COLORS["danger"][0])
            self.banner_lbl.configure(
                text="⚠️ CAUTION: DRY_RUN IS OFF! Real videos will be uploaded directly to YouTube!",
                text_color="#FFFFFF",
            )

    def _save_api_keys(self):
        gk = self.entry_gemini.get().strip()
        pk = self.entry_pexels.get().strip()
        pxk = self.entry_pixabay.get().strip()

        saved_any = False
        if gk:
            self.controller.save_api_key("gemini", gk)
            self.entry_gemini.delete(0, "end")
            saved_any = True
        if pk:
            self.controller.save_api_key("pexels", pk)
            self.entry_pexels.delete(0, "end")
            saved_any = True
        if pxk:
            self.controller.save_api_key("pixabay", pxk)
            self.entry_pixabay.delete(0, "end")
            saved_any = True

        self.refresh_key_badges()
        msg = "API keys saved to Windows Credential Manager." if saved_any else "No new keys entered."
        self.save_feedback_lbl.configure(text=msg, text_color=COLORS["success"][1])

    def _save_all_settings(self):
        # Gather data
        data = {
            "scheduled_time": self.entry_time.get().strip() or "10:00",
            "require_human_approval": bool(self.switch_approval.get()),
            "publisher_device": bool(self.switch_publisher.get()),
            "start_with_windows": bool(self.switch_startup.get()),
            "content_source": self.opt_source.get(),
            "youtube_privacy": self.opt_privacy.get(),
            "dry_run": bool(self.switch_dryrun.get()),
        }

        # Also save keys if user typed them
        self._save_api_keys()

        ok = self.controller.save_settings(data)
        if ok:
            self.save_feedback_lbl.configure(text="✓ Settings saved successfully!", text_color=COLORS["success"][1])
            self._update_banner(data["dry_run"])
            if self.on_settings_saved:
                self.on_settings_saved()
        else:
            self.save_feedback_lbl.configure(text="✕ Error saving settings.", text_color=COLORS["danger"][1])

    # -------------------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------------------
    def refresh(self):
        s = self.controller.get_settings()

        self.entry_time.delete(0, "end")
        self.entry_time.insert(0, s["scheduled_time"])

        if s["require_human_approval"]:
            self.switch_approval.select()
        else:
            self.switch_approval.deselect()

        if s["publisher_device"]:
            self.switch_publisher.select()
        else:
            self.switch_publisher.deselect()

        if s["start_with_windows"]:
            self.switch_startup.select()
        else:
            self.switch_startup.deselect()

        if s["dry_run"]:
            self.switch_dryrun.select()
        else:
            self.switch_dryrun.deselect()

        self.opt_source.set(s["content_source"])
        self.opt_privacy.set(s["youtube_privacy"])

        self._update_banner(s["dry_run"])
        self.refresh_key_badges()

    def refresh_key_badges(self):
        # Gemini
        if self.controller.has_api_key("gemini"):
            self.gemini_badge.configure(text="● Configured", text_color=COLORS["success"][1])
        else:
            self.gemini_badge.configure(text="○ Not Set", text_color=COLORS["danger"][1])

        # Pexels
        if self.controller.has_api_key("pexels"):
            self.pexels_badge.configure(text="● Configured", text_color=COLORS["success"][1])
        else:
            self.pexels_badge.configure(text="○ Optional", text_color=COLORS["text_muted"])

        # Pixabay
        if self.controller.has_api_key("pixabay"):
            self.pixabay_badge.configure(text="● Configured", text_color=COLORS["success"][1])
        else:
            self.pixabay_badge.configure(text="○ Optional", text_color=COLORS["text_muted"])
