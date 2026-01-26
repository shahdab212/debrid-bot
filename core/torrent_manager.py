"""Torrent tracking and progress monitoring."""

import asyncio
import logging
import time
from typing import Dict, Any

from pyrogram.types import Message

from services.debrid_service import debrid_service

logger = logging.getLogger(__name__)

# Global dictionary to track torrents: {torrent_id: {"msg": Message, "user": User, "create_zip": bool}}
TRACKED_TORRENTS: Dict[str, Dict[str, Any]] = {}

# Global dictionary for file pagination: {message_id: {"files": list, "current_page": int, "torrent_id": str, "user": User, "zip_url": str}}
FILE_PAGES: Dict[int, Dict[str, Any]] = {}

# Global consolidated status messages per chat (chat_id -> Message)
CONSOLIDATED_STATUS_MESSAGES: Dict[int, Message] = {}

# Current page for status pagination (0-indexed)
STATUS_CURRENT_PAGE: int = 0

# Track previous download count to detect when new downloads are added
PREVIOUS_DOWNLOAD_COUNT: int = 0




async def check_instant_cache(msg: Message, t_id: str, user, create_zip: bool = False, force_no_zip: bool = False):
    """Checks if a torrent is 100% done immediately after adding."""
    from .message_builder import send_completion_message
    
    # We need to fetch the list because the add response usually doesn't have file links yet
    try:
        response = await debrid_service.get_seedbox_torrents()
        if not response.get("success"):
            # Fallback to monitoring
            TRACKED_TORRENTS[t_id] = {"msg": msg, "user": user, "create_zip": create_zip, "force_no_zip": force_no_zip, "start_time": time.time()}
            await msg.edit_text("🌊 Added to Seedbox. Waiting for metadata...")
            return

        active_list = response.get("value", [])
        data = next((t for t in active_list if t["id"] == t_id), None)
        
        if data and data.get("downloadPercent", 0) >= 100:
            # INSTANT HIT!
            await send_completion_message(msg, data, t_id, user, create_zip, force_no_zip, start_time=time.time())
        else:
            # Not cached or still processing
            TRACKED_TORRENTS[t_id] = {"msg": msg, "user": user, "create_zip": create_zip, "force_no_zip": force_no_zip, "start_time": time.time()}
            await msg.edit_text("🌊 Added to Seedbox. Waiting for metadata...")
            
    except Exception as e:
        logger.error(f"Cache check error: {e}")
        # Fallback
        TRACKED_TORRENTS[t_id] = {"msg": msg, "user": user, "create_zip": create_zip, "force_no_zip": force_no_zip, "start_time": time.time()}
        await msg.edit_text("🌊 Added to Seedbox. Waiting for metadata...")


async def monitor_progress():
    """Background task to monitor torrent progress."""
    from .message_builder import send_completion_message, update_consolidated_status
    from config import config
    
    # Track which chat we're sending status to and client instance
    status_chat_id = None
    client = None
    
    while True:
        try:
            if not TRACKED_TORRENTS:
                await asyncio.sleep(config.PROGRESS_UPDATE_INTERVAL)
                continue

            # Check status
            response = await debrid_service.get_seedbox_torrents()
            if not response.get("success"):
                logger.error("Failed to get torrent list")
                await asyncio.sleep(config.PROGRESS_UPDATE_INTERVAL)
                continue

            active_list = response.get("value", [])
            # Convert list to dict for easier lookup
            active_torrents = {t["id"]: t for t in active_list}

            # Determine chat ID and client from any tracked torrent
            if (status_chat_id is None or client is None) and TRACKED_TORRENTS:
                first_torrent = next(iter(TRACKED_TORRENTS.values()))
                status_chat_id = first_torrent["msg"].chat.id
                client = first_torrent["msg"]._client  # Get Pyrogram client from message

            # Iterate over tracked torrents
            # Create a copy of keys to avoid runtime error during modification
            for t_id in list(TRACKED_TORRENTS.keys()):
                torrent_data = TRACKED_TORRENTS[t_id]
                msg = torrent_data["msg"]
                user = torrent_data["user"]
                create_zip = torrent_data.get("create_zip", False)
                force_no_zip = torrent_data.get("force_no_zip", False)
                
                # Delete individual progress message if it still exists
                if not torrent_data.get("msg_deleted", False):
                    try:
                        await msg.delete()
                        TRACKED_TORRENTS[t_id]["msg_deleted"] = True
                    except Exception as e:
                        logger.debug(f"Could not delete progress message: {e}")
                        TRACKED_TORRENTS[t_id]["msg_deleted"] = True  # Mark as deleted anyway
                
                if t_id not in active_torrents:
                    # Logic to handle removed torrents?
                    # Maybe it finished and disappeared or was manually removed?
                    # For now, just stop tracking.
                    TRACKED_TORRENTS.pop(t_id, None)
                    continue

                data = active_torrents[t_id]
                name = data.get("name", "Unknown")
                status = data.get("status", "unknown")  # downloading, seeding, error, etc
                # Check completion
                progress = data.get("downloadPercent", 0)
                
                # Calculate size from files if not already cached
                if "cached_size" not in torrent_data:
                    files = data.get("files", [])
                    if files:
                        cached_size = sum(f.get("size", 0) for f in files)
                        TRACKED_TORRENTS[t_id]["cached_size"] = cached_size
                
                # Format text
                if progress >= 100:
                    # Done
                    start_time = torrent_data.get("start_time", time.time())
                    await send_completion_message(msg, data, t_id, user, create_zip, force_no_zip, start_time)
            
            # Check if download count changed (new download added or completed)
            current_download_count = len(TRACKED_TORRENTS)
            global PREVIOUS_DOWNLOAD_COUNT
            
            count_changed = current_download_count != PREVIOUS_DOWNLOAD_COUNT
            
            if count_changed:
                # Reset page to 0 so new downloads are visible
                import core.torrent_manager as tm
                tm.STATUS_CURRENT_PAGE = 0
                logger.info(f"Download count changed from {PREVIOUS_DOWNLOAD_COUNT} to {current_download_count}, reset page to 0")
                PREVIOUS_DOWNLOAD_COUNT = current_download_count
            
            # Update consolidated status message for all relevant chats
            # This includes: chats where torrents were added + chats where /status was called
            if client and TRACKED_TORRENTS:
                # Collect ALL unique chat IDs where torrents are active
                torrent_chat_ids = set()
                for torrent_data in TRACKED_TORRENTS.values():
                    torrent_chat_ids.add(torrent_data["msg"].chat.id)
                
                # Also include chats that already have status messages (from /status command)
                existing_status_chats = set(tm.CONSOLIDATED_STATUS_MESSAGES.keys())
                
                # Combine both: chats where torrents were added + chats with existing status
                chats_to_update = list(torrent_chat_ids | existing_status_chats)
                
                logger.debug(f"Updating status in {len(chats_to_update)} chats: {chats_to_update}")
                
                for chat_id in chats_to_update:
                    await update_consolidated_status(client, chat_id, force_recreate=count_changed)
                    
            elif client and not TRACKED_TORRENTS:
                # No torrents left - clean up all status messages
                for chat_id in list(tm.CONSOLIDATED_STATUS_MESSAGES.keys()):
                    await update_consolidated_status(client, chat_id, force_recreate=True)

        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}", exc_info=True)
        
        await asyncio.sleep(config.PROGRESS_UPDATE_INTERVAL)


