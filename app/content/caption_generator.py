from typing import List, Dict, Any


class CaptionGenerator:
    """Formats natural Facebook post captions and hashtag sets."""

    @classmethod
    def format_caption(
        self,
        raw_caption: str,
        hashtags: List[str],
        content_language: str = "bn",
    ) -> str:
        """Ensures caption structure is engaging, accurate, and properly formatted with hashtags."""
        clean_caption = raw_caption.strip()

        # Format hashtags
        formatted_tags = []
        for tag in hashtags:
            clean_tag = tag.strip()
            if not clean_tag.startswith("#"):
                clean_tag = f"#{clean_tag}"
            formatted_tags.append(clean_tag)

        # Default fallback tags if missing
        if not formatted_tags:
            formatted_tags = ["#AI", "#ArtificialIntelligence", "#TechNews", "#GenerativeAI"]

        tags_string = " ".join(formatted_tags)

        if tags_string not in clean_caption:
            full_post = f"{clean_caption}\n\n{tags_string}"
        else:
            full_post = clean_caption

        return full_post
