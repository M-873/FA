import os
import json
from app.jobs.manager import DailyJobManager
from app.jobs.state import DailyJobState, JobStatus
from app.utils.config import get_project_config, get_env_settings, ProjectConfig, EnvironmentSettings


def test_project_config_defaults():
    cfg = get_project_config()
    assert cfg.project_name == "Daily 2D Cartoon AI Shorts"
    assert cfg.language == "bn"
    assert cfg.video_duration == 12
    assert cfg.aspect_ratio == "9:16"


def test_env_settings_sanitizer():
    env = EnvironmentSettings(
        GEMINI_API_KEY="AIzaSyTEST_KEY_12345",
        META_ACCESS_TOKEN="EAAGTEST_TOKEN_67890",
    )
    summary = env.get_sanitized_summary()
    assert summary["GEMINI_API_KEY"] == "[REDACTED]"
    assert summary["META_ACCESS_TOKEN"] == "[REDACTED]"


def test_daily_job_manager(tmp_path):
    test_state_file = os.path.join(tmp_path, "test_job.json")
    mgr = DailyJobManager(state_file_path=test_state_file)

    # Get or create job
    job = mgr.get_or_create_today_job()
    assert job.status == JobStatus.PENDING
    assert job.date == mgr.get_today_date_str()
    assert os.path.exists(test_state_file)

    # Update job status and save
    job.update_status(JobStatus.PUBLISHED)
    job.facebook_reel = "SUCCESS"
    job.youtube_status = "SUCCESS"
    mgr.save_job(job)

    # Reload job
    reloaded = mgr.load_job()
    assert reloaded is not None
    assert reloaded.status == JobStatus.PUBLISHED
    assert reloaded.facebook_reel == "SUCCESS"
    assert reloaded.youtube_status == "SUCCESS"
