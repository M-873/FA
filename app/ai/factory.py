from typing import Optional
from app.ai.base import BaseAIProvider
from app.ai.gemini import GeminiCartoonAIProvider
from app.ai.ollama_manager import OllamaHardwareManager
from app.ai.ollama_provider import OllamaCartoonAIProvider
from app.hardware.detector import HardwareSpecs
from app.utils.config import get_env_settings, get_project_config
from app.utils.logging import logger


class AIProviderFactory:
    """
    Intelligent AI Provider Factory.
    Automatically provisions and selects the appropriate Ollama model based on GPU tier:
    - RTX 4060 / 5060 / 3060 (6GB+ VRAM) -> 'llama3.2:3b'
    - MX110 / GTX 1050 (2GB VRAM)        -> 'qwen2.5:0.5b' / 'llama3.2:1b'
    Falls back seamlessly to Google Gemini API if Ollama is installing or unavailable.
    """

    @classmethod
    def get_provider(cls, specs: Optional[HardwareSpecs] = None) -> BaseAIProvider:
        gemini_model = getattr(get_project_config(), "gemini_model", None) or get_env_settings().GEMINI_MODEL
        env_settings = get_env_settings()

        if env_settings.OLLAMA_ENABLED and specs and OllamaHardwareManager.is_hardware_compatible(specs):
            # Only use Ollama if installed or running
            if OllamaHardwareManager.get_ollama_executable() or OllamaHardwareManager.is_ollama_running():
                target_model = OllamaHardwareManager.get_optimal_model_for_hardware(specs)
                logger.info(f"Targeting Ollama model for hardware: {target_model}")

                # Check if Ollama is ready or try silent setup
                if OllamaHardwareManager.is_ollama_running() or OllamaHardwareManager.auto_install_ollama_if_needed():
                    if OllamaHardwareManager.ensure_model_available(target_model):
                        logger.info(f"Local Ollama AI provider activated with model '{target_model}'.")
                        return OllamaCartoonAIProvider(model=target_model)
                    else:
                        logger.info(f"Ollama model pull in progress or deferred. Using Google Gemini ({gemini_model}).")
                else:
                    logger.info(f"Ollama background service not ready yet. Using Google Gemini ({gemini_model}).")
            else:
                logger.info(f"Ollama is not installed. Using Google Gemini ({gemini_model}).")

        # Default to Cloud Gemini AI
        return GeminiCartoonAIProvider()
