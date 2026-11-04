from app.utils.config import get_env_settings, EnvironmentSettings, get_project_config


def test_project_config():
    pcfg = get_project_config()
    assert pcfg.video_duration == 12
    assert pcfg.aspect_ratio == "9:16"


def test_env_settings_sanitizer():
    env = EnvironmentSettings(
        GEMINI_API_KEY="AIzaSySECRET_KEY_12345",
        META_ACCESS_TOKEN="EAAGSECRET_TOKEN_67890",
    )
    sanitized = env.get_sanitized_summary()
    assert sanitized["GEMINI_API_KEY"] == "[REDACTED]"
    assert sanitized["META_ACCESS_TOKEN"] == "[REDACTED]"
