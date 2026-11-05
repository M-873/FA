import os
from PIL import Image
from app.animation.actions import CharacterTransform, VisemeMouthState
from app.animation.rig import CartoonCharacterRig
from app.animation.lip_sync import VisemeLipSyncGenerator
from app.animation.subtitles import SubtitleOverlayGenerator
from app.animation.engine import CartoonAnimationEngine
from app.hardware.profiles import RenderSettings
from app.jobs.recovery import DailyCartoonAutomationPipeline
from app.utils.config import get_env_settings


def test_character_rig_rendering():
    rig = CartoonCharacterRig("cat", width=300, height=400)
    transform = CharacterTransform(mouth_state=VisemeMouthState.A, arm_angle=20)
    frame = rig.render_frame(transform)
    assert isinstance(frame, Image.Image)
    assert frame.size == (300, 400)


def test_viseme_lip_sync():
    timeline = VisemeLipSyncGenerator.generate_viseme_timeline("হ্যালো এআই রোবট", total_duration_sec=4.0, fps=24)
    assert len(timeline) == 96  # 4 seconds * 24 fps
    assert VisemeMouthState.A in timeline or VisemeMouthState.E in timeline


def test_subtitle_overlay():
    img = Image.new("RGB", (720, 1280), color=(0, 0, 0))
    result = SubtitleOverlayGenerator.overlay_subtitles(img, "হ্যালো বন্ধুরা!")
    assert isinstance(result, Image.Image)


def test_animation_engine(tmp_path):
    settings = RenderSettings(resolution_width=360, resolution_height=640, fps=10, max_duration_seconds=2)
    engine = CartoonAnimationEngine(settings)
    script = {
        "duration": 2,
        "dialogues": [
            {"text": "Hello Robot"},
            {"text": "Hello Cat"},
        ],
    }
    frames_dir = os.path.join(tmp_path, "test_frames")
    frame_files = engine.render_scene_frames(script, {}, frames_dir)
    assert len(frame_files) == 20  # 2 seconds * 10 fps
    assert os.path.exists(frame_files[0])


def test_end_to_end_pipeline_dry_run(tmp_path):
    from unittest.mock import patch
    from app.ai.ollama_manager import OllamaHardwareManager

    env = get_env_settings()
    env.DRY_RUN = True

    with patch.object(OllamaHardwareManager, "is_ollama_running", return_value=False), \
         patch.object(OllamaHardwareManager, "auto_install_ollama_if_needed", return_value=False):
        pipeline = DailyCartoonAutomationPipeline()
        res = pipeline.run_daily_pipeline()

        assert "success" in res
        assert res["success"] is True
    assert res["job_status"] in ("PUBLISHED", "PARTIALLY_PUBLISHED")
