from typing import List
from app.news.base import BaseNewsProvider, NewsItem
from app.news.rss import RSSNewsProvider


class OfficialBlogNewsProvider(BaseNewsProvider):
    """News provider for official tech company blogs and announcements."""

    OFFICIAL_FEEDS = [
        "https://openai.com/news/rss.xml",
        "https://blog.google/technology/ai/rss/",
        "https://ai.meta.com/blog/rss/",
    ]

    def __init__(self, additional_feeds: List[str] = None):
        feeds = list(self.OFFICIAL_FEEDS)
        if additional_feeds:
            feeds.extend(additional_feeds)
        self.rss_provider = RSSNewsProvider(feeds)

    def fetch_news(self) -> List[NewsItem]:
        items = self.rss_provider.fetch_news()
        for item in items:
            item.category = "Official Announcement"
        return items
