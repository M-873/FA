import json
import os
from datetime import datetime
from typing import Optional
from app.jobs.state import DailyJobState, JobStatus
from app.utils.logging import logger


class DailyJobManager:
    """Manages lightweight daily job state stored in daily_job.json."""

    def __init__(self, state_file_path: str = "daily_job.json"):
        self.state_file_path = state_file_path

    def get_today_date_str(self) -> str:
        """Returns today's date in YYYY-MM-DD format."""
        return datetime.now().strftime("%Y-%m-%d")

    def load_job(self) -> Optional[DailyJobState]:
        """Loads existing job state from daily_job.json if it exists."""
        if not os.path.exists(self.state_file_path):
            return None

        try:
            with open(self.state_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return DailyJobState(**data)
        except Exception as e:
            logger.error(f"Error loading {self.state_file_path}: {e}")
            return None

    def save_job(self, state: DailyJobState) -> None:
        """Atomically saves job state to daily_job.json."""
        state.last_updated = datetime.now().isoformat()
        try:
            with open(self.state_file_path, "w", encoding="utf-8") as f:
                f.write(state.model_dump_json(indent=2))
            logger.info(f"Saved daily job state: {state.status} (Date: {state.date})")
        except Exception as e:
            logger.error(f"Error saving job state to {self.state_file_path}: {e}")

    def get_today_job(self) -> Optional[DailyJobState]:
        """Returns today's existing job if present and matching today's date, else None."""
        existing_job = self.load_job()
        if existing_job and existing_job.date == self.get_today_date_str():
            return existing_job
        return None

    def get_or_create_today_job(self) -> DailyJobState:
        """
        Retrieves today's job. If today's job already exists, returns it.
        If PC was off for missed days (or date changed), creates a fresh PENDING job for today.
        """
        today_str = self.get_today_date_str()
        existing_job = self.load_job()

        if existing_job:
            if existing_job.date == today_str:
                logger.info(f"Loaded today's existing job ({today_str}): Status = {existing_job.status}")
                return existing_job
            else:
                logger.info(
                    f"Previous job date was {existing_job.date}. Creating new job for today ({today_str}) [RUN_LATEST=true]."
                )

        # Create new job for today
        new_job = DailyJobState(
            date=today_str,
            job_id=f"{today_str}-main",
            status=JobStatus.PENDING,
        )
        self.save_job(new_job)
        return new_job

    def reset_job(self) -> DailyJobState:
        """Resets today's job state for testing purposes."""
        today_str = self.get_today_date_str()
        new_job = DailyJobState(
            date=today_str,
            job_id=f"{today_str}-main",
            status=JobStatus.PENDING,
        )
        self.save_job(new_job)
        return new_job
