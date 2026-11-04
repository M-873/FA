import re
from typing import List, Tuple
from app.animation.actions import VisemeMouthState


class VisemeLipSyncGenerator:
    """Generates timed viseme mouth state keyframes from dialogue text and duration."""

    @classmethod
    def generate_viseme_timeline(
        self,
        text: str,
        total_duration_sec: float,
        fps: int = 24,
    ) -> List[VisemeMouthState]:
        """
        Calculates mouth state for every video frame (fps * duration).
        """
        total_frames = int(total_duration_sec * fps)
        if total_frames <= 0:
            return []

        words = re.findall(r"\w+", text.lower())
        if not words:
            return [VisemeMouthState.REST] * total_frames

        # Map characters to visemes
        mouth_sequence: List[VisemeMouthState] = []
        for char in "".join(words):
            if char in "aeoঅআএও":
                mouth_sequence.append(VisemeMouthState.A)
            elif char in "iuইঈউঊ":
                mouth_sequence.append(VisemeMouthState.E)
            elif char in "bmpবমপফভ":
                mouth_sequence.append(VisemeMouthState.M_B_P)
            elif char in "szসশষচছ":
                mouth_sequence.append(VisemeMouthState.S_Z)
            else:
                mouth_sequence.append(VisemeMouthState.O)

        # Distribute viseme states across total_frames
        timeline: List[VisemeMouthState] = []
        frames_per_viseme = max(1, total_frames // len(mouth_sequence))

        for viseme in mouth_sequence:
            timeline.extend([viseme] * frames_per_viseme)

        # Pad or trim to exact total_frames
        if len(timeline) < total_frames:
            timeline.extend([VisemeMouthState.REST] * (total_frames - len(timeline)))
        else:
            timeline = timeline[:total_frames]

        return timeline
