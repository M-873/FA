import os
import random
import wave
import struct
import math
from typing import Optional, List
from app.utils.logging import logger


class MusicManager:
    """Manages background royalty-free music selection and auto-generates ambient tracks if empty."""

    def __init__(self, music_dir: str = "assets/music"):
        self.music_dir = music_dir
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
        # Chords: Cmaj7 (C4, E4, G4, B4) -> Am7 (A3, C4, E4, G4) -> Fmaj7 (F3, A3, C4, E4) -> G7 (G3, B3, D4, F4)
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
                
                # Soft envelope decay
                envelope = math.exp(-0.8 * (time_in_chord % 2.0)) * 0.4 + 0.15
                
                # Sum harmonics
                sample_val = 0.0
                for freq in current_chord:
                    sample_val += math.sin(2.0 * math.pi * freq * (i / sample_rate)) * 0.2
                    # Warm soft sub-bass
                    sample_val += math.sin(math.pi * freq * (i / sample_rate)) * 0.15

                sample_val *= envelope * 0.35  # Keep background volume balanced
                
                # Clamp 16-bit PCM
                int_sample = max(-32767, min(32767, int(sample_val * 32767)))
                frames.extend(struct.pack("<hh", int_sample, int_sample))

            wav_file.writeframes(frames)

    def get_music_tracks(self) -> List[str]:
        """Returns a list of valid audio files in the music directory."""
        if not os.path.exists(self.music_dir):
            return []

        valid_extensions = (".mp3", ".wav", ".m4a", ".aac", ".ogg")
        tracks = [
            os.path.join(self.music_dir, f)
            for f in os.listdir(self.music_dir)
            if f.lower().endswith(valid_extensions)
        ]
        return tracks

    def select_track(self) -> Optional[str]:
        """Selects a background track from available royalty-free music."""
        tracks = self.get_music_tracks()
        if not tracks:
            self._ensure_default_track()
            tracks = self.get_music_tracks()

        if not tracks:
            return None

        selected = random.choice(tracks)
        logger.info(f"Selected royalty-free music track: {selected}")
        return selected
