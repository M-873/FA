import re
from typing import List, Dict
from app.news.base import BaseNewsProvider, NewsItem
from app.utils.logging import logger


class NewsAggregator:
    """Aggregates, normalizes, and deduplicates news items from multiple providers."""

    def __init__(self, providers: List[BaseNewsProvider]):
        self.providers = providers

    def _normalize_title(self, title: str) -> str:
        """Removes punctuation and normalizes title for fuzzy matching."""
        clean = re.sub(r"[^\w\s]", "", title.lower())
        return " ".join(clean.split())

    def _compute_similarity(self, title1: str, title2: str) -> float:
        """Simple Jaccard word set similarity coefficient."""
        words1 = set(self._normalize_title(title1).split())
        words2 = set(self._normalize_title(title2).split())
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union)

    def collect_and_deduplicate(self) -> List[NewsItem]:
        """Collects news from all providers and deduplicates similar stories."""
        raw_items: List[NewsItem] = []
        for provider in self.providers:
            try:
                fetched = provider.fetch_news()
                raw_items.extend(fetched)
            except Exception as e:
                logger.error(f"Provider {provider.__class__.__name__} failed: {e}")

        logger.info(f"Collected total {len(raw_items)} raw news items across all providers.")

        # Deduplicate
        unique_items: List[NewsItem] = []
        for item in raw_items:
            is_duplicate = False
            for existing in unique_items:
                similarity = self._compute_similarity(item.title, existing.title)
                if similarity > 0.5:  # 50%+ overlapping key terms
                    is_duplicate = True
                    # Append source to existing item if not present
                    if item.source not in existing.source:
                        existing.source += f", {item.source}"
                    break

            if not is_duplicate:
                unique_items.append(item)

        logger.info(f"Deduplication complete. Retained {len(unique_items)} unique news stories.")
        return unique_items
