"""Keyboard layout utilities for the bot."""
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
from utils.url_proxy import encode_url

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for the /start command."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Help", callback_data="help"),
            InlineKeyboardButton("ℹ️ Bot Info", callback_data="info")
        ]
    ])

def get_help_keyboard() -> InlineKeyboardMarkup:
    """Returns the keyboard for the help message."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Start", callback_data="start")]
    ])

def get_progress_keyboard(torrent_id: str, chat_id: int, admin_ids: list) -> InlineKeyboardMarkup:
    """Returns the keyboard for progress messages (no buttons - use /cancel command instead)."""
    # No buttons - users should use /cancel command instead
    return None

def get_cancel_confirm_keyboard(torrent_id: str) -> InlineKeyboardMarkup:
    """Returns the confirmation keyboard for canceling a download."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Cancel", callback_data=f"confirm_cancel_{torrent_id}"),
            InlineKeyboardButton("❌ No, Keep It", callback_data="dismiss")
        ]
    ])

def get_file_download_keyboard(file_url: str, file_name: str) -> InlineKeyboardMarkup:
    """Returns keyboard with download button for files."""
    from utils.web_stream import get_stream_url, is_web_stream_available
    
    VIDEO_EXTS = {'.mkv', '.mp4', '.mov', '.webm', '.m4v'}
    ext = os.path.splitext(file_name)[1].lower()
    
    # Use proxied URL to route through Cloudflare Worker
    proxied_url = encode_url(file_url, file_name)
    
    buttons = []
    
    if ext in VIDEO_EXTS:
        # Video file - add web stream button only if publicly accessible
        if is_web_stream_available():
            stream_url = get_stream_url(proxied_url, file_name)
            buttons.append([InlineKeyboardButton("🌐 Web Stream", url=stream_url)])
        buttons.append([InlineKeyboardButton("⬇️ Download Now", url=proxied_url)])
    else:
        # Non-video file - add download button only
        buttons.append([InlineKeyboardButton("⬇️ Download Now", url=proxied_url)])
    
    return InlineKeyboardMarkup(buttons)

def get_torrent_files_keyboard(files: list, zip_url: str = None, file_list_id: str = None) -> InlineKeyboardMarkup:
    """Returns keyboard with buttons for torrent files and optional ZIP download."""
    from utils.web_stream import get_stream_url, is_web_stream_available
    from config import settings
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"get_torrent_files_keyboard called with {len(files)} files, zip_url={zip_url}, file_list_id={file_list_id}")
    
    VIDEO_EXTS = {'.mkv', '.mp4', '.mov', '.webm', '.m4v'}
    
    buttons = []
    stream_available = is_web_stream_available()
    
    # If ZIP URL provided, show only ZIP button (priority)
    if zip_url:
        # Use proxied URL for ZIP
        proxied_zip_url = encode_url(zip_url, "archive.zip")
        buttons.append([InlineKeyboardButton("📦 Download ZIP", url=proxied_zip_url)])
    else:
        # Add buttons for up to 3 files
        for i, file in enumerate(files[:3]):
            if 'downloadUrl' not in file:
                continue
                
            file_name = file.get('name', 'File')
            file_url = file['downloadUrl']
            ext = os.path.splitext(file_name)[1].lower()
            
            # Use proxied URL for each file
            proxied_url = encode_url(file_url, file_name)
            
            # Shorter display name for buttons
            display_name = file_name[:22] + "..." if len(file_name) > 25 else file_name
            
            # For video files, add web stream button if publicly accessible
            if ext in VIDEO_EXTS and stream_available:
                row = [
                    InlineKeyboardButton(f"🌐 {display_name}", url=get_stream_url(proxied_url, file_name)),
                    InlineKeyboardButton("⬇️", url=proxied_url)
                ]
                buttons.append(row)
            else:
                # Non-video files or no public URL - download button only
                buttons.append([InlineKeyboardButton(f"⬇️ {display_name}", url=proxied_url)])
    
    # Add "See Full List on Web" button if file list ID is provided
    if file_list_id:
        web_base_url = settings.WEB_BASE_URL
        if not web_base_url:
            # Try to get from RENDER_EXTERNAL_URL
            web_base_url = os.getenv('RENDER_EXTERNAL_URL', '')
        
        logger.info(f"File list ID provided: {file_list_id}, web_base_url: {web_base_url}")
        
        if web_base_url:
            web_base_url = web_base_url.rstrip('/')
            file_list_url = f"{web_base_url}/files/{file_list_id}"
            buttons.append([InlineKeyboardButton("📋 See Full List on Web", url=file_list_url)])
            logger.info(f"Added web button with URL: {file_list_url}")
        else:
            logger.warning("WEB_BASE_URL not configured, skipping web button")
    
    return InlineKeyboardMarkup(buttons) if buttons else None

def get_download_link_keyboard(file_url: str, file_name: str) -> InlineKeyboardMarkup:
    """Returns keyboard with single Download Link button for single files or ZIP."""
    from utils.url_proxy import encode_url
    
    # Use proxied URL
    proxied_url = encode_url(file_url, file_name)
    
    buttons = [[InlineKeyboardButton("📥 Download Link", url=proxied_url)]]
    
    return InlineKeyboardMarkup(buttons)

def get_web_list_keyboard(file_list_id: str) -> InlineKeyboardMarkup:
    """Returns keyboard with only 'See List on Web' button for multiple files."""
    from config import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    web_base_url = settings.WEB_BASE_URL
    if not web_base_url:
        # Try to get from RENDER_EXTERNAL_URL
        web_base_url = os.getenv('RENDER_EXTERNAL_URL', '')
    
    logger.info(f"Creating web list keyboard with file_list_id: {file_list_id}, web_base_url: {web_base_url}")
    
    if not web_base_url:
        logger.warning("WEB_BASE_URL not configured, cannot create web list button")
        return None
    
    web_base_url = web_base_url.rstrip('/')
    file_list_url = f"{web_base_url}/files/{file_list_id}"
    
    buttons = [[InlineKeyboardButton("📋 See Full List on Web", url=file_list_url)]]
    logger.info(f"Created web button with URL: {file_list_url}")
    
    return InlineKeyboardMarkup(buttons)


def get_zip_and_web_keyboard(zip_url: str, file_list_id: str = None) -> InlineKeyboardMarkup:
    """Returns keyboard with ZIP download button and optional See on Web button."""
    from config import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    buttons = [[InlineKeyboardButton("📦 Download ZIP", url=zip_url)]]
    
    if file_list_id:
        web_base_url = settings.WEB_BASE_URL
        if not web_base_url:
            web_base_url = os.getenv('RENDER_EXTERNAL_URL', '')
        
        if web_base_url:
            web_base_url = web_base_url.rstrip('/')
            file_list_url = f"{web_base_url}/files/{file_list_id}"
            buttons.append([InlineKeyboardButton("📋 See Full List on Web", url=file_list_url)])
    
    return InlineKeyboardMarkup(buttons)


def get_status_pagination_keyboard(current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Returns pagination keyboard for consolidated status messages.
    
    Args:
        current_page: Current page number (0-indexed)
        total_pages: Total number of pages
        
    Returns:
        InlineKeyboardMarkup with Previous/Next buttons, or None if only one page
    """
    if total_pages <= 1:
        return None
    
    buttons = []
    row = []
    
    # Add Previous button if not on first page
    if current_page > 0:
        row.append(InlineKeyboardButton("◀️ Previous", callback_data="status_prev"))
    
    # Add page indicator
    row.append(InlineKeyboardButton(f"📄 {current_page + 1}/{total_pages}", callback_data="status_page_info"))
    
    # Add Next button if not on last page
    if current_page < total_pages - 1:
        row.append(InlineKeyboardButton("Next ▶️", callback_data="status_next"))
    
    if row:
        buttons.append(row)
    
    return InlineKeyboardMarkup(buttons) if buttons else None
