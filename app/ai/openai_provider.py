import json
from typing import Dict, Any, List
from app.ai.base import BaseAIProvider
from app.utils.config import get_env_settings
from app.utils.logging import logger


class OpenAIProvider(BaseAIProvider):
    """Optional OpenAI provider for cartoon script/topic backup generation."""

    def __init__(self, api_key: str = None, model: str = None):
        env = get_env_settings()
        self.api_key = api_key or env.OPENAI_API_KEY
        self.model = model or env.OPENAI_MODEL
        self.enabled = env.OPENAI_ENABLED

    def generate_topic(self, niche: str, language: str) -> Dict[str, Any]:
        if not self.enabled or not self.api_key:
            logger.info("OpenAI provider is disabled or missing API key.")
            return {}

        try:
            import httpx
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": f"Generate 2D cartoon topic for niche {niche} in language {language}"}],
                "response_format": {"type": "json_object"},
            }
            res = httpx.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
            return json.loads(res.json()["choices"][0]["message"]["content"])
        except Exception as e:
            logger.warning(f"OpenAI topic generation error: {e}")
            return {}

    def generate_script(self, topic: Dict[str, Any], duration: int, language: str) -> Dict[str, Any]:
        return {}

    def generate_scene_plan(self, script: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def generate_metadata(self, topic: Dict[str, Any], script: Dict[str, Any], language: str) -> Dict[str, Any]:
        return {}
