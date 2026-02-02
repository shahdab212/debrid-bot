"""Centralized status message tracking and management.

This module implements the status message tracking pattern from mltb-read:
- One status message per session ID (sid: user_id or chat_id)
- Per-sid auto-update intervals
- Rate limiting (max 1 update per 3 seconds)
- Content comparison before editing
- Proper lifecycle management and cleanup
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

from pyrogram.types import Message
from pyrogram.errors import FloodWait, MessageNotModified

logger = logging.getLogger(__name__)

# Global status tracking dictionary
# Maps sid (session ID: user_id or chat_id) -> status state
STATUS_MESSAGES: Dict[int, Dict[str, Any]] = {}

# Active update intervals per sid
STATUS_INTERVALS: Dict[int, asyncio.Task] = {}

# Configuration
MIN_UPDATE_INTERVAL = 3  # Minimum seconds between updates
AUTO_UPDATE_INTERVAL = 5  # Seconds between auto-updates


async def build_status_text(download_entries: list, page_no: int, total_pages: int) -> tuple[str, Any]:
    """Build status message text and keyboard (pure function).
    
    Args:
        download_entries: List of download entry dicts
        page_no: Current page number (0-indexed)
        total_pages: Total number of pages
    
    Returns:
        Tuple of (message_text, keyboard)
    """
    from utils import display, keyboards
    from config import config
    
    ITEMS_PER_PAGE = config.STATUS_ITEMS_PER_PAGE
    
    # Get entries for current page
    start_idx = page_no * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, len(download_entries))
    page_entries = download_entries[start_idx:end_idx]
    
    # Build message text
    text_parts = [
        "🌊 **Downloading**\n",
        f"{'─' * 30}\n"
    ]
    
    for idx, entry in enumerate(page_entries, start=start_idx + 1):
        text_parts.append(f"\n**{idx}.**\n")
        text_parts.append(f"📁 **Name:** {entry['name']}\n")
        text_parts.append(f"📏 **File Size:** {display.human_readable_size(entry['size'])}\n\n")
        text_parts.append(f"**Progress:**\n")
        text_parts.append(f"[{display.progress_bar(entry['progress'], 100)}] {display.percentage(entry['progress'], 100)}\n\n")
        text_parts.append(f"🚀 **Speed:** {display.speed_format(entry['speed'])}\n")
        text_parts.append(f"♻️ **Downloaded:** {display.human_readable_size(entry['downloaded'])} / {display.human_readable_size(entry['size'])}\n")
        text_parts.append(f"⏳ **ETA:** {display.human_readable_time(entry['eta'])}\n")
        text_parts.append(f"👤 **Task By:** {entry['user_mention']}\n")
        text_parts.append(f"📛 **Stop Task:** `/cancel {entry['torrent_id'][-6:]}`\n")
    
    text_parts.append(f"\n{'─' * 30}")
    
    text = "".join(text_parts)
    keyboard = keyboards.get_status_pagination_keyboard(page_no, total_pages)
    
    return text, keyboard


async def get_download_entries() -> list:
    """Get all active download entries from tracked torrents.
    
    Returns:
        List of download entry dicts
    """
    from core.torrent_manager import TRACKED_TORRENTS
    from services.debrid_service import debrid_service
    
    if not TRACKED_TORRENTS:
        return []
    
    # Get all active torrents from Debrid-Link
    try:
        response = await debrid_service.get_seedbox_torrents()
        if not response.get("success"):
            logger.error("Failed to get torrent list for status")
            return []
        
        active_list = response.get("value", [])
        active_torrents = {t["id"]: t for t in active_list}
    except Exception as e:
        logger.error(f"Error fetching torrents for status: {e}")
        return []
    
    # Build list of download entries
    download_entries = []
    
    for t_id, torrent_data in TRACKED_TORRENTS.items():
        if t_id not in active_torrents:
            continue
        
        data = active_torrents[t_id]
        user = torrent_data["user"]
        
        name = data.get("name", "Unknown")
        progress = data.get("downloadPercent", 0)
        
        # Calculate size
        if "cached_size" in torrent_data:
            size = torrent_data["cached_size"]
        else:
            files = data.get("files", [])
            if files:
                size = sum(f.get("size", 0) for f in files)
                torrent_data["cached_size"] = size
            else:
                size = 0
        
        # Calculate downloaded and speed
        downloaded_approx = size * (progress / 100)
        speed = data.get("downloadSpeed", 0)
        
        # Calculate ETA
        remaining_bytes = size - downloaded_approx
        if speed > 0 and remaining_bytes > 0:
            eta = int(remaining_bytes / speed)
        else:
            eta = 0
        
        # Create user mention
        user_mention = f"[{user.first_name}](tg://user?id={user.id})"
        
        download_entries.append({
            "name": name,
            "size": size,
            "progress": progress,
            "speed": speed,
            "downloaded": downloaded_approx,
            "eta": eta,
            "user_mention": user_mention,
            "torrent_id": t_id
        })
    
    return download_entries


async def update_status_message(sid: int, client, force: bool = False):
    """Update an existing status message.
    
    Args:
        sid: Session ID (user_id or chat_id)
        client: Pyrogram client instance
        force: If True, bypass rate limiting
    """
    # Check if status exists
    if sid not in STATUS_MESSAGES:
        # Cancel interval if it exists
        if sid in STATUS_INTERVALS:
            STATUS_INTERVALS[sid].cancel()
            del STATUS_INTERVALS[sid]
        return
    
    status_state = STATUS_MESSAGES[sid]
    
    # Rate limiting (skip if not forced and updated recently)
    if not force and (time.time() - status_state["last_update_time"]) < MIN_UPDATE_INTERVAL:
        return
    
    # Get download entries
    download_entries = await get_download_entries()
    
    # If no downloads, cleanup this status
    if not download_entries:
        await cleanup_status_message(sid)
        return
    
    # Calculate pagination
    from config import config
    ITEMS_PER_PAGE = config.STATUS_ITEMS_PER_PAGE
    total_pages = (len(download_entries) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    # Ensure current page is valid
    page_no = status_state["page_no"]
    if page_no >= total_pages:
        page_no = total_pages - 1
    if page_no < 0:
        page_no = 0
    status_state["page_no"] = page_no
    
    # Build message text
    text, keyboard = await build_status_text(download_entries, page_no, total_pages)
    
    # Only edit if content changed
    if text != status_state.get("last_text", ""):
        try:
            await status_state["message"].edit_text(text, reply_markup=keyboard)
            status_state["last_text"] = text
            status_state["last_update_time"] = time.time()
        except MessageNotModified:
            # Message content is identical, no need to edit
            pass
        except FloodWait as e:
            logger.warning(f"FloodWait {e.value}s when updating status for sid {sid}")
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"Error updating status message for sid {sid}: {e}")
            # If message was deleted or other error, cleanup
            await cleanup_status_message(sid)


async def send_status_message(sid: int, client, message: Message, user_id: int = 0):
    """Send or replace a status message.
    
    Args:
        sid: Session ID (user_id or chat_id)
        client: Pyrogram client instance
        message: Original command message
        user_id: User ID if filtering by user, 0 for chat-wide
    """
    is_user = bool(user_id)
    
    # Get download entries
    download_entries = await get_download_entries()
    
    # If no downloads, send message and return
    if not download_entries:
        await message.reply_text(
            "💤 **No Active Downloads**\n\n"
            "────────────────────────────\n\n"
            "📊 **Current Status:**\n"
            "There are no torrents being downloaded at the moment.\n\n"
            "✨ **Get Started:**\n"
            "• Use `/dl <link>` to start a download\n"
            "• Reply to any magnet/torrent with `/dl`\n"
            "• Add `-zip` flag for archives\n\n"
            "💡 Tip: Downloads will show here automatically once started!\n\n"
            "────────────────────────────"
        )
        return
    
    # Build message text for initial page
    from config import config
    ITEMS_PER_PAGE = config.STATUS_ITEMS_PER_PAGE
    total_pages = (len(download_entries) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    text, keyboard = await build_status_text(download_entries, 0, total_pages)
    
    # If status already exists for this sid, delete old message
    if sid in STATUS_MESSAGES:
        try:
            old_message = STATUS_MESSAGES[sid]["message"]
            await old_message.delete()
            logger.info(f"Deleted old status message for sid {sid}")
        except Exception as e:
            logger.debug(f"Could not delete old status message for sid {sid}: {e}")
        
        # Cancel old interval
        if sid in STATUS_INTERVALS:
            STATUS_INTERVALS[sid].cancel()
            del STATUS_INTERVALS[sid]
    
    # Send new status message
    try:
        status_msg = await message.reply_text(text, reply_markup=keyboard)
        
        # Store status state
        STATUS_MESSAGES[sid] = {
            "message": status_msg,
            "last_update_time": time.time(),
            "last_text": text,
            "page_no": 0,
            "page_step": 1,
            "is_user": is_user,
        }
        
        # Start auto-update interval (only for chat-wide status, not user-specific)
        if not is_user:
            task = asyncio.create_task(_auto_update_loop(sid, client))
            STATUS_INTERVALS[sid] = task
            logger.info(f"Started auto-update interval for sid {sid}")
        
    except Exception as e:
        logger.error(f"Error sending status message for sid {sid}: {e}")


async def recreate_status_message(sid: int, client):
    """Recreate status message by deleting old and sending new (moves to bottom)."""
    if sid not in STATUS_MESSAGES:
        return
    
    status_state = STATUS_MESSAGES[sid]
    download_entries = await get_download_entries()
    
    if not download_entries:
        await cleanup_status_message(sid)
        return
    
    from config import config
    ITEMS_PER_PAGE = config.STATUS_ITEMS_PER_PAGE
    total_pages = (len(download_entries) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    text, keyboard = await build_status_text(download_entries, 0, total_pages)
    
    try:
        await status_state["message"].delete()
        logger.info(f"Deleted old status for sid {sid} (recreating)")
    except Exception as e:
        logger.debug(f"Could not delete old status for sid {sid}: {e}")
    
    try:
        new_message = await client.send_message(chat_id=sid, text=text, reply_markup=keyboard)
        status_state["message"] = new_message
        status_state["last_text"] = text
        status_state["last_update_time"] = time.time()
        status_state["page_no"] = 0
        logger.info(f"Recreated status message for sid {sid} (now at bottom)")
    except Exception as e:
        logger.error(f"Error recreating status for sid {sid}: {e}")
        await cleanup_status_message(sid)



async def cleanup_status_message(sid: int):
    """Cleanup a status message and its interval.
    
    Args:
        sid: Session ID to cleanup
    """
    # Delete message
    if sid in STATUS_MESSAGES:
        try:
            await STATUS_MESSAGES[sid]["message"].delete()
            logger.info(f"Cleaned up status message for sid {sid}")
        except Exception as e:
            logger.debug(f"Error deleting status message for sid {sid}: {e}")
        del STATUS_MESSAGES[sid]
    
    # Cancel interval
    if sid in STATUS_INTERVALS:
        STATUS_INTERVALS[sid].cancel()
        del STATUS_INTERVALS[sid]
        logger.info(f"Cancelled auto-update interval for sid {sid}")


async def cleanup_all_status_messages():
    """Cleanup all status messages when no downloads remain."""
    logger.info("Cleaning up all status messages (no active downloads)")
    
    for sid in list(STATUS_MESSAGES.keys()):
        await cleanup_status_message(sid)


async def _auto_update_loop(sid: int, client):
    """Auto-update loop for a specific sid.
    
    Args:
        sid: Session ID
        client: Pyrogram client instance
    """
    try:
        while True:
            await asyncio.sleep(AUTO_UPDATE_INTERVAL)
            await update_status_message(sid, client, force=False)
    except asyncio.CancelledError:
        logger.debug(f"Auto-update loop cancelled for sid {sid}")
    except Exception as e:
        logger.error(f"Error in auto-update loop for sid {sid}: {e}")


async def handle_pagination_callback(sid: int, action: str, param: Optional[str] = None):
    """Handle pagination button callbacks.
    
    Args:
        sid: Session ID
        action: Action type (next, prev, step, refresh)
        param: Optional parameter (e.g., new step value)
    """
    if sid not in STATUS_MESSAGES:
        return
    
    status_state = STATUS_MESSAGES[sid]
    
    if action == "next":
        status_state["page_no"] += status_state["page_step"]
    elif action == "prev":
        status_state["page_no"] -= status_state["page_step"]
    elif action == "step" and param:
        status_state["page_step"] = int(param)
    elif action == "refresh":
        # Force refresh
        pass
    
    # Force update after button action
    # Note: Client needs to be passed from callback handler
