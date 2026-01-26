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
    from .message_builder import send_completion_message, update_progress_message
    
    while True:
        try:
            if not TRACKED_TORRENTS:
                await asyncio.sleep(5)
                continue

            # Check status
            response = await debrid_service.get_seedbox_torrents()
            if not response.get("success"):
                logger.error("Failed to get torrent list")
                await asyncio.sleep(5)
                continue

            active_list = response.get("value", [])
            # Convert list to dict for easier lookup
            active_torrents = {t["id"]: t for t in active_list}

            # Iterate over tracked torrents
            # Create a copy of keys to avoid runtime error during modification
            for t_id in list(TRACKED_TORRENTS.keys()):
                torrent_data = TRACKED_TORRENTS[t_id]
                msg = torrent_data["msg"]
                user = torrent_data["user"]
                create_zip = torrent_data.get("create_zip", False)
                force_no_zip = torrent_data.get("force_no_zip", False)
                
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
                
                else:
                    # In Progress - pass cached size
                    await update_progress_message(msg, data, user, torrent_data.get("cached_size", 0))

        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}", exc_info=True)
        
        await asyncio.sleep(5)
