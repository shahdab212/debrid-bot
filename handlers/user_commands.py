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
        
        "▫️ /search **query** • **Search Torrents**\n"
        "   Search for torrents on 1337x\n"
        "   • Returns results via Telegraph page\n"
        "   • Click 'View Details' to get magnet links\n"
        "   • Example: /search ubuntu 22.04\n\n"
        
        "▫️ /hosters • **View Supported Hosters**\n"
        "   Display status of all file hosting services\n"
        "   • Shows online and offline hosters\n"
        "   • Real-time status from Debrid-Link\n"
        "   • See available domains for each hoster\n\n"
        
        "▫️ /status • **View Active Downloads**\n"
        "   Check status of currently downloading files\n\n"
        
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
        "▪️ /cancel **<torrent_id>** • Cancel own or any download (admin)\n"
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
            f"⚠️ **No Download Source Provided** ⚠️\n\n"
            f"{'─' * 30}\n\n"
            f"ℹ️ **Please provide a download link or file.**\n\n"
            f"✅ **Supported Link Types:**\n"
            f"• Magnet links\n"
            f"• Torrent files (upload or URL)\n"
            f"• File hoster links\n\n"
            f"📝 **Usage Examples:**\n"
            f"• `/dl magnet:?xt=urn:btih:...`\n"
            f"• `/dl https://example.com/file.torrent`\n"
            f"• `/dl https://mega.nz/file/...`\n"
            f"• Reply to any file/link with `/dl`\n\n"
            f"💡 **For a complete list of supported file hosters, use:** `/hosters`\n\n"
            f"{'─' * 30}"
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
            f"⚠️ **Link Not Supported** ⚠️\n\n"
            f"{'─' * 30}\n\n"
            f"Link not supported or the host is down. Try again after some time with a valid link.\n\n"
            f"✅ **Supported Link Types:**\n"
            f"• Torrent files and magnet links\n"
            f"• File hoster links (MEGA, RapidGator, etc.)\n\n"
            f"💡 To view the complete list of supported file hosters and their current status, use /hosters\n\n"
            f"{'─' * 30}"
        )



# NOTE: status_handler has been moved to handlers/user_commands_status.py
# and now uses the centralized status_tracker module


@authorized_only
async def hosters_handler(client: Client, message: Message):
    """Display the status of all supported file hosters."""
    msg = await message.reply_text("⏳ **Fetching hoster information...**")
    
    try:
        resp = await debrid_service.get_hosts()
        if not resp.get("success"):
            await msg.edit_text(
                f"❌ **Error:** Failed to fetch hosters list.\n"
                f"`{resp.get('error', 'Unknown error')}`"
            )
            return
        
        hosters = resp.get("value", [])
        if not hosters:
            await msg.edit_text("⚠️ **No hosters found.**")
            return
        
        # Curated list of popular/major hosters (matching website's ~47 count)
        # This filters out lesser-known or regional variations
        POPULAR_HOSTERS = {
            '1fichier', 'clicknupload', 'ddownload', 'ddl', 'depositfiles', 
            'dailyuploads', 'downup', 'drop.download', 'dropapk', 'dropbox', 
            'elitefile', 'emload', 'wdupload', 'file.al', 'fileal', 'fileaxa', 
            'filecat', 'filedot', 'filefactory', 'filejoker', 'filenext', 
            'filer', 'filesfly', 'filespace', 'filextras', 'gigapeta', 
            'gofile', 'googledrive', 'hitfile', 'hotlink', 'hulkshare', 
            'isracloud', 'jumploads', 'goloady', 'katfile', 'kshared', 
            'mediafire', 'mega', 'mixdrop', 'nelion', 'pixeldrain', 
            'prefiles', 'rapidgator', 'scribd', 'silkfiles', 'terabox', 
            'terabytez', 'tezfiles', 'turbobit', 'uploady', 'uptobox',
            'upvid', 'uqload', 'vidoza', 'workupload', 'worldfiles', 
            'worldbytez', 'icloud', 'hexupload', 'darkibox', 'exload'
        }
        
        # Categorize hosters by status
        # Show only popular services in the message, but keep all in the paste
        online_hosters = []
        offline_hosters = []
        all_hosters_raw = []  # For the full list upload (keep all entries with domains)
        
        # Track unique service names to avoid duplicates
        seen_online = set()
        seen_offline = set()
        
        # Track total counts (all services including filtered ones)
        total_online = 0
        total_offline = 0
        
        for hoster in hosters:
            name = hoster.get("name", "Unknown").lower()  # Use lowercase for comparison
            status = hoster.get("status", 0)
            is_free = hoster.get("isFree", False)
            domains = hoster.get("domains", [])
            
            # Count all services
            if status == 1:
                total_online += 1
            else:
                total_offline += 1
            
            # Only process popular services for both display and full list
            if name in POPULAR_HOSTERS:
                # For full list with domains (only popular services)
                domain_list = ", ".join(domains) if domains else "No domains listed"
                status_text = "✅ Online" if status == 1 else "❌ Offline"
                free_tag_full = " [FREE]" if is_free else ""
                full_info = f"{name.upper()}{free_tag_full}\n  Status: {status_text}\n  Domains: {domain_list}\n"
                all_hosters_raw.append((status, full_info))
                
                # For display message
                free_tag = " 🆓" if is_free else ""
                # Store name and free_tag for numbering later
                hoster_info = (name.capitalize(), free_tag)
                
                if status == 1:
                    if name not in seen_online:
                        online_hosters.append(hoster_info)
                        seen_online.add(name)
                else:
                    if name not in seen_offline:
                        offline_hosters.append(hoster_info)
                        seen_offline.add(name)

        
        # Debug: Log the filtering results
        logger.info(f"Raw API returned {len(hosters)} total entries")
        logger.info(f"Total services: {total_online} online, {total_offline} offline")
        logger.info(f"Showing popular services: {len(online_hosters)} online, {len(offline_hosters)} offline")
        
        # Build the message
        text_parts = [
            "🌐 **Supported File Hosters**\n",
            f"{'━' * 32}\n"
        ]
        
        # Show online hosters with numbering
        if online_hosters:
            text_parts.append(f"\n✅ **Online ({len(online_hosters)} hosters)**\n\n")
            # Add numbering
            numbered_online = [f"{i}. {name}{tag}" for i, (name, tag) in enumerate(online_hosters[:20], 1)]
            text_parts.append("\n".join(numbered_online))
            if len(online_hosters) > 20:
                text_parts.append(f"\n\n...and {len(online_hosters) - 20} more online hosters")
        
        # Show offline hosters with numbering
        if offline_hosters:
            text_parts.append(f"\n\n❌ **Offline ({len(offline_hosters)} hosters)**\n\n")
            # Add numbering
            numbered_offline = [f"{i}. {name}{tag}" for i, (name, tag) in enumerate(offline_hosters[:10], 1)]
            text_parts.append("\n".join(numbered_offline))
            if len(offline_hosters) > 10:
                text_parts.append(f"\n\n...and {len(offline_hosters) - 10} more offline hosters")
        
        text_parts.append(f"\n\n{'━' * 32}")
        # Use deduplicated count (unique services)
        total_unique = len(online_hosters) + len(offline_hosters)
        text_parts.append(f"\n📊 **Total:** {total_unique} hosters")
        text_parts.append(f"\n💡 Status updates in real-time from Debrid-Link")
        
        # Create full list and upload to spaceb.in
        full_list_content = [
            "🌐 DEBRID-LINK SUPPORTED FILE HOSTERS",
            "=" * 80,
            "",
            f"Total Hosters: {total_unique}",
            f"Online: {len(online_hosters)} | Offline: {len(offline_hosters)}",
            "",
            "=" * 80,
            ""
        ]
        
        # Add online hosters (all entries with full domain info and numbering)
        if online_hosters:
            full_list_content.append("\n✅ ONLINE HOSTERS\n")
            full_list_content.append("-" * 80)
            counter = 1
            for status, hoster_info in all_hosters_raw:
                if status == 1:
                    # Add number prefix to each entry
                    full_list_content.append(f"\n{counter}. {hoster_info}")
                    counter += 1
        
        # Add offline hosters (all entries with full domain info and numbering)
        if offline_hosters:
            full_list_content.append("\n\n" + "=" * 80)
            full_list_content.append("\n❌ OFFLINE HOSTERS\n")
            full_list_content.append("-" * 80)
            counter = 1
            for status, hoster_info in all_hosters_raw:
                if status == 0:
                    # Add number prefix to each entry
                    full_list_content.append(f"\n{counter}. {hoster_info}")
                    counter += 1

        
        full_list_content.append("\n\n" + "=" * 80)
        full_list_content.append("\n🤖 Generated by Debrid-Link Telegram Bot")
        
        full_text = "\n".join(full_list_content)
        
        # Upload to spaceb.in
        from services.paste_service import paste_service
        logger.info("Attempting to upload hosters list to spaceb.in...")
        paste_url = await paste_service.upload_to_spacebin(full_text)
        
        if paste_url:
            logger.info(f"Successfully got paste URL: {paste_url}")
        else:
            logger.warning("Failed to upload to spaceb.in - no URL returned")
        
        # Create button if paste was successful
        keyboard = None
        if paste_url:
            from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 See Full List", url=paste_url)]
            ])
            logger.info("Created keyboard with 'See Full List' button")
        else:
            logger.warning("No button created - paste upload failed")
        
        await msg.edit_text("".join(text_parts), reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Hosters command error: {e}", exc_info=True)
        await msg.edit_text(
            f"❌ **Error Fetching Hosters**\n\n"
            f"Error: `{str(e)}`"
        )

