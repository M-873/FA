from typing import List, Dict, Any
from app.ai.base import BaseAIProvider
from app.content.scoring import TopicScorer
from app.news.base import NewsItem
from app.utils.logging import logger


class TopicSelector:
    """Orchestrates topic analysis and selection from deduplicated news items."""

    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider

    def select_best_topic(
        self,
        news_items: List[NewsItem],
        content_type: str = "image",
        language: str = "bn",
    ) -> Dict[str, Any]:
        """
        Analyzes news items, selects best topic, and computes score breakdown.
        """
        if not news_items:
            raise ValueError("Cannot select topic from empty news items list.")

        logger.info(f"Analyzing {len(news_items)} news items for best {content_type} topic...")
        result = self.ai_provider.analyze_topics_and_select_best(
            news_items=news_items,
            content_type=content_type,
            language=language,
        )

        # Enhance with explicit internal scoring disclaimer
        breakdown = result.get("score_breakdown", {})
        computed = TopicScorer.calculate_topic_score(
            freshness=breakdown.get("freshness", 85),
            importance=breakdown.get("importance", 85),
            audience_relevance=breakdown.get("audience_interest", 85),
            source_strength=breakdown.get("source_credibility", 85),
            trend_signals=breakdown.get("trend_signals", 80),
            visual_potential=breakdown.get("visual_potential", 85),
        )

        result["internal_score_analysis"] = computed
        return result
