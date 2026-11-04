from app.content.scoring import TopicScorer
from app.content.caption_generator import CaptionGenerator
from app.content.quality_checker import QualityChecker


def test_topic_scoring():
    res = TopicScorer.calculate_topic_score(
        freshness=95,
        importance=90,
        audience_relevance=92,
        source_strength=90,
        trend_signals=85,
        visual_potential=95,
    )
    assert res["score"] > 85
    assert res["classification"] == "HIGH_POTENTIAL_TRENDING"
    assert "viral" not in res["disclaimer"].lower()


def test_caption_formatting():
    raw_caption = "🚀 OpenAI has introduced a groundbreaking new model!"
    tags = ["#AI", "#Tech", "BengaliAI"]
    caption = CaptionGenerator.format_caption(raw_caption, tags, content_language="bn")

    assert "OpenAI has introduced" in caption
    assert "#AI" in caption
    assert "#BengaliAI" in caption


def test_quality_checker_pass():
    class MockAIProvider:
        def verify_fact_consistency(self, selected_topic, source_items):
            return {"is_valid": True, "confidence_score": 95, "reasoning": "Supported by sources"}

    checker = QualityChecker(MockAIProvider())
    selected_topic = {
        "topic_title": "GPT-5 Released",
        "caption": "OpenAI released GPT-5.",
    }
    res = checker.verify_content(selected_topic, [])
    assert res["passed"] is True
    assert res["confidence_score"] == 95
