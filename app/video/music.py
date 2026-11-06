"""
app/video/music.py
==================
Manages background royalty-free music selection, consecutive-day track rotation,
and verifiable license source URL resolution.
"""

import json
import math
import os
import random
import struct
import wave
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.utils.logging import logger


class MusicManager:
    """
    Manages background royalty-free music selection and auto-generates ambient tracks if empty.
    Supports track rotation so consecutive days don't play the same track, and resolves
    verifiable license source URLs.
    """

    def __init__(
        self,
        music_dir: str = "assets/music",
        history_file: str = "output/music_history.json",
        licenses_file: Optional[str] = None,
    ):
        self.music_dir = music_dir
        self.history_file = history_file
        self.licenses_file = licenses_file or os.path.join(music_dir, "licenses.json")
        os.makedirs(self.music_dir, exist_ok=True)
        self._ensure_default_track()

    def _ensure_default_track(self):
        """Generates a pleasant, lightweight royalty-free upbeat lofi ambient soundtrack if none exists."""
        default_file = os.path.join(self.music_dir, "upbeat_lofi_playful.wav")
        if not os.path.exists(default_file) and not self.get_music_tracks():
            try:
                self._generate_lofi_track(default_file, duration_sec=16, sample_rate=44100)
                logger.info(f"Generated default background music track: {default_file}")
            except Exception as e:
                logger.warning(f"Could not auto-generate default music track: {e}")

    def _generate_lofi_track(self, file_path: str, duration_sec: int = 16, sample_rate: int = 44100):
        """Synthesizes a warm, cheerful lofi chord progression with soft acoustic tones."""
        chord_progression = [
            [261.63, 329.63, 392.00, 493.88],  # Cmaj7
            [220.00, 261.63, 329.63, 392.00],  # Am7
            [174.61, 220.00, 261.63, 329.63],  # Fmaj7
            [196.00, 246.94, 293.66, 349.23],  # G7
        ]

        num_samples = duration_sec * sample_rate
        chord_duration = sample_rate * 4  # 4 seconds per chord

        with wave.open(file_path, "w") as wav_file:
            wav_file.setnchannels(2)  # Stereo
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            for i in range(num_samples):
                chord_idx = (i // chord_duration) % len(chord_progression)
                current_chord = chord_progression[chord_idx]
                time_in_chord = (i % chord_duration) / sample_rate

                envelope = math.exp(-0.8 * (time_in_chord % 2.0)) * 0.4 + 0.15

                sample_val = 0.0
                for freq in current_chord:
                    sample_val += math.sin(2.0 * math.pi * freq * (i / sample_rate)) * 0.2
                    sample_val += math.sin(math.pi * freq * (i / sample_rate)) * 0.15

                sample_val *= envelope * 0.35

                int_sample = max(-32767, min(32767, int(sample_val * 32767)))
                frames.extend(struct.pack("<hh", int_sample, int_sample))

            wav_file.writeframes(frames)

    def get_music_tracks(self) -> List[str]:
        """Returns a sorted list of valid audio files in the music directory."""
        if not os.path.exists(self.music_dir):
            return []

        valid_extensions = (".mp3", ".wav", ".m4a", ".aac", ".ogg")
        tracks = [
            os.path.join(self.music_dir, f)
            for f in sorted(os.listdir(self.music_dir))
            if f.lower().endswith(valid_extensions)
        ]
        return tracks

    def get_last_used_track(self) -> Optional[str]:
        """Retrieves the last selected music track path from history."""
        if not os.path.exists(self.history_file):
            return None
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_track")
        except Exception as e:
            logger.warning(f"Failed to read music history from {self.history_file}: {e}")
            return None

    def record_selected_track(self, track_path: str):
        """Records the selected track into the persistent history file."""
        try:
            os.makedirs(os.path.dirname(self.history_file) or ".", exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump({"last_track": track_path}, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record music history to {self.history_file}: {e}")

    def select_track(self, previous_track: Optional[str] = None) -> Optional[str]:
        """
        Selects a background track from available royalty-free music.
        Rotates selection so the same track is not selected on consecutive days
        when multiple tracks are available.
        """
        tracks = self.get_music_tracks()
        if not tracks:
            self._ensure_default_track()
            tracks = self.get_music_tracks()

        if not tracks:
            return None

        last_track = previous_track or self.get_last_used_track()
        if len(tracks) > 1 and last_track:
            last_name = os.path.basename(last_track)
            candidates = [t for t in tracks if os.path.basename(t) != last_name]
            if candidates:
                tracks = candidates

        selected = random.choice(tracks)
        self.record_selected_track(selected)
        logger.info(f"Selected royalty-free music track: {selected} (previous: {last_track})")
        return selected

    def get_track_source_url(self, track_path: Optional[str]) -> str:
        """
        Resolves a verifiable license source URL for the given track.
        Looks up in sidecar file (<name>.url / <name>.txt) or assets/music/licenses.json.
        Returns verifiable URL string if valid http/https, else 'UNVERIFIED'.
        """
        if not track_path:
            return "UNVERIFIED"

        # 1. Sidecar .url or .txt check
        base_no_ext, _ = os.path.splitext(track_path)
        for ext in (".url", ".txt"):
            sidecar = base_no_ext + ext
            if os.path.exists(sidecar):
                try:
                    with open(sidecar, "r", encoding="utf-8") as f:
                        url = f.read().strip()
                        if self._is_valid_url(url):
                            return url
                except Exception:
                    pass

        # 2. Check licenses.json
        if os.path.exists(self.licenses_file):
            try:
                with open(self.licenses_file, "r", encoding="utf-8") as f:
                    licenses = json.load(f)
                    track_name = os.path.basename(track_path)
                    entry = licenses.get(track_name) or licenses.get(track_path)
                    if isinstance(entry, str) and self._is_valid_url(entry):
                        return entry
                    elif isinstance(entry, dict):
                        url = entry.get("source_url") or entry.get("url")
                        if url and self._is_valid_url(url):
                            return url
            except Exception as e:
                logger.warning(f"Error reading music licenses file {self.licenses_file}: {e}")

        return "UNVERIFIED"

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
