import argparse
import sys
from app.jobs.manager import DailyJobManager
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import JobStatus
from app.ui.main_window import launch_gui
from app.utils.config import get_project_config, get_env_settings
from app.utils.logging import logger


def run_pipeline_job():
    """Triggers end-to-end daily cartoon video pipeline."""
    pipeline = DailyCartoonAutomationPipeline()
    return pipeline.run_daily_pipeline()


def main():
    parser = argparse.ArgumentParser(description="Lightweight 2D Cartoon Daily Video Automation System")
    parser.add_argument("--cli", action="store_true", help="Run end-to-end automation in headless CLI mode")
    parser.add_argument("--gui", action="store_true", help="Launch Windows Tkinter GUI mode")
    parser.add_argument("--reset-job", action="store_true", help="Reset today's job state to PENDING")
    parser.add_argument("--dry-run", action="store_true", help="Enable dry run mode (do not upload)")
    parser.add_argument("--approve", action="store_true", help="Approve today's rendered video and resume publishing")
    parser.add_argument("--reject", action="store_true", help="Reject today's rendered video and reset state")
    parser.add_argument("--regenerate", action="store_true", help="Reject today's rendered video and regenerate immediately")

    args = parser.parse_args()
    env_cfg = get_env_settings()

    if args.dry_run:
        env_cfg.DRY_RUN = True
        logger.info("DRY_RUN mode enabled.")

    if args.reset_job:
        job_mgr = DailyJobManager()
        job_mgr.reset_job()
        logger.info("Today's job state reset to PENDING.")
        return

    if args.approve:
        logger.info("Received --approve CLI command. Resuming publishing...")
        pipeline = DailyCartoonAutomationPipeline()
        res = pipeline.approve_job()
        logger.info(f"Approve result: {res}")
        return

    if args.regenerate:
        logger.info("Received --regenerate CLI command. Resetting and re-running...")
        pipeline = DailyCartoonAutomationPipeline()
        res = pipeline.reject_job(regenerate=True)
        logger.info(f"Regenerate result: {res}")
        return

    if args.reject:
        logger.info("Received --reject CLI command. Resetting today's job...")
        pipeline = DailyCartoonAutomationPipeline()
        res = pipeline.reject_job(regenerate=False)
        logger.info(f"Reject result: {res}")
        return

    if args.cli:
        logger.info("Executing pipeline in CLI mode...")
        run_pipeline_job()
    else:
        logger.info("Launching Phase 1 Desktop Dashboard...")
        launch_gui()


if __name__ == "__main__":
    main()
