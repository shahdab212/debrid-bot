"""User command handlers - /start, /help, /dl, /status"""

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
        "• Check download status: /status\n"
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
        
        "▫️ /status • **Download Status**\n"
        "   View all active downloads and their progress\n\n"
        
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
async def status_handler(client: Client, message: Message):
    """Show current download status for all active torrents."""
    from core.torrent_manager import TRACKED_TORRENTS
    from core.message_builder import update_consolidated_status
    
    if not TRACKED_TORRENTS:
        # No active downloads - send friendly message
        await message.reply_text(
            "💤 **No Active Downloads**\n\n"
            "────────────────────────────\n\n"
            "📊 **Current Status:**\n"
            "There are no torrents being downloaded at the moment.\n\n"
            "✨ **Get Started:**\n"
            "• Use `/dl <link>` to start a download\n"
            "• Reply to any magnet/torrent with `/dl`\n"
            "• Add `-zip` flag for archives\n\n"
            "💡 Tip: Downloads will show here automatically once started!\n\n"
            "────────────────────────────"
        )
        return
    
    # Send a temporary message that will be deleted
    temp_msg = await message.reply_text("📊 Fetching download status...")
    
    try:
        # Delete the temporary message
        await temp_msg.delete()
        
        # Send the consolidated status (force_recreate=False to create fresh message)
        chat_id = message.chat.id
        await update_consolidated_status(client, chat_id, force_recreate=True)
        
    except Exception as e:
        logger.error(f"Status command error: {e}", exc_info=True)
        await message.reply_text(
            "❌ **Error Fetching Status**\n\n"
            f"An error occurred: `{str(e)}`\n\n"
            "Please try again in a moment."
        )
