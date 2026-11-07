"""
app/scheduler/service.py
========================
Automated Daily Video Scheduler with Catch-up and Safety Guards:
- Triggers pipeline at configurable scheduled_time (HH:MM, default 10:00 local)
- Catch-up execution on startup or wake-from-sleep if today's run was missed
- Max 1 job per day enforced by DailyJobState and SQLite PublishingHistoryManager
- Safety guards: respects emergency kill switch, publisher device authorization,
  and human approval (pauses at AWAITING_APPROVAL)
- Non-blocking background worker thread with clean start() / stop() lifecycle
"""

import threading
import time
from datetime import datetime, date, timedelta, time as dt_time
from typing import Optional, Dict, Any, Callable

from app.jobs.history import PublishingHistoryManager
from app.jobs.manager import DailyJobManager
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import DailyJobState, JobStatus
from app.utils.config import get_project_config, get_env_settings
from app.utils.logging import logger


class DailyScheduler:
    """
    Manages daily video pipeline execution based on configurable local clock time.
    Provides catch-up recovery upon system wake-from-sleep or late startup.
    """

    def __init__(
        self,
        job_manager: Optional[DailyJobManager] = None,
        pipeline: Optional[DailyCartoonAutomationPipeline] = None,
        history_manager: Optional[PublishingHistoryManager] = None,
        on_job_completed: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_job_started: Optional[Callable[[], None]] = None,
    ):
        self.project_cfg = get_project_config()
        self.env_cfg = get_env_settings()
        self.job_mgr = job_manager if job_manager is not None else DailyJobManager()
        self.history_mgr = history_manager if history_manager is not None else PublishingHistoryManager()
        self.pipeline = pipeline if pipeline is not None else DailyCartoonAutomationPipeline(
            job_manager=self.job_mgr,
            history_manager=self.history_mgr,
        )
        self.on_job_completed = on_job_completed
        self.on_job_started = on_job_started

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def get_scheduled_time_str(self) -> str:
        """Returns effective HH:MM scheduled time string from env or project config."""
        if self.env_cfg.SCHEDULED_TIME:
            return self.env_cfg.SCHEDULED_TIME
        return getattr(self.project_cfg, "scheduled_time", "10:00")

    def parse_scheduled_time(self, time_str: Optional[str] = None) -> dt_time:
        """Parses 'HH:MM' string to datetime.time, defaulting to 10:00 on error."""
        t_str = time_str or self.get_scheduled_time_str()
        try:
            parts = t_str.strip().split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return dt_time(hour=hour, minute=minute)
        except Exception as e:
            logger.warning(f"Failed to parse scheduled time '{t_str}': {e}. Using default 10:00.")
            return dt_time(hour=10, minute=0)

    def get_scheduled_datetime(self, target_date: date, time_obj: Optional[dt_time] = None) -> datetime:
        """Combines a date and scheduled time into a naive local datetime."""
        t = time_obj or self.parse_scheduled_time()
        return datetime.combine(target_date, t)

    def is_today_done(self, target_date: Optional[str] = None) -> bool:
        """Checks if today's run has already completed (PUBLISHED or DRY_RUN_COMPLETE)."""
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")

        # 1. Check local daily job state
        job = self.job_mgr.get_today_job()
        if job and job.date == date_str:
            if job.status in (JobStatus.PUBLISHED, JobStatus.DRY_RUN_COMPLETE):
                return True

        # 2. Check SQLite publishing history database
        history_records = self.history_mgr.get_records_by_date(date_str)
        done_records = [r for r in history_records if r.get("status") in ("PUBLISHED", "DRY_RUN_COMPLETE")]
        if len(done_records) >= 1:
            return True

        return False

    def is_job_active(self) -> bool:
        """Checks if today's job is currently running or paused in AWAITING_APPROVAL."""
        job = self.job_mgr.get_today_job()
        if not job:
            return False
        return job.status not in (
            JobStatus.PENDING,
            JobStatus.FAILED,
            JobStatus.PUBLISHED,
            JobStatus.DRY_RUN_COMPLETE,
        )

    def should_catch_up(self, now: Optional[datetime] = None) -> bool:
        """
        Determines if today's scheduled run is due or was missed (catch-up condition).
        Returns True if:
        - Emergency kill switch is NOT active
        - Today's job has NOT finished
        - No job is currently active/awaiting approval
        - Current time is >= scheduled time for today
        """
        current_dt = now or datetime.now()

        # Check Emergency Kill Switch
        kill_switch = (
            self.env_cfg.KILL_SWITCH
            if self.env_cfg.KILL_SWITCH is not None
            else getattr(self.project_cfg, "kill_switch", False)
        )
        if kill_switch:
            return False

        today_str = current_dt.strftime("%Y-%m-%d")
        if self.is_today_done(today_str):
            return False

        if self.is_job_active():
            return False

        sched_today = self.get_scheduled_datetime(current_dt.date())
        return current_dt >= sched_today

    def get_next_run_time(self, now: Optional[datetime] = None) -> datetime:
        """
        Computes next scheduled execution datetime:
        - If today is done, returns tomorrow at scheduled time.
        - If today is not done and time hasn't arrived, returns today at scheduled time.
        - If today is not done and time has passed, returns now (due immediately).
        """
        current_dt = now or datetime.now()
        sched_time = self.parse_scheduled_time()
        sched_today = self.get_scheduled_datetime(current_dt.date(), sched_time)
        today_str = current_dt.strftime("%Y-%m-%d")

        if self.is_today_done(today_str):
            tomorrow = current_dt.date() + timedelta(days=1)
            return self.get_scheduled_datetime(tomorrow, sched_time)

        if current_dt < sched_today:
            return sched_today

        return current_dt

    def tick(self, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Single discrete evaluation tick.
        If catch-up / due condition is met, triggers pipeline execution.
        """
        current_dt = now or datetime.now()
        if self.should_catch_up(current_dt):
            logger.info(
                f"[SCHEDULER] Daily job is due (Time: {current_dt.strftime('%H:%M:%S')}, "
                f"Scheduled: {self.get_scheduled_time_str()}). Triggering pipeline..."
            )
            if self.on_job_started:
                try:
                    self.on_job_started()
                except Exception as e:
                    logger.warning(f"on_job_started callback error: {e}")

            res = self.pipeline.run_daily_pipeline()

            if self.on_job_completed:
                try:
                    self.on_job_completed(res)
                except Exception as e:
                    logger.warning(f"on_job_completed callback error: {e}")

            return res

        return None

    def start(self, poll_interval_seconds: float = 5.0):
        """Starts background monitoring thread."""
        if self.is_running():
            logger.warning("DailyScheduler is already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(poll_interval_seconds,),
            daemon=True,
            name="DailySchedulerWorker",
        )
        self._thread.start()
        logger.info(
            f"DailyScheduler started successfully. Next scheduled check: {self.get_next_run_time().strftime('%Y-%m-%d %H:%M:%S')}."
        )

    def stop(self, timeout: float = 5.0):
        """Stops background monitoring thread cleanly."""
        if not self.is_running():
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._thread = None
        logger.info("DailyScheduler stopped.")

    def is_running(self) -> bool:
        """Returns True if the background thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def _run_loop(self, poll_interval_seconds: float):
        """Internal background polling loop. Handles wake-from-sleep by inspecting system clock on each tick."""
        logger.info("Scheduler worker loop entered.")
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.error(f"[SCHEDULER LOOP ERROR] {e}")

            self._stop_event.wait(timeout=poll_interval_seconds)
        logger.info("Scheduler worker loop exited.")
