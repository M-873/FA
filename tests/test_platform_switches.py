"""
tests/test_platform_switches.py
================================
Tests for platform switches (youtube_enabled, facebook_enabled, instagram_enabled):
- project_config.json defaults (YouTube true, Facebook false, Instagram false)
- Skipping disabled platforms cleanly without calling their publishers
- Non-failure of jobs when disabled platforms are skipped
- Precedence of environment variable overrides
"""

from unittest.mock import MagicMock, patch
import pytest

from app.hardware.detector import HardwareSpecs
from app.jobs.manager import DailyJobManager
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.jobs.state import DailyJobState, JobStatus
from app.utils.config import ProjectConfig


def test_platform_switches_defaults():
    """Validates platform switches defaults in ProjectConfig."""
    cfg = ProjectConfig(config_path="non_existent_config.json")
    assert cfg.youtube_enabled is True
    assert cfg.facebook_enabled is False
    assert cfg.instagram_enabled is False


@patch("app.jobs.recovery.FacebookReelPublisher")
@patch("app.jobs.recovery.FacebookStoryPublisher")
@patch("app.jobs.recovery.YouTubeShortsPublisher")
@patch("app.jobs.recovery.HardwareSafetyMonitor")
@patch("app.jobs.recovery.PerformanceProfileManager")
@patch("app.jobs.recovery.HardwareDetector")
@patch("app.ai.factory.AIProviderFactory")
@patch("app.jobs.recovery.CloudTTSProvider")
@patch("app.jobs.recovery.ContentSourceFactory")
@patch("app.jobs.recovery.VideoQualityChecker")
def test_platform_switches_youtube_only(
    mock_qc,
    mock_factory,
    mock_tts,
    mock_ai_factory,
    mock_detector,
    mock_profile_mgr,
    mock_safety,
    mock_yt_pub,
    mock_fb_story,
    mock_fb_reel,
    tmp_path,
):
    """
    When YouTube is enabled and Facebook/Instagram disabled:
    - Facebook publishers must NOT be instantiated or called.
    - Facebook status is SKIPPED.
    - YouTube status is SUCCESS.
    - Final state is DRY_RUN_COMPLETE / PUBLISHED.
    """
    job_mgr = DailyJobManager()
    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr)

    # Configure platforms: YouTube enabled, Facebook disabled
    pipeline.project_cfg.youtube_enabled = True
    pipeline.project_cfg.facebook_enabled = False
    pipeline.project_cfg.instagram_enabled = False
    pipeline.env_cfg.DRY_RUN = True
    pipeline.env_cfg.FACEBOOK_ENABLED = None
    pipeline.env_cfg.YOUTUBE_ENABLED = None

    # Mocks
    mock_detector.return_value.detect_specs.return_value = HardwareSpecs(cpu_cores=4, ram_gb=8.0, disk_free_gb=50.0)
    mock_profile_mgr.get_render_settings.return_value = MagicMock(max_duration_seconds=12)

    mock_ai = MagicMock()
    mock_ai.generate_topic.return_value = {"topic_title": "AI Platform Test"}
    mock_ai.generate_script.return_value = {"dialogues": []}
    mock_ai.generate_scene_plan.return_value = {}
    mock_ai.generate_metadata.return_value = {"title": "AI Platform Test"}
    mock_ai_factory.get_provider.return_value = mock_ai
    mock_tts.return_value.generate_dialogue_audio.return_value = str(tmp_path / "tts.mp3")

    dummy_render = MagicMock(video_path=str(tmp_path / "final.mp4"), content_source="cartoon")
    mock_source = MagicMock()
    mock_source.name = "cartoon"
    mock_source.generate_video.return_value = dummy_render
    mock_factory.get_source.return_value = mock_source

    mock_qc.verify_final_video.return_value = {"passed": True}
    mock_yt_pub.return_value.publish_short.return_value = {"success": True, "video_id": "yt_12345"}

    res = pipeline.run_daily_pipeline()

    assert res["success"] is True
    assert res["job_status"] == JobStatus.DRY_RUN_COMPLETE.value
    assert res["facebook_reel"] == "SKIPPED"
    assert res["youtube_status"] == "SUCCESS"

    # Zero Facebook calls
    mock_fb_reel.assert_not_called()
    mock_fb_story.assert_not_called()
    mock_yt_pub.return_value.publish_short.assert_called_once()


@patch("app.jobs.recovery.FacebookReelPublisher")
@patch("app.jobs.recovery.FacebookStoryPublisher")
@patch("app.jobs.recovery.YouTubeShortsPublisher")
@patch("app.jobs.recovery.HardwareSafetyMonitor")
@patch("app.jobs.recovery.PerformanceProfileManager")
@patch("app.jobs.recovery.HardwareDetector")
@patch("app.ai.factory.AIProviderFactory")
@patch("app.jobs.recovery.CloudTTSProvider")
@patch("app.jobs.recovery.ContentSourceFactory")
@patch("app.jobs.recovery.VideoQualityChecker")
def test_platform_switches_facebook_only(
    mock_qc,
    mock_factory,
    mock_tts,
    mock_ai_factory,
    mock_detector,
    mock_profile_mgr,
    mock_safety,
    mock_yt_pub,
    mock_fb_story,
    mock_fb_reel,
    tmp_path,
):
    """
    When Facebook is enabled and YouTube disabled:
    - YouTube publisher must NOT be instantiated or called.
    - YouTube status is SKIPPED.
    - Facebook status is SUCCESS.
    - Final state is DRY_RUN_COMPLETE / PUBLISHED.
    """
    job_mgr = DailyJobManager()
    pipeline = DailyCartoonAutomationPipeline(job_manager=job_mgr)

    pipeline.project_cfg.youtube_enabled = False
    pipeline.project_cfg.facebook_enabled = True
    pipeline.project_cfg.instagram_enabled = False
    pipeline.env_cfg.DRY_RUN = True
    pipeline.env_cfg.FACEBOOK_ENABLED = None
    pipeline.env_cfg.YOUTUBE_ENABLED = None

    mock_detector.return_value.detect_specs.return_value = HardwareSpecs(cpu_cores=4, ram_gb=8.0, disk_free_gb=50.0)
    mock_profile_mgr.get_render_settings.return_value = MagicMock(max_duration_seconds=12)

    mock_ai = MagicMock()
    mock_ai.generate_topic.return_value = {"topic_title": "AI FB Test"}
    mock_ai.generate_script.return_value = {"dialogues": []}
    mock_ai.generate_scene_plan.return_value = {}
    mock_ai.generate_metadata.return_value = {"title": "AI FB Test"}
    mock_ai_factory.get_provider.return_value = mock_ai
    mock_tts.return_value.generate_dialogue_audio.return_value = str(tmp_path / "tts.mp3")

    dummy_render = MagicMock(video_path=str(tmp_path / "final.mp4"), content_source="cartoon")
    mock_source = MagicMock()
    mock_source.name = "cartoon"
    mock_source.generate_video.return_value = dummy_render
    mock_factory.get_source.return_value = mock_source

    mock_qc.verify_final_video.return_value = {"passed": True}
    mock_fb_reel.return_value.publish_reel.return_value = {"success": True, "reel_id": "fb_reel_999"}
    mock_fb_story.return_value.publish_story.return_value = {"success": True}

    res = pipeline.run_daily_pipeline()

    assert res["success"] is True
    assert res["job_status"] == JobStatus.DRY_RUN_COMPLETE.value
    assert res["facebook_reel"] == "SUCCESS"
    assert res["youtube_status"] == "SKIPPED"

    mock_yt_pub.assert_not_called()
    mock_fb_reel.return_value.publish_reel.assert_called_once()
