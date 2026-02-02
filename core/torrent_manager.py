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
            
            # Recreate status message to move to bottom (like mltb-read)
            from core.status_tracker import send_status_message
            chat_id = msg.chat.id
            await send_status_message(chat_id, None, msg)
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
            
            # Recreate status message to move to bottom (like mltb-read)
            from core.status_tracker import send_status_message
            chat_id = msg.chat.id
            await send_status_message(chat_id, None, msg)
            
    except Exception as e:
        logger.error(f"Cache check error: {e}")
        # Fallback
        TRACKED_TORRENTS[t_id] = {"msg": msg, "user": user, "create_zip": create_zip, "force_no_zip": force_no_zip, "start_time": time.time()}
        logger.info(f"Added torrent {t_id} to TRACKED_TORRENTS (fallback). Total tracked: {len(TRACKED_TORRENTS)}")
        await msg.edit_text("🌊 Added to Seedbox. Waiting for metadata...")


async def monitor_progress():
    """Background task to monitor torrent progress."""
    from .message_builder import send_completion_message
    from core.status_tracker import update_status_message, cleanup_all_status_messages, STATUS_MESSAGES
    from config import config
    
    # Track client instance
    client = None
    
    while True:
        try:
            if not TRACKED_TORRENTS:
                # No torrents - cleanup all status messages
                if STATUS_MESSAGES:
                    logger.info("No tracked torrents, cleaning up all status messages")
                    await cleanup_all_status_messages()
                await asyncio.sleep(config.PROGRESS_UPDATE_INTERVAL)
                continue
            
            logger.debug(f"Monitor loop: {len(TRACKED_TORRENTS)} torrents tracked: {list(TRACKED_TORRENTS.keys())}")

            # Check status
            response = await debrid_service.get_seedbox_torrents()
            if not response.get("success"):
                logger.error("Failed to get torrent list")
                await asyncio.sleep(config.PROGRESS_UPDATE_INTERVAL)
                continue

            active_list = response.get("value", [])
            # Convert list to dict for easier lookup
            active_torrents = {t["id"]: t for t in active_list}

            # Get client from any tracked torrent (if not already set)
            if client is None and TRACKED_TORRENTS:
                first_torrent = next(iter(TRACKED_TORRENTS.values()))
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
                    # Torrent finished or was removed
                    TRACKED_TORRENTS.pop(t_id, None)
                    continue

                data = active_torrents[t_id]
                progress = data.get("downloadPercent", 0)
                
                # Calculate size from files if not already cached
                if "cached_size" not in torrent_data:
                    files = data.get("files", [])
                    if files:
                        cached_size = sum(f.get("size", 0) for f in files)
                        TRACKED_TORRENTS[t_id]["cached_size"] = cached_size
                
                # Check completion
                if progress >= 100:
                    # Done
                    start_time = torrent_data.get("start_time", time.time())
                    await send_completion_message(msg, data, t_id, user, create_zip, force_no_zip, start_time)
            
            # Collect all chats that have active downloads
            if client and TRACKED_TORRENTS:
                download_chat_ids = set()
                for torrent_data in TRACKED_TORRENTS.values():
                    download_chat_ids.add(torrent_data["msg"].chat.id)
                
                # Auto-create status messages for chats with downloads but no status message
                for chat_id in download_chat_ids:
                    if chat_id not in STATUS_MESSAGES:
                        # Create a temporary message object for the status
                        # We need a message to reply to, so we'll create status without a command message
                        try:
                            from core.status_tracker import send_status_message
                            # Get any message from this chat to use as context
                            first_torrent = next(t for t in TRACKED_TORRENTS.values() if t["msg"].chat.id == chat_id)
                            temp_msg = first_torrent["msg"]
                            
                            # Send status message (auto-created)
                            await send_status_message(chat_id, client, temp_msg, user_id=0)
                            logger.info(f"Auto-created status message for chat {chat_id}")
                        except Exception as e:
                            logger.error(f"Failed to auto-create status for chat {chat_id}: {e}")
            
            # Update all existing status messages
            if client and STATUS_MESSAGES:
                for sid in list(STATUS_MESSAGES.keys()):
                    # Force update to ensure latest data
                    await update_status_message(sid, client, force=True)

        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}", exc_info=True)
        
        await asyncio.sleep(config.PROGRESS_UPDATE_INTERVAL)


