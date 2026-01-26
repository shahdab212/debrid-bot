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
    
    # Get keyboard
    if zip_url:
        # ZIP available - show ZIP or files keyboard
        keyboard = keyboards.get_torrent_files_keyboard(files, zip_url=zip_url)
    elif len(files) == 1 and files[0].get('downloadUrl'):
        # Single file - show download/stream keyboard
        single_file = files[0]
        keyboard = keyboards.get_file_download_keyboard(
            single_file['downloadUrl'],
            single_file.get('name', 'File')
        )
    elif len(files) > 1:
        # Multiple files - show files keyboard (up to 3 files with web stream buttons)
        keyboard = keyboards.get_torrent_files_keyboard(files, zip_url=None)
    else:
        # No files or no download URLs
        keyboard = None
    
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




async def update_consolidated_status(client, chat_id: int, force_recreate: bool = False):
    """Updates the consolidated status message showing all active downloads.
    
    Args:
        client: Pyrogram client instance
        chat_id: Chat ID where status message should be sent/updated
        force_recreate: If True, delete old message and create new one. If False, edit existing.
    """
    from .torrent_manager import TRACKED_TORRENTS, CONSOLIDATED_STATUS_MESSAGES, STATUS_CURRENT_PAGE
    import core.torrent_manager as tm
    from utils import keyboards
    
    # If no active torrents, delete status message from ALL chats
    if not TRACKED_TORRENTS:
        # Delete from ALL chats that have status messages, not just the one passed as parameter
        for chat_id_to_clean in list(CONSOLIDATED_STATUS_MESSAGES.keys()):
            try:
                await CONSOLIDATED_STATUS_MESSAGES[chat_id_to_clean].delete()
                logger.info(f"Deleted consolidated status message for chat {chat_id_to_clean} (no active downloads)")
            except Exception as e:
                logger.error(f"Error deleting consolidated status message for chat {chat_id_to_clean}: {e}")
            del tm.CONSOLIDATED_STATUS_MESSAGES[chat_id_to_clean]
        
        # Reset page and count when no downloads
        tm.STATUS_CURRENT_PAGE = 0
        tm.PREVIOUS_DOWNLOAD_COUNT = 0
        return
    
    # Get all active torrents from Debrid-Link
    try:
        response = await debrid_service.get_seedbox_torrents()
        if not response.get("success"):
            logger.error("Failed to get torrent list for consolidated status")
            return
        
        active_list = response.get("value", [])
        active_torrents = {t["id"]: t for t in active_list}
    except Exception as e:
        logger.error(f"Error fetching torrents for status: {e}")
        return
    
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
    
    # If no entries, delete status from ALL chats
    if not download_entries:
        # Clean up ALL status messages when no downloads remain
        for chat_id_to_clean in list(CONSOLIDATED_STATUS_MESSAGES.keys()):
            try:
                await CONSOLIDATED_STATUS_MESSAGES[chat_id_to_clean].delete()
                logger.info(f"Deleted empty status message for chat {chat_id_to_clean}")
            except Exception as e:
                logger.error(f"Error deleting empty status message for chat {chat_id_to_clean}: {e}")
            del tm.CONSOLIDATED_STATUS_MESSAGES[chat_id_to_clean]
        return
    
    # Pagination: configurable items per page
    from config import config
    ITEMS_PER_PAGE = config.STATUS_ITEMS_PER_PAGE
    total_pages = (len(download_entries) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    
    # Ensure current page is valid (important after downloads complete/cancel)
    current_page = min(STATUS_CURRENT_PAGE, total_pages - 1)
    if current_page < 0:
        current_page = 0
    
    # Update global if we had to adjust
    if current_page != STATUS_CURRENT_PAGE:
        tm.STATUS_CURRENT_PAGE = current_page
        logger.info(f"Adjusted page from {STATUS_CURRENT_PAGE} to {current_page} (total_pages: {total_pages})")

    
    # Get entries for current page
    start_idx = current_page * ITEMS_PER_PAGE
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
    
    # Get pagination keyboard
    keyboard = keyboards.get_status_pagination_keyboard(current_page, total_pages)
    
    # Send or update message for this chat
    try:
        if chat_id in CONSOLIDATED_STATUS_MESSAGES:
            # Message exists for this chat
            if force_recreate:
                # Only force recreate if the text content is fundamentally different
                # (e.g., different page structure or major changes)
                # For most count changes, just edit the existing message
                try:
                    await CONSOLIDATED_STATUS_MESSAGES[chat_id].edit_text(text, reply_markup=keyboard)
                except MessageNotModified:
                    pass
                except Exception as e:
                    # If edit fails, try delete and recreate as fallback
                    logger.debug(f"Could not edit status message for chat {chat_id}, recreating: {e}")
                    try:
                        await CONSOLIDATED_STATUS_MESSAGES[chat_id].delete()
                    except Exception:
                        pass
                    
                    tm.CONSOLIDATED_STATUS_MESSAGES[chat_id] = await client.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=keyboard
                    )
            else:
                # Edit existing message for smooth updates
                try:
                    await CONSOLIDATED_STATUS_MESSAGES[chat_id].edit_text(text, reply_markup=keyboard)
                except MessageNotModified:
                    pass
                except Exception as e:
                    logger.debug(f"Could not edit status message for chat {chat_id}: {e}")
        else:
            # Create new message (first time for this chat)
            tm.CONSOLIDATED_STATUS_MESSAGES[chat_id] = await client.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Error sending consolidated status for chat {chat_id}: {e}")


