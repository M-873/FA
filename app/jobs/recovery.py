import os
from typing import Dict, Any
from app.ai.gemini import GeminiCartoonAIProvider
from app.animation.engine import CartoonAnimationEngine
from app.facebook.reels import FacebookReelPublisher
from app.facebook.stories import FacebookStoryPublisher
from app.hardware.detector import HardwareDetector
from app.hardware.monitor import HardwareSafetyMonitor
from app.hardware.profiles import PerformanceProfileManager
from app.jobs.manager import DailyJobManager
from app.jobs.state import JobStatus, DailyJobState
from app.tts.online import CloudTTSProvider
from app.utils.cleanup import TempFileManager
from app.utils.config import get_project_config, get_env_settings
from app.utils.logging import logger
from app.video.music import MusicManager
from app.video.quality import VideoQualityChecker
from app.video.renderer import CartoonMasterRenderer
from app.youtube.publisher import YouTubeShortsPublisher


class DailyCartoonAutomationPipeline:
    """
    End-to-End Orchestrator for 2D Cartoon Daily Video Automation.
    Guarantees SINGLE render of output/final.mp4 and SAME-FILE upload to Facebook and YouTube.
    Supports partial failure recovery (e.g. retrying failed YouTube upload without re-rendering).
    """

    def __init__(self):
        self.project_cfg = get_project_config()
        self.env_cfg = get_env_settings()
        self.job_mgr = DailyJobManager()

    def run_daily_pipeline(self) -> Dict[str, Any]:
        """Executes today's automated video pipeline."""
        logger.info("==============================================================================")
        logger.info("STARTING LIGHTWEIGHT 2D CARTOON DAILY AUTOMATION PIPELINE")
        logger.info("==============================================================================")

        # 1. Hardware Specs & Profile Selection
        detector = HardwareDetector()
        specs = detector.detect()
        profile_info = PerformanceProfileManager.determine_profile(specs)
        render_settings = profile_info["render_settings"]

        # 2. Today's Job State & Recovery Check
        job = self.job_mgr.get_or_create_today_job()
        if job.status == JobStatus.PUBLISHED:
            logger.info(f"[JOB COMPLETED] Today's video ({job.date}) is already PUBLISHED. Doing nothing.")
            return {"success": True, "job_status": JobStatus.PUBLISHED, "reason": "Already published"}

        # Check Partial Failure Recovery
        if job.status == JobStatus.PARTIALLY_PUBLISHED and job.video_path and os.path.exists(job.video_path):
            logger.info("Detected PARTIALLY_PUBLISHED state. Resuming upload stage for failed platform without re-rendering...")
            return self._resume_uploads(job, job.video_path, topic_title=job.topic_title or "Cartoon Short")

        with TempFileManager(prefix="cartoon_render_") as temp_mgr:
            # 3. AI Generation Stage
            job.update_status(JobStatus.GENERATING_TOPIC)
            self.job_mgr.save_job(job)

            from app.ai.factory import AIProviderFactory
            ai_provider = AIProviderFactory.get_provider(specs)
            topic = ai_provider.generate_topic(self.project_cfg.niche, self.project_cfg.language)
            job.topic_title = topic.get("topic_title")

            job.update_status(JobStatus.GENERATING_SCRIPT)
            self.job_mgr.save_job(job)
            script = ai_provider.generate_script(topic, self.project_cfg.video_duration, self.project_cfg.language)
            scene_plan = ai_provider.generate_scene_plan(script)
            metadata = ai_provider.generate_metadata(topic, script, self.project_cfg.language)

            # 4. Cloud TTS Audio Stage
            job.update_status(JobStatus.GENERATING_VOICE)
            self.job_mgr.save_job(job)
            tts_provider = CloudTTSProvider()
            dialogue_text = " ".join([d.get("text", "") for d in script.get("dialogues", [])])
            temp_tts_path = temp_mgr.get_path("dialogue.mp3")
            tts_path = tts_provider.generate_audio(dialogue_text, temp_tts_path, voice_id=self.project_cfg.language)

            HardwareSafetyMonitor.purge_resources()

            # 5. 2D Frame Animation Stage
            job.update_status(JobStatus.ANIMATING)
            self.job_mgr.save_job(job)
            anim_engine = CartoonAnimationEngine(render_settings)
            frames_dir = temp_mgr.get_path("frames")
            anim_engine.render_scene_frames(script, scene_plan, frames_dir)

            HardwareSafetyMonitor.purge_resources()

            # 6. Master FFmpeg Render Stage (SINGLE MASTER MP4)
            job.update_status(JobStatus.RENDERING)
            self.job_mgr.save_job(job)
            music_mgr = MusicManager()
            music_track = music_mgr.select_track()

            master_renderer = CartoonMasterRenderer(render_settings)
            final_mp4_path = "output/final.mp4"
            master_renderer.render_master_mp4(
                frame_dir=frames_dir,
                tts_audio_path=tts_path,
                music_path=music_track,
                output_mp4_path=final_mp4_path,
            )

            # 7. Quality Verification
            job.update_status(JobStatus.QUALITY_CHECK)
            self.job_mgr.save_job(job)
            quality_res = VideoQualityChecker.verify_video(final_mp4_path)

            if not quality_res.get("passed"):
                logger.error(f"Quality Check Failed: {quality_res.get('reason')}. Aborting upload.")
                job.update_status(JobStatus.FAILED, error=quality_res.get("reason"))
                self.job_mgr.save_job(job)
                return {"success": False, "reason": quality_res.get("reason")}

            job.video_path = final_mp4_path
            job.update_status(JobStatus.READY_TO_UPLOAD)
            self.job_mgr.save_job(job)

            # 8. Multi-Platform Upload Stage (SAME MASTER FINAL MP4)
            return self._resume_uploads(job, final_mp4_path, metadata)

    def _resume_uploads(self, job: DailyJobState, master_mp4_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Uploads the SAME master MP4 file to Facebook and YouTube with status state tracking."""
        title = metadata.get("title", job.topic_title or "AI Cartoon Short") if metadata else job.topic_title or "AI Cartoon Short"
        description = metadata.get("description", "Daily 2D Cartoon AI Short") if metadata else "Daily 2D Cartoon AI Short"
        hashtags = metadata.get("hashtags", self.project_cfg.default_hashtags) if metadata else self.project_cfg.default_hashtags
        full_caption = f"{description}\n\n{' '.join(hashtags)}"

        # 8a. Facebook Reel & Story Upload
        if job.facebook_reel != "SUCCESS":
            job.update_status(JobStatus.UPLOADING_FACEBOOK)
            self.job_mgr.save_job(job)

            fb_reel_pub = FacebookReelPublisher()
            fb_res = fb_reel_pub.publish_reel(video_path=master_mp4_path, caption=full_caption)

            if fb_res.get("success"):
                job.facebook_reel = "SUCCESS"
                job.facebook_post_id = fb_res.get("reel_id")
            elif fb_res.get("skipped"):
                job.facebook_reel = "SKIPPED"
            else:
                job.facebook_reel = "FAILED"

            # Optional Story Attempt
            fb_story_pub = FacebookStoryPublisher()
            story_res = fb_story_pub.publish_story(media_path=master_mp4_path, media_type="video")
            job.facebook_story = "SUCCESS" if story_res.get("success") else ("SKIPPED" if story_res.get("skipped") else "FAILED")

            self.job_mgr.save_job(job)

        # 8b. YouTube Shorts Upload (SAME MASTER MP4 FILE)
        if job.youtube_status != "SUCCESS":
            job.update_status(JobStatus.UPLOADING_YOUTUBE)
            self.job_mgr.save_job(job)

            yt_pub = YouTubeShortsPublisher()
            yt_res = yt_pub.publish_short(
                video_path=master_mp4_path,
                title=title,
                description=description,
                hashtags=hashtags,
            )

            if yt_res.get("success"):
                job.youtube_status = "SUCCESS"
                job.youtube_video_id = yt_res.get("video_id")
            else:
                job.youtube_status = "FAILED"

            self.job_mgr.save_job(job)

        # 9. Final State Assessment
        fb_ok = job.facebook_reel in ("SUCCESS", "SKIPPED")
        yt_ok = job.youtube_status == "SUCCESS"

        if fb_ok and yt_ok:
            job.update_status(JobStatus.PUBLISHED)
        elif yt_ok or job.facebook_reel == "SUCCESS":
            job.update_status(JobStatus.PARTIALLY_PUBLISHED)
        else:
            job.update_status(JobStatus.FAILED, error="Platform upload failed")

        self.job_mgr.save_job(job)

        # 10. Clean up master output file if configured
        if job.status == JobStatus.PUBLISHED and os.path.exists(master_mp4_path):
            try:
                os.remove(master_mp4_path)
                logger.info(f"Purged final master video file {master_mp4_path} after successful publishing.")
            except Exception as e:
                logger.warning(f"Could not remove {master_mp4_path}: {e}")

        logger.info("==============================================================================")
        logger.info(f"DAILY PIPELINE FINISHED. Final Job Status: {job.status.value}")
        logger.info("==============================================================================")

        return {
            "success": job.status in (JobStatus.PUBLISHED, JobStatus.PARTIALLY_PUBLISHED),
            "job_status": job.status.value,
            "facebook_reel": job.facebook_reel,
            "youtube_status": job.youtube_status,
        }
