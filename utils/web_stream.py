"""Web stream utilities for generating player URLs."""
from urllib.parse import quote
import os


def is_web_stream_available() -> bool:
    """
    Check if web streaming is available (requires public URL).
    Returns False if running on localhost (Telegram rejects localhost URLs).
    
    Returns:
        True if web stream URLs can be used, False otherwise
    """
    from config import config
    
    # Check if explicit WEB_BASE_URL is set
    if hasattr(config, 'WEB_BASE_URL') and config.WEB_BASE_URL:
        base_url = config.WEB_BASE_URL
        # Check if it's not localhost
        return 'localhost' not in base_url.lower() and '127.0.0.1' not in base_url
    
    # Check for Render deployment
    render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if render_url:
        return True  # Render URLs are always public
    
    # No public URL available (localhost only)
    return False


def get_stream_url(proxified_video_url: str, filename: str = "Video") -> str:
    """
    Generate a web stream URL for the Shaka Player.
    
    Args:
        proxified_video_url: The CF Worker proxified URL (not direct Debrid link)
        filename: Display name of the video file
        
    Returns:
        Full URL to the web player endpoint, or None if not available
    """
    from config import config
    
    # Get the web server base URL
    # In production (Render), use the deployment URL
    # In development, use localhost
    if hasattr(config, 'WEB_BASE_URL') and config.WEB_BASE_URL:
        base_url = config.WEB_BASE_URL.rstrip('/')
    else:
        # Fallback: try to construct from PORT
        port = os.environ.get('PORT', '8080')
        render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
        
        if render_url:
            base_url = render_url.rstrip('/')
        else:
            base_url = f"http://localhost:{port}"
    
    # URL encode the parameters
    encoded_url = quote(proxified_video_url, safe='')
    encoded_filename = quote(filename, safe='')
    
    # Build the stream URL
    stream_url = f"{base_url}/stream?url={encoded_url}&name={encoded_filename}"
    
    return stream_url
