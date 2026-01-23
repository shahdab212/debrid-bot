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
    VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}
    ext = os.path.splitext(file_name)[1].lower()
    
    # Use proxied URL to route through Cloudflare Worker
    proxied_url = encode_url(file_url, file_name)
    
    buttons = []
    
    if ext in VIDEO_EXTS:
        # Video file - add download button
        buttons.append([InlineKeyboardButton("⬇️ Download Now", url=proxied_url)])
    else:
        # Non-video file - add download button
        buttons.append([InlineKeyboardButton("⬇️ Download Now", url=proxied_url)])
    
    return InlineKeyboardMarkup(buttons)

def get_torrent_files_keyboard(files: list, zip_url: str = None) -> InlineKeyboardMarkup:
    """Returns keyboard with buttons for torrent files and optional ZIP download."""
    VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}
    
    buttons = []
    
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
            
            # All files get download button
            display_name = file_name[:22] + "..." if len(file_name) > 25 else file_name
            buttons.append([InlineKeyboardButton(f"⬇️ {display_name}", url=proxied_url)])
    
    return InlineKeyboardMarkup(buttons) if buttons else None
