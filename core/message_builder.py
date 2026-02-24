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
    
    # Auto-enable ZIP for all multi-file torrents (unless force_no_zip is set)
    if len(files) > 1 and not force_no_zip:
        create_zip = True
        logger.info(f"Auto-enabling ZIP for {name} ({len(files)} files)")
    
    # Create ZIP if needed (status message shows "📦 Zipping..." during this)
    zip_url = None
    if create_zip:
        try:
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
                            
                            # Poll for ZIP completion (max 150 attempts = ~5 minutes)
                            max_attempts = 150
                            poll_interval = 2  # seconds
                            
                            for attempt in range(1, max_attempts + 1):
                                await asyncio.sleep(poll_interval)
                                
                                # Check ZIP status
                                status_resp = await debrid_service.get_zip_status(t_id)
                                
                                if status_resp.get("success"):
                                    status_val = status_resp.get("value", {})
                                    if isinstance(status_val, dict):
                                        zip_url = status_val.get("link") or status_val.get("url") or status_val.get("downloadUrl")
                                        current_status = status_val.get("status", "")
                                        
                                        if zip_url:
                                            logger.info(f"ZIP ready after {attempt} attempts: {zip_url}")
                                            break
                                        elif current_status not in ["create", "processing", ""]:
                                            logger.warning(f"Unexpected ZIP status: {current_status}")
                                            break
                                else:
                                    status_code = status_resp.get("status_code", 0)
                                    if status_code == 404:
                                        # 404 means ZIP is still being created, keep polling
                                        if attempt % 15 == 0:
                                            logger.info(f"ZIP still processing (attempt {attempt}/{max_attempts})...")
                                    else:
                                        logger.error(f"ZIP status check error (attempt {attempt}): {status_resp}")
                                        break
                            else:
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

    if zip_url:
        # ZIP available
        from utils.url_proxy import encode_url
        proxied_zip = encode_url(zip_url, f"{name}.zip")
        
        if len(files) > 1:
            # Multi-file with ZIP: create file list for web, no embedded links
            _, file_list_id = await get_file_links(files, t_id, name)
            links_text = ""  # No embedded links — buttons handle it
            keyboard = keyboards.get_zip_and_web_keyboard(proxied_zip, file_list_id)
        else:
            # Single file ZIP
            links_text = f"\n\n📦 **Archive:** [{name}.zip]({proxied_zip})"
            keyboard = keyboards.get_download_link_keyboard(proxied_zip, "ZIP Archive")
    elif len(files) == 1 and files[0].get('downloadUrl'):
        # Single file - use file download keyboard (includes stream button for videos)
        single_file = files[0]
        links_text, _ = await get_file_links(files, t_id, name)
        keyboard = keyboards.get_file_download_keyboard(
            single_file['downloadUrl'],
            single_file.get('name', 'File')
        )
    elif len(files) > 1:
        # Multi-file but ZIP failed — show See on Web only
        links_text = ""
        _, file_list_id = await get_file_links(files, t_id, name)
        keyboard = keyboards.get_web_list_keyboard(file_list_id)
    else:
        # No files or no download URLs
        links_text, _ = await get_file_links(files, t_id, name)
        keyboard = None
    
    # Create user mention
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"
    
    # Calculate time taken
    import time
    time_taken_text = ""
    if start_time:
        elapsed_seconds = time.time() - start_time
        time_taken_text = f"\n⏱️ **Time Taken:** {display.human_readable_time(int(elapsed_seconds))}"
    
    final_text = (
        f"✨ **Download Complete!** ✨\n\n"
        f"{'━' * 30}\n\n"
        f"📦 **File Name:** __{name}__\n"
        f"📏 **File Size:** {display.human_readable_size(size)}"
        f"{time_taken_text}\n\n"
        f"👤 **User:** {user_mention}\n"
        f"🆔 **User ID:** `{user.id}`"
        f"{links_text}\n\n"
        f"{'━' * 30}"
    )
    
    try:
        # Delete original status/progress message
        try:
            await msg.delete()
        except Exception as e:
            logger.debug(f"Could not delete original message: {e}")
        
        # Send final completion message
        await msg.reply_text(final_text, quote=False, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending completion msg: {e}")
    
    TRACKED_TORRENTS.pop(t_id, None)
