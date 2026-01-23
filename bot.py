import asyncio
# Fix for Pyrogram on Python 3.14 (RuntimeError: There is no current event loop)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import io
import io
import os
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, MessageNotModified

from config import config
from services.auth_service import auth_service, authorized_only
from services.debrid_service import debrid_service
from services.paste_service import paste_service
from utils import display
from utils import keyboards

# Import web server for health checks (Render hosting)
from web_server import start_web_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('bot.log', mode='a')  # File output
    ]
)
logger = logging.getLogger(__name__)

app = Client(
    "debrid_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Global dictionary to track torrents: {torrent_id: {"msg": Message, "user": User, "create_zip": bool}}
TRACKED_TORRENTS = {}

# Global dictionary for file pagination: {message_id: {"files": list, "current_page": int, "torrent_id": str, "user": User, "zip_url": str}}
FILE_PAGES = {}

@app.on_message(filters.command("start"))
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

@app.on_message(filters.command("help"))
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


@app.on_message(filters.command("auth"))
async def auth_handler(client: Client, message: Message):
    """Authorize a chat to use the bot (admin only)."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can authorize chats."
        )
        return
    
    if len(message.command) < 2:
        # If no ID provided, auth the current chat
        chat_id = message.chat.id
    else:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ **Invalid Chat ID**\nPlease provide a valid numeric chat ID.")
            return
    
    await auth_service.add_chat(chat_id, authorized_by=message.from_user.id)
    await message.reply_text(
        f"✅ **Authorization Successful**\n\n"
        f"Chat ID: `{chat_id}`\n"
        f"Status: Authorized to use the bot"
    )

@app.on_message(filters.command("deauth"))
async def deauth_handler(client: Client, message: Message):
    """Revoke authorization for a chat (admin only)."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can revoke authorization."
        )
        return
    
    if len(message.command) < 2:
        chat_id = message.chat.id
    else:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            await message.reply_text("❌ **Invalid Chat ID**\nPlease provide a valid numeric chat ID.")
            return

    await auth_service.remove_chat(chat_id)
    await message.reply_text(
        f"🚫 **Authorization Revoked**\n\n"
        f"Chat ID: `{chat_id}`\n"
        f"Status: No longer authorized"
    )

@app.on_message(filters.command("log"))
async def log_handler(client: Client, message: Message):
    """View recent bot logs (admin only)."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can view logs."
        )
        return
    
    # Get number of lines (default 60)
    lines_count = 60
    if len(message.command) > 1:
        try:
            lines_count = int(message.command[1])
            lines_count = min(max(lines_count, 10), 1000)  # Limit between 10-1000
        except ValueError:
            lines_count = 60
    
    try:
        if not os.path.exists("bot.log"):
            await message.reply_text(
                "❌ **No Log File Found**\n\n"
                "The log file doesn't exist yet. This could mean:\n"
                "• The bot just started and hasn't logged anything\n"
                "• Logging isn't configured properly\n\n"
                "💡 Try running the bot for a while and check again."
            )
            return

        with open("bot.log", "r") as f:
            # Read all lines and take the last N
            all_lines = f.readlines()
            logs = all_lines[-lines_count:] if len(all_lines) > lines_count else all_lines
        
        if not logs:
            await message.reply_text("⚠️ **Log File Empty**")
            return

        # Create temp file in memory
        import io
        log_content = "".join(logs)
        log_file = io.BytesIO(log_content.encode('utf-8'))
        log_file.name = "log.txt"

        await message.reply_document(
            document=log_file,
            caption=f"📋 **System Log**\nLast {len(logs)} lines from `bot.log`"
        )
        
    except Exception as e:
        logger.error(f"Log command error: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Log command error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error reading logs: {str(e)}")

@app.on_message(filters.command("users"))
async def users_handler(client: Client, message: Message):
    """List all authorized users (admin only)."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can view authorized users."
        )
        return
    
    msg = await message.reply_text("⏳ **Fetching authorized users...**")
    
    try:
        from database import AsyncSessionLocal
        from models import AuthorizedChat
        from sqlalchemy import select
        
        # Get all authorized chats from database
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AuthorizedChat).order_by(AuthorizedChat.authorized_at.desc())
            )
            authorized_chats = result.scalars().all()
        
        if not authorized_chats:
            await msg.edit_text(
                "📋 **Authorized Users**\n\n"
                "No authorized users found.\n\n"
                "💡 Use `/auth <chat_id>` to authorize users."
            )
            return
        
        # Build user list with names
        user_list = []
        for idx, chat in enumerate(authorized_chats, 1):
            try:
                # Try to get chat info
                chat_info = await client.get_chat(chat.chat_id)
                
                # Format name based on chat type
                if chat_info.type == enums.ChatType.PRIVATE:
                    # Private chat - show user name with mention
                    if chat_info.first_name:
                        name = chat_info.first_name
                        if chat_info.last_name:
                            name += f" {chat_info.last_name}"
                        user_mention = f"[{name}](tg://user?id={chat.chat_id})"
                    else:
                        user_mention = f"User `{chat.chat_id}`"
                else:
                    # Group/channel - show title
                    user_mention = f"**{chat_info.title}**" if chat_info.title else f"Chat `{chat.chat_id}`"
                
                # Format authorized by
                auth_by_text = ""
                if chat.authorized_by:
                    auth_by_text = f" • By: `{chat.authorized_by}`"
                
                # Format date
                import datetime
                auth_date = chat.authorized_at.strftime("%Y-%m-%d %H:%M")
                
                user_list.append(
                    f"{idx}. {user_mention}\n"
                    f"   ID: `{chat.chat_id}`{auth_by_text}\n"
                    f"   Date: `{auth_date}`"
                )
                
            except Exception as e:
                # If we can't get chat info, just show ID
                logger.warning(f"Could not get info for chat {chat.chat_id}: {e}")
                auth_date = chat.authorized_at.strftime("%Y-%m-%d %H:%M")
                user_list.append(
                    f"{idx}. Chat ID: `{chat.chat_id}`\n"
                    f"   Date: `{auth_date}`"
                )
        
        # Send formatted message
        users_text = (
            f"👥 **Authorized Users** ({len(authorized_chats)} total)\n\n"
            f"{'━' * 35}\n\n"
            + "\n\n".join(user_list) +
            f"\n\n{'━' * 35}\n\n"
            f"💡 Use `/auth` to add or `/deauth` to remove users"
        )
        
        await msg.edit_text(users_text)
        
    except Exception as e:
        logger.error(f"Users command error: {e}", exc_info=True)
        await msg.edit_text(
            f"❌ **Error Fetching Users**\n\n"
            f"Error: `{str(e)}`"
        )

@app.on_message(filters.command("restart"))
async def restart_handler(client: Client, message: Message):
    """Restart the bot (admin only)."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can restart the bot."
        )
        return
    
    msg = await message.reply_text(
        "🔄 **Restarting Bot...**\n\n"
        "The bot will restart in a moment.\n"
        "Please wait a few seconds."
    )
    
    logger.info(f"Bot restart initiated by admin {message.from_user.id}")
    
    # Save restart info to file for confirmation after restart
    import json
    restart_info = {
        "chat_id": message.chat.id,
        "message_id": msg.id
    }
    with open(".restart_flag", "w") as f:
        json.dump(restart_info, f)
    
    # Give time for message to send
    await asyncio.sleep(1)
    
    # Restart the bot
    import sys
    import os
    
    logger.info("Executing bot restart...")
    os.execv(sys.executable, ['python'] + sys.argv)


@app.on_message(filters.command("limits"))
@authorized_only
async def limits_handler(client: Client, message: Message):
    """View Debrid-Link account limits and usage."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can check limits."
        )
        return

    msg = await message.reply_text("⏳ **Checking limits...**")
    
    try:
        resp = await debrid_service.get_limits()
        if not resp.get("success"):
            await msg.edit_text(f"❌ **Error:** Failed to fetch limits.\n`{resp.get('error', 'Unknown error')}`")
            return
            
        data = resp.get("value", {})
        
        # Parse Usage
        usage = data.get("usagePercent", {})
        usage_curr = usage.get("current", 0)
        usage_total = usage.get("value", 100)
        
        # Parse Daily Count
        day_count = data.get("dayCount", {})
        daily_curr = day_count.get("current", 0)
        daily_total = day_count.get("value", 30)
        
        # Parse Reset Time
        reset = data.get("nextResetSeconds", {})
        reset_seconds = reset.get("value", 0)
        
        # Format reset time
        import datetime
        reset_time = "Unknown"
        if reset_seconds > 0:
            m, s = divmod(reset_seconds, 60)
            h, m = divmod(m, 60)
            reset_time = f"{int(h)}h {int(m)}m"
            
        # Create progress bar
        def get_bar(current, total, length=10):
            percent = min(current / total, 1.0) if total > 0 else 0
            filled = int(length * percent)
            return "▓" * filled + "░" * (length - filled)
            
        text = (
            "📊 **Debrid-Link Account Limits**\n\n"
            f"📦 **Storage Usage:**\n"
            f"`{get_bar(usage_curr, usage_total)}` {usage_curr}%\n"
            f"Used: {usage_curr} / {usage_total} (Limit)\n\n"
            
            f"📅 **Daily Torrent Limit:**\n"
            f"`{get_bar(daily_curr, daily_total)}`\n"
            f"Used: {daily_curr} / {daily_total} torrents\n\n"
            
            f"⏳ **Quota Resets In:** `{reset_time}`\n"
            f"{'─' * 30}"
        )
        
        await msg.edit_text(text)
        
    except Exception as e:
        logger.error(f"Limits command error: {e}", exc_info=True)
        await msg.edit_text(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("limits"))
@authorized_only
async def limits_handler(client: Client, message: Message):
    """View Debrid-Link account limits and usage."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can check limits."
        )
        return

    msg = await message.reply_text("⏳ **Checking limits...**")
    
    try:
        resp = await debrid_service.get_limits()
        if not resp.get("success"):
            await msg.edit_text(f"❌ **Error:** Failed to fetch limits.\n`{resp.get('error', 'Unknown error')}`")
            return
            
        data = resp.get("value", {})
        
        # Parse Usage
        usage = data.get("usagePercent", {})
        usage_curr = usage.get("current", 0)
        usage_total = usage.get("value", 100)
        
        # Parse Daily Count
        day_count = data.get("dayCount", {})
        daily_curr = day_count.get("current", 0)
        daily_total = day_count.get("value", 30)
        
        # Parse Reset Time
        reset = data.get("nextResetSeconds", {})
        reset_seconds = reset.get("value", 0)
        
        # Format reset time
        import datetime
        reset_time = "Unknown"
        if reset_seconds > 0:
            m, s = divmod(reset_seconds, 60)
            h, m = divmod(m, 60)
            reset_time = f"{int(h)}h {int(m)}m"
            
        # Create progress bar
        def get_bar(current, total, length=10):
            percent = min(current / total, 1.0) if total > 0 else 0
            filled = int(length * percent)
            return "▓" * filled + "░" * (length - filled)
            
        text = (
            "📊 **Debrid-Link Account Limits**\n\n"
            f"📦 **Storage Usage:**\n"
            f"`{get_bar(usage_curr, usage_total)}` {usage_curr}%\n"
            f"Used: {usage_curr} / {usage_total} (Limit)\n\n"
            
            f"📅 **Daily Torrent Limit:**\n"
            f"`{get_bar(daily_curr, daily_total)}`\n"
            f"Used: {daily_curr} / {daily_total} torrents\n\n"
            
            f"⏳ **Quota Resets In:** `{reset_time}`\n"
            f"{'─' * 30}"
        )
        
        await msg.edit_text(text)
        
    except Exception as e:
        logger.error(f"Limits command error: {e}", exc_info=True)
        await msg.edit_text(f"❌ **Error:** {str(e)}")
        await message.reply_text(
            f"❌ **Error Reading Logs**\n\n"
            f"Error: `{str(e)}`"
        )

@app.on_message(filters.command("cancel"))
@authorized_only
async def cancel_handler(client: Client, message: Message):
    """Cancel an active download (admin only)."""
    # Check if user is admin
    if not config.is_admin(message.from_user.id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "Only bot administrators can cancel downloads."
        )
        return
    
    # Check if torrent ID was provided
    if len(message.command) < 2:
        await message.reply_text(
            "❌ **Missing Torrent ID**\n\n"
            "Usage: `/cancel <torrent_id>`\n\n"
            "💡 **Tip:** The torrent ID is shown in the progress message."
        )
        return
    
    provided_id = message.command[1]
    
    # Find torrent by full ID or last 6 characters
    torrent_id = None
    if provided_id in TRACKED_TORRENTS:
        # Exact match
        torrent_id = provided_id
    else:
        # Try to match by last 6 characters
        for tid in TRACKED_TORRENTS.keys():
            if tid.endswith(provided_id):
                torrent_id = tid
                break
    
    # Check if torrent is being tracked
    if not torrent_id:
        await message.reply_text(
            "⚠️ **Torrent Not Found**\n\n"
            f"Torrent ID: `{provided_id}`\n\n"
            "This torrent is not currently being tracked by the bot.\n"
            "It may have already completed or been cancelled."
        )
        return
    
    msg = await message.reply_text("⏳ **Cancelling download...**")
    
    try:
        # Get the progress message before removing from tracking
        progress_msg = TRACKED_TORRENTS[torrent_id].get("msg")
        
        # Delete the torrent from Debrid-Link seedbox
        result = await debrid_service.delete_torrent(torrent_id)
        
        # Remove from tracking
        TRACKED_TORRENTS.pop(torrent_id, None)
        
        # Delete the progress message
        if progress_msg:
            try:
                await progress_msg.delete()
            except Exception as e:
                logger.error(f"Error deleting progress message: {e}")
        
        if result.get("success"):
            await msg.edit_text(
                "✅ **Download Cancelled Successfully**\n\n"
                f"Torrent ID: `{torrent_id}`\n\n"
                "The download has been stopped and removed from seedbox."
            )
        else:
            error_msg = result.get("error", "Unknown error")
            await msg.edit_text(
                "⚠️ **Partial Cancellation**\n\n"
                f"Torrent ID: `{torrent_id}`\n\n"
                f"❌ **Server Error:** {error_msg}\n\n"
                "The torrent has been removed from bot tracking, but may still be on the server.\n"
                "You may need to manually remove it from Debrid-Link website."
            )
    except Exception as e:
        logger.error(f"Cancel command error: {e}", exc_info=True)
        await msg.edit_text(
            f"❌ **Error Cancelling Download**\n\n"
            f"Torrent ID: `{torrent_id}`\n\n"
            f"Error: `{str(e)}`"
        )


@app.on_message(filters.command("dl"))
@authorized_only
async def dl_handler(client: Client, message: Message):
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
            "Please either:\n"
            "• Send `/dl <link>`\n"
            "• Reply to a .torrent file with `/dl`\n\n"
            "💡 Use `/help` for more information."
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
                # Store ZIP flag in tracked torrents
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
            if link.lower().endswith('.torrent') or '.torrent?' in link.lower():
                # Download the .torrent file from URL
                try:
                    import aiohttp
                    status_msg = await sent_msg.edit_text("⏬️ **Downloading .torrent file from URL...**")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(link) as response:
                            if response.status == 200:
                                file_bytes = await response.read()
                                await status_msg.edit_text("⬆️ **Uploading .torrent file...**")
                                
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
            elif "magnet:" in link:
                # Magnet Link
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
            else:
                # Hoster Link
                # Validate Google Drive links - reject folder links
                if "drive.google.com" in link.lower():
                    # Google Drive folder patterns: /folders/, /drive/folders/
                    if "/folders/" in link or "/drive/folders/" in link or "/drive/u/" in link and "/folders/" in link:
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
                    # MEGA folder patterns: /folder/, /#F!, /#!
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
                    # If no download link or returned link is same as original, it failed
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

async def check_instant_cache(msg: Message, t_id: str, user, create_zip: bool = False, force_no_zip: bool = False):
    """Checks if a torrent is 100% done immediately after adding."""
    # We need to fetch the list because the add response usually doesn't have file links yet
    try:
        response = await debrid_service.get_seedbox_torrents()
        if not response.get("success"):
            # Fallback to monitoring
            TRACKED_TORRENTS[t_id] = {"msg": msg, "user": user, "create_zip": create_zip, "force_no_zip": force_no_zip}
            await msg.edit_text("🌊 Added to Seedbox. Waiting for metadata...")
            return

        active_list = response.get("value", [])
        data = next((t for t in active_list if t["id"] == t_id), None)
        
        if data and data.get("downloadPercent", 0) >= 100:
            # INSTANT HIT!
            await send_completion_message(msg, data, t_id, user, create_zip, force_no_zip)
        else:
            # Not cached or still processing
            TRACKED_TORRENTS[t_id] = {"msg": msg, "user": user, "create_zip": create_zip, "force_no_zip": force_no_zip}
            await msg.edit_text("🌊 Added to Seedbox. Waiting for metadata...")
            
    except Exception as e:
        logger.error(f"Cache check error: {e}")
        # Fallback
        TRACKED_TORRENTS[t_id] = {"msg": msg, "user": user, "create_zip": create_zip, "force_no_zip": force_no_zip}
        await msg.edit_text("🌊 Added to Seedbox. Waiting for metadata...")

async def monitor_progress():
    """Background task to monitor torrent progress."""
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
                status = data.get("status", "unknown") # downloading, seeding, error, etc
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
                    await send_completion_message(msg, data, t_id, user, create_zip, force_no_zip)
                
                else:
                    # In Progress - pass cached size
                    await update_progress_message(msg, data, user, torrent_data.get("cached_size", 0))

        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}", exc_info=True)
        
        await asyncio.sleep(5)

def get_file_links(files: list) -> str:
    """Generates formatted links for files, distinguishing streams."""
    from utils.url_proxy import encode_url
    
    links_text = ""
    if not files:
        return links_text
    
    links_text = "\n\n📂 **Files:**"
    VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv'}
    
    count = 0
    for f in files:
        if count >= 20:  # Increased limit to 20 files
            links_text += f"\n...and {len(files)-20} more."
            break
            
        if "downloadUrl" in f:
            name = f['name']
            ext = os.path.splitext(name)[1].lower()
            
            # Proxify the URL for embedded link
            proxied_url = encode_url(f['downloadUrl'], name)
            
            if ext in VIDEO_EXTS:
                # Video file with proxified link
                links_text += f"\n- 🎬 [{name}]({proxied_url})"
            else:
                # Other files with proxified link
                links_text += f"\n- ⬇️ [{name}]({proxied_url})"
        count += 1
    return links_text

async def send_completion_message(msg: Message, data: dict, t_id: str, user, create_zip: bool = False, force_no_zip: bool = False):
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
            status = await msg.edit_text("📦 Creating ZIP archive...")
            
            # Extract all file IDs
            file_ids = [f['id'] for f in files if 'id' in f]
            
            if file_ids:
                zip_resp = await debrid_service.create_zip(t_id, file_ids)
                logger.info(f"ZIP API Raw Response: {zip_resp}")
                
                if zip_resp.get("success"):
                    # Check different possible locations for the link
                    val = zip_resp.get("value", {})
                    if isinstance(val, str):
                        zip_url = val
                    elif isinstance(val, dict):
                        zip_url = val.get("link") or val.get("url") or val.get("downloadUrl")
                    
                    if zip_url:
                        logger.info(f"Found ZIP URL: {zip_url}")
                    else:
                        logger.warning(f"ZIP success but no link found in value: {val}")
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
        links_text = "" # Clear file list if ZIP is available
    else:
        links_text = get_file_links(files)
    
    # Get keyboard: only show keyboard if ZIP is available, otherwise None
    keyboard = keyboards.get_torrent_files_keyboard(files, zip_url=zip_url) if zip_url else None
    
    # Create user mention
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"
    
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
        f"📏 **File Size:** {display.human_readable_size(size)}\n\n"
        f"👤 **User:** {user_mention}\n"
        f"🆔 **User ID:** `{user.id}`"
        f"{links_text}"
        f"{zip_info}\n\n"
        f"{'━' * 30}"
    )
    
    try:
        await msg.delete() # Delete progress message
        # Use default Markdown parse mode for consistent formatting
        await msg.reply_text(final_text, quote=False, reply_markup=keyboard) # Send new message
    except Exception as e:
        logger.error(f"Error sending completion msg: {e}")
    
    TRACKED_TORRENTS.pop(t_id, None)

async def update_progress_message(msg: Message, data: dict, user, cached_size: int = 0):
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



@app.on_callback_query()
async def callback_handler(client: Client, callback: CallbackQuery):
    """Handle all callback queries from inline buttons."""
    data = callback.data
    
    try:
        # Help button
        if data == "help":
            help_text = (
                "📖 **Debrid-Link Bot - Help**\n\n"
                "**Available Commands:**\n\n"
                
                "🔹 `/start` - Start the bot and see welcome message\n"
                "🔹 `/help` - Show this help message\n"
                "🔹 `/dl <link> [-zip|-z]` - Download a link\n"
                "   • Supports: Magnet links, torrent files, hoster links\n"
                "   • Example: `/dl magnet:?xt=... -zip`\n"
                "   • Or reply to a message with `/dl -z`\n"
                "   • Add `-zip` or `-z` to create a ZIP archive\n\n"
                
                "**Admin Commands:**\n"
                "🔹 `/auth [chat_id]` - Authorize a chat\n"
                "🔹 `/deauth [chat_id]` - Revoke chat authorization\n\n"
                
                "**How to Download:**\n"
                "1️⃣ Send `/dl <link>` or reply to a torrent/magnet/link\n"
                "2️⃣ Add `-zip` or `-z` flag for ZIP archive (multi-file torrents)\n"
                "3️⃣ Wait for the download to complete\n"
                "4️⃣ Get your download links!\n\n"
                
                "**Supported Link Types:**\n"
                "• 🧲 Magnet links\n"
                "• 📁 Torrent files (.torrent)\n"
                "• 🔗 Direct download links (Debrid-supported hosters)\n\n"
                
                "**Need Help?**\n"
                "Contact the bot owner if you have issues.\n\n"
                "💡 **Tip:** Video files will provide stream links!"
            )
            await callback.message.edit_text(
                help_text,
                reply_markup=keyboards.get_help_keyboard()
            )
            await callback.answer()
        
        # Info button
        elif data == "info":
            info_text = (
                "ℹ️ **Bot Information**\n\n"
                "🤖 **Name:** Debrid-Link Bot\n"
                "🔧 **Service:** Debrid-Link.fr\n"
                "💻 **Framework:** Pyrogram\n\n"
                "**Features:**\n"
                "• Download magnet links\n"
                "• Process torrent files\n"
                "• Handle hoster links\n"
                "• Real-time progress tracking\n"
                "• Stream video files\n\n"
                "🔐 Authorization required for use."
            )
            await callback.message.edit_text(
                info_text,
                reply_markup=keyboards.get_help_keyboard()
            )
            await callback.answer()
        
        # Start button (back to start)
        elif data == "start":
            welcome_text = (
                "🎉 **Welcome to Debrid-Link Bot!**\n\n"
                "I help you download torrents, magnet links, and hoster links using Debrid-Link.\n\n"
                "**Quick Start:**\n"
                "• Use `/dl <link>` to download\n"
                "• Reply to a `.torrent` file with `/dl`\n"
                "• Use `/help` to see all commands\n\n"
                "✨ Let's get started!"
            )
            await callback.message.edit_text(
                welcome_text,
                reply_markup=keyboards.get_start_keyboard()
            )
            await callback.answer()
        
        # Delete message button (admin only)
        elif data == "delete_msg":
            if not config.is_admin(callback.from_user.id):
                await callback.answer("⛔ Only bot administrators can delete messages.", show_alert=True)
                return
            
            await callback.message.delete()
            await callback.answer("🗑️ Message deleted!")
        
        # Cancel download button (admin only)
        elif data.startswith("cancel_"):
            if not config.is_admin(callback.from_user.id):
                await callback.answer("⛔ Only bot administrators can cancel downloads.", show_alert=True)
                return
            
            torrent_id = data.replace("cancel_", "")
            await callback.message.edit_text(
                "⚠️ **Cancel Download?**\n\n"
                "Are you sure you want to cancel this download?\n"
                "This action cannot be undone.",
                reply_markup=keyboards.get_cancel_confirm_keyboard(torrent_id)
            )
            await callback.answer()
        
        # Confirm cancel
        elif data.startswith("confirm_cancel_"):
            if not config.is_admin(callback.from_user.id):
                await callback.answer("⛔ Only bot administrators can cancel downloads.", show_alert=True)
                return
            
            torrent_id = data.replace("confirm_cancel_", "")
            
            # Actually delete the torrent from Debrid-Link seedbox
            result = await debrid_service.delete_torrent(torrent_id)
            
            # Remove from tracking
            TRACKED_TORRENTS.pop(torrent_id, None)
            
            if result.get("success"):
                await callback.message.edit_text(
                    "✅ **Download Cancelled**\n\n"
                    f"Torrent ID: `{torrent_id}`\n\n"
                    "The download has been stopped and removed from Debrid-Link seedbox."
                )
                await callback.answer("✅ Download cancelled and removed from server!")
            else:
                error_msg = result.get("error", "Unknown error")
                await callback.message.edit_text(
                    "⚠️ **Cancel Attempted**\n\n"
                    f"Torrent ID: `{torrent_id}`\n\n"
                    f"❌ Error: {error_msg}\n\n"
                    "The torrent has been removed from bot tracking, but may still be on the server."
                )
                await callback.answer("⚠️ Removed from tracking, but server deletion failed")
        
        # Dismiss button
        elif data == "dismiss":
            await callback.answer("✅ Action cancelled")
            # Restore the progress message if possible
            # For now, just dismiss the confirmation
            await callback.message.delete()
        
        else:
            await callback.answer("❓ Unknown action")
    
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        await callback.answer("❌ An error occurred", show_alert=True)

async def main():
    # Initialize database
    logger.info("Initializing database...")
    from database import init_database
    await init_database()
    
    # Run migration from auth_chats.txt if it exists
    logger.info("Checking for auth migration...")
    await auth_service.migrate_from_file()
    
    async with app:
        # Start health check web server for Render hosting
        await start_web_server()
        
        # Check if bot was just restarted
        import json
        if os.path.exists(".restart_flag"):
            try:
                with open(".restart_flag", "r") as f:
                    restart_info = json.load(f)
                
                # Send success message
                await app.send_message(
                    chat_id=restart_info["chat_id"],
                    text=(
                        "✅ **Bot Restarted Successfully!**\n\n"
                        "The bot is now online and ready to use."
                    ),
                    reply_to_message_id=restart_info["message_id"]
                )
                logger.info("Restart success notification sent")
                
                # Remove the flag file
                os.remove(".restart_flag")
            except Exception as e:
                logger.error(f"Failed to send restart confirmation: {e}")
                # Clean up flag file anyway
                try:
                    os.remove(".restart_flag")
                except:
                    pass
        
        # Start background task
        asyncio.create_task(monitor_progress())
        logger.info("Bot started and monitoring...")
        await asyncio.get_running_loop().create_future() # Run forever

if __name__ == "__main__":
    try:
        app.run(main())
    except KeyboardInterrupt:
        pass
