from typing import Optional
from app.ai.base import BaseAIProvider
from app.ai.gemini import GeminiCartoonAIProvider
from app.ai.ollama_manager import OllamaHardwareManager
from app.ai.ollama_provider import OllamaCartoonAIProvider
from app.hardware.detector import HardwareSpecs
from app.utils.logging import logger


class AIProviderFactory:
    """
    Intelligent AI Provider Factory.
    Automatically provisions and selects the appropriate Ollama model based on GPU tier:
    - RTX 4060 / 5060 / 3060 (6GB+ VRAM) -> 'llama3.2:3b'
    - MX110 / GTX 1050 (2GB VRAM)        -> 'qwen2.5:0.5b' / 'llama3.2:1b'
    Falls back seamlessly to Google Gemini 2.0 Flash (Free API) if Ollama is installing or unavailable.
    """

    @classmethod
    def get_provider(cls, specs: Optional[HardwareSpecs] = None) -> BaseAIProvider:
        if specs and OllamaHardwareManager.is_hardware_compatible(specs):
            target_model = OllamaHardwareManager.get_optimal_model_for_hardware(specs)
            logger.info(f"Targeting Ollama model for hardware: {target_model}")

            # Check if Ollama is ready or try silent setup
            if OllamaHardwareManager.is_ollama_running() or OllamaHardwareManager.auto_install_ollama_if_needed():
                if OllamaHardwareManager.ensure_model_available(target_model):
                    logger.info(f"Local Ollama AI provider activated with model '{target_model}'.")
                    return OllamaCartoonAIProvider(model=target_model)
                else:
                    logger.info("Ollama model pull in progress or deferred. Using Google Gemini 2.0 Flash.")
            else:
                logger.info("Ollama background service not ready yet. Using Google Gemini 2.0 Flash.")

        # Default to Cloud Gemini AI (Free & Fast)
        return GeminiCartoonAIProvider()
