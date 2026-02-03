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
            
            # Immediately update the status messages in ALL chats
            # This ensures the cancelled torrent is removed from everyone's view
            from core.status_tracker import update_status_message, STATUS_MESSAGES
            
            logger.info(f"Cancellation: TRACKED_TORRENTS count after removal: {len(TRACKED_TORRENTS)}")
            logger.info(f"Cancellation: Active status messages: {list(STATUS_MESSAGES.keys())}")
            
            # Update status for ALL chats that have a status message
            for sid in list(STATUS_MESSAGES.keys()):
                logger.info(f"Updating status for sid {sid} after cancellation")
                # Force update to show updated list immediately
                await update_status_message(sid, client, force=True)
            
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
            from core.status_tracker import STATUS_MESSAGES
            
            # Get sid from callback message
            sid = callback.message.chat.id
            
            if sid in STATUS_MESSAGES:
                status_state = STATUS_MESSAGES[sid]
                status_state["page_no"] += status_state.get("page_step", 1)
                
                # Force update to show new page
                from core.status_tracker import update_status_message
                await update_status_message(sid, client, force=True)
            
            await callback.answer("➡️ Next page")
        
        # Status pagination - Previous button
        elif data == "status_prev":
            from core.status_tracker import STATUS_MESSAGES
            
            # Get sid from callback message
            sid = callback.message.chat.id
            
            if sid in STATUS_MESSAGES:
                status_state = STATUS_MESSAGES[sid]
                status_state["page_no"] = max(0, status_state["page_no"] - status_state.get("page_step", 1))
                
                # Force update to show new page
                from core.status_tracker import update_status_message
                await update_status_message(sid, client, force=True)
            
            await callback.answer("⬅️ Previous page")
        
        # Status page info button (just informational)
        elif data == "status_page_info":
            await callback.answer("📄 Page indicator", show_alert=False)
        
        # Search help callback
        elif data == "search_help":
            await callback.answer()
            await callback.message.reply_text(
                "📖 **How to Download Search Results**\n\n"
                "**Step 1:** Click 'View Results' button\n"
                "This opens a Telegraph page with all torrents\n\n"
                "**Step 2:** Browse the results\n"
                "Look for the torrent you want to download\n\n"
                "**Step 3:** Click 'View Details'\n"
                "This takes you to the torrent info page on 1337x\n\n"
                "**Step 4:** Get the magnet link\n"
                "Copy the magnet link from the info page\n\n"
                "**Step 5:** Download with bot\n"
                "Send the command: `/dl magnet:...`\n\n"
                f"{'━' * 30}\n\n"
                "💡 **Pro Tip:** You can also use `-zip` flag:\n"
                "`/dl magnet:... -zip`"
            )
        
        else:
            await callback.answer("❓ Unknown action")
    
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        await callback.answer("❌ An error occurred", show_alert=True)
