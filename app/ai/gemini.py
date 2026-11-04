import json
from typing import Dict, Any, List
from google import genai
from google.genai import types

from app.ai.base import BaseAIProvider
from app.utils.config import get_env_settings
from app.utils.logging import logger
from app.utils.retry import with_retry


class GeminiCartoonAIProvider(BaseAIProvider):
    """Primary Cartoon AI Provider leveraging Google Gemini SDK for structured JSON generation."""

    def __init__(self, api_key: str = None, model: str = None):
        env = get_env_settings()
        self.api_key = api_key or env.GEMINI_API_KEY
        self.model_name = model or env.GEMINI_MODEL
        self._client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is missing. Please set it in environment variables or .env file.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @with_retry(max_retries=2)
    def generate_topic(self, niche: str, language: str) -> Dict[str, Any]:
        """Generates candidate daily cartoon topic concept."""
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is missing. Utilizing demonstration cartoon topic concept.")
            return self._fallback_topic()

        prompt = f"""
You are an expert 2D cartoon director for short vertical videos (Facebook Reels & YouTube Shorts).
Target Niche: {niche}
Language: {language}

Task:
Generate ONE humorous, engaging, 10-15 second 2D cartoon video concept.
Important Rules:
1. Do NOT claim anything is "guaranteed viral".
2. Focus on relatable tech/AI humor or interesting science facts.
3. Keep character dialogue fast-paced and punchy.

Return JSON strictly in this format:
{{
  "topic_title": "...",
  "concept_summary": "...",
  "characters": ["cat", "robot"],
  "humor_hook": "...",
  "estimated_duration": 12
}}
"""
        try:
            logger.info(f"Generating cartoon topic via Gemini ('{self.model_name}')...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.7,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini API topic call failed ({e}). Utilizing fallback topic.")
            return self._fallback_topic()

    @with_retry(max_retries=2)
    def generate_script(self, topic: Dict[str, Any], duration: int, language: str) -> Dict[str, Any]:
        """Generates 10-15 second dialogue script."""
        if not self.api_key:
            return self._fallback_script(duration)

        prompt = f"""
Generate a short 2D cartoon script based on this concept:
Title: {topic.get('topic_title')}
Summary: {topic.get('concept_summary')}
Target Duration: {duration} seconds
Language: {language}

Requirements:
- Pacing: Fast (10-15 seconds total).
- 2 main characters.
- Lines must be short, punchy, clear, and easy for TTS voice generation.

Return JSON format:
{{
  "duration": {duration},
  "dialogues": [
    {{
      "id": 1,
      "character": "cat",
      "text": "...",
      "expression": "surprised",
      "action": "jump"
    }},
    {{
      "id": 2,
      "character": "robot",
      "text": "...",
      "expression": "smug",
      "action": "wave"
    }}
  ]
}}
"""
        try:
            logger.info(f"Generating cartoon script via Gemini ('{self.model_name}')...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.5,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini API script call failed ({e}). Utilizing fallback script.")
            return self._fallback_script(duration)

    @with_retry(max_retries=2)
    def generate_scene_plan(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """Generates structured scene breakdown and character action instructions."""
        if not self.api_key:
            return self._fallback_scene_plan()

        dialogues_text = json.dumps(script.get("dialogues", []))
        prompt = f"""
Convert this dialogue script into lightweight 2D character animation instructions:
Script: {dialogues_text}

Instructions for 2D Rigging:
- Supported actions: walk, talk, blink, wave, jump, head_turn.
- Supported mouth states: REST, A, E, I, O, U, M_B_P, S_Z.

Return JSON format:
{{
  "scenes": [
    {{
      "scene_id": 1,
      "duration": 6,
      "background": "cyberpunk_lab",
      "character": "cat",
      "initial_position": [0.3, 0.6],
      "actions": [
        {{"type": "walk", "duration": 2}},
        {{"type": "talk", "duration": 4}}
      ]
    }}
  ]
}}
"""
        try:
            logger.info(f"Generating 2D scene plan via Gemini ('{self.model_name}')...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini API scene plan call failed ({e}). Utilizing fallback scene plan.")
            return self._fallback_scene_plan()

    @with_retry(max_retries=2)
    def generate_metadata(self, topic: Dict[str, Any], script: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Generates title, description, and hashtags for social platforms."""
        if not self.api_key:
            return self._fallback_metadata()

        prompt = f"""
Generate social media post metadata for Facebook Reels and YouTube Shorts.
Topic Title: {topic.get('topic_title')}
Concept: {topic.get('concept_summary')}
Language: {language}

Return JSON format:
{{
  "title": "...",
  "description": "...",
  "hashtags": ["#AICartoon", "#TechShorts", "#BanglaAI", "#Shorts", "#Reels"]
}}
"""
        try:
            logger.info(f"Generating post metadata via Gemini ('{self.model_name}')...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini API metadata call failed ({e}). Utilizing fallback metadata.")
            return self._fallback_metadata()

    def _fallback_topic(self) -> Dict[str, Any]:
        return {
            "topic_title": "AI Robot Tries Fish Curry",
            "concept_summary": "A robot attempts to cook fish curry with surprising results.",
            "characters": ["cat", "robot"],
            "humor_hook": "Robot adds 10x chilli powder.",
            "estimated_duration": 12,
        }

    def _fallback_script(self, duration: int) -> Dict[str, Any]:
        return {
            "duration": duration,
            "dialogues": [
                {
                    "id": 1,
                    "character": "cat",
                    "text": "রোবট ভাই, এআই দিয়ে কি রান্না শেখা সম্ভব?",
                    "expression": "doubtful",
                    "action": "wave",
                },
                {
                    "id": 2,
                    "character": "robot",
                    "text": "অবশ্যই! আমার অ্যালগরিদমে ইলিশ মাছের রেসিপি লোড করা!",
                    "expression": "proud",
                    "action": "jump",
                },
            ],
        }

    def _fallback_scene_plan(self) -> Dict[str, Any]:
        return {
            "scenes": [
                {
                    "scene_id": 1,
                    "duration": 6,
                    "background": "kitchen",
                    "character": "cat",
                    "initial_position": [0.3, 0.6],
                    "actions": [{"type": "talk", "duration": 4}],
                }
            ]
        }

    def _fallback_metadata(self) -> Dict[str, Any]:
        return {
            "title": "রোবটের ইলিশ রান্না 🤖🐟",
            "description": "রোবট যখন প্রথমবার রান্না ঘরে ঢোকে...",
            "hashtags": ["#AICartoon", "#BanglaHumor", "#Reels", "#Shorts"],
        }
