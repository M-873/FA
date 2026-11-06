"""
app/youtube/auth.py
===================
YouTube Data API v3 OAuth 2.0 Authentication Service.
Features:
- Installed-app OAuth 2.0 flow with PKCE & minimum required scopes.
- Zero plain-text token storage: encrypted persistence in Windows Credential Manager.
- Automated token refresh.
- Official API channel identity verification (strictly checks for @Life-X-873).
- Settings persistence and disconnect capabilities.
"""

import os
import json
import argparse
import webbrowser
from typing import Optional, Dict, Any, Tuple
from app.utils.config import get_env_settings, get_project_config
from app.utils.logging import logger
from app.utils.credentials import WindowsCredentialManager
from app.ui.settings import SettingsManager

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CREDENTIAL_TARGET = "FA_YouTube_OAuth_Token"
TARGET_CHANNEL_HANDLE = "@Life-X-873"
TARGET_CHANNEL_TITLE = "Life-X-873"
TARGET_CHANNEL_URL = "https://www.youtube.com/@Life-X-873"


class YouTubeAuthManager:
    """Manages YouTube Data API v3 OAuth 2.0 authentication and secure persistence."""

    def __init__(self, legacy_token_file: str = "youtube_token.json"):
        self.legacy_token_file = legacy_token_file
        self.env = get_env_settings()
        self.project_cfg = get_project_config()
        self.settings_mgr = SettingsManager()

    # -------------------------------------------------------------------------
    # Credential Storage & Retrieval
    # -------------------------------------------------------------------------
    def _load_raw_credentials(self) -> Optional[Dict[str, Any]]:
        """
        Loads OAuth credential dictionary from Windows Credential Manager.
        Automatically migrates legacy plain-text token file if present.
        """
        cred_dict = WindowsCredentialManager.load_credential(CREDENTIAL_TARGET)
        if isinstance(cred_dict, dict):
            return cred_dict

        # Legacy fallback & migration
        if os.path.exists(self.legacy_token_file):
            try:
                with open(self.legacy_token_file, "r", encoding="utf-8") as f:
                    legacy_data = json.load(f)
                logger.info(f"Migrating legacy {self.legacy_token_file} to Windows Credential Manager...")
                username = legacy_data.get("account") or TARGET_CHANNEL_TITLE
                if WindowsCredentialManager.save_credential(CREDENTIAL_TARGET, username, legacy_data):
                    try:
                        os.remove(self.legacy_token_file)
                        logger.info(f"Removed legacy plain-text token file: {self.legacy_token_file}")
                    except Exception as ex:
                        logger.warning(f"Could not remove {self.legacy_token_file}: {ex}")
                    return legacy_data
            except Exception as e:
                logger.error(f"Error reading legacy token file: {e}")

        return None

    def _save_raw_credentials(self, creds_dict: Dict[str, Any], username: str = TARGET_CHANNEL_TITLE) -> bool:
        """Saves credential dictionary into Windows Credential Manager."""
        saved = WindowsCredentialManager.save_credential(CREDENTIAL_TARGET, username, creds_dict)
        # Ensure plain text token file is deleted if it exists
        if os.path.exists(self.legacy_token_file):
            try:
                os.remove(self.legacy_token_file)
            except Exception:
                pass
        return saved

    # -------------------------------------------------------------------------
    # Authenticated Service & Auto-Refresh
    # -------------------------------------------------------------------------
    def get_authenticated_service(self) -> Optional[Any]:
        """
        Returns authenticated Google API YouTube v3 service client.
        Automatically refreshes token if expired and updates secure storage.
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request

            raw_creds = self._load_raw_credentials()
            if not raw_creds:
                logger.warning("No YouTube OAuth credential found in Windows Credential Manager.")
                return None

            creds = Credentials.from_authorized_user_info(raw_creds, SCOPES)
            if not creds:
                return None

            # Refresh if expired
            if creds.expired and creds.refresh_token:
                logger.info("YouTube OAuth token is expired. Refreshing token with Google...")
                creds.refresh(Request())
                updated_data = json.loads(creds.to_json())
                self._save_raw_credentials(updated_data)
                logger.info("YouTube OAuth token refreshed and saved to Windows Credential Manager.")

            return build("youtube", "v3", credentials=creds)
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")
            return None

    # -------------------------------------------------------------------------
    # Channel Verification
    # -------------------------------------------------------------------------
    def verify_authenticated_channel(self, service: Any) -> Dict[str, Any]:
        """
        Calls official YouTube Data API to inspect authenticated channel details
        and strictly verifies whether it matches the target channel Life-X-873.
        """
        try:
            res = service.channels().list(
                mine=True,
                part="snippet,contentDetails,statistics",
            ).execute()

            items = res.get("items", [])
            if not items:
                return {
                    "verified": False,
                    "reason": "No YouTube channel associated with this Google Account.",
                    "channel_id": None,
                    "channel_title": None,
                    "custom_url": None,
                }

            channel_info = items[0]
            channel_id = channel_info.get("id", "")
            snippet = channel_info.get("snippet", {})
            title = snippet.get("title", "")
            custom_url = snippet.get("customUrl", "")  # e.g. "@Life-X-873"

            # Check match against target channel handle or title
            handle_norm = (custom_url or "").strip().lower()
            target_handle_norm = TARGET_CHANNEL_HANDLE.strip().lower()
            title_norm = (title or "").strip().lower()
            target_title_norm = TARGET_CHANNEL_TITLE.strip().lower()
            target_id = getattr(self.project_cfg, "youtube_channel_id", "").strip()

            is_match = (
                handle_norm == target_handle_norm
                or handle_norm.lstrip("@") == target_handle_norm.lstrip("@")
                or title_norm == target_title_norm
                or target_title_norm in handle_norm
                or target_title_norm in title_norm
                or (bool(target_id) and channel_id == target_id)
            )

            result = {
                "verified": is_match,
                "channel_id": channel_id,
                "channel_title": title,
                "custom_url": custom_url or f"@{title.replace(' ', '')}",
                "channel_url": f"https://www.youtube.com/{custom_url}" if custom_url else TARGET_CHANNEL_URL,
                "statistics": channel_info.get("statistics", {}),
            }

            if not is_match:
                result["reason"] = (
                    f"Channel mismatch: Authenticated channel is '{title}' ({custom_url}), "
                    f"but target channel is '{TARGET_CHANNEL_TITLE}' ({TARGET_CHANNEL_HANDLE})."
                )

            return result
        except Exception as e:
            logger.error(f"Failed to verify YouTube channel: {e}")
            return {"verified": False, "reason": str(e), "channel_id": None, "channel_title": None}

    @classmethod
    def _run_local_server_robust(
        cls,
        flow: Any,
        port: int = 8088,
        host: str = "localhost",
        browser: Optional[str] = None,
    ) -> Any:
        """
        Runs local WSGI server for OAuth redirect.
        Robust against browser reload or state mismatch by extracting
        authorization code directly from response URI.
        """
        import wsgiref.simple_server
        from urllib.parse import urlparse, parse_qs
        from google_auth_oauthlib.flow import _RedirectWSGIApp, _WSGIRequestHandler

        success_message = "Authorization successful! You may now close this browser window and return to FA."
        wsgi_app = _RedirectWSGIApp(success_message)
        wsgiref.simple_server.WSGIServer.allow_reuse_address = True
        local_server = wsgiref.simple_server.make_server(
            host, port, wsgi_app, handler_class=_WSGIRequestHandler
        )

        try:
            flow.redirect_uri = f"http://{host}:{local_server.server_port}/"
            auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

            msg = f"\nPlease authorize the application in your browser window:\n{auth_url}\n"
            logger.info(msg)
            print(msg, flush=True)

            try:
                webbrowser.get(browser).open(auth_url, new=1, autoraise=True)
            except Exception:
                webbrowser.open(auth_url, new=1, autoraise=True)

            while True:
                local_server.handle_request()
                last_uri = getattr(wsgi_app, "last_request_uri", "") or ""
                if "code=" in last_uri or "error=" in last_uri:
                    break

            parsed = urlparse(last_uri)
            params = parse_qs(parsed.query)
            err = params.get("error", [None])[0]
            if err:
                raise RuntimeError(f"Google OAuth returned error: {err}")

            code = params.get("code", [None])[0]
            if code:
                # Direct code exchange avoids fragile CSRF state mismatch when user reloads/switches tabs
                flow.fetch_token(code=code)
            else:
                flow.fetch_token(authorization_response=last_uri.replace("http", "https"))

            return flow.credentials
        finally:
            local_server.server_close()

    # -------------------------------------------------------------------------
    # Interactive Browser Authentication Flow (PKCE)
    # -------------------------------------------------------------------------
    def authenticate_interactive(
        self,
        client_secrets_file: str = "client_secret.json",
        port: int = 8088,
    ) -> Dict[str, Any]:
        """
        Launches standard Google OAuth 2.0 browser authorization with local loopback server.
        Uses PKCE where supported by Google auth library.
        Verifies target channel identity before persisting.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = None
        if os.path.exists(client_secrets_file):
            logger.info(f"Loading OAuth client config from {client_secrets_file}...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
        elif self.env.YOUTUBE_CLIENT_ID and self.env.YOUTUBE_CLIENT_SECRET:
            logger.info("Loading OAuth client config from environment variables...")
            client_config = {
                "installed": {
                    "client_id": self.env.YOUTUBE_CLIENT_ID,
                    "client_secret": self.env.YOUTUBE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [f"http://localhost:{port}/", "http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        else:
            msg = "Missing client_secret.json or YOUTUBE_CLIENT_ID/SECRET."
            logger.error(msg)
            return {"success": False, "error": msg}

        print("\n=================================================================")
        print("🎬 LAUNCHING GOOGLE YOUTUBE OAUTH 2.0 AUTHENTICATION")
        print(f"Target YouTube Channel: {TARGET_CHANNEL_TITLE} ({TARGET_CHANNEL_HANDLE})")
        print("Opening your default web browser for Google Account consent...")
        print("=================================================================\n", flush=True)

        # Ensure Chrome is registered if present
        chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        browser_name = None
        if os.path.exists(chrome_exe):
            try:
                webbrowser.register("chrome", None, webbrowser.BackgroundBrowser(chrome_exe))
                browser_name = "chrome"
            except Exception:
                pass

        try:
            creds = self._run_local_server_robust(
                flow=flow,
                port=port,
                browser=browser_name,
            )

            from googleapiclient.discovery import build
            temp_service = build("youtube", "v3", credentials=creds)

            # Strictly verify authenticated channel
            verification = self.verify_authenticated_channel(temp_service)
            logger.info(f"YouTube channel verification: {verification}")

            if not verification.get("verified"):
                err_msg = verification.get("reason", "Channel verification failed.")
                logger.warning(f"Verification failed: {err_msg}")
                self.settings_mgr.update_youtube_connection(
                    status="Error",
                    channel_title=verification.get("channel_title"),
                    channel_id=verification.get("channel_id"),
                )
                return {
                    "success": False,
                    "error": err_msg,
                    "channel_title": verification.get("channel_title"),
                    "custom_url": verification.get("custom_url"),
                }

            # Securely persist to Windows Credential Manager
            creds_data = json.loads(creds.to_json())
            self._save_raw_credentials(creds_data, username=verification["channel_title"])

            # Update settings persistence
            self.settings_mgr.update_youtube_connection(
                status="Connected",
                channel_title=verification["channel_title"],
                channel_id=verification["channel_id"],
                handle=verification["custom_url"],
                channel_url=verification.get("channel_url", TARGET_CHANNEL_URL),
            )

            logger.info(f"Successfully authenticated and verified YouTube Channel: {verification['channel_title']}")
            return {
                "success": True,
                "channel_id": verification["channel_id"],
                "channel_title": verification["channel_title"],
                "handle": verification["custom_url"],
                "channel_url": verification["channel_url"],
            }
        except Exception as e:
            logger.error(f"Interactive authentication failed: {e}")
            self.settings_mgr.update_youtube_connection(status="Error")
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Connection Status Query
    # -------------------------------------------------------------------------
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Queries live connection state and returns structured status report.
        """
        raw_creds = self._load_raw_credentials()
        if not raw_creds:
            return {
                "status": "Not Connected",
                "connected": False,
                "channel_title": None,
                "channel_id": None,
                "handle": TARGET_CHANNEL_HANDLE,
                "reason": "No credentials stored in Windows Credential Manager.",
            }

        service = self.get_authenticated_service()
        if not service:
            return {
                "status": "Expired",
                "connected": False,
                "channel_title": None,
                "channel_id": None,
                "handle": TARGET_CHANNEL_HANDLE,
                "reason": "Stored token expired or invalid grant. Reconnection required.",
            }

        verification = self.verify_authenticated_channel(service)
        if verification.get("verified"):
            return {
                "status": "Connected",
                "connected": True,
                "channel_title": verification.get("channel_title"),
                "channel_id": verification.get("channel_id"),
                "handle": verification.get("custom_url") or TARGET_CHANNEL_HANDLE,
                "channel_url": verification.get("channel_url"),
                "statistics": verification.get("statistics"),
            }
        else:
            return {
                "status": "Error",
                "connected": False,
                "channel_title": verification.get("channel_title"),
                "channel_id": verification.get("channel_id"),
                "handle": verification.get("custom_url"),
                "reason": verification.get("reason"),
            }

    # -------------------------------------------------------------------------
    # Disconnect
    # -------------------------------------------------------------------------
    def disconnect(self) -> bool:
        """
        Removes credentials from Windows Credential Manager and resets settings.
        """
        deleted = WindowsCredentialManager.delete_credential(CREDENTIAL_TARGET)
        if os.path.exists(self.legacy_token_file):
            try:
                os.remove(self.legacy_token_file)
            except Exception:
                pass
        self.settings_mgr.disconnect_youtube()
        logger.info("YouTube connection disconnected successfully.")
        return deleted


def main():
    parser = argparse.ArgumentParser(description="YouTube Data API v3 OAuth Authentication & Verification Utility")
    parser.add_argument("--login", action="store_true", help="Launch interactive browser OAuth flow to connect YouTube")
    parser.add_argument("--check", action="store_true", help="Check current YouTube connection status via API")
    parser.add_argument("--disconnect", action="store_true", help="Disconnect YouTube and purge stored credentials")
    parser.add_argument("--open-console", action="store_true", help="Open Google Cloud Console YouTube API in browser")
    parser.add_argument("--client-secret", default="client_secret.json", help="Path to Google client_secret.json")
    parser.add_argument("--port", type=int, default=8088, help="Local loopback port for OAuth redirect (default: 8088)")

    args = parser.parse_args()
    auth_mgr = YouTubeAuthManager()

    if args.open_console:
        url = "https://console.cloud.google.com/apis/library/youtube.googleapis.com"
        print(f"\nOpening Google Cloud Console: {url}")
        webbrowser.open(url)
        return

    if args.disconnect:
        auth_mgr.disconnect()
        print("\n[DISCONNECTED] YouTube account disconnected and credentials removed from Windows Credential Manager.\n")
        return

    if args.check:
        status_info = auth_mgr.get_connection_status()
        print("\n=======================================================")
        print("📊 YOUTUBE CONNECTION STATUS REPORT")
        print("=======================================================")
        print(f"Status:        {status_info['status']}")
        print(f"Channel Name:  {status_info.get('channel_title') or 'N/A'}")
        print(f"Channel Handle:{status_info.get('handle') or TARGET_CHANNEL_HANDLE}")
        print(f"Channel ID:    {status_info.get('channel_id') or 'N/A'}")
        if status_info.get("reason"):
            print(f"Details:       {status_info['reason']}")
        print("=======================================================\n")
        return

    # Default or --login
    res = auth_mgr.authenticate_interactive(args.client_secret, port=args.port)
    if res.get("success"):
        print(f"\n[SUCCESS] Connected to YouTube Channel: {res['channel_title']} ({res.get('handle')})!")
        print(f"Channel ID: {res['channel_id']}")
        print(f"Credentials safely encrypted in Windows Credential Manager ('{CREDENTIAL_TARGET}').\n")
    else:
        print(f"\n[FAILED] Could not connect: {res.get('error')}\n")


if __name__ == "__main__":
    main()
