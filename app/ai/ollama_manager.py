import os
import sys
import shutil
import subprocess
import urllib.request
import httpx
from typing import Optional, Tuple
from app.hardware.detector import HardwareSpecs
from app.utils.logging import logger


class OllamaHardwareManager:
    """
    Intelligent Hardware-Adaptive Ollama Manager.
    Automatically provisions and selects the optimal Ollama model based on host GPU:
    - Tier 1: RTX 4060 / 5060 / 3060 (>= 6GB VRAM) -> 'llama3.2:3b' (High capability)
    - Tier 2: MX110 / 2GB GPUs / 8GB RAM          -> 'qwen2.5:0.5b' / 'llama3.2:1b' (Ultra-lightweight)
    """

    OLLAMA_API_URL = "http://localhost:11434"
    OLLAMA_WIN_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"

    # Hardware tier models
    MODEL_TIER_HIGH = "llama3.2:3b"       # For >= 6GB VRAM (RTX 4060, 5060, etc.)
    MODEL_TIER_LOW = "qwen2.5:0.5b"       # For 2GB VRAM (MX110, GTX 1050, 8GB RAM)
    DEFAULT_MODEL = MODEL_TIER_HIGH

    @classmethod
    def get_optimal_model_for_hardware(cls, specs: HardwareSpecs) -> str:
        """
        Selects the best model matched to GPU VRAM and system memory.
        """
        if specs.vram_mb >= 6000 and specs.ram_gb >= 14.0:
            logger.info(f"[GPU TIER: HIGH] Detected {specs.gpu_name} ({specs.vram_mb}MB VRAM). Selected model: {cls.MODEL_TIER_HIGH}")
            return cls.MODEL_TIER_HIGH
        else:
            logger.info(f"[GPU TIER: LOW/2GB] Detected {specs.gpu_name} ({specs.vram_mb}MB VRAM). Selected ultra-lightweight model: {cls.MODEL_TIER_LOW}")
            return cls.MODEL_TIER_LOW

    @classmethod
    def is_hardware_compatible(cls, specs: HardwareSpecs) -> bool:
        """
        All systems are supported:
        - 2GB+ GPUs can run quantized 0.5B/1B models.
        - 6GB+ GPUs run 3B/7B models.
        """
        return specs.ram_gb >= 6.0

    @classmethod
    def get_ollama_executable(cls) -> Optional[str]:
        """Finds Ollama binary path on Windows."""
        cmd = shutil.which("ollama")
        if cmd:
            return cmd

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        possible_paths = [
            os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe"),
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Ollama", "ollama.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Ollama", "ollama.exe"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return None

    @classmethod
    def is_ollama_running(cls) -> bool:
        """Checks if local Ollama server is active and answering HTTP requests."""
        try:
            res = httpx.get(f"{cls.OLLAMA_API_URL}/api/tags", timeout=2.0)
            return res.status_code == 200
        except Exception:
            return False

    @classmethod
    def auto_install_ollama_if_needed(cls) -> bool:
        """
        Automatically downloads and installs Ollama on Windows if not present.
        """
        if cls.get_ollama_executable():
            cls.start_ollama_service()
            return True

        logger.info("Ollama is not installed. Initiating automatic silent download & installation...")
        installer_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "OllamaSetup.exe")

        try:
            urllib.request.urlretrieve(cls.OLLAMA_WIN_INSTALLER_URL, installer_path)
            logger.info(f"Downloaded Ollama setup to {installer_path}. Running silent installation...")
            subprocess.run([installer_path, "/silent"], check=True, timeout=180)
            logger.info("Ollama installed successfully.")
            cls.start_ollama_service()
            return True
        except Exception as e:
            logger.warning(f"Automatic Ollama installation skipped or deferred: {e}")
            return False

    @classmethod
    def start_ollama_service(cls):
        """Starts Ollama daemon in background if not already running."""
        if cls.is_ollama_running():
            return

        ollama_bin = cls.get_ollama_executable()
        if ollama_bin:
            try:
                subprocess.Popen([ollama_bin, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Started Ollama background service.")
            except Exception as e:
                logger.warning(f"Could not launch Ollama service: {e}")

    @classmethod
    def ensure_model_available(cls, model_name: str) -> bool:
        """Checks if local model is pulled, otherwise pulls it automatically."""
        try:
            res = httpx.get(f"{cls.OLLAMA_API_URL}/api/tags", timeout=3.0)
            if res.status_code == 200:
                models = [m.get("name", "") for m in res.json().get("models", [])]
                if any(model_name in m for m in models):
                    return True

            logger.info(f"Automatically pulling hardware-matched Ollama model: '{model_name}'...")
            pull_res = httpx.post(f"{cls.OLLAMA_API_URL}/api/pull", json={"name": model_name}, timeout=300.0)
            return pull_res.status_code == 200
        except Exception as e:
            logger.warning(f"Could not pull Ollama model '{model_name}': {e}")
            return False
