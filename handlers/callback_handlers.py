"""Callback query handlers for inline buttons."""

import logging
from pyrogram import Client
from pyrogram.types import CallbackQuery

from config import config
from services.debrid_service import debrid_service
from core.torrent_manager import TRACKED_TORRENTS
from utils import keyboards

logger = logging.getLogger(__name__)


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
            
            # Immediately update the consolidated status message in ALL chats
            # This ensures the cancelled torrent is removed from everyone's view
            from core.message_builder import update_consolidated_status
            import core.torrent_manager as tm
            
            logger.info(f"Cancellation: TRACKED_TORRENTS count after removal: {len(TRACKED_TORRENTS)}")
            logger.info(f"Cancellation: CONSOLIDATED_STATUS_MESSAGES chats: {list(tm.CONSOLIDATED_STATUS_MESSAGES.keys())}")
            
            # Update status for ALL chats that have a status message
            for chat_id in list(tm.CONSOLIDATED_STATUS_MESSAGES.keys()):
                logger.info(f"Updating status for chat {chat_id} after cancellation")
                # Force recreate to show updated list immediately
                await update_consolidated_status(client, chat_id, force_recreate=True)
            
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
        
        # Status pagination - Next button
        elif data == "status_next":
            import core.torrent_manager as tm
            from core.message_builder import update_consolidated_status
            
            # Increment page
            tm.STATUS_CURRENT_PAGE += 1
            
            # Update the consolidated status message
            chat_id = callback.message.chat.id
            await update_consolidated_status(client, chat_id)
            await callback.answer("➡️ Next page")
        
        # Status pagination - Previous button
        elif data == "status_prev":
            import core.torrent_manager as tm
            from core.message_builder import update_consolidated_status
            
            # Decrement page
            tm.STATUS_CURRENT_PAGE = max(0, tm.STATUS_CURRENT_PAGE - 1)
            
            # Update the consolidated status message
            chat_id = callback.message.chat.id
            await update_consolidated_status(client, chat_id)
            await callback.answer("⬅️ Previous page")
        
        # Status page info button (just informational)
        elif data == "status_page_info":
            await callback.answer("📄 Page indicator", show_alert=False)
        
        else:
            await callback.answer("❓ Unknown action")
    
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        await callback.answer("❌ An error occurred", show_alert=True)
