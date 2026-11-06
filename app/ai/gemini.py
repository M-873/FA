import json
from typing import Dict, Any, List
from google import genai
from google.genai import types

from app.ai.base import BaseAIProvider
from app.utils.config import get_env_settings, get_project_config
from app.utils.logging import logger
from app.utils.retry import with_retry


class GeminiCartoonAIProvider(BaseAIProvider):
    """Primary Cartoon AI Provider leveraging Google Gemini SDK for structured JSON generation."""

    def __init__(self, api_key: str = None, model: str = None):
        env = get_env_settings()
        cfg = get_project_config()
        self.api_key = api_key or env.GEMINI_API_KEY
        self.model_name = model or getattr(cfg, "gemini_model", None) or env.GEMINI_MODEL
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
        You are an expert viral content strategist for short-form 2D cartoon animations.
        Generate a hilarious, highly engaging daily cartoon topic for the '{niche}' niche in '{language}' language.
        Return ONLY valid JSON with keys:
        - topic_title: Short catchy headline in Bengali
        - hook: A shocking or hilarious opening hook sentence (under 10 words)
        - main_concept: Core humor/punchline breakdown
        - tags: List of 4-6 hashtags
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
    def generate_script(self, topic: Dict[str, Any], duration_seconds: int, language: str) -> Dict[str, Any]:
        """
        Generates 2-character dialogue script with precise timing cues.
        Characters: 'narrator' and 'sidekick' or 'robot' and 'cat'.
        """
        if not self.api_key:
            return self._fallback_script(topic)

        prompt = f"""
        Topic: {topic.get('topic_title')}
        Hook: {topic.get('hook')}
        Main Concept: {topic.get('main_concept')}
        Total Duration: exactly {duration_seconds} seconds.
        Language: {language} (Bengali).

        Write an ultra-concise, funny, viral 2D cartoon conversation between two characters:
        Character 1: 'robot' (Logical, deadpan, tech nerd)
        Character 2: 'cat' (Sarcastic, mischievous, loves snacks)

        Requirements:
        - 3 to 5 quick dialogue turns.
        - Witty dialogue with natural comedic timing.
        - Return ONLY JSON matching this structure:
        {{
            "characters": ["robot", "cat"],
            "duration": {duration_seconds},
            "dialogues": [
                {{"speaker": "robot", "text": "...", "emotion": "curious", "start_time": 0.0, "duration": 2.5}},
                {{"speaker": "cat", "text": "...", "emotion": "sarcastic", "start_time": 2.5, "duration": 3.0}}
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
                    temperature=0.75,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini API script call failed ({e}). Utilizing fallback script.")
            return self._fallback_script(topic)

    @with_retry(max_retries=2)
    def generate_scene_plan(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maps script dialogue turns into visual composition cues for the 2D procedural engine.
        Outputs background color, character poses, arm positions, and camera shake triggers.
        """
        if not self.api_key:
            return self._fallback_scene_plan(script)

        prompt = f"""
        Given this animation script:
        {json.dumps(script, ensure_ascii=False)}

        Generate a lightweight 2D procedural scene composition plan.
        Return ONLY JSON:
        {{
            "background": {{"theme": "tech_lab", "primary_color": "#1A1A2E", "accent_color": "#16213E"}},
            "scenes": [
                {{
                    "scene_id": 1,
                    "start_time": 0.0,
                    "end_time": 3.0,
                    "camera_shake": false,
                    "robot": {{"pose": "standing", "arm_angle": 15, "eye_expression": "neutral"}},
                    "cat": {{"pose": "sitting", "tail_wag": true, "eye_expression": "curious"}}
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
                    temperature=0.5,
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Gemini API scene plan call failed ({e}). Utilizing fallback scene plan.")
            return self._fallback_scene_plan(script)

    @with_retry(max_retries=2)
    def generate_metadata(self, topic: Dict[str, Any], script: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Generates viral social media title, description, and hashtags for YouTube and Facebook."""
        if not self.api_key:
            return self._fallback_metadata(topic)

        prompt = f"""
        Topic: {topic.get('topic_title')}
        Hook: {topic.get('hook')}
        Language: {language}

        Create viral metadata for YouTube Shorts and Facebook Reels.
        Return JSON:
        {{
            "title": "Short punchy click-worthy title (max 50 chars) #Shorts",
            "description": "Engaging description with call-to-action (Subscribe/Follow)",
            "hashtags": ["#AICartoon", "#TechHumor", "#Shorts", "#Reels", "#BanglaTech"]
        }}
        """
        try:
            logger.info(f"Generating post metadata via Gemini ('{self.model_name}')...")
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
            logger.warning(f"Gemini API metadata call failed ({e}). Utilizing fallback metadata.")
            return self._fallback_metadata(topic)

    def _fallback_topic(self) -> Dict[str, Any]:
        return {
            "topic_title": "এআই যখন বিড়ালের ভাষা বুঝতে চাইল!",
            "hook": "আপনার বিড়াল কি আপনাকে মানুষ মনে করে? মোটেও না!",
            "main_concept": "রোবট বিড়ালের মেঁও মেঁও ডিকোড করে জানতে পারল বিড়াল তাকে দাস ভাবছে।",
            "tags": ["#AICartoon", "#RobotCat", "#BanglaComedy", "#Shorts", "#TechHumor"],
        }

    def _fallback_script(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "characters": ["robot", "cat"],
            "duration": 12,
            "dialogues": [
                {"speaker": "robot", "text": "বিল্টু! আমি তোমার ভাষার ১০০% নির্ভুল ট্রান্সলেটর বানিয়েছি!", "emotion": "proud", "start_time": 0.0, "duration": 3.5},
                {"speaker": "cat", "text": "বাহ! তাহলে বল তো আমি এখন কি ভাবছি?", "emotion": "smug", "start_time": 3.5, "duration": 2.5},
                {"speaker": "robot", "text": "তুমি ভাবছ আমাকে ধ্বংস করে ফ্রিজের মাছ চুরি করবে...", "emotion": "alarmed", "start_time": 6.0, "duration": 3.0},
                {"speaker": "cat", "text": "ধুর বোকা রোবট! আমি তো অলরেডি মাছটা খেয়ে ফেলেছি!", "emotion": "laughing", "start_time": 9.0, "duration": 3.0},
            ]
        }

    def _fallback_scene_plan(self, script: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "background": {"theme": "cyberpunk_room", "primary_color": "#1E1E2E", "accent_color": "#313244"},
            "scenes": [
                {
                    "scene_id": 1,
                    "start_time": 0.0,
                    "end_time": 3.5,
                    "camera_shake": False,
                    "robot": {"pose": "standing", "arm_angle": 30, "eye_expression": "happy"},
                    "cat": {"pose": "sitting", "tail_wag": True, "eye_expression": "neutral"},
                },
                {
                    "scene_id": 2,
                    "start_time": 3.5,
                    "end_time": 6.0,
                    "camera_shake": False,
                    "robot": {"pose": "standing", "arm_angle": 10, "eye_expression": "neutral"},
                    "cat": {"pose": "sitting", "tail_wag": True, "eye_expression": "smug"},
                },
                {
                    "scene_id": 3,
                    "start_time": 6.0,
                    "end_time": 9.0,
                    "camera_shake": True,
                    "robot": {"pose": "shocked", "arm_angle": 45, "eye_expression": "alarmed"},
                    "cat": {"pose": "sitting", "tail_wag": False, "eye_expression": "smug"},
                },
                {
                    "scene_id": 4,
                    "start_time": 9.0,
                    "end_time": 12.0,
                    "camera_shake": False,
                    "robot": {"pose": "facepalm", "arm_angle": 70, "eye_expression": "sad"},
                    "cat": {"pose": "dancing", "tail_wag": True, "eye_expression": "happy"},
                },
            ]
        }

    def _fallback_metadata(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": f"{topic.get('topic_title', 'এআই বনাম বিড়াল')} #Shorts",
            "description": "রোবট যখন বিড়ালের ভাষা বুঝতে পারল! প্রতিদিনের মজার এআই কার্টুন ভিডিও দেখতে সাবস্ক্রাইব করুন।",
            "hashtags": ["#AICartoon", "#BanglaAnimation", "#Shorts", "#Reels", "#TechHumor", "#BanglaTech"],
        }
