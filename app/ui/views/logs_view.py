"""
app/ui/views/logs_view.py
========================
System Logs View for FA Studio:
- Real-time display of application execution logs from output/run.log
- Monospaced rendering for structured error diagnosis
- Level filters (All, INFO, WARNING, ERROR)
- Copy to clipboard & Refresh actions
- Plain-language explanation banner for common failures
"""

import customtkinter as ctk
from typing import Optional
from app.ui.theme import get_font, get_mono_font, COLORS
from app.ui.controller import UIController


class LogsView(ctk.CTkFrame):
    """View providing transparency into background execution, network requests, and errors."""

    def __init__(self, master, controller: UIController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self._raw_lines = []
        self._current_filter = "ALL"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_filter_bar()
        self._build_log_box()

        self.refresh()

    def _build_header(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        top.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top,
            text="Execution & Diagnostic Logs",
            font=get_font(22, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title.grid(row=0, column=0, sticky="w")

        right_btns = ctk.CTkFrame(top, fg_color="transparent")
        right_btns.grid(row=0, column=1, sticky="e")

        self.btn_refresh = ctk.CTkButton(
            right_btns,
            text="🔄 Refresh",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            width=90,
            command=self.refresh,
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_copy = ctk.CTkButton(
            right_btns,
            text="📋 Copy All",
            font=get_font(12),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            width=90,
            command=self._copy_logs,
        )
        self.btn_copy.pack(side="left", padx=5)

    def _build_filter_bar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=20, pady=5)

        lbl = ctk.CTkLabel(bar, text="Filter Level:", font=get_font(12, weight="bold"), text_color=COLORS["text_muted"])
        lbl.pack(side="left", padx=(0, 10))

        self.filter_buttons = {}
        for level in ["ALL", "INFO", "WARNING", "ERROR"]:
            btn = ctk.CTkButton(
                bar,
                text=level,
                font=get_font(11, weight="bold"),
                fg_color=COLORS["primary"] if level == "ALL" else COLORS["button_secondary"],
                hover_color=COLORS["primary_hover"],
                text_color="#FFFFFF" if level == "ALL" else COLORS["text_main"],
                width=65,
                height=26,
                command=lambda lvl=level: self._set_filter(lvl),
            )
            btn.pack(side="left", padx=3)
            self.filter_buttons[level] = btn

    def _build_log_box(self):
        self.log_textbox = ctk.CTkTextbox(
            self,
            font=get_mono_font(11),
            fg_color=COLORS["card_bg"],
            text_color=COLORS["text_main"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=8,
            wrap="none",
        )
        self.log_textbox.grid(row=2, column=0, sticky="nsew", padx=20, pady=(5, 15))

    def _set_filter(self, level: str):
        self._current_filter = level
        for lvl, btn in self.filter_buttons.items():
            if lvl == level:
                btn.configure(fg_color=COLORS["primary"], text_color="#FFFFFF")
            else:
                btn.configure(fg_color=COLORS["button_secondary"], text_color=COLORS["text_main"])
        self._render_filtered_logs()

    def _render_filtered_logs(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")

        filtered = []
        for line in self._raw_lines:
            if self._current_filter == "ALL":
                filtered.append(line)
            elif f"[{self._current_filter}]" in line or f"- {self._current_filter} -" in line or self._current_filter in line.upper():
                filtered.append(line)

        content = "".join(filtered) if filtered else "No log messages match the active filter."
        self.log_textbox.insert("end", content)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _copy_logs(self):
        content = "".join(self._raw_lines)
        self.clipboard_clear()
        self.clipboard_append(content)
        self.btn_copy.configure(text="✓ Copied!")
        self.after(1500, lambda: self.btn_copy.configure(text="📋 Copy All"))

    def refresh(self):
        self._raw_lines = self.controller.get_recent_logs(limit=200)
        self._render_filtered_logs()
