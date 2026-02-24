"""File link generation and management."""

import os
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


async def get_file_links(files: List[Dict[str, Any]], torrent_id: str = "", torrent_name: str = "") -> Tuple[str, Optional[str]]:
    """
    Generates formatted links for files, distinguishing streams.
    
    Args:
        files: List of file objects
        torrent_id: The torrent ID (required when files > 1)
        torrent_name: The torrent name (required when files > 1)
        
    Returns:
        Tuple of (formatted_text, file_list_id)
        - formatted_text: The text to display in Telegram message
        - file_list_id: UUID of file list in database (None if single file)
    """
    from utils.url_proxy import encode_url
    
    links_text = ""
    file_list_id = None
    
    if not files:
        return links_text, file_list_id
    
    links_text = "\n\n📂 **Files:**"
    VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv'}
    
    # If more than 1 file, save to database for web viewing
    if len(files) > 1:
        from services.file_list_service import create_file_list
        try:
            file_list_id = await create_file_list(torrent_id, torrent_name, files)
            logger.info(f"Created file list {file_list_id} for {len(files)} files")
        except Exception as e:
            logger.error(f"Failed to create file list: {e}")
            # Continue without file list ID
    
    count = 0
    for f in files:
        if count >= 10:  # Show first 10 files in message
            remaining = len(files) - 10
            links_text += f"\n...and {remaining} more."
            if file_list_id:
                links_text += " Click the button below to see all files on web."
            break
            
        if "downloadUrl" in f:
            name = f['name']
            ext = os.path.splitext(name)[1].lower()
            
            # Proxify the URL for embedded link
            proxied_url = encode_url(f['downloadUrl'], name)
            
            if ext in VIDEO_EXTS:
                # Video file with proxified link
                links_text += f"\n- 🎬 [{name}]({proxied_url})"
            else:
                # Other files with proxified link
                links_text += f"\n- ⬇️ [{name}]({proxied_url})"
        count += 1
    
    return links_text, file_list_id


