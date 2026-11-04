import os
from typing import Dict, Any
from app.ai.gemini import GeminiProvider
from app.content.caption_generator import CaptionGenerator
from app.content.quality_checker import QualityChecker
from app.content.topic_selector import TopicSelector
from app.facebook.feed import FacebookFeedPublisher
from app.facebook.stories import FacebookStoryPublisher
from app.image.generator import GeminiImageGenerator
from app.news.aggregator import NewsAggregator
from app.news.official_sources import OfficialBlogNewsProvider
from app.news.rss import RSSNewsProvider
from app.utils.cleanup import TempFileManager
from app.utils.config import get_settings
from app.utils.logging import logger


class DailyWorkflow:
    """Executes the automated Daily Image Post workflow."""

    def __init__(self):
        self.settings = get_settings()

    def run(self) -> Dict[str, Any]:
        """
        Main entry point for daily automated workflow.
        """
        logger.info("==================================================")
        logger.info("STARTING DAILY AUTOMATED CONTENT WORKFLOW")
        logger.info("==================================================")

        with TempFileManager(prefix="daily_post_") as temp_mgr:
            # 1. Collect & Normalize AI News
            logger.info("STEP 1: Collecting AI news from configured RSS feeds & official blogs...")
            rss_provider = RSSNewsProvider(self.settings.RSS_FEED_URLS)
            official_provider = OfficialBlogNewsProvider()
            aggregator = NewsAggregator([rss_provider, official_provider])

            news_items = aggregator.collect_and_deduplicate()
            if not news_items:
                logger.error("No news items collected. Aborting daily workflow.")
                return {"success": False, "reason": "No news collected"}

            # 2. AI Topic Analysis & Selection
            logger.info("STEP 2: Selecting best daily AI topic using Gemini...")
            ai_provider = GeminiProvider()
            selector = TopicSelector(ai_provider)

            topic_data = selector.select_best_topic(
                news_items=news_items,
                content_type="image",
                language=self.settings.CONTENT_LANGUAGE,
            )

            # 3. Quality & Fact Consistency Verification
            logger.info("STEP 3: Running Pre-Publishing Quality & Fact Verification...")
            checker = QualityChecker(ai_provider)
            quality_res = checker.verify_content(topic_data, news_items)

            if not quality_res.get("passed"):
                logger.warning(f"Daily content failed quality check: {quality_res.get('reason')}. Aborting safely.")
                return {"success": False, "reason": quality_res.get("reason")}

            # 4. Generate Daily Image
            logger.info("STEP 4: Generating daily image using Gemini Image Generator...")
            image_gen = GeminiImageGenerator()
            temp_image_path = temp_mgr.get_path("daily_post_image.jpg")
            image_prompt = topic_data.get("ai_media_prompt", topic_data.get("topic_title"))
            final_image_path = image_gen.generate_image(image_prompt, temp_image_path)

            # 5. Format Caption & Hashtags
            logger.info("STEP 5: Formatting Facebook caption and hashtags...")
            raw_caption = topic_data.get("caption", "")
            hashtags = topic_data.get("hashtags", [])
            final_caption = CaptionGenerator.format_caption(
                raw_caption=raw_caption,
                hashtags=hashtags,
                content_language=self.settings.CONTENT_LANGUAGE,
            )

            # 6. Publish to Facebook Page Feed
            logger.info("STEP 6: Publishing image post to Facebook Page feed...")
            feed_publisher = FacebookFeedPublisher()
            feed_res = feed_publisher.publish_image_post(
                image_path=final_image_path,
                caption=final_caption,
            )

            # 7. Publish to Facebook Story (if officially supported)
            logger.info("STEP 7: Publishing image to Facebook Page Story (if officially supported)...")
            story_publisher = FacebookStoryPublisher()
            story_res = story_publisher.publish_story(
                media_path=final_image_path,
                media_type="image",
            )

            # 8. Temporary files are automatically cleaned up by TempFileManager
            logger.info("==================================================")
            logger.info("DAILY WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info("==================================================")

            return {
                "success": True,
                "topic": topic_data.get("topic_title"),
                "trend_score": topic_data.get("trend_potential_score"),
                "feed_result": feed_res,
                "story_result": story_res,
            }
