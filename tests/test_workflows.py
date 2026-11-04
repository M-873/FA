from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.utils.config import get_env_settings


def test_cartoon_workflow_dry_run():
    env = get_env_settings()
    env.DRY_RUN = True

    pipeline = DailyCartoonAutomationPipeline()
    res = pipeline.run_daily_pipeline()

    assert "success" in res
    assert res["success"] is True
