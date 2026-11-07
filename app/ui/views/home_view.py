"""
app/ui/views/home_view.py
=========================
Home View for FA Studio:
- Consolidated large status card (Running / Waiting for approval / Done today / Idle / Error)
- Hardware profile badge (e.g. Low-power mode: stock edit)
- Next run time with catch-up indicator
- 6-step visual progress chain (Topic, Clip, Edit, Quality, Approval, Upload)
- Big Start/Stop scheduler toggle, Run Now, and Cancel buttons
- Instant telemetry updates
"""

import customtkinter as ctk
from typing import Callable, Optional
from app.ui.theme import get_font, COLORS
from app.ui.controller import UIController


class HomeView(ctk.CTkFrame):
    """Primary dashboard view displaying pipeline status, steps, and scheduling controls."""

    def __init__(self, master, controller: UIController, on_navigate: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.on_navigate = on_navigate

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header_and_badge()
        self._build_main_status_card()
        self._build_step_progress()
        self._build_action_bar()
        self._build_status_log_strip()

        # Initial refresh
        self.refresh()

    def _build_header_and_badge(self):
        """Top section: hardware detection badge and title."""
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        top_frame.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            top_frame,
            text="Pipeline Dashboard",
            font=get_font(22, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        # Hardware Badge Frame
        self.badge_card = ctk.CTkFrame(
            top_frame,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=8,
        )
        self.badge_card.grid(row=0, column=1, sticky="e")

        self.badge_lbl = ctk.CTkLabel(
            self.badge_card,
            text="Detecting hardware...",
            font=get_font(11, weight="bold"),
            text_color=COLORS["primary"],
            padx=12,
            pady=4,
        )
        self.badge_lbl.pack()

    def _build_main_status_card(self):
        """Large prominent status card showing live state, next execution, and topic."""
        self.status_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        self.status_card.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        self.status_card.grid_columnconfigure(0, weight=1)

        # Card Header: Status Pill & Next Run
        card_top = ctk.CTkFrame(self.status_card, fg_color="transparent")
        card_top.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        card_top.grid_columnconfigure(0, weight=1)

        self.status_badge = ctk.CTkLabel(
            card_top,
            text="IDLE",
            font=get_font(13, weight="bold"),
            text_color=("#FFFFFF", "#FFFFFF"),
            fg_color=COLORS["primary"][1],
            corner_radius=6,
            padx=12,
            pady=3,
        )
        self.status_badge.grid(row=0, column=0, sticky="w")

        self.next_run_lbl = ctk.CTkLabel(
            card_top,
            text="Next Run: Scheduled at 10:00",
            font=get_font(12),
            text_color=COLORS["text_muted"],
        )
        self.next_run_lbl.grid(row=0, column=1, sticky="e")

        # Large Headline Status
        self.status_headline = ctk.CTkLabel(
            self.status_card,
            text="System Ready",
            font=get_font(26, weight="bold"),
            text_color=COLORS["text_main"],
        )
        self.status_headline.grid(row=1, column=0, sticky="w", padx=20, pady=(5, 5))

        # Detail description / Bangla Topic Title
        self.status_subtext = ctk.CTkLabel(
            self.status_card,
            text="No active pipeline run in progress. Scheduler is standing by.",
            font=get_font(14),
            text_color=COLORS["text_muted"],
            wraplength=800,
            justify="left",
        )
        self.status_subtext.grid(row=2, column=0, sticky="w", padx=20, pady=(0, 15))

    def _build_step_progress(self):
        """Visual step progress chain for the 6 pipeline stages."""
        container = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        container.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        container.grid_columnconfigure(list(range(6)), weight=1)

        steps_title = ctk.CTkLabel(
            container,
            text="Daily Pipeline Execution Stages",
            font=get_font(13, weight="bold"),
            text_color=COLORS["text_main"],
        )
        steps_title.grid(row=0, column=0, columnspan=6, sticky="w", padx=15, pady=(12, 8))

        self.step_labels = {}
        step_definitions = [
            ("topic", "1. Topic\n(Gemini)"),
            ("clip", "2. Clip\n(Stock/AI)"),
            ("edit", "3. Edit\n(FFmpeg)"),
            ("quality", "4. Quality\n(9:16 Check)"),
            ("approval", "5. Approval\n(Human Gate)"),
            ("upload", "6. Upload\n(YouTube)"),
        ]

        for idx, (key, label) in enumerate(step_definitions):
            box = ctk.CTkFrame(
                container,
                fg_color=COLORS["button_secondary"],
                corner_radius=8,
                border_width=1,
                border_color=COLORS["card_border"],
            )
            box.grid(row=1, column=idx, padx=6, pady=(0, 15), sticky="nsew")
            box.grid_columnconfigure(0, weight=1)

            lbl = ctk.CTkLabel(
                box,
                text=f"○ {label}",
                font=get_font(11, weight="bold"),
                text_color=COLORS["text_muted"],
                justify="center",
                pady=10,
            )
            lbl.pack(fill="both", expand=True)
            self.step_labels[key] = (box, lbl, label)

    def _build_action_bar(self):
        """Action buttons: Start/Stop Scheduler, Run Now, Cancel, Open Folder."""
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", padx=20, pady=15)
        bar.grid_columnconfigure(3, weight=1)

        self.btn_toggle_scheduler = ctk.CTkButton(
            bar,
            text="▶ Start Scheduler",
            font=get_font(13, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=40,
            width=160,
            command=self._on_toggle_scheduler,
        )
        self.btn_toggle_scheduler.grid(row=0, column=0, padx=(0, 10), sticky="w")

        self.btn_run_now = ctk.CTkButton(
            bar,
            text="⚡ Run Today's Job Now",
            font=get_font(13, weight="bold"),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            height=40,
            width=190,
            command=self._on_run_now,
        )
        self.btn_run_now.grid(row=0, column=1, padx=(0, 10), sticky="w")

        self.btn_cancel = ctk.CTkButton(
            bar,
            text="⏹ Cancel Job",
            font=get_font(13, weight="bold"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            text_color="#FFFFFF",
            height=40,
            width=130,
            state="disabled",
            command=self._on_cancel,
        )
        self.btn_cancel.grid(row=0, column=2, padx=(0, 10), sticky="w")

        self.btn_open_folder = ctk.CTkButton(
            bar,
            text="📁 Open Output Folder",
            font=get_font(12),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            height=40,
            command=lambda: self.controller.open_output_folder("output"),
        )
        self.btn_open_folder.grid(row=0, column=4, sticky="e")

    def _build_status_log_strip(self):
        """Bottom strip for immediate background worker notifications."""
        self.telemetry_lbl = ctk.CTkLabel(
            self,
            text="Scheduler standing by. All background systems nominal.",
            font=get_font(12),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.telemetry_lbl.grid(row=4, column=0, sticky="ew", padx=25, pady=(0, 10))

    # -------------------------------------------------------------------------
    # Actions & State Handlers
    # -------------------------------------------------------------------------
    def _on_toggle_scheduler(self):
        running = self.controller.toggle_scheduler()
        self.refresh()

    def _on_run_now(self):
        self.telemetry_lbl.configure(text="Initiating daily pipeline worker thread...")
        self.btn_run_now.configure(state="disabled")
        self.btn_cancel.configure(state="normal")

        def _on_progress(msg: str):
            self.after(0, lambda: self.telemetry_lbl.configure(text=f"Pipeline: {msg}"))
            self.after(0, self.refresh)

        def _on_complete(res: dict):
            self.after(0, lambda: self._handle_complete(res))

        started = self.controller.run_pipeline_async(on_progress=_on_progress, on_complete=_on_complete)
        if not started:
            self.telemetry_lbl.configure(text="Could not start pipeline: worker already running.")
            self.btn_run_now.configure(state="normal")
            self.btn_cancel.configure(state="disabled")
        self.refresh()

    def _handle_complete(self, res: dict):
        self.btn_run_now.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        status = res.get("job_status") or ("Success" if res.get("success") else "Stopped")
        self.telemetry_lbl.configure(text=f"Pipeline finished: {status} ({res.get('reason', 'OK')})")
        self.refresh()

        # If awaiting approval, navigate to Today's Video view if requested
        if res.get("job_status") == "AWAITING_APPROVAL" and self.on_navigate:
            self.on_navigate("today_video")

    def _on_cancel(self):
        self.controller.cancel_pipeline()
        self.telemetry_lbl.configure(text="Cancel requested. Terminating current worker...")
        self.refresh()

    # -------------------------------------------------------------------------
    # Public Refresh
    # -------------------------------------------------------------------------
    def refresh(self):
        """Pulls latest state from controller and updates UI widgets."""
        state = self.controller.get_home_state()

        # Badge
        self.badge_lbl.configure(text=state["hardware_badge"])

        # Scheduler button
        if state["scheduler_active"]:
            self.btn_toggle_scheduler.configure(
                text="⏹ Stop Scheduler",
                fg_color=COLORS["warning"],
                hover_color=("#B45309", "#D97706"),
            )
        else:
            self.btn_toggle_scheduler.configure(
                text="▶ Start Scheduler",
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
            )

        # Worker state
        if state["is_running"]:
            self.btn_cancel.configure(state="normal")
            self.btn_run_now.configure(state="disabled")
        else:
            self.btn_cancel.configure(state="disabled")
            self.btn_run_now.configure(state="normal")

        # Next run
        self.next_run_lbl.configure(text=f"Next Run: {state['next_run']}")

        # Status Badge & Headline
        status_text = state["status_text"]
        job = state["today_job"]

        if state["kill_switch"]:
            self.status_badge.configure(text="EMERGENCY STOP", fg_color=COLORS["danger"][1])
            self.status_headline.configure(text="Emergency Kill Switch Active")
            self.status_subtext.configure(text="All scheduling and upload operations are strictly blocked.")
        elif status_text == "AWAITING_APPROVAL":
            self.status_badge.configure(text="ACTION REQUIRED", fg_color=COLORS["warning"][1])
            self.status_headline.configure(text="Video Awaiting Human Approval")
            topic = getattr(job, "topic_title", "Video rendered") if job else "Video rendered"
            self.status_subtext.configure(text=f"Today's topic: {topic}. Ready for review in 'Today\\'s Video'.")
        elif status_text in ("PUBLISHED", "DRY_RUN_COMPLETE"):
            self.status_badge.configure(text="DONE TODAY", fg_color=COLORS["success"][1])
            self.status_headline.configure(text="Today's Job Successfully Completed")
            topic = getattr(job, "topic_title", "") if job else ""
            self.status_subtext.configure(text=f"Topic: {topic} | Hard cap enforced (1 publish/day).")
        elif status_text in ("FAILED", "ERROR"):
            self.status_badge.configure(text="ERROR", fg_color=COLORS["danger"][1])
            self.status_headline.configure(text="Pipeline Encountered an Error")
            err = getattr(job, "error_details", "Check logs for details") if job else "Check logs."
            self.status_subtext.configure(text=f"Reason: {err}")
        elif state["is_running"]:
            self.status_badge.configure(text="EXECUTING", fg_color=COLORS["info"][1])
            self.status_headline.configure(text="Generating Today's Video...")
            self.status_subtext.configure(text=f"Current stage: {status_text}")
        else:
            self.status_badge.configure(text="IDLE", fg_color=COLORS["primary"][1])
            self.status_headline.configure(text="Automation Standby")
            self.status_subtext.configure(text="Waiting for scheduled time or manual trigger.")

        # Step Progress
        steps = state["steps"]
        for key, (box, lbl, base_label) in self.step_labels.items():
            if steps.get(key):
                box.configure(fg_color=COLORS["success"])
                lbl.configure(text=f"✓ {base_label}", text_color=("#FFFFFF", "#FFFFFF"))
            else:
                box.configure(fg_color=COLORS["button_secondary"])
                lbl.configure(text=f"○ {base_label}", text_color=COLORS["text_muted"])
