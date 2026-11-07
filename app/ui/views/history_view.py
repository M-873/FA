"""
app/ui/views/history_view.py
============================
History View for FA Studio:
- Tabular display of historical daily publishing runs from SQLite (publishing_history.db)
- Shows Date, Topic Title (Bangla typography), Provider/Clip, Status, and YouTube Video ID
- Clickable YouTube link (opens in browser)
- Detailed error messages viewable in tooltip/subtext
- Refresh and record counter
"""

import webbrowser
import customtkinter as ctk
from typing import Optional
from app.ui.theme import get_font, COLORS
from app.ui.controller import UIController


class HistoryView(ctk.CTkFrame):
    """View rendering all historical video automation and publication runs."""

    def __init__(self, master, controller: UIController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_table_headers()
        self._build_scroll_table()

        self.refresh()

    def _build_header(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        top.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top,
            text="Publishing & Run History",
            font=get_font(22, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title.grid(row=0, column=0, sticky="w")

        right_bar = ctk.CTkFrame(top, fg_color="transparent")
        right_bar.grid(row=0, column=1, sticky="e")

        self.count_lbl = ctk.CTkLabel(
            right_bar,
            text="Total Records: 0",
            font=get_font(12),
            text_color=COLORS["text_muted"],
        )
        self.count_lbl.pack(side="left", padx=10)

        btn_refresh = ctk.CTkButton(
            right_bar,
            text="🔄 Refresh",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            width=90,
            command=self.refresh,
        )
        btn_refresh.pack(side="left")

    def _build_table_headers(self):
        header_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=8,
            height=36,
        )
        header_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 5))
        header_card.grid_columnconfigure(0, weight=1)
        header_card.grid_columnconfigure(1, weight=3)
        header_card.grid_columnconfigure(2, weight=1)
        header_card.grid_columnconfigure(3, weight=1)
        header_card.grid_columnconfigure(4, weight=1)

        headers = [
            ("Date", 0, "w"),
            ("Topic (Bangla)", 1, "w"),
            ("Provider / Clip", 2, "w"),
            ("Status", 3, "center"),
            ("YouTube / Action", 4, "center"),
        ]

        for text, col, align in headers:
            lbl = ctk.CTkLabel(
                header_card,
                text=text,
                font=get_font(12, weight="bold"),
                text_color=COLORS["primary"],
                anchor=align,
            )
            lbl.grid(row=0, column=col, padx=12, pady=6, sticky="ew")

    def _build_scroll_table(self):
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        self.scroll_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    def refresh(self):
        """Reloads records from SQLite database and populates rows."""
        # Clear existing rows
        for child in self.scroll_frame.winfo_children():
            child.destroy()

        records = self.controller.get_publishing_history()
        self.count_lbl.configure(text=f"Total Records: {len(records)}")

        if not records:
            empty_card = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=COLORS["card_bg"],
                border_width=1,
                border_color=COLORS["card_border"],
                corner_radius=8,
            )
            empty_card.pack(fill="x", pady=20)
            lbl = ctk.CTkLabel(
                empty_card,
                text="No publishing records found yet. Run today's job to populate history.",
                font=get_font(13),
                text_color=COLORS["text_muted"],
                pady=30,
            )
            lbl.pack()
            return

        for idx, rec in enumerate(records):
            row_frame = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=COLORS["card_bg"],
                border_width=1,
                border_color=COLORS["card_border"],
                corner_radius=8,
            )
            row_frame.pack(fill="x", pady=4)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=3)
            row_frame.grid_columnconfigure(2, weight=1)
            row_frame.grid_columnconfigure(3, weight=1)
            row_frame.grid_columnconfigure(4, weight=1)

            # Date
            dt_lbl = ctk.CTkLabel(
                row_frame,
                text=str(rec.get("date", "N/A")),
                font=get_font(12),
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            dt_lbl.grid(row=0, column=0, padx=12, pady=10, sticky="w")

            # Topic Title (Bengali OpenType font)
            topic_text = rec.get("topic") or "Untitled automation run"
            topic_lbl = ctk.CTkLabel(
                row_frame,
                text=topic_text,
                font=get_font(13, weight="bold"),
                text_color=COLORS["text_main"],
                anchor="w",
                justify="left",
                wraplength=340,
            )
            topic_lbl.grid(row=0, column=1, padx=12, pady=10, sticky="w")

            # Provider & Clip
            prov_text = f"{rec.get('provider', 'local')} ({str(rec.get('clip_id', ''))[:10]})"
            prov_lbl = ctk.CTkLabel(
                row_frame,
                text=prov_text,
                font=get_font(11),
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            prov_lbl.grid(row=0, column=2, padx=12, pady=10, sticky="w")

            # Status Pill
            st = str(rec.get("status", "UNKNOWN")).upper()
            st_color = COLORS["success"][1] if "PUBLISHED" in st or "COMPLETE" in st else (COLORS["danger"][1] if "FAIL" in st else COLORS["warning"][1])

            st_pill = ctk.CTkLabel(
                row_frame,
                text=st,
                font=get_font(11, weight="bold"),
                text_color="#FFFFFF",
                fg_color=st_color,
                corner_radius=6,
                padx=8,
                pady=2,
            )
            st_pill.grid(row=0, column=3, padx=12, pady=10)

            # Action / YouTube link
            yt_id = rec.get("video_id")
            if yt_id and yt_id not in ("DRY_RUN", "N/A"):
                btn_link = ctk.CTkButton(
                    row_frame,
                    text=f"▶ youtu.be/{yt_id}",
                    font=get_font(11),
                    fg_color=COLORS["primary"],
                    hover_color=COLORS["primary_hover"],
                    height=28,
                    command=lambda v=yt_id: webbrowser.open(f"https://youtu.be/{v}"),
                )
                btn_link.grid(row=0, column=4, padx=12, pady=10)
            elif yt_id == "DRY_RUN":
                lbl_dry = ctk.CTkLabel(
                    row_frame,
                    text="[DRY RUN]",
                    font=get_font(11),
                    text_color=COLORS["info"][1],
                )
                lbl_dry.grid(row=0, column=4, padx=12, pady=10)
            else:
                err_text = str(rec.get("error") or "No link")[:18]
                lbl_err = ctk.CTkLabel(
                    row_frame,
                    text=err_text,
                    font=get_font(11),
                    text_color=COLORS["text_muted"],
                )
                lbl_err.grid(row=0, column=4, padx=12, pady=10)
