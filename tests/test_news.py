from app.news.base import NewsItem
from app.news.aggregator import NewsAggregator


def test_news_aggregator_deduplication():
    item1 = NewsItem(
        id="1",
        title="OpenAI Releases GPT-5 with Advanced Reasoning Abilities",
        description="Major new AI model announced.",
        source="TechCrunch",
        url="https://techcrunch.com/gpt-5",
    )
    item2 = NewsItem(
        id="2",
        title="OpenAI releases new GPT-5 model with advanced reasoning",
        description="Duplicate article from another source.",
        source="VentureBeat",
        url="https://venturebeat.com/gpt-5",
    )
    item3 = NewsItem(
        id="3",
        title="Google DeepMind Unveils New Quantum AI Chip",
        description="Unrelated story.",
        source="Google Blog",
        url="https://blog.google/quantum",
    )

    class MockProvider:
        def fetch_news(self):
            return [item1, item2, item3]

    aggregator = NewsAggregator([MockProvider()])
    deduped = aggregator.collect_and_deduplicate()

    assert len(deduped) == 2
    titles = [item.title for item in deduped]
    assert "OpenAI Releases GPT-5 with Advanced Reasoning Abilities" in titles
    assert "Google DeepMind Unveils New Quantum AI Chip" in titles
