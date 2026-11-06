import json
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectConfig:
    """Manages non-sensitive project configuration settings loaded from project_config.json."""

    def __init__(self, config_path: str = "project_config.json"):
        self.config_path = config_path
        self.project_name: str = "Daily 2D Cartoon AI Shorts"
        self.niche: str = "AI Tech & Science Humor"
        self.language: str = "bn"
        self.video_duration: int = 12
        self.aspect_ratio: str = "9:16"
        self.character_style: str = "minimal_flat_vector"
        self.voice_style: str = "expressive_bn"
        self.subtitle_style: str = "yellow_shadow_bold"
        self.music_style: str = "upbeat_lofi_playful"
        self.default_hashtags: List[str] = ["#AICartoon", "#TechShorts", "#Reels", "#Shorts"]
        self.youtube_category_id: str = "24"
        self.content_source: str = "auto"
        self.auto_run_on_start: bool = True
        self.start_with_windows: bool = False
        self.load()

    def load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
            except Exception as e:
                print(f"[WARNING] Failed to load project_config.json: {e}")

    def save(self):
        data = {
            "project_name": self.project_name,
            "niche": self.niche,
            "language": self.language,
            "video_duration": self.video_duration,
            "aspect_ratio": self.aspect_ratio,
            "character_style": self.character_style,
            "voice_style": self.voice_style,
            "subtitle_style": self.subtitle_style,
            "music_style": self.music_style,
            "default_hashtags": self.default_hashtags,
            "youtube_category_id": self.youtube_category_id,
            "content_source": self.content_source,
            "auto_run_on_start": self.auto_run_on_start,
            "start_with_windows": self.start_with_windows,
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


class EnvironmentSettings(BaseSettings):
    """Manages sensitive environment variables loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Primary AI: Gemini
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash", description="Gemini Text Model")

    # Optional AI: OpenAI
    OPENAI_ENABLED: bool = Field(default=False, description="Enable OpenAI fallback")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", description="OpenAI Model")

    # Optional AI: Ollama
    OLLAMA_ENABLED: bool = Field(default=True, description="Enable local / cloud Ollama")
    OLLAMA_API_KEY: str = Field(default="", description="Ollama API Key")
    OLLAMA_API_URL: str = Field(default="http://localhost:11434", description="Ollama API Base URL")

    # Cloud TTS
    TTS_PROVIDER: str = Field(default="gtts", description="Cloud TTS Provider")
    TTS_API_KEY: str = Field(default="", description="TTS API Key if required")
    TTS_VOICE: str = Field(default="bn-BD-Standard-A", description="Voice ID")

    # Meta Graph API (Facebook Page)
    META_ACCESS_TOKEN: str = Field(default="", description="Meta Page Access Token")
    META_PAGE_ID: str = Field(default="", description="Meta Facebook Page ID")
    META_API_VERSION: str = Field(default="v20.0", description="Meta API Version")

    # YouTube Data API (OAuth 2.0)
    YOUTUBE_CLIENT_ID: str = Field(default="", description="YouTube OAuth Client ID")
    YOUTUBE_CLIENT_SECRET: str = Field(default="", description="YouTube OAuth Client Secret")
    YOUTUBE_CHANNEL_ID: str = Field(default="", description="YouTube Channel ID")

    # Stock Video APIs
    PEXELS_API_KEY: str = Field(default="", description="Pexels Video API Key")
    PIXABAY_API_KEY: str = Field(default="", description="Pixabay Video API Key")

    # Content Source Override
    CONTENT_SOURCE_OVERRIDE: Optional[str] = Field(
        default=None,
        description="Manual override for content source: auto, stock_edit, stock_plus_generate, cartoon"
    )

    # Automation Flags
    AUTO_RUN_ON_START: bool = Field(default=True, description="Automatically start job on app launch")
    RUN_LATEST: bool = Field(default=True, description="Run only current video if days were missed")
    DRY_RUN: bool = Field(default=True, description="Dry run mode (do not upload to social platforms)")
    TEST_FACEBOOK: bool = Field(default=False, description="Isolated Facebook test mode")
    TEST_YOUTUBE: bool = Field(default=False, description="Isolated YouTube test mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging verbosity level")

    def get_sanitized_summary(self) -> dict:
        """Returns sanitized dictionary suitable for GUI display and logging."""
        d = self.model_dump()
        secrets = [
            "GEMINI_API_KEY",
            "OPENAI_API_KEY",
            "OLLAMA_API_KEY",
            "TTS_API_KEY",
            "META_ACCESS_TOKEN",
            "YOUTUBE_CLIENT_SECRET",
            "PEXELS_API_KEY",
            "PIXABAY_API_KEY",
        ]
        for key in secrets:
            if key in d and d[key]:
                d[key] = "[REDACTED]"
            else:
                d[key] = "[NOT SET]"
        return d


_project_config_instance: Optional[ProjectConfig] = None
_env_settings_instance: Optional[EnvironmentSettings] = None


def get_project_config() -> ProjectConfig:
    global _project_config_instance
    if _project_config_instance is None:
        _project_config_instance = ProjectConfig()
    return _project_config_instance


def get_env_settings() -> EnvironmentSettings:
    global _env_settings_instance
    if _env_settings_instance is None:
        _env_settings_instance = EnvironmentSettings()
    return _env_settings_instance
