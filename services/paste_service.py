"""
Paste service for uploading file links
Uses reliable paste services with proper error handling
"""
import aiohttp
from typing import Optional


class PasteService:
    """Service for uploading text to paste sites"""
    
    def __init__(self):
        # Using dpaste.com - simple and reliable
        self.dpaste_url = "https://dpaste.com"
        
    async def upload_to_dpaste(self, content: str) -> Optional[str]:
        """
        Upload content to dpaste.com
        Returns the paste URL or None if failed
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "content": content,
                    "syntax": "text",
                    "expiry_days": 7
                }
                
                async with session.post(
                    f"{self.dpaste_url}/api/v2/",
                    data=payload
                ) as resp:
                    if resp.status in [200, 201]:
                        # dpaste returns the URL directly in text
                        url = (await resp.text()).strip()
                        if url and url.startswith('http'):
                            return url
            return None
        except Exception as e:
            print(f"Dpaste upload error: {e}")
            return None
    
    async def upload_to_termbin(self, content: str) -> Optional[str]:
        """
        Upload to termbin.com via netcat (super reliable)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://termbin.com",
                    data=content.encode('utf-8')
                ) as resp:
                    if resp.status == 200:
                        url = (await resp.text()).strip()
                        if url and url.startswith('http'):
                            return url
            return None
        except Exception as e:
            print(f"Termbin upload error: {e}")
            return None
    
    async def upload_to_spacebin(self, content: str) -> Optional[str]:
        """
        Upload to spaceb.in (modern paste service)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "content": content
                }
                
                logger.info("Uploading to spaceb.in...")
                async with session.post(
                    "https://spaceb.in/api/",
                    json=payload
                ) as resp:
                    logger.info(f"Spacebin response status: {resp.status}")
                    if resp.status in [200, 201]:
                        data = await resp.json()
                        logger.info(f"Spacebin response data: {data}")
                        # spaceb.in returns {"payload": {"id": "abc123"}} or just {"id": "abc123"}
                        doc_id = data.get("payload", {}).get("id") or data.get("id")
                        if doc_id:
                            url = f"https://spaceb.in/{doc_id}"
                            logger.info(f"Successfully uploaded to spaceb.in: {url}")
                            return url
                        else:
                            logger.error(f"No document ID in response: {data}")
                    else:
                        error_text = await resp.text()
                        logger.error(f"Spacebin upload failed with status {resp.status}: {error_text}")
            return None
        except Exception as e:
            logger.error(f"Spacebin upload error: {e}", exc_info=True)
            return None
    
    async def create_paste(self, file_links: list, torrent_name: str) -> Optional[str]:
        """
        Create a paste with all file download links
        
        Args:
            file_links: List of file dicts with 'name' and 'downloadUrl'
            torrent_name: Name of the torrent
            
        Returns:
            URL to the paste or None if failed
        """
        if not file_links:
            return None
        
        # Format the content
        content_lines = [
            f"🎬 {torrent_name}",
            f"📦 Total Files: {len(file_links)}",
            "",
            "📥 Download Links:",
            "=" * 80,
            ""
        ]
        
        for i, file in enumerate(file_links, 1):
            file_name = file.get('name', 'Unknown')
            file_url = file.get('downloadUrl', '')
            file_size = file.get('size', 0)
            
            # Format size
            if file_size:
                size_gb = file_size / (1024**3)
                size_mb = file_size / (1024**2)
                if size_gb >= 1:
                    size_str = f"{size_gb:.2f} GB"
                else:
                    size_str = f"{size_mb:.2f} MB"
            else:
                size_str = "Unknown size"
            
            content_lines.append(f"{i}. {file_name}")
            content_lines.append(f"   Size: {size_str}")
            content_lines.append(f"   {file_url}")
            content_lines.append("")
        
        content_lines.extend([
            "=" * 80,
            "",
            "💡 Tip: Use a download manager (JDownloader, IDM) to batch download all files.",
            "",
            f"🤖 Generated by Debrid-Link Bot"
        ])
        
        content = "\n".join(content_lines)
        
        # Try dpaste first
        paste_url = await self.upload_to_dpaste(content)
        
        # Fallback to termbin
        if not paste_url:
            paste_url = await self.upload_to_termbin(content)
        
        return paste_url


paste_service = PasteService()
