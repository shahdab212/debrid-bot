"""User command handlers - /start, /help, /dl"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config  
from services.auth_service import authorized_only
from services.debrid_service import debrid_service
from utils import display, keyboards
from core import check_instant_cache

logger = logging.getLogger(__name__)


async def start_handler(client: Client, message: Message):
    """Enhanced start command with inline keyboard."""
    welcome_text = (
        "🎉 **Welcome to Debrid-Link Bot!** 🎉\n\n"
        "🚀 **What I Do:**\n"
        "I help you download torrents, magnets, and hoster links __fast__ using Debrid-Link!\n\n"
        "✨ **Quick Start Guide:**\n"
        "• Download directly: /dl **link**\n"
        "• Reply to any link/file with: /dl\n"
        "• Create ZIP archive: /dl **link** -zip\n"
        "• Get help anytime: /help\n\n"
        "🎯 **Tip:** Works with torrents, magnets, and 50+ file hosters!\n\n"
        "👉 **Tap Help below to learn more**"
    )
    
    await message.reply_text(
        welcome_text,
        reply_markup=keyboards.get_start_keyboard()
    )


async def help_handler(client: Client, message: Message):
    """Display comprehensive help information."""
    help_text = (
        "📖 **Debrid-Link Bot • Help Center**\n\n"
        f"{'━' * 32}\n\n"
        "📌 **USER COMMANDS**\n\n"
        
        "▫️ /start • **Launch Bot**\n"
        "   Start the bot and see the welcome screen\n\n"
        
        "▫️ /help • **Show Help**\n"
        "   Display this help message\n\n"
        
        "▫️ /dl **link** • **Download**\n"
        "   Download any supported link instantly\n"
        "   • Works with: Magnets, torrents, hosters\n"
        "   • Add **-zip** or **-z** for ZIP archives\n"
        "   • Add **-nozip** or **-nz** to prevent auto-ZIP\n"
        "   • Reply to links/files with /dl\n"
        "   • Example: /dl magnet:?xt=abc123 -zip\n\n"
        
        f"{'━' * 32}\n\n"
        "⚡ **QUICK USAGE GUIDE**\n\n"
        
        "🔹 **Method 1:** Direct Command\n"
        "   • Type: /dl **your-link-here**\n"
        "   • Optional: Add -zip for archives\n\n"
        
        "🔹 **Method 2:** Reply Mode\n"
        "   • Send/forward any link or .torrent file\n"
        "   • Reply to it with: /dl\n"
        "   • Optional: /dl -z for ZIP\n\n"
        
        f"{'━' * 32}\n\n"
        "💾 **SUPPORTED SOURCES**\n\n"
        "• 🧲 **Magnet Links** - Torrents via magnet\n"
        "• 📁 **Torrent Files** - Upload .torrent files\n"
        "• 🔗 **File Hosters** - MEGA, RapidGator, etc.\n"
        "• ⚠️ __Note: Folder links not supported__\n\n"
        
        f"{'━' * 32}\n\n"
        "🔒 **ADMIN COMMANDS**\n\n"
        "▪️ /auth **[chat_id]** • Authorize chat\n"
        "▪️ /deauth **[chat_id]** • Revoke access\n"
        "▪️ /users • List authorized users\n"
        "▪️ /cancel **<torrent_id>** • Cancel download\n"
        "▪️ /limits • View account usage\n"
        "▪️ /log **[lines]** • View bot logs\n"
        "▪️ /restart • Restart the bot\n\n"
        
        f"{'━' * 32}\n\n"
        "💡 __Fast, reliable downloads powered by Debrid-Link__"
    )
    
    await message.reply_text(
        help_text,
        reply_markup=keyboards.get_help_keyboard()
    )

@authorized_only
async def dl_handler(client: Client, message: Message):
    """Download handler for torrents, magnets, and hoster links."""
    link = None
    file_bytes = None
    create_zip = False  # Flag for ZIP creation
    force_no_zip = False  # Flag to prevent auto-ZIP
    
    # 1. Parse flags first (works for both direct links and replies)
    args = message.command[1:] if len(message.command) > 1 else []
    
    # Check for ZIP flag in command arguments
    if '-zip' in args or '-z' in args:
        create_zip = True
        # Remove flags from args
        args = [arg for arg in args if arg not in ['-zip', '-z']]
    
    # Check for NO-ZIP flag (overrides auto-ZIP behavior)
    if '-nozip' in args or '-nz' in args:
        force_no_zip = True
        create_zip = False  # Explicitly disable ZIP
        # Remove flags from args
        args = [arg for arg in args if arg not in ['-nozip', '-nz']]
    
    # 2. Determine the download source
    # Priority: explicit argument > reply to message
    if args:
        # User provided link directly: /dl <link> [-zip|-z]
        link = args[0]
    elif message.reply_to_message:
        # User replied to a message: reply with /dl [-zip|-z]
        reply = message.reply_to_message
        if reply.document and reply.document.file_name.endswith(".torrent"):
            status_msg = await message.reply_text("⬇️ Downloading .torrent file...")
            file_path = await client.download_media(reply.document, in_memory=True)
            file_bytes = bytes(file_path.getbuffer())
            await status_msg.delete()
        elif reply.text:
            link = reply.text
    
    if not link and not file_bytes:
        await message.reply_text(
            "❌ **No Download Source Provided**\n\n"
            "**Supported Sources:**\n"
            "🧲 Magnet links\n"
            "📁 .torrent files (upload or URL)\n"
            "🔗 File hosters (MEGA, RapidGator, 1fichier, Mediafire, etc.)\n\n"
            "**Usage Examples:**\n"
            "• `/dl magnet:?xt=urn:btih:...`\n"
            "• `/dl https://example.com/file.torrent`\n"
            "• `/dl https://mega.nz/file/...`\n"
            "• Reply to any file/link with `/dl`\n\n"
            "💡 Use `/help` for detailed instructions"
        )
        return

    # 3. Process
    sent_msg = await message.reply_text("⏳ **Processing your request...**")
    
    try:
        if file_bytes:
            # Torrent File
            resp = await debrid_service.add_file(file_bytes)
            if resp.get("success"):
                t_id = resp["value"]["id"]
                # Check directly if cached
                await check_instant_cache(sent_msg, t_id, message.from_user, create_zip, force_no_zip)
            else:
                error_msg = resp.get('error', 'Unknown error')
                status_code = resp.get('status_code', '')
                
                await sent_msg.edit_text(
                    f"⚠️ **Error Adding Torrent File** ⚠️\n\n"
                    f"{'─' * 30}\n\n"
                    f"❌ **Error:** {error_msg}\n"
                    f"{f'🔢 **Status Code:** {status_code}' if status_code else ''}\n\n"
                    f"💡 **Suggestions:**\n"
                    f"• Verify the .torrent file is valid\n"
                    f"• Check your Debrid-Link account status\n"
                    f"• Try uploading again\n\n"
                    f"{'─' * 30}"
                )

        elif link:
            # Check if it's a .torrent file URL
            is_torrent_url = link.lower().endswith('.torrent') or '.torrent?' in link.lower()
            
            # Check for common torrent download URL patterns
            torrent_patterns = ['/torrent/download/', '/download/torrent/', '.torrent/', 'download.php?torrent=']
            if not is_torrent_url:
                is_torrent_url = any(pattern in link.lower() for pattern in torrent_patterns)
            
            # If still not detected, check Content-Type header
            if not is_torrent_url and not link.startswith('magnet:'):
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.head(link, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=5)) as response:
                            content_type = response.headers.get('Content-Type', '').lower()
                            is_torrent_url = 'torrent' in content_type or content_type == 'application/x-bittorrent'
                except:
                    pass  # If HEAD request fails, continue with normal processing
            
            if is_torrent_url:
                # Download the .torrent file from URL
                await _handle_torrent_url(link, sent_msg, message, create_zip, force_no_zip)
            
            elif "magnet:" in link:
                # Magnet Link
                await _handle_magnet(link, sent_msg, message, create_zip, force_no_zip)
            
            else:
                # Hoster Link
                await _handle_hoster_link(link, sent_msg, message)

    except Exception as e:
        logger.error(f"DL Error: {e}", exc_info=True)
        await sent_msg.edit_text(
            f"🚫 **Unexpected Error** 🚫\n\n"
            f"{'─' * 30}\n\n"
            f"❌ **Error Details:**\n"
            f"`{str(e)}`\n\n"
            f"💡 **What to do:**\n"
            f"• Try again in a few moments\n"
            f"• Check your internet connection\n"
            f"• Contact support if the issue persists\n\n"
            f"{'─' * 30}"
        )


async def _handle_torrent_url(link, sent_msg, message, create_zip, force_no_zip):
    """Handle .torrent file URLs."""
    try:
        import aiohttp
        await sent_msg.edit_text("⏬️ **Downloading .torrent file from URL...**")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                if response.status == 200:
                    file_bytes = await response.read()
                    await sent_msg.edit_text("⬆️ **Uploading .torrent file...**")
                    
                    # Upload the downloaded torrent file
                    resp = await debrid_service.add_file(file_bytes)
                    if resp.get("success"):
                        t_id = resp["value"]["id"]
                        await check_instant_cache(sent_msg, t_id, message.from_user, create_zip, force_no_zip)
                    else:
                        error_msg = resp.get('error', 'Unknown error')
                        status_code = resp.get('status_code', '')
                        
                        await sent_msg.edit_text(
                            f"⚠️ **Error Adding Torrent File** ⚠️\n\n"
                            f"{'─' * 30}\n\n"
                            f"❌ **Error:** {error_msg}\n"
                            f"{f'🔢 **Status Code:** {status_code}' if status_code else ''}\n\n"
                            f"💡 **Suggestions:**\n"
                            f"• Verify the .torrent file is valid\n"
                            f"• Check your Debrid-Link account status\n\n"
                            f"{'─' * 30}"
                        )
                else:
                    await sent_msg.edit_text(
                        f"❌ **Failed to Download .torrent File**\n\n"
                        f"HTTP Status: {response.status}\n\n"
                        f"💡 **Suggestions:**\n"
                        f"• Verify the URL is accessible\n"
                        f"• Check if the link is still valid\n"
                        f"• Try uploading the .torrent file directly"
                    )
    except Exception as e:
        logger.error(f"Error downloading .torrent from URL: {e}", exc_info=True)
        await sent_msg.edit_text(
            f"❌ **Error Processing .torrent URL**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"💡 Try uploading the .torrent file directly instead."
        )


async def _handle_magnet(link, sent_msg, message, create_zip, force_no_zip):
    """Handle magnet links."""
    resp = await debrid_service.add_magnet(link)
    if resp.get("success"):
        t_id = resp["value"]["id"]
        # Check directly if cached
        await check_instant_cache(sent_msg, t_id, message.from_user, create_zip, force_no_zip)
    else:
        error_msg = resp.get('error', 'Unknown error')
        status_code = resp.get('status_code', '')
        
        await sent_msg.edit_text(
            f"⚠️ **Error Adding Magnet Link** ⚠️\n\n"
            f"{'─' * 30}\n\n"
            f"❌ **Error:** {error_msg}\n"
            f"{f'🔢 **Status Code:** {status_code}' if status_code else ''}\n\n"
            f"💡 **Suggestions:**\n"
            f"• Verify the magnet link is complete\n"
            f"• Check your Debrid-Link account status\n"
            f"• Ensure you have available slots\n\n"
            f"{'─' * 30}"
        )


async def _handle_hoster_link(link, sent_msg, message):
    """Handle hoster links (MEGA, RapidGator, etc.)."""
    # Validate Google Drive links - reject folder links
    if "drive.google.com" in link.lower():
        if "/folders/" in link or "/drive/folders/" in link or ("/drive/u/" in link and "/folders/" in link):
            await sent_msg.edit_text(
                f"⚠️ **Google Drive Folder Links Not Supported** ⚠️\n\n"
                f"{'─' * 30}\n\n"
                f"❌ **Issue:**\n"
                f"You've provided a Google Drive folder link.\n"
                f"Folder links will generate spam messages for each file.\n\n"
                f"✅ **Solution:**\n"
                f"• Open the folder on Google Drive\n"
                f"• Right-click on the specific file you want\n"
                f"• Select 'Get link' or 'Share' for that file\n"
                f"• Make sure it's publicly accessible\n"
                f"• Send the direct file link instead\n\n"
                f"💡 **Example:**\n"
                f"✅ Good: `https://drive.google.com/file/d/xxxxx/view`\n"
                f"❌ Bad: `https://drive.google.com/drive/folders/xxxxx`\n\n"
                f"{'─' * 30}"
            )
            return
    
    # Validate MEGA links - only allow direct file links, not folders
    if "mega.nz" in link.lower():
        if "/folder/" in link or "/#F!" in link or "/#!" in link:
            await sent_msg.edit_text(
                f"⚠️ **MEGA Folder Links Not Supported** ⚠️\n\n"
                f"{'─' * 30}\n\n"
                f"❌ **Issue:**\n"
                f"You've provided a MEGA folder link.\n"
                f"Folder links cannot be processed directly.\n\n"
                f"✅ **Solution:**\n"
                f"• Open the folder on MEGA\n"
                f"• Right-click on the specific file you want\n"
                f"• Select 'Get link' for that individual file\n"
                f"• Send the direct file link instead\n\n"
                f"💡 **Example:**\n"
                f"✅ Good: `https://mega.nz/file/xxxxx#xxxxx`\n"
                f"❌ Bad: `https://mega.nz/folder/xxxxx#xxxxx`\n\n"
                f"{'─' * 30}"
            )
            return
    
    resp = await debrid_service.add_hoster_link(link)
    if resp.get("success"):
        data = resp.get("value", {})
        
        # Handle both dict and list responses from API
        if isinstance(data, list):
            if len(data) > 0:
                data = data[0]
            else:
                await sent_msg.edit_text(
                    f"⚠️ **Processing Error** ⚠️\n\n"
                    f"{'─' * 30}\n\n"
                    f"❌ **Error:** Empty response from Debrid-Link\n\n"
                    f"💡 **Suggestions:**\n"
                    f"• The link might not be supported\n"
                    f"• Try a different link source\n\n"
                    f"{'─' * 30}"
                )
                return
        
        dl_link = data.get("downloadUrl") or data.get("downloadLink")
        file_name = data.get("name", "File")
        
        # Validate if link was actually processed
        if not dl_link or dl_link == link:
            await sent_msg.edit_text(
                f"⚠️ **Link Not Supported** ⚠️\n\n"
                f"{'─' * 30}\n\n"
                f"❌ **Issue:**\n"
                f"Debrid-Link couldn't convert this link.\n\n"
                f"💡 **Common Cause:**\n"
                f"• Link may be password-protected\n"
                f"• File may have been deleted\n"
                f"• Host might be temporarily unavailable\n\n"
                f"✅ **Try Instead:**\n"
                f"• Use torrent/magnet links (better support)\n"
                f"• Upload to Rapidgator, Uploaded, etc.\n"
                f"• Use direct HTTP links\n\n"
                f"{'─' * 30}"
            )
            return
        
        # Get user info
        user = message.from_user
        user_mention = f"[{user.first_name}](tg://user?id={user.id})"
        
        # Get file size from response
        file_size = data.get("size", 0)
        
        # Proxify the download link for display
        from utils.url_proxy import encode_url
        proxied_link = encode_url(dl_link, file_name)
        
        # Get appropriate keyboard
        keyboard = keyboards.get_file_download_keyboard(dl_link, file_name)
        
        await sent_msg.edit_text(
            f"✨ **Download Ready!** ✨\n\n"
            f"{'━' * 30}\n\n"
            f"📂 **Filename:** __{file_name}__\n"
            f"📏 **File Size:** {display.human_readable_size(file_size)}\n\n"
            f"👤 **User:** {user_mention}\n"
            f"🆔 **User ID:** `{user.id}`\n\n"
            f"🔗 **Download Link:**\n"
            f"`{proxied_link}`\n\n"
            f"{'━' * 30}",
            reply_markup=keyboard
        )
    else:
        error_msg = resp.get('error', 'Unknown error')
        status_code = resp.get('status_code', '')
        
        # Detect if it's a Google Drive link for better error messaging
        is_gdrive = "drive.google.com" in link.lower() or "docs.google.com" in link.lower()
        
        suggestions = ""
        if is_gdrive:
            suggestions = (
                f"💡 **For Google Drive Links:**\n"
                f"• Make sure the link is publicly accessible\n"
                f"• Try using the direct download format:\n"
                f"  `https://drive.google.com/uc?id=FILE_ID&export=download`\n"
                f"• Ensure the file isn't in a folder (use direct file link)\n"
                f"• Check if file size exceeds your account limits\n\n"
            )
        else:
            suggestions = (
                f"💡 **Suggestions:**\n"
                f"• Check if the link is valid\n"
                f"• Ensure your Debrid-Link account is active\n"
                f"• Try again in a few moments\n\n"
            )
        
        await sent_msg.edit_text(
            f"⚠️ **Error Processing Link** ⚠️\n\n"
            f"{'─' * 30}\n\n"
            f"❌ **Error:** {error_msg}\n"
            f"{f'🔢 **Status Code:** {status_code}' if status_code else ''}\n\n"
            f"{suggestions}"
            f"{'─' * 30}"
        )
