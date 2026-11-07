"""
app/ui/views/today_view.py
==========================
Today's Video Review & Approval Screen:
- Preview thumbnail / open in external media player
- Bengali title & topic display (OpenType Bengali shaping)
- Clip source, stock provider ID, and CC0/Pexels license info
- Technical specs (duration, 1080x1920 9:16 resolution, audio stream)
- Approve and Reject/Regenerate with custom confirmation dialogs
"""

import os
import customtkinter as ctk
from PIL import Image
from typing import Callable, Optional
from app.ui.theme import get_font, COLORS
from app.ui.controller import UIController


class ConfirmDialog(ctk.CTkToplevel):
    """Reusable modal dialog for confirmation actions."""

    def __init__(self, parent, title: str, message: str, confirm_text: str = "Confirm", is_destructive: bool = False, on_confirm: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.title(title)
        self.geometry("450x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        lbl_title = ctk.CTkLabel(self, text=title, font=get_font(16, weight="bold"), text_color=COLORS["text_main"])
        lbl_title.pack(pady=(20, 10), padx=20)

        lbl_msg = ctk.CTkLabel(self, text=message, font=get_font(13), text_color=COLORS["text_muted"], wraplength=400)
        lbl_msg.pack(pady=10, padx=20)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=20)

        btn_cancel = ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=get_font(12),
            fg_color=COLORS["button_secondary"],
            text_color=COLORS["text_main"],
            width=100,
            command=self.destroy,
        )
        btn_cancel.pack(side="left", padx=10)

        confirm_color = COLORS["danger"] if is_destructive else COLORS["primary"]
        confirm_hover = COLORS["danger_hover"] if is_destructive else COLORS["primary_hover"]

        btn_ok = ctk.CTkButton(
            btn_row,
            text=confirm_text,
            font=get_font(12, weight="bold"),
            fg_color=confirm_color,
            hover_color=confirm_hover,
            width=120,
            command=self._confirm,
        )
        btn_ok.pack(side="left", padx=10)

    def _confirm(self):
        if self.on_confirm:
            self.on_confirm()
        self.destroy()


class TodayVideoView(ctk.CTkFrame):
    """View presenting today's master video for human inspection, playback, and approval."""

    def __init__(self, master, controller: UIController, on_status_changed: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.on_status_changed = on_status_changed

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_preview_panel()
        self._build_details_panel()

        self.refresh()

    def _build_header(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(15, 10))
        top.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top,
            text="Today's Video Master & Approval",
            font=get_font(22, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title.grid(row=0, column=0, sticky="w")

        self.status_pill = ctk.CTkLabel(
            top,
            text="AWAITING APPROVAL",
            font=get_font(12, weight="bold"),
            text_color="#FFFFFF",
            fg_color=COLORS["warning"][1],
            corner_radius=6,
            padx=12,
            pady=4,
        )
        self.status_pill.grid(row=0, column=1, sticky="e")

    def _build_preview_panel(self):
        """Left side: preview thumbnail and media player launcher."""
        left = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        left.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=10)
        left.grid_columnconfigure(0, weight=1)

        lbl_sec = ctk.CTkLabel(left, text="Visual Preview", font=get_font(14, weight="bold"), text_color=COLORS["text_main"])
        lbl_sec.pack(anchor="w", padx=15, pady=(15, 10))

        # Preview Image Box (9:16 aspect thumbnail)
        self.preview_canvas = ctk.CTkLabel(
            left,
            text="No preview frame found",
            width=270,
            height=400,
            fg_color=COLORS["sidebar_bg"],
            corner_radius=8,
            font=get_font(12),
            text_color=COLORS["text_muted"],
        )
        self.preview_canvas.pack(padx=20, pady=10)

        # Player Action Buttons
        btn_box = ctk.CTkFrame(left, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(10, 15))
        btn_box.grid_columnconfigure(0, weight=1)
        btn_box.grid_columnconfigure(1, weight=1)

        self.btn_play = ctk.CTkButton(
            btn_box,
            text="▶ Open in Player",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._open_in_player,
        )
        self.btn_play.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.btn_folder = ctk.CTkButton(
            btn_box,
            text="📁 Open Folder",
            font=get_font(12),
            fg_color=COLORS["button_secondary"],
            text_color=COLORS["text_main"],
            command=lambda: self.controller.open_output_folder("output"),
        )
        self.btn_folder.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    def _build_details_panel(self):
        """Right side: metadata, license, Bengali title, and approval buttons."""
        right = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        right.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=10)
        right.grid_columnconfigure(0, weight=1)

        lbl_sec = ctk.CTkLabel(right, text="Video Metadata & Licensing", font=get_font(14, weight="bold"), text_color=COLORS["text_main"])
        lbl_sec.pack(anchor="w", padx=15, pady=(15, 10))

        # Bangla Topic Card
        topic_box = ctk.CTkFrame(right, fg_color=COLORS["sidebar_bg"], corner_radius=8)
        topic_box.pack(fill="x", padx=15, pady=5)
        lbl_t_title = ctk.CTkLabel(topic_box, text="Today's Topic & Title (Bengali):", font=get_font(11, weight="bold"), text_color=COLORS["primary"])
        lbl_t_title.pack(anchor="w", padx=12, pady=(8, 2))

        self.lbl_topic = ctk.CTkLabel(
            topic_box,
            text="এআই যখন বিড়ালের ভাষা বুঝতে চাইল!",
            font=get_font(16, weight="bold"),
            text_color=COLORS["text_main"],
            wraplength=420,
            justify="left",
        )
        self.lbl_topic.pack(anchor="w", padx=12, pady=(0, 10))

        # Details Grid
        details_grid = ctk.CTkFrame(right, fg_color="transparent")
        details_grid.pack(fill="x", padx=15, pady=10)
        details_grid.grid_columnconfigure(1, weight=1)

        fields = [
            ("Clip Source:", "lbl_provider"),
            ("Clip ID:", "lbl_clip_id"),
            ("License:", "lbl_license"),
            ("Format:", "lbl_format"),
            ("File Size:", "lbl_size"),
            ("Job Status:", "lbl_job_status"),
        ]

        self.field_labels = {}
        for idx, (label_text, attr_name) in enumerate(fields):
            lbl_k = ctk.CTkLabel(details_grid, text=label_text, font=get_font(12, weight="bold"), text_color=COLORS["text_muted"], anchor="w")
            lbl_k.grid(row=idx, column=0, sticky="w", pady=4, padx=(0, 10))

            lbl_v = ctk.CTkLabel(details_grid, text="...", font=get_font(12), text_color=COLORS["text_main"], anchor="w")
            lbl_v.grid(row=idx, column=1, sticky="w", pady=4)
            self.field_labels[attr_name] = lbl_v

        # Action Buttons Container (Approve / Reject)
        actions_box = ctk.CTkFrame(right, fg_color="transparent")
        actions_box.pack(fill="x", padx=15, pady=(20, 15), side="bottom")
        actions_box.grid_columnconfigure(0, weight=1)
        actions_box.grid_columnconfigure(1, weight=1)

        self.btn_approve = ctk.CTkButton(
            actions_box,
            text="✓ Approve & Publish",
            font=get_font(13, weight="bold"),
            fg_color=COLORS["success"],
            hover_color=("#047857", "#059669"),
            height=42,
            command=self._confirm_approve,
        )
        self.btn_approve.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.btn_reject = ctk.CTkButton(
            actions_box,
            text="✕ Reject / Regenerate",
            font=get_font(13, weight="bold"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            height=42,
            command=self._confirm_reject,
        )
        self.btn_reject.grid(row=0, column=1, padx=(5, 0), sticky="ew")

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def _open_in_player(self):
        details = self.controller.get_today_video_details()
        self.controller.open_video_in_player(details.get("video_path"))

    def _confirm_approve(self):
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Approve Today's Video?",
            message="Are you sure you want to approve this video? It will proceed directly to the YouTube publishing stage.",
            confirm_text="Approve Now",
            is_destructive=False,
            on_confirm=self._do_approve,
        )

    def _do_approve(self):
        res = self.controller.approve_today_video()
        self.refresh()
        if self.on_status_changed:
            self.on_status_changed()

    def _confirm_reject(self):
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Reject & Reset Video?",
            message="Do you want to reject this video? The job will be reset. You can also regenerate a new video immediately.",
            confirm_text="Reject & Reset",
            is_destructive=True,
            on_confirm=self._do_reject,
        )

    def _do_reject(self):
        self.controller.reject_today_video(regenerate=False)
        self.refresh()
        if self.on_status_changed:
            self.on_status_changed()

    # -------------------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------------------
    def refresh(self):
        details = self.controller.get_today_video_details()
        self.lbl_topic.configure(text=details["topic"])
        self.field_labels["lbl_provider"].configure(text=details["provider"].capitalize())
        self.field_labels["lbl_clip_id"].configure(text=str(details["clip_id"]))
        self.field_labels["lbl_license"].configure(text="CC0 / Free to Use (Pexels / Commercial)")
        self.field_labels["lbl_format"].configure(text="1080x1920 (9:16 Vertical) | AAC Stereo")
        self.field_labels["lbl_size"].configure(text=f"{details['size_mb']} MB" if details["exists"] else "Not rendered")
        self.field_labels["lbl_job_status"].configure(text=details["status"])

        # Status Pill
        st = details["status"]
        if st == "AWAITING_APPROVAL":
            self.status_pill.configure(text="AWAITING APPROVAL", fg_color=COLORS["warning"][1])
            self.btn_approve.configure(state="normal")
            self.btn_reject.configure(state="normal")
        elif st in ("PUBLISHED", "DRY_RUN_COMPLETE"):
            self.status_pill.configure(text="PUBLISHED / COMPLETE", fg_color=COLORS["success"][1])
            self.btn_approve.configure(state="disabled")
            self.btn_reject.configure(state="normal")
        else:
            self.status_pill.configure(text=st, fg_color=COLORS["primary"][1])
            self.btn_approve.configure(state="disabled" if not details["can_approve"] else "normal")

        # Load Preview Image
        preview_candidates = [
            os.path.join("output", "preview", "frame_middle.png"),
            os.path.join("output", "preview", "frame_start.png"),
            os.path.join("output", "preview", "preview_frame_02.png"),
        ]
        loaded_img = None
        for p in preview_candidates:
            if os.path.exists(p):
                try:
                    pil_img = Image.open(p)
                    # Scale to 270x400 (preserving vertical aspect)
                    loaded_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(240, 380))
                    break
                except Exception:
                    pass

        if loaded_img:
            self.preview_canvas.configure(image=loaded_img, text="")
        else:
            self.preview_canvas.configure(image=None, text="Preview frame not available\n(Run pipeline to generate)")
