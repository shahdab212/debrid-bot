"""Search command handler for torrent search"""
import logging
from urllib.parse import quote
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from html import escape

from services.auth_service import authorized_only

logger = logging.getLogger(__name__)


@authorized_only
async def search_handler(client: Client, message: Message):
    """
    Handle /search command - shows links to popular torrent sites
    
    Usage: /search <query>
    """
    # Extract query from message
    query = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None
    
    if not query:
        await message.reply_text(
            "**🔍 Torrent Search**\n\n"
            "**Usage:** `/search <query>`\n\n"
            "**Example:**\n"
            "`/search avengers endgame`\n"
            "`/search ubuntu 22.04`\n\n"
            "I'll show you direct links to popular torrent sites with your search pre-filled!"
        )
        return
    
    # URL encode the query
    encoded_query = quote(query)
    
    # Build search URLs for various torrent sites
    search_urls = {
        "1337x": f"https://1337x.to/search/{encoded_query}/1/",
        "YTS": f"https://yts.bz/browse-movies/{encoded_query}",
        "ThePirateBay": f"https://thepiratebay.org/search.php?q={encoded_query}",
        "TorrentGalaxy": f"https://torrentgalaxy.one/get-posts/keywords:{query.replace(' ', '%20')}",
        "LimeTorrents": f"https://www.limetorrents.lol/search/all/{encoded_query}/",
        "EZTV": f"https://eztvx.to/search/{encoded_query}",
    }
    
    # Create inline keyboard with search buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔎 1337x", url=search_urls["1337x"]),
            InlineKeyboardButton("🎬 YTS", url=search_urls["YTS"]),
        ],
        [
            InlineKeyboardButton("🏴‍☠️ ThePirateBay", url=search_urls["ThePirateBay"]),
            InlineKeyboardButton("🌌 TorrentGalaxy", url=search_urls["TorrentGalaxy"]),
        ],
        [
            InlineKeyboardButton("🍋 LimeTorrents", url=search_urls["LimeTorrents"]),
            InlineKeyboardButton("📺 EZTV", url=search_urls["EZTV"]),
        ],
        [
            InlineKeyboardButton("ℹ️ How to Download", callback_data="search_help")
        ]
    ])
    
    # Send message with buttons
    await message.reply_text(
        f"🔍 **Torrent Search**\n\n"
        f"**Query:** `{escape(query)}`\n\n"
        f"👆 Click any site below to search:\n\n"
        f"{'━' * 30}\n\n"
        f"**How it works:**\n"
        f"1. Click a torrent site button\n"
        f"2. Browse search results\n"
        f"3. Copy the magnet link\n"
        f"4. Send to bot: `/dl magnet:...`\n\n"
        f"{'━' * 30}\n\n"
        f"💡 **Tip:** YTS is best for movies, 1337x for everything else!",
        reply_markup=keyboard
    )
    
    logger.info(f"Search links provided for: {query}")
