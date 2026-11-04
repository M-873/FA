from abc import ABC, abstractmethod


class BaseTTSProvider(ABC):
    """Abstract interface for Cloud TTS providers."""

    @abstractmethod
    def generate_audio(self, text: str, output_path: str, voice_id: str = "bn") -> str:
        """Generates dialogue audio file from text script."""
        pass
