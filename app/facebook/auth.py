import httpx
from typing import Dict, Any
from app.utils.config import get_env_settings
from app.utils.logging import logger



class MetaAuthValidator:
    """Validates Meta Page Access Token and inspects Page information."""

    def __init__(self, access_token: str = None, page_id: str = None, api_version: str = None):
        env = get_env_settings()
        self.access_token = access_token or env.META_ACCESS_TOKEN
        self.page_id = page_id or env.META_PAGE_ID
        self.api_version = api_version or env.META_API_VERSION

        self.graph_url = f"https://graph.facebook.com/{self.api_version}"

    def validate_access_token(self) -> Dict[str, Any]:
        """Inspects token validity and permissions via debug_token endpoint."""
        if not self.access_token or not self.page_id:
            logger.warning("META_ACCESS_TOKEN or META_PAGE_ID is missing. Meta authentication check skipped.")
            return {"valid": False, "reason": "Missing credentials"}

        try:
            url = f"{self.graph_url}/{self.page_id}"
            params = {
                "fields": "id,name,category,access_token",
                "access_token": self.access_token,
            }
            response = httpx.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Meta Page Access Token verified successfully for Page: '{data.get('name')}' (ID: {data.get('id')})")
                return {"valid": True, "page_name": data.get("name"), "page_id": data.get("id")}
            else:
                logger.error(f"Meta Token validation failed: {response.status_code} - {response.text}")
                return {"valid": False, "error": response.text}
        except Exception as e:
            logger.error(f"Error checking Meta access token: {e}")
            return {"valid": False, "error": str(e)}
