"""Debrid-Link API service"""
import aiohttp
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

API_BASE = "https://debrid-link.fr/api/v2"

class DebridService:
    def __init__(self, api_key: str = None):
        from config import config
        self.api_key = api_key or config.DEBRID_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.session = None

    async def get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        session = await self.get_session()
        try:
            async with session.request(method, f"{API_BASE}{endpoint}", **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientResponseError as e:
            # Clean error message formatting
            error_msg = f"{e.status} {e.message}"
            logger.error(f"API Error: {error_msg} - {endpoint}")
            return {"success": False, "error": error_msg, "status_code": e.status}
        except aiohttp.ClientError as e:
            # Other network errors
            logger.error(f"Network Error: {e}")
            return {"success": False, "error": "Network error occurred"}

    async def add_magnet(self, magnet_link: str) -> Dict[str, Any]:
        # Use JSON payload
        return await self._request("POST", "/seedbox/add", json={"url": magnet_link, "async": True})
    
    async def add_file(self, file_bytes: bytes) -> Dict[str, Any]:
        data = aiohttp.FormData()
        data.add_field('file', file_bytes, filename='torrent.torrent', content_type='application/x-bittorrent')
        return await self._request("POST", "/seedbox/add", data=data)

    async def add_hoster_link(self, link: str) -> Dict[str, Any]:
        return await self._request("POST", "/downloader/add", json={"url": link, "async": False})

    async def delete_torrent(self, torrent_id: str) -> Dict[str, Any]:
        return await self._request("DELETE", f"/seedbox/{torrent_id}/remove")

    async def get_seedbox_torrents(self) -> Dict[str, Any]:
        return await self._request("GET", "/seedbox/list")
    
    async def create_zip(self, torrent_id: str, file_ids: list) -> Dict[str, Any]:
        """
        Create a ZIP archive of specific files
        
        Args:
            torrent_id: The torrent ID
            file_ids: List of file IDs to zip
            
        Returns:
            Response with ZIP download link
        """
        # IDs must be comma-delimited string or JSON array
        ids_str = ",".join(file_ids)
        logger.info(f"Creating ZIP for torrent {torrent_id} with files: {ids_str}")
        
        return await self._request("POST", f"/seedbox/{torrent_id}/zip", json={"ids": ids_str})

    async def get_limits(self) -> Dict[str, Any]:
        """
        Get account limits and usage statistics
        
        Returns:
            Dict containing usagePercent, dayCount, etc.
        """
        return await self._request("GET", "/seedbox/limits")

debrid_service = DebridService()
