"""
app/utils/windows.py
===================
Windows OS integration utilities:
- "Start with Windows" Registry management (HKCU Run key)
- Windows Credential Manager integration for masked API keys
- Safe path / folder opening in Windows Explorer
"""

import sys
import os
import subprocess
from typing import Optional
from app.utils.logging import logger

if sys.platform == "win32":
    import winreg
    import ctypes
    from ctypes import wintypes


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_RUN_NAME = "FA_DailyVideoAutomation"


def is_start_with_windows_enabled(app_name: str = APP_RUN_NAME) -> bool:
    """Checks whether the application is registered in HKCU Run registry key."""
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, app_name)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning(f"Error checking Windows startup registry: {e}")
        return False


def set_start_with_windows(enable: bool, app_name: str = APP_RUN_NAME, args: str = "--tray") -> bool:
    """
    Enables or disables automatic launch on Windows login using HKCU Run key.
    Uses dynamic sys.executable resolution (no machine-specific usernames or hardcoded paths).
    """
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                python_exe = sys.executable
                # Wrap paths with spaces in quotes
                cmd = f'"{python_exe}" -m app.main {args}'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
                logger.info(f"Registered Windows startup command: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    logger.info("Unregistered Windows startup entry.")
                except FileNotFoundError:
                    pass
            return True
    except Exception as e:
        logger.error(f"Error updating Windows startup registry: {e}")
        return False


def open_folder_in_explorer(folder_path: str) -> bool:
    """Opens a folder safely in Windows Explorer without freezing the application."""
    abs_path = os.path.abspath(folder_path)
    if not os.path.exists(abs_path):
        os.makedirs(abs_path, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(abs_path)
        else:
            subprocess.Popen(["xdg-open", abs_path])
        return True
    except Exception as e:
        logger.warning(f"Could not open folder in Explorer: {e}")
        return False
