"""
tests/test_youtube.py
=====================
Automated tests for YouTube integration:
- Windows Credential Manager secure persistence
- YouTube Data API v3 channel verification (strictly verifying @Life-X-873)
- Mismatch detection
- Resumable upload & dry-run publishing
"""

import pytest
from unittest.mock import MagicMock
from app.utils.credentials import WindowsCredentialManager
from app.youtube.auth import (
    YouTubeAuthManager,
    TARGET_CHANNEL_HANDLE,
    TARGET_CHANNEL_TITLE,
    CREDENTIAL_TARGET,
)
from app.youtube.publisher import YouTubePublisher


def test_windows_credential_manager():
    """Verifies that Windows Credential Manager correctly saves, loads, and deletes encrypted data."""
    test_target = "FA_Test_Cred_Target"
    test_data = {"token": "ya29.test123", "refresh_token": "1//test456", "scopes": ["read"]}

    assert WindowsCredentialManager.is_supported() is True

    # Save
    saved = WindowsCredentialManager.save_credential(test_target, "Life-X-873", test_data)
    assert saved is True

    # Has credential
    assert WindowsCredentialManager.has_credential(test_target) is True

    # Load & Verify
    loaded = WindowsCredentialManager.load_credential(test_target)
    assert isinstance(loaded, dict)
    assert loaded["token"] == "ya29.test123"
    assert loaded["refresh_token"] == "1//test456"

    # Delete
    deleted = WindowsCredentialManager.delete_credential(test_target)
    assert deleted is True
    assert WindowsCredentialManager.has_credential(test_target) is False
    assert WindowsCredentialManager.load_credential(test_target) is None


def test_channel_verification_success_by_handle():
    """Verifies that a channel with customUrl @Life-X-873 is verified successfully."""
    auth_mgr = YouTubeAuthManager()

    mock_service = MagicMock()
    mock_service.channels().list().execute.return_value = {
        "items": [
            {
                "id": "UC_TEST_CHANNEL_ID_12345",
                "snippet": {
                    "title": "Life X",
                    "customUrl": "@Life-X-873",
                },
                "statistics": {"viewCount": "1000", "subscriberCount": "50"},
            }
        ]
    }

    result = auth_mgr.verify_authenticated_channel(mock_service)
    assert result["verified"] is True
    assert result["channel_id"] == "UC_TEST_CHANNEL_ID_12345"
    assert result["custom_url"] == "@Life-X-873"


def test_channel_verification_success_by_title():
    """Verifies that a channel with title Life-X-873 is verified successfully."""
    auth_mgr = YouTubeAuthManager()

    mock_service = MagicMock()
    mock_service.channels().list().execute.return_value = {
        "items": [
            {
                "id": "UC_TEST_CHANNEL_ID_67890",
                "snippet": {
                    "title": "Life-X-873",
                    "customUrl": "",
                },
                "statistics": {"viewCount": "500"},
            }
        ]
    }

    result = auth_mgr.verify_authenticated_channel(mock_service)
    assert result["verified"] is True
    assert result["channel_id"] == "UC_TEST_CHANNEL_ID_67890"


def test_channel_verification_mismatch():
    """Verifies that authenticating with an unrelated channel is rejected with a clear explanation."""
    auth_mgr = YouTubeAuthManager()

    mock_service = MagicMock()
    mock_service.channels().list().execute.return_value = {
        "items": [
            {
                "id": "UC_WRONG_CHANNEL",
                "snippet": {
                    "title": "Unrelated Personal Vlog",
                    "customUrl": "@some_other_vlog",
                },
            }
        ]
    }

    result = auth_mgr.verify_authenticated_channel(mock_service)
    assert result["verified"] is False
    assert "mismatch" in result["reason"].lower()


def test_youtube_publisher_dry_run():
    """Verifies dry run mode creates formatted payload without actual network upload."""
    pub = YouTubePublisher()
    pub.env.DRY_RUN = True

    res = pub.publish_short(
        video_path="dummy.mp4",
        title="Test Animation",
        description="Daily Cartoon Short",
        hashtags=["#Shorts", "#Tech"],
    )

    assert res["success"] is True
    assert res["dry_run"] is True
    assert "DRY_RUN" in res["video_id"]

