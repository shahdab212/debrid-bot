"""URL Proxy Utility - Encode/Decode URLs for Cloudflare Worker"""
import base64
from typing import Tuple
from urllib.parse import quote, unquote
import logging

logger = logging.getLogger(__name__)

def encode_url(debrid_url: str, filename: str = "") -> str:
    """
    Encode a Debrid-Link URL for proxying through Cloudflare Worker.
    
    This uses simple base64 encoding (URL-safe) without encryption.
    For production with sensitive data, consider adding encryption.
    
    Args:
        debrid_url: The actual Debrid-Link download URL
        filename: Optional filename for Content-Disposition header
        
    Returns:
        Proxied URL in format: https://worker.dev/download?data=...&filename=...
    """
    from config import config
    
    if not hasattr(config, 'WORKER_URL') or not config.WORKER_URL:
        logger.warning("WORKER_URL not configured, returning original URL")
        return debrid_url
    
    try:
        # Base64 encode the URL (URL-safe)
        encoded_bytes = base64.urlsafe_b64encode(debrid_url.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8').rstrip('=')  # Remove padding
        
        # Build the proxied URL
        worker_url = config.WORKER_URL.rstrip('/')
        proxied_url = f"{worker_url}/download?data={encoded_str}"
        
        # Add filename if provided
        if filename:
            # URL encode the filename
            safe_filename = quote(filename)
            proxied_url += f"&filename={safe_filename}"
        
        logger.debug(f"Encoded URL: {debrid_url[:50]}... -> {proxied_url[:80]}...")
        return proxied_url
        
    except Exception as e:
        logger.error(f"URL encoding error: {e}", exc_info=True)
        # Fallback to original URL if encoding fails
        return debrid_url


def decode_url(data: str) -> Tuple[str, str]:
    """
    Decode a proxied URL back to the original Debrid-Link URL.
    This is mainly for testing/debugging purposes.
    
    Args:
        data: The base64-encoded data parameter
        
    Returns:
        Tuple of (decoded_url, error_message)
        If successful: (url, "")
        If failed: ("", error_message)
    """
    try:
        # URL-safe base64 decoding
        # Add padding if needed
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        
        decoded_bytes = base64.urlsafe_b64decode(data)
        decoded_url = decoded_bytes.decode('utf-8')
        
        return decoded_url, ""
        
    except Exception as e:
        error_msg = f"Decoding error: {str(e)}"
        logger.error(error_msg)
        return "", error_msg


def is_proxy_enabled() -> bool:
    """
    Check if proxy is enabled in configuration.
    
    Returns:
        True if WORKER_URL is configured, False otherwise
    """
    from config import config
    return hasattr(config, 'WORKER_URL') and bool(config.WORKER_URL)
