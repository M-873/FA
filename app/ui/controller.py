"""
app/ui/controller.py
====================
Decoupled UI Controller / View-Model:
Encapsulates all business logic, background execution, cancellation,
history querying, settings persistence, and diagnostics for the Desktop UI.
Fully testable without requiring an active graphical desktop.
"""

import os
import sys
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from app.hardware.detector import HardwareDetector
from app.hardware.profiles import PerformanceProfileManager
from app.jobs.history import PublishingHistoryManager
from app.jobs.manager import DailyJobManager
from app.jobs.state import DailyJobState, JobStatus
from app.notifications import get_notifier
from app.utils.config import get_project_config, get_env_settings
from app.utils.credentials import WindowsCredentialManager
from app.video.ffmpeg_helper import get_ffmpeg_binary, get_ffprobe_binary
from app.utils.logging import logger
from app.utils.windows import (
    is_start_with_windows_enabled,
    set_start_with_windows,
    open_folder_in_explorer,
)
from app.youtube.auth import YouTubeAuthManager


class UIController:
    """
    Central controller managing state and actions for the desktop interface.
    """

    def __init__(
        self,
        job_manager: Optional[DailyJobManager] = None,
        pipeline: Optional[Any] = None,
        scheduler: Optional[Any] = None,
        history_manager: Optional[PublishingHistoryManager] = None,
    ):
        self.job_mgr = job_manager if job_manager is not None else DailyJobManager()
        self.history_mgr = history_manager if history_manager is not None else PublishingHistoryManager()
        if pipeline is not None:
            self.pipeline = pipeline
        else:
            from app.jobs.recovery import DailyCartoonAutomationPipeline
            self.pipeline = DailyCartoonAutomationPipeline(
                job_manager=self.job_mgr,
                history_manager=self.history_mgr,
            )

        if scheduler is not None:
            self.scheduler = scheduler
        else:
            from app.scheduler.service import DailyScheduler
            self.scheduler = DailyScheduler(
                job_manager=self.job_mgr,
                pipeline=self.pipeline,
                history_manager=self.history_mgr,
            )
        self.project_cfg = get_project_config()
        self.env_cfg = get_env_settings()
        self.auth_mgr = YouTubeAuthManager()

        self._active_worker: Optional[threading.Thread] = None
        self._cancel_requested = threading.Event()
        self._is_running = False

    # -------------------------------------------------------------------------
    # 1. Home View State
    # -------------------------------------------------------------------------
    def get_home_state(self) -> Dict[str, Any]:
        """Returns consolidated state dictionary for Home dashboard card."""
        job = self.job_mgr.get_today_job()
        specs = HardwareDetector().detect()
        profile_info = PerformanceProfileManager.determine_profile(specs)
        profile_name = getattr(profile_info, "profile", "LOW")

        content_src = getattr(self.project_cfg, "content_source", "auto")
        badge = f"Hardware: {specs.cpu_name[:18]}... | GPU: {specs.gpu_name or 'None'} | Profile: {profile_name} ({content_src})"

        next_run_dt = self.scheduler.get_next_run_time()
        next_run_str = next_run_dt.strftime("%Y-%m-%d %H:%M") if next_run_dt else "None"

        # Determine step progress
        steps = {
            "topic": False,
            "clip": False,
            "edit": False,
            "quality": False,
            "approval": False,
            "upload": False,
        }

        if job:
            status = job.status
            if status in (
                JobStatus.GENERATING_SCRIPT,
                JobStatus.GENERATING_VOICE,
                JobStatus.ANIMATING,
                JobStatus.RENDERING,
                JobStatus.QUALITY_CHECK,
                JobStatus.AWAITING_APPROVAL,
                JobStatus.READY_TO_UPLOAD,
                JobStatus.UPLOADING_YOUTUBE,
                JobStatus.PUBLISHED,
                JobStatus.DRY_RUN_COMPLETE,
            ):
                steps["topic"] = True
            if status in (
                JobStatus.ANIMATING,
                JobStatus.RENDERING,
                JobStatus.QUALITY_CHECK,
                JobStatus.AWAITING_APPROVAL,
                JobStatus.READY_TO_UPLOAD,
                JobStatus.UPLOADING_YOUTUBE,
                JobStatus.PUBLISHED,
                JobStatus.DRY_RUN_COMPLETE,
            ):
                steps["clip"] = True
            if status in (
                JobStatus.QUALITY_CHECK,
                JobStatus.AWAITING_APPROVAL,
                JobStatus.READY_TO_UPLOAD,
                JobStatus.UPLOADING_YOUTUBE,
                JobStatus.PUBLISHED,
                JobStatus.DRY_RUN_COMPLETE,
            ):
                steps["edit"] = True
            if status in (
                JobStatus.AWAITING_APPROVAL,
                JobStatus.READY_TO_UPLOAD,
                JobStatus.UPLOADING_YOUTUBE,
                JobStatus.PUBLISHED,
                JobStatus.DRY_RUN_COMPLETE,
            ):
                steps["quality"] = True
            if status in (
                JobStatus.READY_TO_UPLOAD,
                JobStatus.UPLOADING_YOUTUBE,
                JobStatus.PUBLISHED,
                JobStatus.DRY_RUN_COMPLETE,
            ):
                steps["approval"] = True
            if status in (JobStatus.PUBLISHED, JobStatus.DRY_RUN_COMPLETE):
                steps["upload"] = True
            status_text = status.value
        else:
            status_text = "IDLE"

        if getattr(self.project_cfg, "kill_switch", False):
            status_text = "KILL SWITCH ACTIVE"

        return {
            "status_text": status_text,
            "is_running": self._is_running,
            "scheduler_active": self.scheduler.is_running(),
            "next_run": next_run_str,
            "hardware_badge": badge,
            "kill_switch": getattr(self.project_cfg, "kill_switch", False),
            "steps": steps,
            "today_job": job,
        }

    # -------------------------------------------------------------------------
    # 2. Pipeline Execution & Cancellation
    # -------------------------------------------------------------------------
    def run_pipeline_async(
        self,
        on_progress: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> bool:
        """Launches daily pipeline in a dedicated worker thread."""
        if self._is_running:
            logger.warning("Pipeline is already executing.")
            return False

        self._is_running = True
        self._cancel_requested.clear()

        def _worker():
            try:
                if on_progress:
                    on_progress("Pipeline initiated...")
                res = self.pipeline.run_daily_pipeline()
                if on_complete:
                    on_complete(res)
            except Exception as e:
                logger.error(f"Unhandled error in pipeline thread: {e}")
                if on_complete:
                    on_complete({"success": False, "reason": str(e)})
            finally:
                self._is_running = False

        self._active_worker = threading.Thread(target=_worker, daemon=True, name="PipelineWorker")
        self._active_worker.start()
        return True

    def cancel_pipeline(self):
        """Requests cancellation of ongoing operations."""
        self._cancel_requested.set()
        logger.info("Pipeline cancellation requested by user.")

    def is_pipeline_running(self) -> bool:
        return self._is_running

    # -------------------------------------------------------------------------
    # 3. Approval & Rejection Actions
    # -------------------------------------------------------------------------
    def approve_today_video(self) -> Dict[str, Any]:
        """Approves today's video and resumes publishing."""
        return self.pipeline.approve_job()

    def reject_today_video(self, regenerate: bool = False) -> Dict[str, Any]:
        """Rejects today's video, resets state, and optionally regenerates."""
        return self.pipeline.reject_job(regenerate=regenerate)

    def get_today_video_details(self) -> Dict[str, Any]:
        """Returns details of today's rendered master video."""
        job = self.job_mgr.get_today_job()
        video_path = getattr(job, "video_path", None) if job else "output/final.mp4"
        exists = os.path.exists(video_path) if video_path else False

        size_mb = 0.0
        if exists:
            try:
                size_mb = os.path.getsize(video_path) / (1024 * 1024)
            except Exception:
                pass

        return {
            "exists": exists,
            "video_path": video_path or "output/final.mp4",
            "topic": getattr(job, "topic_title", "No topic generated yet") if job else "None",
            "status": getattr(job, "status", JobStatus.PENDING).value if job else "None",
            "clip_id": getattr(job, "clip_id", "local_sample_tech_vertical") if job else "N/A",
            "provider": getattr(job, "provider", "local") if job else "N/A",
            "content_source": getattr(job, "content_source", "stock_edit") if job else "stock_edit",
            "size_mb": round(size_mb, 2),
            "can_approve": bool(job and job.status == JobStatus.AWAITING_APPROVAL and exists),
        }

    # -------------------------------------------------------------------------
    # 4. History Queries
    # -------------------------------------------------------------------------
    def get_publishing_history(self) -> List[Dict[str, Any]]:
        """Queries all SQLite publication history records."""
        return self.history_mgr.get_all_records()

    # -------------------------------------------------------------------------
    # 5. Accounts & Platforms
    # -------------------------------------------------------------------------
    def get_accounts_state(self) -> Dict[str, Any]:
        """Returns connected account status and platform toggle states."""
        yt_creds = self.auth_mgr.get_authenticated_service()
        is_yt_connected = (yt_creds is not None)
        channel_name = getattr(self.project_cfg, "youtube_channel_handle", "@Life-X-873")
        channel_id = getattr(self.project_cfg, "youtube_channel_id", "UCEX2BPA56iFeANOrrGY_eYg")

        return {
            "youtube": {
                "connected": is_yt_connected,
                "status_text": f"Connected as {channel_name}" if is_yt_connected else "Re-login required / Not connected",
                "channel_id": channel_id,
                "enabled": getattr(self.project_cfg, "youtube_enabled", True),
            },
            "facebook": {
                "enabled": getattr(self.project_cfg, "facebook_enabled", False),
                "status_text": "Coming Soon (Reels API integration)",
            },
            "instagram": {
                "enabled": getattr(self.project_cfg, "instagram_enabled", False),
                "status_text": "Coming Soon (Instagram Graph API)",
            },
        }

    def update_platform_toggle(self, platform: str, enabled: bool):
        """Updates platform switch in project config."""
        if platform == "youtube":
            self.project_cfg.youtube_enabled = enabled
        elif platform == "facebook":
            self.project_cfg.facebook_enabled = enabled
        elif platform == "instagram":
            self.project_cfg.instagram_enabled = enabled
        self.project_cfg.save()

    # -------------------------------------------------------------------------
    # 6. Settings Persistence
    # -------------------------------------------------------------------------
    def get_settings(self) -> Dict[str, Any]:
        """Returns current configuration dictionary."""
        return {
            "scheduled_time": getattr(self.project_cfg, "scheduled_time", "10:00"),
            "require_human_approval": getattr(self.project_cfg, "require_human_approval", True),
            "content_source": getattr(self.project_cfg, "content_source", "stock_edit"),
            "dry_run": getattr(self.project_cfg, "dry_run", True),
            "publisher_device": getattr(self.project_cfg, "publisher_device", True),
            "kill_switch": getattr(self.project_cfg, "kill_switch", False),
            "start_with_windows": is_start_with_windows_enabled(),
            "youtube_privacy": getattr(self.project_cfg, "youtube_privacy", "private"),
        }

    def save_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Saves configuration updates to project_config.json and Windows registry."""
        try:
            if "scheduled_time" in settings_data:
                self.project_cfg.scheduled_time = str(settings_data["scheduled_time"])
            if "require_human_approval" in settings_data:
                self.project_cfg.require_human_approval = bool(settings_data["require_human_approval"])
            if "content_source" in settings_data:
                self.project_cfg.content_source = str(settings_data["content_source"])
            if "dry_run" in settings_data:
                self.project_cfg.dry_run = bool(settings_data["dry_run"])
            if "publisher_device" in settings_data:
                self.project_cfg.publisher_device = bool(settings_data["publisher_device"])
            if "kill_switch" in settings_data:
                self.project_cfg.kill_switch = bool(settings_data["kill_switch"])
            if "youtube_privacy" in settings_data:
                self.project_cfg.youtube_privacy = str(settings_data["youtube_privacy"])

            # Windows Startup Key
            if "start_with_windows" in settings_data:
                enable_startup = bool(settings_data["start_with_windows"])
                set_start_with_windows(enable_startup)
                self.project_cfg.start_with_windows = enable_startup

            self.project_cfg.save()
            logger.info("Project settings saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Error saving project settings: {e}")
            return False

    def toggle_kill_switch(self) -> bool:
        """Toggles the emergency kill switch and persists to config."""
        current = getattr(self.project_cfg, "kill_switch", False)
        new_val = not current
        self.project_cfg.kill_switch = new_val
        self.project_cfg.save()
        logger.warning(f"Emergency kill switch toggled to: {new_val}")
        return new_val

    def toggle_scheduler(self) -> bool:
        """Starts or stops the daily scheduler worker."""
        if self.scheduler.is_running():
            self.scheduler.stop()
            return False
        else:
            self.scheduler.start()
            return True

    # -------------------------------------------------------------------------
    # 7. First-Run Wizard Diagnostics
    # -------------------------------------------------------------------------
    def run_first_run_diagnostics(self) -> List[Dict[str, Any]]:
        """
        Runs complete system check for First-Run Wizard:
        - Hardware specifications
        - FFmpeg & FFprobe binary availability
        - Gemini API key availability
        - YouTube authentication & channel verification
        - Output directory write access
        """
        results = []

        # 1. Hardware Check
        try:
            specs = HardwareDetector().detect()
            results.append({
                "item": "Hardware Detection",
                "passed": True,
                "detail": f"CPU: {specs.cpu_name} ({specs.cpu_cores}T) | RAM: {specs.ram_gb:.1f}GB | GPU: {specs.gpu_name or 'Integrated'}",
                "fix": None,
            })
        except Exception as e:
            results.append({
                "item": "Hardware Detection",
                "passed": False,
                "detail": str(e),
                "fix": "Ensure WMI/PowerShell is accessible.",
            })

        # 2. FFmpeg & FFprobe Check
        ffmpeg_bin = get_ffmpeg_binary()
        ffprobe_bin = get_ffprobe_binary()
        if ffmpeg_bin and ffprobe_bin:
            results.append({
                "item": "FFmpeg Engine",
                "passed": True,
                "detail": f"FFmpeg: {ffmpeg_bin} | FFprobe: {ffprobe_bin}",
                "fix": None,
            })
        else:
            results.append({
                "item": "FFmpeg Engine",
                "passed": False,
                "detail": "FFmpeg or FFprobe binary not detected in PATH or imageio.",
                "fix": "Install FFmpeg or run: pip install imageio[ffmpeg]",
            })

        # 3. AI Key Configuration
        gemini_key = self.env_cfg.GEMINI_API_KEY
        if gemini_key:
            results.append({
                "item": "Gemini AI Key",
                "passed": True,
                "detail": "Configured in environment.",
                "fix": None,
            })
        else:
            results.append({
                "item": "Gemini AI Key",
                "passed": False,
                "detail": "GEMINI_API_KEY is not configured.",
                "fix": "Enter your Google AI Studio API key in Settings.",
            })

        # 4. YouTube OAuth Authentication
        try:
            svc = self.auth_mgr.get_authenticated_service()
            if svc:
                chan_res = self.auth_mgr.verify_authenticated_channel(svc)
                if chan_res.get("valid"):
                    results.append({
                        "item": "YouTube Channel (@Life-X-873)",
                        "passed": True,
                        "detail": f"Connected as {chan_res.get('channel_title')} ({chan_res.get('channel_handle')})",
                        "fix": None,
                    })
                else:
                    results.append({
                        "item": "YouTube Channel (@Life-X-873)",
                        "passed": False,
                        "detail": chan_res.get("reason", "Channel handle mismatch."),
                        "fix": "Authenticate using the target channel @Life-X-873 in Accounts tab.",
                    })
            else:
                results.append({
                    "item": "YouTube Channel (@Life-X-873)",
                    "passed": False,
                    "detail": "Not authenticated. Token missing or expired in Credential Manager.",
                    "fix": "Click 'Connect Channel' in Accounts tab to authenticate via browser.",
                })
        except Exception as e:
            results.append({
                "item": "YouTube Channel (@Life-X-873)",
                "passed": False,
                "detail": str(e),
                "fix": "Re-run OAuth login on port 8088.",
            })

        # 5. Output Directory Check
        try:
            os.makedirs("output", exist_ok=True)
            test_file = "output/.write_test"
            with open(test_file, "w") as f:
                f.write("OK")
            os.remove(test_file)
            results.append({
                "item": "Output Storage Directory",
                "passed": True,
                "detail": f"Write access confirmed for {os.path.abspath('output')}",
                "fix": None,
            })
        except Exception as e:
            results.append({
                "item": "Output Storage Directory",
                "passed": False,
                "detail": str(e),
                "fix": "Check folder permissions for output directory.",
            })

        return results

    # -------------------------------------------------------------------------
    # 8. External File / Folder Utilities & OAuth Trigger
    # -------------------------------------------------------------------------
    def open_video_in_player(self, video_path: Optional[str] = None) -> bool:
        """Opens rendered video in default Windows media player."""
        target = video_path or "output/final.mp4"
        abs_path = os.path.abspath(target)
        if not os.path.exists(abs_path):
            logger.warning(f"Video file not found: {abs_path}")
            return False
        try:
            if sys.platform == "win32":
                os.startfile(abs_path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", abs_path])
            return True
        except Exception as e:
            logger.error(f"Failed to launch video player: {e}")
            return False

    def open_output_folder(self, folder_path: str = "output") -> bool:
        """Opens folder in Windows Explorer."""
        return open_folder_in_explorer(folder_path)

    def trigger_youtube_oauth_async(
        self,
        port: int = 8088,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """Launches YouTube OAuth flow on a background thread so UI never freezes."""
        def _worker():
            try:
                res = self.auth_mgr.authenticate_interactive(port=port)
                if on_complete:
                    on_complete(res)
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                if on_complete:
                    on_complete({"success": False, "reason": str(e)})

        threading.Thread(target=_worker, daemon=True, name="OAuthWorker").start()

    # -------------------------------------------------------------------------
    # 9. Secure API Key Persistence (Windows Credential Manager)
    # -------------------------------------------------------------------------
    def save_api_key(self, service: str, key_val: str) -> bool:
        """
        Saves API key to Windows Credential Manager under 'FA_<SERVICE>_API_KEY'.
        Never logs or displays the key value.
        """
        if not key_val or not key_val.strip():
            return False
        svc_upper = service.upper()
        target_name = f"FA_{svc_upper}_API_KEY"
        saved = WindowsCredentialManager.save_credential(
            target_name=target_name,
            username="FA_User",
            secret_data=key_val.strip(),
            comment=f"FA {service} API Key",
        )
        if saved:
            # Also set in-memory env variable for the active process
            env_var = f"{svc_upper}_API_KEY"
            os.environ[env_var] = key_val.strip()
            logger.info(f"API key for {service} saved securely to Windows Credential Manager.")
        return saved

    def has_api_key(self, service: str) -> bool:
        """Checks if API key is stored in Credential Manager or loaded in environment."""
        svc_upper = service.upper()
        target_name = f"FA_{svc_upper}_API_KEY"
        if WindowsCredentialManager.has_credential(target_name):
            return True
        env_val = os.environ.get(f"{svc_upper}_API_KEY")
        if env_val and env_val.strip():
            return True
        # Check settings
        if svc_upper == "GEMINI" and self.env_cfg.GEMINI_API_KEY:
            return True
        if svc_upper == "PEXELS" and getattr(self.env_cfg, "PEXELS_API_KEY", None):
            return True
        if svc_upper == "PIXABAY" and getattr(self.env_cfg, "PIXABAY_API_KEY", None):
            return True
        return False

    def get_recent_logs(self, limit: int = 150) -> List[str]:
        """Reads recent logs from output/run.log if available."""
        log_file = os.path.join("output", "run.log")
        if not os.path.exists(log_file):
            return ["No log records found yet."]
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return lines[-limit:]
        except Exception as e:
            return [f"Error reading logs: {e}"]
