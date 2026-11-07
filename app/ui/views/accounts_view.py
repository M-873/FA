"""
app/ui/views/accounts_view.py
=============================
Accounts & Channels View for FA Studio:
- YouTube channel connection state (@Life-X-873 verification)
- Interactive OAuth 2.0 browser connect button (runs in worker thread)
- Windows Credential Manager encrypted token status
- Platform toggles (YouTube, Facebook Coming Soon, Instagram Coming Soon)
"""

import customtkinter as ctk
from typing import Optional, Callable
from app.ui.theme import get_font, COLORS
from app.ui.controller import UIController
from app.utils.logging import logger


class AccountsView(ctk.CTkFrame):
    """View managing platform authentication and distribution channels."""

    def __init__(self, master, controller: UIController, on_account_changed: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.on_account_changed = on_account_changed

        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_youtube_card()
        self._build_coming_soon_cards()

        self.refresh()

    def _build_header(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(15, 10))

        title = ctk.CTkLabel(
            top,
            text="Connected Accounts & Distribution",
            font=get_font(22, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            top,
            text="OAuth authentication and publishing channel settings. Tokens are encrypted in Windows Credential Manager.",
            font=get_font(12),
            text_color=COLORS["text_muted"],
        )
        subtitle.pack(anchor="w", pady=(2, 0))

    def _build_youtube_card(self):
        self.yt_card = ctk.CTkFrame(
            self,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            corner_radius=12,
        )
        self.yt_card.pack(fill="x", padx=20, pady=10)
        self.yt_card.grid_columnconfigure(0, weight=1)

        # Header Row
        header_row = ctk.CTkFrame(self.yt_card, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        header_row.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            header_row,
            text="YouTube Channel Integration",
            font=get_font(16, weight="bold"),
            text_color=COLORS["text_main"],
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        self.yt_switch = ctk.CTkSwitch(
            header_row,
            text="Enable YouTube Publishing",
            font=get_font(12),
            command=self._on_yt_toggle,
        )
        self.yt_switch.grid(row=0, column=1, sticky="e")

        # Status & Channel Info Box
        info_box = ctk.CTkFrame(self.yt_card, fg_color=COLORS["sidebar_bg"], corner_radius=8)
        info_box.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        info_box.grid_columnconfigure(1, weight=1)

        self.yt_status_lbl = ctk.CTkLabel(
            info_box,
            text="Checking authentication status...",
            font=get_font(13, weight="bold"),
            text_color=COLORS["success"][1],
            anchor="w",
        )
        self.yt_status_lbl.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 4))

        self.yt_detail_lbl = ctk.CTkLabel(
            info_box,
            text="Channel ID: UCEX2BPA56iFeANOrrGY_eYg | Encrypted in Windows Credential Manager",
            font=get_font(11),
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.yt_detail_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 12))

        # Action Buttons
        btn_box = ctk.CTkFrame(self.yt_card, fg_color="transparent")
        btn_box.grid(row=2, column=0, sticky="ew", padx=20, pady=(5, 15))

        self.btn_connect = ctk.CTkButton(
            btn_box,
            text="🔗 Connect Channel (OAuth 8088)",
            font=get_font(12, weight="bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            command=self._connect_youtube,
        )
        self.btn_connect.pack(side="left", padx=(0, 10))

        self.btn_disconnect = ctk.CTkButton(
            btn_box,
            text="🗑 Disconnect",
            font=get_font(12),
            fg_color=COLORS["button_secondary"],
            hover_color=COLORS["button_secondary_hover"],
            text_color=COLORS["text_main"],
            command=self._disconnect_youtube,
        )
        self.btn_disconnect.pack(side="left")

        self.oauth_status_lbl = ctk.CTkLabel(
            btn_box,
            text="",
            font=get_font(11),
            text_color=COLORS["text_muted"],
        )
        self.oauth_status_lbl.pack(side="left", padx=15)

    def _build_coming_soon_cards(self):
        """Coming soon cards for Meta platforms."""
        for platform_name in ["Facebook Reels", "Instagram Reels"]:
            card = ctk.CTkFrame(
                self,
                fg_color=COLORS["card_bg"],
                border_width=1,
                border_color=COLORS["card_border"],
                corner_radius=12,
            )
            card.pack(fill="x", padx=20, pady=8)
            card.grid_columnconfigure(0, weight=1)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=15)
            row.grid_columnconfigure(0, weight=1)

            lbl = ctk.CTkLabel(
                row,
                text=f"{platform_name} Integration",
                font=get_font(15, weight="bold"),
                text_color=COLORS["text_muted"],
            )
            lbl.grid(row=0, column=0, sticky="w")

            pill = ctk.CTkLabel(
                row,
                text="COMING SOON",
                font=get_font(11, weight="bold"),
                text_color="#FFFFFF",
                fg_color=COLORS["info"][1],
                corner_radius=6,
                padx=10,
                pady=2,
            )
            pill.grid(row=0, column=1, sticky="e")

            desc = ctk.CTkLabel(
                card,
                text="Integration with Meta Graph & Reels Publishing API will be available in an upcoming release.",
                font=get_font(11),
                text_color=COLORS["text_muted"],
                anchor="w",
            )
            desc.pack(fill="x", padx=20, pady=(0, 15))

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def _on_yt_toggle(self):
        val = bool(self.yt_switch.get())
        self.controller.update_platform_toggle("youtube", val)

    def _connect_youtube(self):
        self.oauth_status_lbl.configure(text="Opening browser for authorization...")
        self.btn_connect.configure(state="disabled")

        def _on_oauth_complete(res: dict):
            def _ui_update():
                self.btn_connect.configure(state="normal")
                if res.get("verified") or res.get("success"):
                    self.oauth_status_lbl.configure(text="Connected successfully!")
                else:
                    self.oauth_status_lbl.configure(text=f"Auth: {res.get('reason', 'Failed')}")
                self.refresh()
                if self.on_account_changed:
                    self.on_account_changed()

            self.after(0, _ui_update)

        self.controller.trigger_youtube_oauth_async(port=8088, on_complete=_on_oauth_complete)

    def _disconnect_youtube(self):
        self.controller.auth_mgr.disconnect()
        self.oauth_status_lbl.configure(text="Account disconnected.")
        self.refresh()
        if self.on_account_changed:
            self.on_account_changed()

    # -------------------------------------------------------------------------
    # Refresh
    # -------------------------------------------------------------------------
    def refresh(self):
        accounts = self.controller.get_accounts_state()
        yt = accounts["youtube"]

        if yt["connected"]:
            self.yt_status_lbl.configure(
                text=f"● {yt['status_text']}",
                text_color=COLORS["success"][1],
            )
            self.yt_detail_lbl.configure(
                text=f"Channel ID: {yt['channel_id']} | Verified: @Life-X-873 | Windows Credential Manager Active"
            )
            self.btn_connect.configure(text="🔄 Re-authenticate")
        else:
            self.yt_status_lbl.configure(
                text="● Re-login required / Not Connected",
                text_color=COLORS["danger"][1],
            )
            self.yt_detail_lbl.configure(
                text="Token expired or not found. Click 'Connect Channel' to authenticate with @Life-X-873."
            )
            self.btn_connect.configure(text="🔗 Connect Channel (OAuth 8088)")

        if yt.get("enabled"):
            self.yt_switch.select()
        else:
            self.yt_switch.deselect()
