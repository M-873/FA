"""
News providers and aggregation system.
"""
from app.news.base import NewsItem, BaseNewsProvider
from app.news.rss import RSSNewsProvider
from app.news.official_sources import OfficialBlogNewsProvider
from app.news.aggregator import NewsAggregator

__all__ = [
    "NewsItem",
    "BaseNewsProvider",
    "RSSNewsProvider",
    "OfficialBlogNewsProvider",
    "NewsAggregator",
]
