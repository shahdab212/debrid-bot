import asyncio
# Fix for Pyrogram on Python 3.14 (RuntimeError: There is no current event loop)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import json
import logging
import os

from pyrogram import Client, filters

from config import config
from services.auth_service import auth_service
from core import monitor_progress
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

# Initialize Pyrogram client
app = Client(
    "debrid_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

# Custom filter to accept both / and . command prefixes
def dual_prefix_command(commands):
    """Filter that accepts both / and . as command prefixes"""
    if isinstance(commands, str):
        commands = [commands]
    return (filters.command(commands, prefixes="/") | filters.command(commands, prefixes="."))


# Import and register all handlers
from handlers.user_commands import start_handler, help_handler, dl_handler, hosters_handler
from handlers.user_commands_status import status_handler
from handlers.search_handler import search_handler
from handlers.admin_commands import (
    auth_handler, deauth_handler, log_handler, users_handler,
    restart_handler, limits_handler, cancel_handler
)
from handlers.callback_handlers import callback_handler

# Register user command handlers
app.on_message(dual_prefix_command("start"))(start_handler)
app.on_message(dual_prefix_command("help"))(help_handler)
app.on_message(dual_prefix_command("dl"))(dl_handler)
app.on_message(dual_prefix_command("status"))(status_handler)
app.on_message(dual_prefix_command("search"))(search_handler)
app.on_message(dual_prefix_command("hosters"))(hosters_handler)

# Register admin command handlers
app.on_message(dual_prefix_command("auth"))(auth_handler)
app.on_message(dual_prefix_command("deauth"))(deauth_handler)
app.on_message(dual_prefix_command("log"))(log_handler)
app.on_message(dual_prefix_command("users"))(users_handler)
app.on_message(dual_prefix_command("restart"))(restart_handler)
app.on_message(dual_prefix_command("limits"))(limits_handler)
app.on_message(dual_prefix_command("cancel"))(cancel_handler)

# Register callback query handler
app.on_callback_query()(callback_handler)


async def main():
    """Main bot initialization and startup."""
    # Initialize database
    logger.info("Initializing database...")
    from database import init_database
    await init_database()
    
    async with app:
        # Start health check web server for Render hosting
        await start_web_server()
        
        # Check if bot was just restarted
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
        
        # Start background task for torrent monitoring
        asyncio.create_task(monitor_progress())
        logger.info("Bot started and monitoring...")
        await asyncio.get_running_loop().create_future()  # Run forever


if __name__ == "__main__":
    try:
        app.run(main())
    except KeyboardInterrupt:
        pass
