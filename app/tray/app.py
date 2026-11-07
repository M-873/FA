"""
app/tray/app.py
===============
System Tray Application using pystray:
- Start/Stop scheduler
- Live Status display
- Open output folder
- Approve / Reject buttons with desktop notifications
- Emergency Kill Switch toggle
- Clean background thread lifecycle
"""

import os
import sys
import threading
import subprocess
from typing import Optional, Callable
from PIL import Image, ImageDraw, ImageFont
import pystray

from app.jobs.manager import DailyJobManager
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import JobStatus
from app.notifications import get_notifier
from app.scheduler.service import DailyScheduler
from app.utils.config import get_project_config
from app.utils.logging import logger
from app.utils.windows import open_folder_in_explorer


def create_tray_icon_image(size=(64, 64), color=(30, 144, 255), alert=False) -> Image.Image:
    """Generates a dynamic 64x64 RGBA icon with clean typography."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_color = (220, 20, 60) if alert else color
    # Draw rounded rectangle icon
    draw.rounded_rectangle([(2, 2), (size[0] - 2, size[1] - 2)], radius=12, fill=bg_color)

    # Draw centered text "FA"
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    text = "FA"
    # Approximate centering
    draw.text((18, 22), text, fill=(255, 255, 255, 255), font=font)
    return img


class SystemTrayApp:
    """
    Manages the Windows notification tray icon and menu interactions.
    """

    def __init__(
        self,
        scheduler: Optional[DailyScheduler] = None,
        job_manager: Optional[DailyJobManager] = None,
        pipeline: Optional[DailyCartoonAutomationPipeline] = None,
        on_open_dashboard: Optional[Callable[[], None]] = None,
    ):
        self.job_mgr = job_manager if job_manager is not None else DailyJobManager()
        self.pipeline = pipeline if pipeline is not None else DailyCartoonAutomationPipeline(job_manager=self.job_mgr)
        self.scheduler = scheduler if scheduler is not None else DailyScheduler(
            job_manager=self.job_mgr,
            pipeline=self.pipeline,
        )
        self.project_cfg = get_project_config()
        self.on_open_dashboard = on_open_dashboard

        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def get_status_summary(self) -> str:
        """Returns human-readable status for menu header."""
        job = self.job_mgr.get_today_job()
        if self.project_cfg.kill_switch:
            return "Status: KILL SWITCH ACTIVE"
        if not job:
            return f"Status: Idle (Next: {self.scheduler.get_scheduled_time_str()})"
        if job.status == JobStatus.AWAITING_APPROVAL:
            return "Status: AWAITING APPROVAL (!)"
        if job.status in (JobStatus.PUBLISHED, JobStatus.DRY_RUN_COMPLETE):
            return f"Status: Done Today ({job.status.value})"
        return f"Status: {job.status.value}"

    def build_menu(self) -> pystray.Menu:
        """Builds pystray context menu."""
        return pystray.Menu(
            pystray.MenuItem(lambda text: self.get_status_summary(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda text: "Stop Scheduler" if self.scheduler.is_running() else "Start Scheduler",
                self.toggle_scheduler,
            ),
            pystray.MenuItem("Run Today's Job Now", self.run_job_now),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Approve Video", self.approve_video),
            pystray.MenuItem("Reject Video", self.reject_video),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Output Folder", self.open_output_folder),
            pystray.MenuItem(
                "Emergency Kill Switch",
                self.toggle_kill_switch,
                checked=lambda item: getattr(self.project_cfg, "kill_switch", False),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Open Desktop Dashboard", self.open_dashboard),
            pystray.MenuItem("Exit", self.exit_app),
        )

    def toggle_scheduler(self, icon=None, item=None):
        """Starts or stops the scheduler worker thread."""
        if self.scheduler.is_running():
            self.scheduler.stop()
            logger.info("Scheduler stopped from tray.")
        else:
            self.scheduler.start()
            logger.info("Scheduler started from tray.")

    def run_job_now(self, icon=None, item=None):
        """Triggers pipeline run immediately in a background thread."""
        threading.Thread(target=self._run_job_worker, daemon=True).start()

    def _run_job_worker(self):
        logger.info("Manual pipeline run triggered from tray.")
        res = self.pipeline.run_daily_pipeline()
        logger.info(f"Tray run completed: {res.get('job_status')}")

    def approve_video(self, icon=None, item=None):
        """Approves today's job and resumes upload."""
        threading.Thread(target=self._approve_worker, daemon=True).start()

    def _approve_worker(self):
        res = self.pipeline.approve_job()
        if res.get("success"):
            get_notifier().notify_success(video_id=getattr(self.job_mgr.get_today_job(), "youtube_video_id", "N/A"))
        else:
            logger.warning(f"Tray approve failed: {res.get('reason')}")

    def reject_video(self, icon=None, item=None):
        """Rejects today's video and resets job."""
        res = self.pipeline.reject_job(regenerate=False)
        logger.info(f"Video rejected from tray: {res}")

    def open_output_folder(self, icon=None, item=None):
        open_folder_in_explorer("output")

    def toggle_kill_switch(self, icon=None, item=None):
        new_state = not getattr(self.project_cfg, "kill_switch", False)
        self.project_cfg.kill_switch = new_state
        self.project_cfg.save()
        logger.info(f"Kill switch set to {new_state} from tray.")

    def open_dashboard(self, icon=None, item=None):
        if self.on_open_dashboard:
            self.on_open_dashboard()
        else:
            # Launch desktop UI
            subprocess.Popen([sys.executable, "-m", "app.main", "--gui"])

    def exit_app(self, icon=None, item=None):
        """Stops scheduler and terminates tray loop."""
        self.scheduler.stop()
        if self._icon:
            self._icon.stop()
        logger.info("SystemTrayApp terminated.")

    def run(self):
        """Runs the tray icon event loop."""
        job = self.job_mgr.get_today_job()
        is_alert = (job and job.status == JobStatus.AWAITING_APPROVAL)
        img = create_tray_icon_image(alert=is_alert)

        self._icon = pystray.Icon(
            name="FA_Automation",
            icon=img,
            title="FA Video Automation",
            menu=self.build_menu(),
        )

        # Connect notifier to tray icon for balloon notifications
        get_notifier().set_tray_icon(self._icon)

        # Start scheduler by default if configured
        if getattr(self.project_cfg, "auto_run_on_start", True):
            self.scheduler.start()

        self._icon.run()
