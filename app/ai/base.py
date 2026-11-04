from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseAIProvider(ABC):
    """Abstract interface for Cartoon Video AI Generation providers."""

    @abstractmethod
    def generate_topic(self, niche: str, language: str) -> Dict[str, Any]:
        """Generates a candidate daily cartoon topic concept."""
        pass

    @abstractmethod
    def generate_script(self, topic: Dict[str, Any], duration: int, language: str) -> Dict[str, Any]:
        """Generates a 10-15 second dialogue script for the cartoon."""
        pass

    @abstractmethod
    def generate_scene_plan(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """Generates structured scene breakdown and character action instructions."""
        pass

    @abstractmethod
    def generate_metadata(self, topic: Dict[str, Any], script: Dict[str, Any], language: str) -> Dict[str, Any]:
        """Generates title, description, and hashtags for Facebook & YouTube."""
        pass
