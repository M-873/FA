import hashlib
import time
from datetime import datetime
from typing import List
import feedparser
from app.news.base import BaseNewsProvider, NewsItem
from app.utils.logging import logger


class RSSNewsProvider(BaseNewsProvider):
    """RSS / Atom feed news provider."""

    def __init__(self, feed_urls: List[str]):
        self.feed_urls = feed_urls

    def fetch_news(self) -> List[NewsItem]:
        items: List[NewsItem] = []
        for url in self.feed_urls:
            try:
                logger.info(f"Fetching RSS feed from: {url}")
                feed = feedparser.parse(url)
                source_title = feed.feed.get("title", url.split("/")[2])

                for entry in feed.entries[:10]:  # Limit top 10 items per feed
                    title = entry.get("title", "").strip()
                    if not title:
                        continue

                    link = entry.get("link", "")
                    summary = entry.get("summary", entry.get("description", "")).strip()

                    # Parse pubdate
                    pub_dt = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        pub_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                        pub_dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed))

                    # Deduplication ID generator
                    item_id = hashlib.md5(f"{title.lower()}_{link}".encode("utf-8")).hexdigest()

                    item = NewsItem(
                        id=item_id,
                        title=title,
                        description=summary[:500],  # Trim long snippets
                        source=source_title,
                        url=link,
                        published_at=pub_dt,
                        category="AI News",
                        raw_content=summary,
                    )
                    items.append(item)

            except Exception as e:
                logger.warning(f"Failed to fetch or parse RSS feed {url}: {e}")
                # Continue with other feeds if one fails
                continue

        logger.info(f"Fetched total {len(items)} news items from RSS feeds.")
        return items
