import os
from typing import Dict, Any
from app.ai.gemini import GeminiProvider
from app.content.caption_generator import CaptionGenerator
from app.content.quality_checker import QualityChecker
from app.content.topic_selector import TopicSelector
from app.facebook.reels import FacebookReelPublisher
from app.facebook.stories import FacebookStoryPublisher
from app.news.aggregator import NewsAggregator
from app.news.official_sources import OfficialBlogNewsProvider
from app.news.rss import RSSNewsProvider
from app.utils.cleanup import TempFileManager
from app.utils.config import get_settings
from app.utils.logging import logger
from app.video.huggingface import HuggingFaceVideoGenerator
from app.video.music import MusicManager
from app.video.processor import FFmpegProcessor


class WeeklyWorkflow:
    """Executes the automated Weekly Video Reel workflow."""

    def __init__(self):
        self.settings = get_settings()

    def run(self) -> Dict[str, Any]:
        """
        Main entry point for weekly automated video workflow.
        """
        logger.info("==================================================")
        logger.info("STARTING WEEKLY AUTOMATED REEL WORKFLOW")
        logger.info("==================================================")

        with TempFileManager(prefix="weekly_reel_") as temp_mgr:
            # 1. Collect & Normalize AI News
            logger.info("STEP 1: Collecting AI news for weekly video topic...")
            rss_provider = RSSNewsProvider(self.settings.RSS_FEED_URLS)
            official_provider = OfficialBlogNewsProvider()
            aggregator = NewsAggregator([rss_provider, official_provider])

            news_items = aggregator.collect_and_deduplicate()
            if not news_items:
                logger.error("No news items collected. Aborting weekly reel workflow.")
                return {"success": False, "reason": "No news collected"}

            # 2. AI Video Topic Selection
            logger.info("STEP 2: Selecting best video topic using Gemini...")
            ai_provider = GeminiProvider()
            selector = TopicSelector(ai_provider)

            topic_data = selector.select_best_topic(
                news_items=news_items,
                content_type="video",
                language=self.settings.CONTENT_LANGUAGE,
            )

            # 3. Quality & Fact Consistency Verification
            logger.info("STEP 3: Running Pre-Publishing Quality Check...")
            checker = QualityChecker(ai_provider)
            quality_res = checker.verify_content(topic_data, news_items)

            if not quality_res.get("passed"):
                logger.warning(f"Weekly content failed quality check: {quality_res.get('reason')}. Aborting safely.")
                return {"success": False, "reason": quality_res.get("reason")}

            # 4. Generate AI Video via Hugging Face
            logger.info("STEP 4: Generating 3-10s video using Hugging Face Inference API...")
            hf_generator = HuggingFaceVideoGenerator()
            raw_video_path = temp_mgr.get_path("hf_raw_video.mp4")
            video_prompt = topic_data.get("ai_media_prompt", topic_data.get("topic_title"))
            raw_video = hf_generator.generate_video(video_prompt, raw_video_path)

            # 5. FFmpeg Video Formatting & Background Music Overlay
            logger.info("STEP 5: Processing video with FFmpeg and mixing royalty-free background music...")
            processor = FFmpegProcessor()
            music_mgr = MusicManager()
            music_track = music_mgr.select_track()

            final_video_path = temp_mgr.get_path("final_reel_916.mp4")
            processed_video = processor.process_video_for_reel(
                input_video_path=raw_video,
                output_video_path=final_video_path,
                audio_path=music_track,
            )

            # 6. Format Caption & Hashtags
            logger.info("STEP 6: Formatting Facebook Reel caption and hashtags...")
            raw_caption = topic_data.get("caption", "")
            hashtags = topic_data.get("hashtags", [])
            final_caption = CaptionGenerator.format_caption(
                raw_caption=raw_caption,
                hashtags=hashtags,
                content_language=self.settings.CONTENT_LANGUAGE,
            )

            # 7. Publish Facebook Reel
            logger.info("STEP 7: Publishing Reel to Facebook Page via Meta Reels API...")
            reel_publisher = FacebookReelPublisher()
            reel_res = reel_publisher.publish_reel(
                video_path=processed_video,
                caption=final_caption,
            )

            # 8. Publish to Facebook Story (if officially supported)
            logger.info("STEP 8: Publishing Reel video to Facebook Page Story (if officially supported)...")
            story_publisher = FacebookStoryPublisher()
            story_res = story_publisher.publish_story(
                media_path=processed_video,
                media_type="video",
            )

            # 9. Cleanup happens automatically via context manager
            logger.info("==================================================")
            logger.info("WEEKLY REEL WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info("==================================================")

            return {
                "success": True,
                "topic": topic_data.get("topic_title"),
                "trend_score": topic_data.get("trend_potential_score"),
                "reel_result": reel_res,
                "story_result": story_res,
            }
