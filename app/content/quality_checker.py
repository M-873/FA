from typing import Dict, Any, List
from app.ai.base import BaseAIProvider
from app.news.base import NewsItem
from app.utils.logging import logger


class QualityChecker:
    """Pre-publishing quality control and factual consistency verifier."""

    MIN_CONFIDENCE_SCORE = 75

    def __init__(self, ai_provider: BaseAIProvider):
        self.ai_provider = ai_provider

    def verify_content(
        self,
        selected_topic: Dict[str, Any],
        source_items: List[NewsItem],
    ) -> Dict[str, Any]:
        """
        Runs quality check against source items and safety guidelines.
        """
        logger.info("Executing Quality & Fact Consistency Check...")

        # 1. Structural check
        if not selected_topic.get("topic_title") or not selected_topic.get("caption"):
            return {
                "passed": False,
                "reason": "Missing topic title or caption.",
            }

        # 2. Fact check via AI provider
        fact_check_result = self.ai_provider.verify_fact_consistency(
            selected_topic=selected_topic,
            source_items=source_items,
        )

        confidence = fact_check_result.get("confidence_score", 90)
        is_valid = fact_check_result.get("is_valid", True)

        if not is_valid or confidence < self.MIN_CONFIDENCE_SCORE:
            logger.warning(f"Quality check failed! Confidence: {confidence}/100. Reason: {fact_check_result.get('reasoning')}")
            return {
                "passed": False,
                "confidence_score": confidence,
                "reason": fact_check_result.get("reasoning", "Fact verification confidence below threshold."),
            }

        logger.info(f"Quality Check PASSED! Confidence score: {confidence}/100")
        return {
            "passed": True,
            "confidence_score": confidence,
            "reason": "Content verified against sources.",
        }
