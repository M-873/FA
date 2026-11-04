"""
TTS Package.
"""
from app.tts.base import BaseTTSProvider
from app.tts.online import CloudTTSProvider

__all__ = ["BaseTTSProvider", "CloudTTSProvider"]
