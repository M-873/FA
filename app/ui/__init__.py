"""
Lightweight Windows GUI Package & Modern CustomTkinter Desktop Interface.
"""
from app.ui.main_window import AutoPostDashboardApp, CartoonAutomationUI, launch_gui


def launch_modern_gui() -> None:
    """Launches modern CustomTkinter Studio UI with lazy module import."""
    from app.ui.modern_app import launch_modern_gui as _launch
    _launch()


__all__ = [
    "AutoPostDashboardApp",
    "CartoonAutomationUI",
    "launch_gui",
    "launch_modern_gui",
]
