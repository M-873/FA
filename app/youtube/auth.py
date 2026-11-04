import os
import json
import argparse
from typing import Optional, Any
from app.utils.config import get_env_settings
from app.utils.logging import logger

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]


class YouTubeAuthManager:
    """Manages YouTube Data API v3 OAuth 2.0 authentication and token persistence."""

    def __init__(self, token_file: str = "youtube_token.json"):
        self.token_file = token_file
        self.env = get_env_settings()

    def get_authenticated_service(self) -> Optional[Any]:
        """Returns authenticated YouTube API service client."""
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                # Refresh if expired
                if creds and creds.expired and creds.refresh_token:
                    from google.auth.transport.requests import Request
                    creds.refresh(Request())
                    with open(self.token_file, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                return build("youtube", "v3", credentials=creds)

            logger.warning(f"No existing YouTube OAuth token found at {self.token_file}.")
            return None
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")
            return None

    def authenticate_interactive(self, client_secrets_file: str = "client_secret.json") -> bool:
        """
        Runs interactive one-time browser OAuth flow and saves token to youtube_token.json.
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = None
            if os.path.exists(client_secrets_file):
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            elif self.env.YOUTUBE_CLIENT_ID and self.env.YOUTUBE_CLIENT_SECRET:
                client_config = {
                    "installed": {
                        "client_id": self.env.YOUTUBE_CLIENT_ID,
                        "client_secret": self.env.YOUTUBE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost:8088/"]
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            else:
                logger.error(
                    "Cannot authenticate YouTube: Neither client_secret.json nor YOUTUBE_CLIENT_ID/SECRET in .env was found."
                )
                print("\n[ERROR] Missing YouTube OAuth credentials.")
                print("Option A: Place your downloaded 'client_secret.json' in the project root folder.")
                print("Option B: Put YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in your .env file.\n")
                return False

            print("\n=======================================================")
            print("🎬 LAUNCHING GOOGLE YOUTUBE OAUTH 2.0 AUTHENTICATION")
            print("Opening your web browser for a one-time login...")
            print("=======================================================\n")

            creds = flow.run_local_server(port=8088, prompt="consent")
            with open(self.token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

            logger.info(f"YouTube OAuth token saved successfully to {self.token_file}!")
            print(f"\n[SUCCESS] YouTube connected successfully! Token saved to: {self.token_file}\n")
            return True
        except Exception as e:
            logger.error(f"YouTube interactive authentication failed: {e}")
            print(f"\n[ERROR] YouTube authentication failed: {e}\n")
            return False


def main():
    parser = argparse.ArgumentParser(description="YouTube Data API v3 OAuth Authentication Utility")
    parser.add_argument("--login", action="store_true", help="Launch interactive browser login to connect YouTube")
    parser.add_argument("--check", action="store_true", help="Check current YouTube connection status")
    parser.add_argument("--client-secret", default="client_secret.json", help="Path to Google client_secret.json")

    args = parser.parse_args()
    auth_mgr = YouTubeAuthManager()

    if args.login or (not args.check and not args.login):
        auth_mgr.authenticate_interactive(args.client_secret)
    elif args.check:
        service = auth_mgr.get_authenticated_service()
        if service:
            try:
                res = service.channels().list(mine=True, part="snippet").execute()
                items = res.get("items", [])
                if items:
                    title = items[0]["snippet"]["title"]
                    print(f"\n[CONNECTED] YouTube Connected to Channel: {title}\n")
                else:
                    print("\n[CONNECTED] YouTube OAuth token valid.\n")
            except Exception as e:
                print(f"\n[WARNING] Token valid but channel query failed: {e}\n")
        else:
            print("\n[DISCONNECTED] YouTube is not authenticated yet. Run: python -m app.youtube.auth --login\n")


if __name__ == "__main__":
    main()
