"""
app/utils/credentials.py
========================
Secure Credential Storage using native Windows Credential Manager (advapi32.dll).
Ensures zero plain-text storage of access tokens, refresh tokens, or secrets.
"""

import os
import sys
import json
import ctypes
from ctypes import wintypes
from typing import Any, Dict, Optional, Union
from app.utils.logging import logger


class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2


class WindowsCredentialManager:
    """
    Interfaces directly with Windows Credential Manager via Advapi32 API.
    Stores secrets encrypted under the active Windows user account.
    """

    @classmethod
    def is_supported(cls) -> bool:
        return sys.platform == "win32" and hasattr(ctypes.windll, "advapi32")

    @classmethod
    def save_credential(
        cls,
        target_name: str,
        username: str,
        secret_data: Union[str, Dict[str, Any]],
        comment: str = "FA Automation Secure Credential",
    ) -> bool:
        """
        Saves a secret into Windows Credential Manager under target_name.
        """
        if not cls.is_supported():
            logger.error("Windows Credential Manager is only supported on Windows.")
            return False

        try:
            if isinstance(secret_data, dict):
                raw_bytes = json.dumps(secret_data).encode("utf-8")
            elif isinstance(secret_data, str):
                raw_bytes = secret_data.encode("utf-8")
            else:
                raw_bytes = str(secret_data).encode("utf-8")

            blob = (ctypes.c_byte * len(raw_bytes))(*raw_bytes)

            cred = CREDENTIAL()
            cred.Flags = 0
            cred.Type = CRED_TYPE_GENERIC
            cred.TargetName = target_name
            cred.Comment = comment
            cred.CredentialBlobSize = len(raw_bytes)
            cred.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_byte))
            cred.Persist = CRED_PERSIST_LOCAL_MACHINE
            cred.UserName = username

            result = ctypes.windll.advapi32.CredWriteW(ctypes.byref(cred), 0)
            if result:
                logger.info(f"Securely saved credential '{target_name}' to Windows Credential Manager.")
                return True
            else:
                err = ctypes.GetLastError()
                logger.error(f"CredWriteW failed for '{target_name}' with Win32 error: {err}")
                return False
        except Exception as e:
            logger.error(f"Exception saving credential '{target_name}': {e}")
            return False

    @classmethod
    def load_credential(cls, target_name: str) -> Optional[Union[Dict[str, Any], str]]:
        """
        Loads and decrypts a secret from Windows Credential Manager.
        Returns parsed JSON dict if applicable, else string, or None if not found.
        """
        if not cls.is_supported():
            return None

        p_cred = ctypes.POINTER(CREDENTIAL)()
        try:
            ok = ctypes.windll.advapi32.CredReadW(
                target_name,
                CRED_TYPE_GENERIC,
                0,
                ctypes.byref(p_cred),
            )
            if not ok:
                return None

            raw_bytes = ctypes.string_at(
                p_cred.contents.CredentialBlob,
                p_cred.contents.CredentialBlobSize,
            )
            text = raw_bytes.decode("utf-8")
            try:
                return json.loads(text)
            except Exception:
                return text
        except Exception as e:
            logger.error(f"Exception reading credential '{target_name}': {e}")
            return None
        finally:
            if p_cred:
                ctypes.windll.advapi32.CredFree(p_cred)

    @classmethod
    def delete_credential(cls, target_name: str) -> bool:
        """
        Removes a credential from Windows Credential Manager.
        """
        if not cls.is_supported():
            return False

        try:
            result = ctypes.windll.advapi32.CredDeleteW(target_name, CRED_TYPE_GENERIC, 0)
            if result:
                logger.info(f"Deleted credential '{target_name}' from Windows Credential Manager.")
                return True
            return False
        except Exception as e:
            logger.error(f"Exception deleting credential '{target_name}': {e}")
            return False

    @classmethod
    def has_credential(cls, target_name: str) -> bool:
        """
        Returns True if credential exists in Windows Credential Manager.
        """
        return cls.load_credential(target_name) is not None

