"""Input validation utilities."""

import re
from typing import Optional
from urllib.parse import urlparse


def validate_magnet(link: str) -> bool:
    """
    Validate if a string is a valid magnet link.
    
    Args:
        link: URL string to validate
        
    Returns:
        True if valid magnet link, False otherwise
    """
    if not link:
        return False
    return link.startswith("magnet:?") and "xt=urn:btih:" in link


def validate_torrent_url(url: str) -> bool:
    """
    Validate if a URL is potentially a torrent file URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid HTTP/HTTPS URL, False otherwise
    """
    if not url:
        return False
    
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https') and len(url) < 4096
    except Exception:
        return False


def validate_chat_id(chat_id_str: str) -> Optional[int]:
    """
    Validate and convert chat ID string to integer.
    
    Args:
        chat_id_str: Chat ID as string
        
    Returns:
        Integer chat ID if valid, None otherwise
    """
    try:
        chat_id = int(chat_id_str)
        # Telegram chat IDs are typically within certain ranges
        if -10**15 < chat_id < 10**15:
            return chat_id
    except (ValueError, TypeError):
        pass
    return None


def is_folder_link(url: str) -> bool:
    """
    Check if URL appears to be a folder link (Google Drive, MEGA, etc.).
    
    Args:
        url: URL to check
        
    Returns:
        True if appears to be a folder link, False otherwise
    """
    url_lower = url.lower()
    
    # Google Drive folders
    if "drive.google.com" in url_lower:
        return "/folders/" in url or "/drive/folders/" in url or ("/drive/u/" in url and "/folders/" in url)
    
    # MEGA folders
    if "mega.nz" in url_lower:
        return "/folder/" in url or "/#F!" in url or "/#!" in url
    
    return False


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed length
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters for most filesystems
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > max_length:
        # Try to preserve extension
        parts = filename.rsplit('.', 1)
        if len(parts) == 2:
            name, ext = parts
            max_name_len = max_length - len(ext) - 1
            filename = name[:max_name_len] + '.' + ext
        else:
            filename = filename[:max_length]
    
    # Ensure it's not empty
    return filename if filename else "file"


def validate_torrent_id(torrent_id: str) -> bool:
    """
    Validate torrent ID format.
    
    Args:
        torrent_id: Torrent ID string
        
    Returns:
        True if valid format, False otherwise
    """
    # Basic validation - alphanumeric and some special chars, reasonable length
    if not torrent_id or len(torrent_id) > 100:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', torrent_id))
