"""
app/ui/settings.py
==================
Lightweight local configuration and state persistence for Phase 1.
Zero database dependency: persists state in a simple local JSON file.
Maintains independent states for Daily Auto Post and Link to Reels.
"""

import json
import os
from typing import Any, Dict, List, Optional
from app.utils.logging import logger

DEFAULT_SETTINGS_FILENAME = "app_settings.json"


def get_default_settings() -> Dict[str, Any]:
    return {
        "daily_auto_post": {
            "enabled": False,
            "status": "OFF",  # "ON", "OFF", or "PAUSED"
            "last_run": "Yesterday, 09:30 AM (Demo)",
            "next_run": "Tomorrow, 09:00 AM (Scheduled)",
            "today_progress": "Idle (0/1 image)",
        },
        "link_to_reels": {
            "enabled": False,
            "status": "OFF",  # "ON" or "OFF"
        },
        "mock_reels_jobs": [
            {
                "id": "reel_job_101",
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "status": "COMPLETED",
                "progress": 100,
                "created_at": "Today, 10:15 AM",
                "note": "Mock highlight reel rendered (Demo)",
            },
            {
                "id": "reel_job_102",
                "url": "https://vimeo.com/76979871",
                "status": "PROCESSING",
                "progress": 65,
                "created_at": "Today, 11:20 AM",
                "note": "Simulating highlight extraction (Demo)",
            },
            {
                "id": "reel_job_103",
                "url": "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
                "status": "QUEUED",
                "progress": 0,
                "created_at": "Today, 11:45 AM",
                "note": "Waiting in simulated queue",
            },
            {
                "id": "reel_job_104",
                "url": "https://www.youtube.com/watch?v=2vjPBrBU-TM",
                "status": "FAILED",
                "progress": 25,
                "created_at": "Yesterday, 04:30 PM",
                "note": "Mock Error: Simulated video stream timeout",
            },
        ],
        "connected_accounts": {
            "youtube": {"status": "Not Connected", "username": None},
            "facebook": {"status": "Not Connected", "page_name": None},
            "instagram": {"status": "Not Connected", "handle": None},
        },
        "hardware_report": None,
        "hardware_profile_override": "auto",
    }


class SettingsManager:
    """
    Manages local JSON persistence of application settings and mock jobs.
    Ensures that toggling Daily Auto Post does NOT change Link to Reels,
    and toggling Link to Reels does NOT change Daily Auto Post.
    """

    def __init__(self, filepath: Optional[str] = None):
        if filepath:
            self.filepath = filepath
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.filepath = os.path.join(base_dir, DEFAULT_SETTINGS_FILENAME)

        self.data: Dict[str, Any] = self.load()

    def load(self) -> Dict[str, Any]:
        """Loads settings from disk, falling back to defaults if missing or corrupt."""
        defaults = get_default_settings()
        if not os.path.exists(self.filepath):
            logger.info(f"Settings file not found at {self.filepath}. Creating with defaults.")
            self.save(defaults)
            return defaults

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Ensure top-level keys exist
            for key, val in defaults.items():
                if key not in loaded:
                    loaded[key] = val
                elif isinstance(val, dict) and isinstance(loaded[key], dict):
                    for subkey, subval in val.items():
                        if subkey not in loaded[key]:
                            loaded[key][subkey] = subval
            return loaded
        except Exception as e:
            logger.error(f"Error loading {self.filepath}: {e}. Restoring defaults.")
            self.save(defaults)
            return defaults

    def save(self, data: Optional[Dict[str, Any]] = None) -> bool:
        """Saves current settings dictionary to disk."""
        if data is not None:
            self.data = data
        try:
            parent = os.path.dirname(self.filepath)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save settings to {self.filepath}: {e}")
            return False

    # -------------------------------------------------------------------------
    # Daily Auto Post Toggle & Status (Independent)
    # -------------------------------------------------------------------------
    def get_daily_auto_post(self) -> Dict[str, Any]:
        return self.data.get("daily_auto_post", get_default_settings()["daily_auto_post"])

    def set_daily_auto_post_toggle(self, enabled: bool) -> None:
        """
        Updates Daily Auto Post toggle state without modifying Link to Reels.
        """
        dap = self.data.setdefault("daily_auto_post", {})
        dap["enabled"] = bool(enabled)
        if enabled:
            dap["status"] = "ON"
            dap["next_run"] = "Tomorrow, 09:00 AM (Scheduled)"
        else:
            dap["status"] = "OFF"
            dap["next_run"] = "Disabled / Standing by"
        self.save()
        logger.info(f"Daily Auto Post toggle updated: enabled={enabled}, status={dap['status']}")

    def set_daily_auto_post_status(self, status: str) -> None:
        """Sets status: ON, OFF, or PAUSED."""
        if status not in ("ON", "OFF", "PAUSED"):
            raise ValueError(f"Invalid status '{status}'. Must be ON, OFF, or PAUSED.")
        dap = self.data.setdefault("daily_auto_post", {})
        dap["status"] = status
        if status == "ON":
            dap["enabled"] = True
            dap["next_run"] = "Tomorrow, 09:00 AM (Scheduled)"
        elif status == "PAUSED":
            dap["enabled"] = True
            dap["next_run"] = "Paused"
        elif status == "OFF":
            dap["enabled"] = False
            dap["next_run"] = "Disabled / Standing by"
        self.save()

    # -------------------------------------------------------------------------
    # Link to Reels Toggle & Jobs (Independent)
    # -------------------------------------------------------------------------
    def get_link_to_reels(self) -> Dict[str, Any]:
        return self.data.get("link_to_reels", get_default_settings()["link_to_reels"])

    def set_link_to_reels_toggle(self, enabled: bool) -> None:
        """
        Updates Link to Reels toggle state without modifying Daily Auto Post.
        """
        ltr = self.data.setdefault("link_to_reels", {})
        ltr["enabled"] = bool(enabled)
        ltr["status"] = "ON" if enabled else "OFF"
        self.save()
        logger.info(f"Link to Reels toggle updated: enabled={enabled}, status={ltr['status']}")

    def get_reels_jobs(self) -> List[Dict[str, Any]]:
        return self.data.get("mock_reels_jobs", [])

    def add_mock_reels_job(self, url: str) -> Dict[str, Any]:
        """
        Adds a new mock job in QUEUED status. Does not download or process videos.
        """
        jobs = self.data.setdefault("mock_reels_jobs", [])
        job_count = len(jobs) + 101
        new_job = {
            "id": f"reel_job_{job_count}",
            "url": url.strip(),
            "status": "QUEUED",
            "progress": 0,
            "created_at": "Just now",
            "note": "Queued for highlight analysis (Phase 1 Mock)",
        }
        # Insert at the beginning of the list for visibility
        jobs.insert(0, new_job)
        self.save()
        logger.info(f"Added mock reels job: {new_job['id']} for URL {url}")
        return new_job

    # -------------------------------------------------------------------------
    # Hardware Telemetry & Profile Persistence (Phase 2)
    # -------------------------------------------------------------------------
    def get_hardware_report(self) -> Optional[Dict[str, Any]]:
        """Returns the last known hardware detection report, if any."""
        return self.data.get("hardware_report")

    def save_hardware_report(self, specs_dict: Dict[str, Any], profile_dict: Dict[str, Any]) -> None:
        """
        Persists the latest hardware detection report and selected profile.
        Does not overwrite unrelated settings or mock jobs.
        """
        import datetime
        report = {
            "specs": specs_dict,
            "profile": profile_dict,
            "saved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.data["hardware_report"] = report
        self.save()
        logger.info("Persisted hardware detection report and profile to settings.")

    def reset_to_defaults(self) -> None:
        """Resets all settings to default state."""
        self.data = get_default_settings()
        self.save()

    # -------------------------------------------------------------------------
    # Hardware Profile Override
    # -------------------------------------------------------------------------
    def get_hardware_profile_override(self) -> str:
        """Returns the manual hardware profile override: auto, low, medium, or high."""
        val = self.data.get("hardware_profile_override", "auto")
        return str(val).lower() if val else "auto"

    def set_hardware_profile_override(self, override: str) -> None:
        """Sets the manual hardware profile override: auto, low, medium, or high."""
        val = str(override).lower().strip()
        if val not in ("auto", "low", "medium", "high", "ultra", "legacy_2gb"):
            raise ValueError(f"Invalid profile override '{override}'. Must be auto, low, medium, high, ultra, or legacy_2gb.")
        self.data["hardware_profile_override"] = val
        self.save()
        logger.info(f"Hardware profile override updated to: {val}")

    # -------------------------------------------------------------------------
    # Connected Accounts Management
    # -------------------------------------------------------------------------
    def get_connected_accounts(self) -> Dict[str, Any]:
        return self.data.get("connected_accounts", get_default_settings()["connected_accounts"])

    def get_youtube_connection(self) -> Dict[str, Any]:
        accounts = self.get_connected_accounts()
        return accounts.get("youtube", {"status": "Not Connected"})

    def update_youtube_connection(
        self,
        status: str,
        channel_title: Optional[str] = None,
        channel_id: Optional[str] = None,
        handle: Optional[str] = None,
        channel_url: Optional[str] = None,
    ) -> None:
        import datetime
        accounts = self.data.setdefault("connected_accounts", {})
        yt = accounts.setdefault("youtube", {})
        yt["status"] = status
        if channel_title is not None:
            yt["channel_title"] = channel_title
            yt["username"] = channel_title
        if channel_id is not None:
            yt["channel_id"] = channel_id
        if handle is not None:
            yt["handle"] = handle
        if channel_url is not None:
            yt["channel_url"] = channel_url
        if status == "Connected":
            yt["connected_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        logger.info(f"Updated YouTube connection status: {status} (Channel: {channel_title or yt.get('channel_title')})")

    def disconnect_youtube(self) -> None:
        accounts = self.data.setdefault("connected_accounts", {})
        accounts["youtube"] = {
            "status": "Not Connected",
            "username": None,
            "channel_title": None,
            "channel_id": None,
            "handle": None,
            "channel_url": None,
            "connected_at": None,
        }
        self.save()
        logger.info("YouTube account disconnected from settings.")



def load_settings(filepath: Optional[str] = None) -> Dict[str, Any]:
    """Module-level helper to load settings dictionary."""
    mgr = SettingsManager(filepath=filepath)
    return mgr.data


def save_settings(data: Dict[str, Any], filepath: Optional[str] = None) -> bool:
    """Module-level helper to save settings dictionary."""
    mgr = SettingsManager(filepath=filepath)
    return mgr.save(data)


def get_hardware_report(settings_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Module-level helper to retrieve hardware report."""
    mgr = SettingsManager(filepath=settings_path)
    return mgr.get_hardware_report()


def save_hardware_report(
    specs_dict: Dict[str, Any],
    profile_dict: Dict[str, Any],
    settings_path: Optional[str] = None,
) -> bool:
    """Module-level helper to persist hardware report."""
    mgr = SettingsManager(filepath=settings_path)
    mgr.save_hardware_report(specs_dict, profile_dict)
    return True

