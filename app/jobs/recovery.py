import os
from typing import Dict, Any, Optional
from app.ai.gemini import GeminiCartoonAIProvider
from app.content.factory import ContentSourceFactory
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
from app.youtube.publisher import YouTubeShortsPublisher


class DailyCartoonAutomationPipeline:
    """
    End-to-End Orchestrator for Daily Video Automation.
    Guarantees SINGLE render of output/final.mp4 and SAME-FILE upload to Facebook and YouTube.
    Supports partial failure recovery (e.g. retrying failed YouTube upload without re-rendering).
    """

    def __init__(self, job_manager: Optional[DailyJobManager] = None):
        self.project_cfg = get_project_config()
        self.env_cfg = get_env_settings()
        self.job_mgr = job_manager if job_manager is not None else DailyJobManager()

    def run_daily_pipeline(self) -> Dict[str, Any]:
        """Executes today's automated video pipeline."""
        logger.info("==============================================================================")
        logger.info("STARTING LIGHTWEIGHT DAILY AUTOMATION PIPELINE")
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
            return self._resume_uploads(job, job.video_path, metadata={"title": job.topic_title or "Video Short"})

        # Check Awaiting Approval
        if job.status == JobStatus.AWAITING_APPROVAL and job.video_path and os.path.exists(job.video_path):
            logger.info(f"[AWAITING APPROVAL] Today's video ({job.date}) is waiting for human approval at {job.video_path}.")
            return {
                "success": True,
                "job_status": JobStatus.AWAITING_APPROVAL.value,
                "video_path": job.video_path,
                "awaiting_approval": True,
            }

        with TempFileManager(prefix="daily_render_") as temp_mgr:
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

            # 5. Content Generation & Master Render Stage
            configured_source = getattr(self.project_cfg, "content_source", "auto")
            content_source = ContentSourceFactory.get_source(specs, configured_source)
            job.content_source = content_source.name

            job.update_status(JobStatus.ANIMATING if content_source.name == "cartoon" else JobStatus.RENDERING)
            self.job_mgr.save_job(job)

            music_mgr = MusicManager()
            music_track = music_mgr.select_track()
            music_source_url = music_mgr.get_track_source_url(music_track)

            final_mp4_path = "output/final.mp4"
            from app.stock.provider import NoClipFoundError
            try:
                render_res = content_source.generate_video(
                    topic=topic,
                    script=script,
                    scene_plan=scene_plan,
                    tts_audio_path=tts_path,
                    music_path=music_track,
                    render_settings=render_settings,
                    temp_mgr=temp_mgr,
                    output_mp4_path=final_mp4_path,
                    music_source_url=music_source_url,
                )
                final_mp4_path = render_res.video_path
                job.clip_id = render_res.metadata.get("clip_id")
                job.provider = render_res.metadata.get("provider")
            except NoClipFoundError as e:
                logger.error(f"No stock clip found: {e}. Ending job in FAILED state.")
                job.update_status(JobStatus.FAILED, error=str(e))
                self.job_mgr.save_job(job)
                return {"success": False, "reason": str(e)}

            # 6. Quality Verification
            job.update_status(JobStatus.QUALITY_CHECK)
            self.job_mgr.save_job(job)
            quality_res = VideoQualityChecker.verify_video(final_mp4_path)

            if not quality_res.get("passed"):
                logger.error(f"Quality Check Failed: {quality_res.get('reason')}. Aborting upload.")
                job.update_status(JobStatus.FAILED, error=quality_res.get("reason"))
                self.job_mgr.save_job(job)
                return {"success": False, "reason": quality_res.get("reason")}

            job.video_path = final_mp4_path

            # Check human approval requirement
            approval_needed = (
                self.env_cfg.REQUIRE_HUMAN_APPROVAL
                if self.env_cfg.REQUIRE_HUMAN_APPROVAL is not None
                else getattr(self.project_cfg, "require_human_approval", True)
            )
            if approval_needed:
                job.update_status(JobStatus.AWAITING_APPROVAL)
                self.job_mgr.save_job(job)
                abs_video_path = os.path.abspath(final_mp4_path)
                logger.info("=" * 78)
                logger.info(f"JOB PAUSED FOR HUMAN APPROVAL: {job.job_id}")
                logger.info(f"Rendered Video: {abs_video_path}")
                logger.info(f"Topic: {job.topic_title}")
                logger.info("To approve and publish, run: python -m app.main --approve")
                logger.info("To reject and regenerate, run: python -m app.main --reject")
                logger.info("=" * 78)
                return {
                    "success": True,
                    "job_status": JobStatus.AWAITING_APPROVAL.value,
                    "video_path": final_mp4_path,
                    "awaiting_approval": True,
                }

            job.update_status(JobStatus.READY_TO_UPLOAD)
            self.job_mgr.save_job(job)

            # 7. Multi-Platform Upload Stage (SAME MASTER FINAL MP4)
            return self._resume_uploads(job, final_mp4_path, metadata)

    def _resume_uploads(self, job: DailyJobState, master_mp4_path: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Uploads the SAME master MP4 file to Facebook and YouTube with status state tracking."""
        if isinstance(metadata, dict):
            title = metadata.get("title", job.topic_title or "AI Video Short")
            description = metadata.get("description", "Daily AI Video Short")
            hashtags = metadata.get("hashtags", self.project_cfg.default_hashtags)
        elif isinstance(metadata, str):
            title = metadata
            description = "Daily AI Video Short"
            hashtags = self.project_cfg.default_hashtags
        else:
            title = job.topic_title or "AI Video Short"
            description = "Daily AI Video Short"
            hashtags = self.project_cfg.default_hashtags
        full_caption = f"{description}\n\n{' '.join(hashtags)}"

        # Resolve platform switches (env override takes precedence over project_config.json)
        fb_enabled = self.env_cfg.FACEBOOK_ENABLED if self.env_cfg.FACEBOOK_ENABLED is not None else getattr(self.project_cfg, "facebook_enabled", False)
        yt_enabled = self.env_cfg.YOUTUBE_ENABLED if self.env_cfg.YOUTUBE_ENABLED is not None else getattr(self.project_cfg, "youtube_enabled", True)
        ig_enabled = self.env_cfg.INSTAGRAM_ENABLED if self.env_cfg.INSTAGRAM_ENABLED is not None else getattr(self.project_cfg, "instagram_enabled", False)

        # 7a. Facebook Reel & Story Upload
        if not fb_enabled:
            logger.info("Facebook publishing is disabled in configuration. Skipping Facebook.")
            job.facebook_reel = "SKIPPED"
            job.facebook_story = "SKIPPED"
            self.job_mgr.save_job(job)
        elif job.facebook_reel != "SUCCESS":
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

        # 7b. YouTube Shorts Upload (SAME MASTER MP4 FILE)
        if not yt_enabled:
            logger.info("YouTube publishing is disabled in configuration. Skipping YouTube.")
            job.youtube_status = "SKIPPED"
            self.job_mgr.save_job(job)
        elif job.youtube_status != "SUCCESS":
            job.update_status(JobStatus.UPLOADING_YOUTUBE)
            self.job_mgr.save_job(job)

            yt_pub = YouTubeShortsPublisher()
            privacy = getattr(self.project_cfg, "youtube_privacy", "private")
            yt_res = yt_pub.publish_short(
                video_path=master_mp4_path,
                title=title,
                description=description,
                hashtags=hashtags,
                privacy_status=privacy,
            )

            if yt_res.get("success"):
                job.youtube_status = "SUCCESS"
                job.youtube_video_id = yt_res.get("video_id")
            else:
                job.youtube_status = "FAILED"

            self.job_mgr.save_job(job)

        # 7c. Instagram Publishing (Skipped if disabled or stubbed)
        if not ig_enabled:
            job.instagram_status = "SKIPPED"
        else:
            logger.info("Instagram publishing is enabled in config, but publisher is not yet configured. Marking SKIPPED.")
            job.instagram_status = "SKIPPED"
        self.job_mgr.save_job(job)

        # 8. Final State Assessment
        enabled_platforms = []
        if yt_enabled:
            enabled_platforms.append("youtube")
        if fb_enabled:
            enabled_platforms.append("facebook")
        if ig_enabled:
            enabled_platforms.append("instagram")

        yt_success = (job.youtube_status == "SUCCESS")
        fb_success = (job.facebook_reel == "SUCCESS")
        ig_success = (job.instagram_status == "SUCCESS")

        if not enabled_platforms:
            all_enabled_ok = True
            any_success = True
        else:
            all_enabled_ok = (
                (not yt_enabled or yt_success) and
                (not fb_enabled or fb_success) and
                (not ig_enabled or ig_success or job.instagram_status == "SKIPPED")
            )
            any_success = (
                (yt_enabled and yt_success) or
                (fb_enabled and fb_success) or
                (ig_enabled and ig_success)
            )

        if all_enabled_ok:
            if self.env_cfg.DRY_RUN:
                job.update_status(JobStatus.DRY_RUN_COMPLETE)
            else:
                job.update_status(JobStatus.PUBLISHED)
        elif any_success:
            job.update_status(JobStatus.PARTIALLY_PUBLISHED)
        else:
            job.update_status(JobStatus.FAILED, error="Platform upload failed")

        # Record into local SQLite publishing history
        try:
            from app.jobs.history import PublishingHistoryManager
            history_mgr = PublishingHistoryManager()
            history_mgr.record_publication(
                date=job.date,
                topic=job.topic_title,
                clip_id=getattr(job, "clip_id", None),
                provider=getattr(job, "provider", None) or job.content_source,
                video_id=job.youtube_video_id,
                status=job.status.value,
                error=job.error_message,
            )
        except Exception as e:
            logger.warning(f"Could not record publication history to SQLite: {e}")

        self.job_mgr.save_job(job)

        # 9. Clean up master output file if configured
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
            "success": job.status in (JobStatus.PUBLISHED, JobStatus.PARTIALLY_PUBLISHED, JobStatus.DRY_RUN_COMPLETE),
            "job_status": job.status.value,
            "facebook_reel": job.facebook_reel,
            "youtube_status": job.youtube_status,
        }

    def approve_job(self) -> Dict[str, Any]:
        """
        Approves today's job currently in AWAITING_APPROVAL state and resumes publishing.
        """
        job = self.job_mgr.get_today_job()
        if not job or job.status != JobStatus.AWAITING_APPROVAL:
            msg = f"Cannot approve: No job in AWAITING_APPROVAL state (current status: {job.status.value if job else 'None'})."
            logger.warning(msg)
            return {"success": False, "reason": msg}

        if not job.video_path or not os.path.exists(job.video_path):
            msg = f"Cannot approve: Rendered video file '{job.video_path}' not found on disk."
            logger.error(msg)
            job.update_status(JobStatus.FAILED, error=msg)
            self.job_mgr.save_job(job)
            return {"success": False, "reason": msg}

        logger.info(f"Human approval received for job {job.job_id}. Resuming publication...")
        job.update_status(JobStatus.READY_TO_UPLOAD)
        self.job_mgr.save_job(job)
        return self._resume_uploads(job, job.video_path, metadata={"title": job.topic_title or "AI Video Short"})

    def reject_job(self, regenerate: bool = False) -> Dict[str, Any]:
        """
        Rejects today's job in AWAITING_APPROVAL state.
        Resets state to PENDING so pipeline can regenerate fresh content.
        If regenerate is True, immediately starts a new pipeline run.
        """
        job = self.job_mgr.get_today_job()
        if not job:
            msg = "Cannot reject: No job found for today."
            logger.warning(msg)
            return {"success": False, "reason": msg}

        logger.info(f"Rejecting job {job.job_id}. Resetting job state to PENDING...")
        self.job_mgr.reset_job()

        if regenerate:
            logger.info("Regenerating daily video from scratch...")
            return self.run_daily_pipeline()

        return {"success": True, "job_status": JobStatus.PENDING.value, "rejected": True}
