from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """Normalized AI News Item data structure."""

    id: str = Field(description="Unique identifier for deduplication")
    title: str = Field(description="Headline / Title of news item")
    description: str = Field(default="", description="Summary or snippet of content")
    source: str = Field(description="Name of publishing source")
    url: str = Field(description="Original URL link")
    published_at: Optional[datetime] = Field(default=None, description="Publication timestamp")
    category: str = Field(default="AI", description="General category tag")
    raw_content: str = Field(default="", description="Full text snippet if available")


class BaseNewsProvider(ABC):
    """Abstract Base Class for News Providers."""

    @abstractmethod
    def fetch_news(self) -> List[NewsItem]:
        """Fetches and returns normalized list of news items."""
        pass
