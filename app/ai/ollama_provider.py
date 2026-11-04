import json
import httpx
from typing import Dict, Any
from app.ai.base import BaseAIProvider
from app.ai.ollama_manager import OllamaHardwareManager
from app.utils.logging import logger
from app.utils.retry import with_retry


class OllamaCartoonAIProvider(BaseAIProvider):
    """
    Local Offline 2D Cartoon AI Script Provider powered by Ollama.
    Used automatically on high-performance GPUs with >= 6GB VRAM.
    """

    def __init__(self, model: str = OllamaHardwareManager.DEFAULT_MODEL):
        self.model = model
        from app.utils.config import get_env_settings
        self.env = get_env_settings()
        self.api_url = f"{self.env.OLLAMA_API_URL or OllamaHardwareManager.OLLAMA_API_URL}/api/generate"

    @with_retry(max_retries=2)
    def _call_ollama_json(self, prompt: str) -> Dict[str, Any]:
        """Queries local or cloud Ollama instance with JSON format enforcement and API key auth."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.7,
            }
        }
        headers = {}
        if self.env.OLLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {self.env.OLLAMA_API_KEY}"

        res = httpx.post(self.api_url, json=payload, headers=headers, timeout=60.0)
        res.raise_for_status()
        raw_text = res.json().get("response", "{}")
        return json.loads(raw_text)

    def generate_topic(self, niche: str, language: str) -> Dict[str, Any]:
        prompt = f"""
        Generate 1 funny viral 2D cartoon video topic in {language} about {niche}.
        Return ONLY valid JSON with keys:
        - "topic_title": string
        - "characters": list of 2 character names (e.g. ["cat", "robot"])
        - "hook": string
        """
        try:
            return self._call_ollama_json(prompt)
        except Exception as e:
            logger.warning(f"Ollama topic generation failed: {e}. Using fallback.")
            return {
                "topic_title": "AI Coding Assistant Chaos",
                "characters": ["cat", "robot"],
                "hook": "When your AI writes 10,000 lines of code in 1 second"
            }

    def generate_script(self, topic: Dict[str, Any], duration: int, language: str) -> Dict[str, Any]:
        prompt = f"""
        Write a funny {duration}-second dialogue between 2 characters for a 2D cartoon in {language}.
        Topic: {topic.get('topic_title', '')}
        Return ONLY valid JSON with keys:
        - "duration": {duration}
        - "dialogues": [
            {{"character": "cat", "text": "...", "duration": 6}},
            {{"character": "robot", "text": "...", "duration": 6}}
          ]
        """
        try:
            return self._call_ollama_json(prompt)
        except Exception as e:
            logger.warning(f"Ollama script generation failed: {e}. Using fallback.")
            return {
                "duration": duration,
                "dialogues": [
                    {"character": "cat", "text": "রোবট ভাই, এআই কি সত্যি প্রোগ্রামারদের চাকরি খেয়ে নেবে?", "duration": 6},
                    {"character": "robot", "text": "চাকরি খাবে না ভাই, তবে বাগ ফিক্স করতে করতে কফি বেশি খাওয়া লাগবে!", "duration": 6}
                ]
            }

    def generate_scene_plan(self, script: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "scenes": [
                {"scene_id": 1, "duration": 6, "character": "cat", "action": "talk"},
                {"scene_id": 2, "duration": 6, "character": "robot", "action": "laugh"}
            ]
        }

    def generate_metadata(self, topic: Dict[str, Any], script: Dict[str, Any], language: str) -> Dict[str, Any]:
        return {
            "title": f"{topic.get('topic_title', 'AI Cartoon')} 🤖",
            "description": "Daily 2D Cartoon AI Short.",
            "hashtags": ["#AICartoon", "#TechShorts", "#Reels", "#Shorts"]
        }
