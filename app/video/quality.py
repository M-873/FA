"""
app/video/quality.py
====================
Automated Video Quality Checker for YouTube Shorts & Reels.
Validates:
1. File existence and non-trivial file size
2. Presence of valid Video stream
3. Presence of valid Audio stream (TTS dialogue and/or background music)
4. Aspect ratio conformity to 9:16 vertical shorts (within configurable tolerance)
5. Video duration compliance (configurable min/max boundaries, default 3-15s)
6. Black-frame ratio ceiling (prevents rendering black/blank video errors)
Uses ffprobe when available, and falls back seamlessly to ffmpeg.
"""

import json
import os
import re
import subprocess
from typing import Any, Dict, Optional
from app.utils.logging import logger
from app.video.ffmpeg_helper import get_ffmpeg_binary, get_ffprobe_binary


class VideoQualityChecker:
    """Verifies that final.mp4 meets quality criteria before platform uploads."""

    TARGET_ASPECT_RATIO = 9.0 / 16.0  # 0.5625 for 9:16 vertical shorts

    @classmethod
    def probe_video_metadata(cls, video_path: str) -> Dict[str, Any]:
        """
        Extracts stream metadata (duration, resolution, audio presence) using
        ffprobe if available, or ffmpeg fallback.
        """
        result = {
            "duration_sec": 0.0,
            "width": 0,
            "height": 0,
            "aspect_ratio": 0.0,
            "has_video": False,
            "has_audio": False,
            "file_size_bytes": os.path.getsize(video_path) if os.path.exists(video_path) else 0,
        }

        # 1. Try ffprobe (structured JSON output)
        ffprobe_bin = get_ffprobe_binary()
        if ffprobe_bin:
            try:
                cmd = [
                    ffprobe_bin,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    video_path,
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if proc.returncode == 0:
                    data = json.loads(proc.stdout)
                    streams = data.get("streams", [])
                    format_info = data.get("format", {})

                    # Extract duration
                    dur_str = format_info.get("duration")
                    if dur_str:
                        result["duration_sec"] = float(dur_str)

                    # Extract streams
                    for stream in streams:
                        ctype = stream.get("codec_type")
                        if ctype == "video" and not result["has_video"]:
                            result["has_video"] = True
                            w = int(stream.get("width", 0))
                            h = int(stream.get("height", 0))
                            result["width"] = w
                            result["height"] = h
                            if h > 0:
                                result["aspect_ratio"] = round(w / h, 4)
                            if result["duration_sec"] == 0.0 and stream.get("duration"):
                                result["duration_sec"] = float(stream["duration"])
                        elif ctype == "audio":
                            result["has_audio"] = True

                    return result
            except Exception as e:
                logger.debug(f"ffprobe extraction failed ({e}), falling back to ffmpeg probe.")

        # 2. Fallback: Parse ffmpeg -i stderr
        ffmpeg_bin = get_ffmpeg_binary()
        if ffmpeg_bin:
            try:
                cmd = [ffmpeg_bin, "-i", video_path]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                stderr = proc.stderr or ""

                # Duration: 00:00:12.50
                dur_match = re.search(r"Duration:\s*(\d+):(\d+):([\d\.]+)", stderr)
                if dur_match:
                    h, m, s = dur_match.groups()
                    result["duration_sec"] = round(int(h) * 3600 + int(m) * 60 + float(s), 2)

                # Video stream: 720x1280
                vid_match = re.search(r"Stream #\d+:\d+.*Video:.*?[,\s](\d{2,5})x(\d{2,5})", stderr)
                if vid_match:
                    result["has_video"] = True
                    w, h = int(vid_match.group(1)), int(vid_match.group(2))
                    result["width"] = w
                    result["height"] = h
                    if h > 0:
                        result["aspect_ratio"] = round(w / h, 4)

                # Audio stream
                if re.search(r"Stream #\d+:\d+.*Audio:", stderr):
                    result["has_audio"] = True

                return result
            except Exception as e:
                logger.debug(f"ffmpeg fallback probe failed: {e}")

        return result

    @classmethod
    def detect_black_frame_ratio(cls, video_path: str, duration: float) -> float:
        """
        Runs the FFmpeg blackdetect filter to calculate the ratio of black frames.
        Returns float between 0.0 and 1.0.
        """
        if duration <= 0.0:
            return 0.0

        ffmpeg_bin = get_ffmpeg_binary()
        if not ffmpeg_bin:
            return 0.0

        try:
            cmd = [
                ffmpeg_bin,
                "-i", video_path,
                "-vf", "blackdetect=d=0.2:pix_th=0.10",
                "-f", "null",
                "-",
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            stderr = proc.stderr or ""

            # Extract black_duration:([\d\.]+)
            black_durations = re.findall(r"black_duration:([\d\.]+)", stderr)
            total_black_sec = sum(float(d) for d in black_durations)
            ratio = min(1.0, max(0.0, total_black_sec / duration))
            return round(ratio, 4)
        except Exception as e:
            logger.debug(f"blackdetect analysis failed: {e}")
            return 0.0

    @classmethod
    def verify_video(
        cls,
        video_path: str,
        min_duration: float = 3.0,
        max_duration: float = 15.0,
        aspect_ratio_tolerance: float = 0.05,
        max_black_frame_ratio: float = 0.25,
        min_file_size_bytes: int = 1024,
    ) -> Dict[str, Any]:
        """
        Performs comprehensive quality and integrity checks on master MP4.
        Validates:
        - File existence and minimum file size
        - Video stream presence
        - Audio stream presence
        - Aspect ratio (9:16 within +-tolerance)
        - Duration (min_duration <= duration <= max_duration)
        - Black frame ratio (<= max_black_frame_ratio)
        """
        logger.info(f"Executing Pre-Upload Quality Check on {video_path}...")

        # 1. File existence
        if not os.path.exists(video_path):
            logger.error("Quality Check Failed: Master MP4 file does not exist.")
            return {"passed": False, "reason": "File does not exist", "details": {}}

        # 2. File size
        file_size_bytes = os.path.getsize(video_path)
        if file_size_bytes < min_file_size_bytes:
            logger.error(f"Quality Check Failed: File size too small ({file_size_bytes} bytes < {min_file_size_bytes}).")
            return {
                "passed": False,
                "reason": f"File size too small ({file_size_bytes} bytes)",
                "details": {"file_size_bytes": file_size_bytes},
            }

        # 3. Stream Metadata Probe
        meta = cls.probe_video_metadata(video_path)

        if not meta["has_video"]:
            logger.error("Quality Check Failed: No video stream detected.")
            return {"passed": False, "reason": "No video stream detected", "details": meta}

        if not meta["has_audio"]:
            logger.error("Quality Check Failed: No audio stream detected.")
            return {"passed": False, "reason": "No audio stream detected", "details": meta}

        # 4. Aspect Ratio Check (Target 9:16 = ~0.5625, +-tolerance)
        ar = meta["aspect_ratio"]
        target_ar = cls.TARGET_ASPECT_RATIO
        min_ar = target_ar * (1.0 - aspect_ratio_tolerance)
        max_ar = target_ar * (1.0 + aspect_ratio_tolerance)

        if not (min_ar <= ar <= max_ar):
            reason = (
                f"Invalid aspect ratio {ar:.4f} ({meta['width']}x{meta['height']}). "
                f"Expected 9:16 vertical format ({min_ar:.4f} - {max_ar:.4f})."
            )
            logger.error(f"Quality Check Failed: {reason}")
            return {"passed": False, "reason": reason, "details": meta}

        # 5. Duration Check (min_duration <= dur <= max_duration)
        dur = meta["duration_sec"]
        # Allow 0.5s margin for container/encoder padding
        if dur < (min_duration - 0.5) or dur > (max_duration + 1.0):
            reason = f"Duration {dur:.2f}s outside allowed range ({min_duration}s - {max_duration}s)."
            logger.error(f"Quality Check Failed: {reason}")
            return {"passed": False, "reason": reason, "details": meta}

        # 6. Black-frame ratio check
        black_ratio = cls.detect_black_frame_ratio(video_path, dur)
        meta["black_frame_ratio"] = black_ratio
        if black_ratio > max_black_frame_ratio:
            reason = f"Black frame ratio ({black_ratio:.1%}) exceeds maximum limit ({max_black_frame_ratio:.1%})."
            logger.error(f"Quality Check Failed: {reason}")
            return {"passed": False, "reason": reason, "details": meta}

        logger.info(
            f"Quality Check PASSED! Resolution: {meta['width']}x{meta['height']} | "
            f"Duration: {dur:.2f}s | Size: {round(file_size_bytes / 1024, 2)} KB | "
            f"Black Ratio: {black_ratio:.1%}"
        )
        return {
            "passed": True,
            "reason": "Video verified successfully.",
            "file_size_bytes": file_size_bytes,
            "details": meta,
        }
