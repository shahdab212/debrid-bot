"""Message building and formatting for torrent status updates."""

import asyncio
import logging
from typing import Dict, Any

from pyrogram.types import Message
from pyrogram.errors import FloodWait, MessageNotModified

from services.debrid_service import debrid_service
from utils import display, keyboards
from .torrent_manager import TRACKED_TORRENTS
from .file_manager import get_file_links

logger = logging.getLogger(__name__)


async def send_completion_message(msg: Message, data: Dict[str, Any], t_id: str, user, create_zip: bool = False, force_no_zip: bool = False, start_time: float = None):
    """Sends the final completion message and stops tracking."""
    name = data.get("name", "Unknown")
    files = data.get("files", [])
    logger.info(f"Completion Data for {name}: {files}")
    
    # Calculate total size from all files (API doesn't provide total size at torrent level)
    size = sum(f.get("size", 0) for f in files)
    
    # Auto-enable ZIP for torrents with 15 or more files (unless force_no_zip is set)
    if len(files) >= 15 and not force_no_zip:
        create_zip = True
        logger.info(f"Auto-enabling ZIP for {name} ({len(files)} files)")
    
    # If ZIP flag is set, create ZIP
    zip_url = None
    if create_zip and len(files) > 1:
        try:
            await msg.edit_text("📦 Creating ZIP archive...")
            
            # Extract all file IDs
            file_ids = [f['id'] for f in files if 'id' in f]
            
            if file_ids:
                zip_resp = await debrid_service.create_zip(t_id, file_ids)
                logger.info(f"ZIP API Raw Response: {zip_resp}")
                
                if zip_resp.get("success"):
                    val = zip_resp.get("value", {})
                    
                    # Check if ZIP is ready immediately or needs polling
                    if isinstance(val, dict):
                        zip_status = val.get("status", "")
                        zip_url = val.get("link") or val.get("url") or val.get("downloadUrl")
                        
                        # If status is 'create', ZIP is being created asynchronously - poll for it
                        if zip_status == "create" and not zip_url:
                            logger.info(f"ZIP creation started, polling for completion...")
                            
                            # Poll for ZIP completion (max 30 attempts = ~60 seconds)
                            max_attempts = 30
                            poll_interval = 2  # seconds
                            
                            for attempt in range(1, max_attempts + 1):
                                await asyncio.sleep(poll_interval)
                                
                                # Check ZIP status (silently, no message updates)
                                status_resp = await debrid_service.get_zip_status(t_id)
                                logger.info(f"ZIP Status Poll #{attempt}: {status_resp}")
                                
                                if status_resp.get("success"):
                                    status_val = status_resp.get("value", {})
                                    if isinstance(status_val, dict):
                                        zip_url = status_val.get("link") or status_val.get("url") or status_val.get("downloadUrl")
                                        current_status = status_val.get("status", "")
                                        
                                        if zip_url:
                                            logger.info(f"ZIP ready after {attempt} attempts: {zip_url}")
                                            break
                                        elif current_status not in ["create", "processing", ""]:
                                            # Unexpected status
                                            logger.warning(f"Unexpected ZIP status: {current_status}")
                                            break
                            else:
                                # Timeout reached
                                logger.warning(f"ZIP creation timeout after {max_attempts} attempts")
                        
                        elif zip_url:
                            logger.info(f"ZIP ready immediately: {zip_url}")
                    elif isinstance(val, str):
                        zip_url = val
                    
                    if not zip_url:
                        logger.warning(f"ZIP creation completed but no download URL found")
                else:
                    logger.error(f"ZIP creation failed: {zip_resp}")
            else:
                logger.error("No file IDs found for ZIP creation")
                
        except Exception as e:
            logger.error(f"ZIP creation error: {e}")
            # Try to recover message if stuck
            try:
                await msg.delete()
            except:
                pass

    if zip_url:
        links_text = ""  # Clear file list if ZIP is available
    else:
        links_text = get_file_links(files)
    
    # Get keyboard: only show keyboard if ZIP is available, otherwise None
    keyboard = keyboards.get_torrent_files_keyboard(files, zip_url=zip_url) if zip_url else None
    
    # Create user mention
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"
    
    # Calculate time taken
    import time
    time_taken_text = ""
    if start_time:
        elapsed_seconds = time.time() - start_time
        time_taken_text = f"\n⏱️ **Time Taken:** {display.human_readable_time(int(elapsed_seconds))}"
    
    # Add ZIP info if available with download link
    from utils.url_proxy import encode_url
    zip_info = ""
    if zip_url:
        proxied_zip = encode_url(zip_url, f"{name}.zip")
        zip_info = (
            f"\n\n📦 **Archive:** __Complete ZIP archive ready__\n\n"
            f"🔗 **Download Link:**\n"
            f"`{proxied_zip}`"
        )
    
    final_text = (
        f"✨ **Download Complete!** ✨\n\n"
        f"{'━' * 30}\n\n"
        f"📦 **File Name:** __{name}__\n"
        f"📏 **File Size:** {display.human_readable_size(size)}"
        f"{time_taken_text}\n\n"
        f"👤 **User:** {user_mention}\n"
        f"🆔 **User ID:** `{user.id}`"
        f"{links_text}"
        f"{zip_info}\n\n"
        f"{'━' * 30}"
    )
    
    try:
        await msg.delete()  # Delete progress message
        # Use default Markdown parse mode for consistent formatting
        await msg.reply_text(final_text, quote=False, reply_markup=keyboard)  # Send new message
    except Exception as e:
        logger.error(f"Error sending completion msg: {e}")
    
    TRACKED_TORRENTS.pop(t_id, None)


async def update_progress_message(msg: Message, data: Dict[str, Any], user, cached_size: int = 0):
    """Updates the progress message."""
    name = data.get("name", "Unknown")
    status = data.get("status", "unknown")
    # Convert status to string if it's not already (API sometimes returns int)
    status = str(status) if not isinstance(status, str) else status
    progress = data.get("downloadPercent", 0)
    # Use cached size if API doesn't provide it
    size = data.get("size", 0) or cached_size
    t_id = data.get("id", "")
    
    # Calculate downloaded approx
    downloaded_approx = size * (progress / 100)
    speed = data.get("downloadSpeed", 0)
    
    # Calculate ETA: remaining bytes / speed
    remaining_bytes = size - downloaded_approx
    if speed > 0 and remaining_bytes > 0:
        eta = int(remaining_bytes / speed)  # ETA in seconds
    else:
        eta = 0
    
    # Create user mention
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"
    
    text = (
        f"🌊 **Downloading**\n\n"
        f"{'─' * 30}\n\n"
        f"📁 **Name:** {name}\n"
        f"📏 **File Size:** {display.human_readable_size(size)}\n\n\n"
        f"**Progress:**\n"
        f"[{display.progress_bar(progress, 100)}] {display.percentage(progress, 100)}\n\n"
        f"🚀 **Speed:** {display.speed_format(speed)}\n"
        f"♻️ **Downloaded:** {display.human_readable_size(downloaded_approx)} / {display.human_readable_size(size)}\n"
        f"⏳ **ETA:** {display.human_readable_time(eta)}\n"
        f"👤 **Task By:** {user_mention}\n"
        f"📛 **Stop Task:** `/cancel {t_id[-6:]}`\n\n"
        f"{'─' * 30}"
    )
    
    # No keyboard - users should use /cancel command
    keyboard = None
    
    try:
        # Only update if text changed to avoid unnecessary API calls
        current_text = msg.text or ""
        if current_text.split("\n━━━━━━━━━━━━━━━━━━━━")[0] != text.split("\n━━━━━━━━━━━━━━━━━━━━")[0]:
            await msg.edit_text(text, reply_markup=keyboard)
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.error(f"Error editing message: {e}")
