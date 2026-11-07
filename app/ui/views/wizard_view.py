"""
app/ui/views/wizard_view.py
===========================
First-Run Setup & System Diagnostic Wizard for FA Studio:
- Verifies Hardware detection & profile classification
- Verifies FFmpeg and FFprobe binary availability
- Checks AI API keys (Google Gemini)
- Validates YouTube OAuth authentication & channel binding (@Life-X-873)
- Validates output storage write permissions
- Provides plain-language explanations with actionable suggested fixes (no raw tracebacks)
- Allows one-click dry-run pipeline test execution
"""

import customtkinter as ctk
from typing import Optional, Callable
from app.ui.theme import get_font, COLORS
from app.ui.controller import UIController


class WizardView(ctk.CTkFrame):
    """View guiding new installations through prerequisites, system checks, and initial tests."""

    def __init__(self, master, controller: UIController, on_complete: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.on_complete = on_complete

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_action_strip()
        self._build_check_list()

        self.refresh()

    def _build_header(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        top.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top,
            text="First-Run Setup & Diagnostics Wizard",
            font=get_font(22, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            top,
            text="Automated verification of system prerequisites, multimedia engines, API keys, and channel permissions.",
            font=get_font(12),
            text_color=COLORS["text_muted"],
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _build_action_strip(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        self.btn_run_checks = ctk.CTkButton(
            bar,
            text="🔄 Re-run Diagnostics",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self.refresh,
        )
        self.btn_run_checks.pack(side="left", padx=(0, 10))

        self.btn_test_pipeline = ctk.CTkButton(
            bar,
            text="⚡ Run Dry-Run Pipeline Test",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            command=self._run_dry_run_test,
        )
        self.btn_test_pipeline.pack(side="left")

        self.test_status_lbl = ctk.CTkLabel(
            bar,
            text="",
            font=get_font(11),
            text_color=COLORS["text_muted"],
        )
        self.test_status_lbl.pack(side="left", padx=15)

    def _build_check_list(self):
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.scroll.grid_columnconfigure(0, weight=1)

    def _run_dry_run_test(self):
        self.test_status_lbl.configure(text="Executing dry-run test...")
        self.btn_test_pipeline.configure(state="disabled")

        def _on_complete(res: dict):
            def _update():
                self.btn_test_pipeline.configure(state="normal")
                success = res.get("success", False)
                if success:
                    self.test_status_lbl.configure(text="✓ Dry-run test passed successfully!", text_color=COLORS["success"][1])
                else:
                    self.test_status_lbl.configure(text=f"✕ Test stopped: {res.get('reason', 'Failed')}", text_color=COLORS["danger"][1])
                self.refresh()

            self.after(0, _update)

        self.controller.run_pipeline_async(on_complete=_on_complete)

    def refresh(self):
        for child in self.scroll.winfo_children():
            child.destroy()

        results = self.controller.run_first_run_diagnostics()

        for check in results:
            passed = check["passed"]
            item_name = check["item"]
            detail = check["detail"]
            fix = check.get("fix")

            card = ctk.CTkFrame(
                self.scroll,
                fg_color=COLORS["card_bg"],
                border_width=1,
                border_color=COLORS["card_border"],
                corner_radius=10,
            )
            card.pack(fill="x", pady=6)
            card.grid_columnconfigure(1, weight=1)

            # Icon / Status badge
            status_text = "PASS" if passed else "ATTENTION"
            status_color = COLORS["success"][1] if passed else COLORS["danger"][1]

            badge = ctk.CTkLabel(
                card,
                text=status_text,
                font=get_font(11, weight="bold"),
                text_color="#FFFFFF",
                fg_color=status_color,
                corner_radius=6,
                width=85,
                pady=4,
            )
            badge.grid(row=0, column=0, padx=15, pady=15, sticky="w")

            # Text content
            content_box = ctk.CTkFrame(card, fg_color="transparent")
            content_box.grid(row=0, column=1, sticky="ew", padx=(0, 15), pady=12)
            content_box.grid_columnconfigure(0, weight=1)

            lbl_name = ctk.CTkLabel(content_box, text=item_name, font=get_font(14, weight="bold"), text_color=COLORS["text_main"], anchor="w")
            lbl_name.pack(fill="x")

            lbl_detail = ctk.CTkLabel(content_box, text=detail, font=get_font(12), text_color=COLORS["text_muted"], anchor="w", wraplength=600, justify="left")
            lbl_detail.pack(fill="x", pady=(2, 0))

            if not passed and fix:
                fix_frame = ctk.CTkFrame(content_box, fg_color=COLORS["sidebar_bg"], corner_radius=6)
                fix_frame.pack(fill="x", pady=(6, 2))
                lbl_fix = ctk.CTkLabel(
                    fix_frame,
                    text=f"💡 Suggested Fix: {fix}",
                    font=get_font(11, weight="bold"),
                    text_color=COLORS["warning"][1],
                    anchor="w",
                    padx=10,
                    pady=4,
                )
                lbl_fix.pack(fill="x")
