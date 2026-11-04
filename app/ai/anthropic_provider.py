import json
from typing import Dict, Any, List
from app.ai.base import BaseAIProvider
from app.news.base import NewsItem
from app.utils.config import get_settings
from app.utils.logging import logger


class AnthropicProvider(BaseAIProvider):
    """Optional Anthropic Claude provider for backup analysis or second opinion."""

    def __init__(self, api_key: str = None, model: str = None):
        settings = get_settings()
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self.enabled = settings.ANTHROPIC_ENABLED

    def analyze_topics_and_select_best(
        self,
        news_items: List[NewsItem],
        content_type: str = "image",
        language: str = "bn",
    ) -> Dict[str, Any]:
        if not self.enabled or not self.api_key:
            logger.info("Anthropic provider is disabled or missing API key.")
            return {}

        try:
            import httpx
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            prompt = f"Analyze AI news for {content_type} post in {language}: " + json.dumps([i.title for i in news_items[:5]])
            payload = {
                "model": self.model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            }
            response = httpx.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            content = response.json()["content"][0]["text"]
            return {"raw_claude_response": content}
        except Exception as e:
            logger.warning(f"Anthropic API call failed: {e}")
            return {}

    def verify_fact_consistency(
        self,
        selected_topic: Dict[str, Any],
        source_items: List[NewsItem],
    ) -> Dict[str, Any]:
        return {"is_valid": True, "verdict": "PASSED"}
