from app.ai.base import BaseAIProvider


class MockCartoonAIProvider(BaseAIProvider):
    """Mock AI Provider for testing cartoon content generation pipeline."""

    def generate_topic(self, niche: str, language: str):
        return {
            "topic_title": "AI Robot Learns to Cook Fish Curry",
            "concept_summary": "A robot tries to fry fish and causes hilarious chaos.",
            "characters": ["robot", "chef_cat"],
            "humor_hook": "Robot adds oil to dry pan.",
            "estimated_duration": 12,
        }

    def generate_script(self, topic, duration, language):
        return {
            "duration": duration,
            "dialogues": [
                {
                    "id": 1,
                    "character": "chef_cat",
                    "text": "রোবট, মাছ ভাজতে পারবি?",
                    "expression": "doubtful",
                    "action": "wave",
                },
                {
                    "id": 2,
                    "character": "robot",
                    "text": "১০০% নির্ভুল অ্যালগরিদম লোডেড!",
                    "expression": "proud",
                    "action": "jump",
                },
            ],
        }

    def generate_scene_plan(self, script):
        return {
            "scenes": [
                {
                    "scene_id": 1,
                    "duration": 6,
                    "background": "kitchen",
                    "character": "chef_cat",
                    "initial_position": [0.3, 0.6],
                    "actions": [{"type": "talk", "duration": 4}],
                }
            ]
        }

    def generate_metadata(self, topic, script, language):
        return {
            "title": "রোবটের ইলিশ মাছ ভাজা 🤖🐟",
            "description": "রোবট যখন প্রথমবার রান্না ঘরে ঢোকে...",
            "hashtags": ["#AICartoon", "#BanglaHumor", "#Reels", "#Shorts"],
        }


def test_mock_ai_provider():
    ai = MockCartoonAIProvider()
    topic = ai.generate_topic("AI Tech", "bn")
    assert topic["topic_title"] == "AI Robot Learns to Cook Fish Curry"

    script = ai.generate_script(topic, 12, "bn")
    assert len(script["dialogues"]) == 2

    scene_plan = ai.generate_scene_plan(script)
    assert len(scene_plan["scenes"]) == 1

    metadata = ai.generate_metadata(topic, script, "bn")
    assert "#Reels" in metadata["hashtags"]


def test_ollama_hardware_compatibility():
    from app.hardware.detector import HardwareSpecs
    from app.ai.ollama_manager import OllamaHardwareManager
    from app.ai.factory import AIProviderFactory
    from app.ai.gemini import GeminiCartoonAIProvider

    # 1. Low-end setup (MX110 2GB + 8GB RAM) -> Selects ultra-lightweight tier model (qwen2.5:0.5b)
    low_specs = HardwareSpecs(
        cpu_name="i5-7200U", cpu_cores=2, cpu_threads=4,
        ram_total_gb=8.0, ram_available_gb=4.0,
        gpu_name="NVIDIA GeForce MX110", gpu_vendor="NVIDIA", vram_mb=2048,
        os_version="Windows 11", driver_version="536.23", cuda_available=True
    )
    assert OllamaHardwareManager.is_hardware_compatible(low_specs) is True
    optimal_low = OllamaHardwareManager.get_optimal_model_for_hardware(low_specs)
    assert optimal_low == "qwen2.5:0.5b"

    # 2. High-end setup (RTX 4060 / 4070 12GB + 32GB RAM) -> Selects high tier model (llama3.2:3b)
    high_specs = HardwareSpecs(
        cpu_name="i7-13700K", cpu_cores=16, cpu_threads=24,
        ram_total_gb=32.0, ram_available_gb=24.0,
        gpu_name="NVIDIA GeForce RTX 4060", gpu_vendor="NVIDIA", vram_mb=8192,
        os_version="Windows 11", driver_version="550.00", cuda_available=True
    )
    assert OllamaHardwareManager.is_hardware_compatible(high_specs) is True
    optimal_high = OllamaHardwareManager.get_optimal_model_for_hardware(high_specs)
    assert optimal_high == "llama3.2:3b"

    # 3. Factory returns Gemini by default when Ollama daemon is offline
    from unittest.mock import patch
    with patch.object(OllamaHardwareManager, "is_ollama_running", return_value=False), \
         patch.object(OllamaHardwareManager, "auto_install_ollama_if_needed", return_value=False):
        provider = AIProviderFactory.get_provider(low_specs)
        assert isinstance(provider, GeminiCartoonAIProvider)
