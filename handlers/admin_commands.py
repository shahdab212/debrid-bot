"""
Admin command handlers for the Debrid-Link Telegram bot.

Contains all administrative commands:
- /auth - Authorize a chat
- /deauth - Revoke authorization
- /users - List authorized users
- /restart - Restart the bot
- /log - View bot logs
- /limits - Check Debrid-Link account limits
- /cancel - Cancel active download
"""
import asyncio
import os
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from sqlalchemy import select

from config import config
from services.auth_service import auth_service
from services.debrid_service import debrid_service
from database import AsyncSessionLocal
from models import AuthorizedChat

logger = logging.getLogger(__name__)

# Import from parent module (will be set when handlers are registered)
TRACKED_TORRENTS = None


def set_tracked_torrents(tracked_dict):
    """Set reference to the global TRACKED_TORRENTS dictionary."""
    global TRACKED_TORRENTS
    TRACKED_TORRENTS = tracked_dict


@filters.create
def admin_only_filter(_, __, message):
    """Filter to restrict commands to admins only."""
    return config.is_admin(message.from_user.id)


# Handler instances (will be registered with app in bot.py)
auth_handler = filters.command("auth") & admin_only_filter
deauth_handler = filters.command("deauth") & admin_only_filter
users_handler = filters.command("users") & admin_only_filter
restart_handler = filters.command("restart") & admin_only_filter
log_handler = filters.command("log") & admin_only_filter
limits_handler = filters.command("limits") & admin_only_filter
cancel_handler = filters.command("cancel") & admin_only_filter


async def handle_auth(client: Client, message: Message):
    """Authorize a chat to use the bot (admin only)."""
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


async def handle_deauth(client: Client, message: Message):
    """Revoke authorization for a chat (admin only)."""
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


async def handle_log(client: Client, message: Message):
    """View recent bot logs (admin only)."""
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
        await message.reply_text(
            f"❌ **Error Reading Logs**\n\n"
            f"Error: `{str(e)}`"
        )


async def handle_users(client: Client, message: Message):
    """List all authorized users (admin only)."""
    msg = await message.reply_text("⏳ **Fetching authorized users...**")
    
    try:
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


async def handle_restart(client: Client, message: Message):
    """Restart the bot (admin only)."""
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
    
    logger.info("Executing bot restart...")
    os.execv(sys.executable, ['python'] + sys.argv)


async def handle_limits(client: Client, message: Message):
    """View Debrid-Link account limits and usage (admin only)."""
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


async def handle_cancel(client: Client, message: Message):
    """Cancel an active download (admin only)."""
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
