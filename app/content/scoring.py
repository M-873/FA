from typing import Dict, Any


class TopicScorer:
    """Calculates internal AI topic potential scores without claiming guaranteed virality."""

    WEIGHT_FRESHNESS = 0.25
    WEIGHT_IMPORTANCE = 0.20
    WEIGHT_AUDIENCE_RELEVANCE = 0.20
    WEIGHT_SOURCE_STRENGTH = 0.15
    WEIGHT_TREND_SIGNALS = 0.10
    WEIGHT_VISUAL_POTENTIAL = 0.10

    @classmethod
    def calculate_topic_score(
        self,
        freshness: float,
        importance: float,
        audience_relevance: float,
        source_strength: float,
        trend_signals: float,
        visual_potential: float,
    ) -> Dict[str, Any]:
        """Calculates final composite score (0-100) and classification label."""

        composite_score = round(
            (freshness * self.WEIGHT_FRESHNESS)
            + (importance * self.WEIGHT_IMPORTANCE)
            + (audience_relevance * self.WEIGHT_AUDIENCE_RELEVANCE)
            + (source_strength * self.WEIGHT_SOURCE_STRENGTH)
            + (trend_signals * self.WEIGHT_TREND_SIGNALS)
            + (visual_potential * self.WEIGHT_VISUAL_POTENTIAL),
            2,
        )

        if composite_score >= 85:
            classification = "HIGH_POTENTIAL_TRENDING"
        elif composite_score >= 70:
            classification = "STRONG_INTEREST"
        else:
            classification = "MODERATE_POTENTIAL"

        return {
            "score": composite_score,
            "classification": classification,
            "disclaimer": "Internal AI content score. Does NOT guarantee post reach or performance.",
            "metrics": {
                "freshness": freshness,
                "importance": importance,
                "audience_relevance": audience_relevance,
                "source_strength": source_strength,
                "trend_signals": trend_signals,
                "visual_potential": visual_potential,
            },
        }

