import os
import aiofiles
from functools import wraps
from config import config

AUTH_FILE = "auth_chats.txt"

class AuthService:
    def __init__(self):
        self.auth_chats = set()
        self.load_auth_chats()

    def load_auth_chats(self):
        if not os.path.exists(AUTH_FILE):
            return
        with open(AUTH_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.auth_chats.add(int(line))
                    except ValueError:
                        pass

    async def add_chat(self, chat_id: int):
        if chat_id in self.auth_chats:
            return
        self.auth_chats.add(chat_id)
        async with aiofiles.open(AUTH_FILE, "a") as f:
            await f.write(f"{chat_id}\n")

    async def remove_chat(self, chat_id: int):
        if chat_id not in self.auth_chats:
            return
        self.auth_chats.discard(chat_id)
        # Rewrite file
        async with aiofiles.open(AUTH_FILE, "w") as f:
            for cid in self.auth_chats:
                await f.write(f"{cid}\n")

    def is_authorized(self, chat_id: int) -> bool:
        """Check if a chat is authorized (either admin or in auth list)."""
        return config.is_admin(chat_id) or chat_id in self.auth_chats

auth_service = AuthService()

def authorized_only(func):
    """Decorator to restrict commands to authorized users only."""
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if not auth_service.is_authorized(message.chat.id):
            await message.reply_text(
                "🔒 **Access Denied**\n\n"
                "You are not authorized to use this bot.\n\n"
                "📧 Please contact the bot administrator to request access."
            )
            return
        return await func(client, message, *args, **kwargs)
    return wrapper
