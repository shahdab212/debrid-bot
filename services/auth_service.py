"""Authentication service for managing authorized Telegram chats."""
import os
import logging
from functools import wraps
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError

from config import config
from database import AsyncSessionLocal
from models import AuthorizedChat

logger = logging.getLogger(__name__)


class AuthService:
    """Service for managing authorized chats using database storage."""
    
    def __init__(self):
        self.auth_chats = set()
        self._cache_loaded = False

    async def _load_cache(self):
        """Load authorized chat IDs into memory cache."""
        if self._cache_loaded:
            return
            
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(AuthorizedChat.chat_id))
                self.auth_chats = set(result.scalars().all())
                self._cache_loaded = True
                logger.info(f"Loaded {len(self.auth_chats)} authorized chats from database")
        except Exception as e:
            logger.error(f"Failed to load auth cache: {e}", exc_info=True)
            self.auth_chats = set()

    async def add_chat(self, chat_id: int, authorized_by: int = None):
        """Add a chat to the authorized list."""
        try:
            async with AsyncSessionLocal() as session:
                # Check if already exists
                result = await session.execute(
                    select(AuthorizedChat).filter(AuthorizedChat.chat_id == chat_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    logger.info(f"Chat {chat_id} is already authorized")
                    return
                
                # Add new authorized chat
                new_chat = AuthorizedChat(
                    chat_id=chat_id,
                    authorized_by=authorized_by
                )
                session.add(new_chat)
                await session.commit()
                
                # Update cache
                self.auth_chats.add(chat_id)
                logger.info(f"Authorized chat {chat_id} (by admin {authorized_by})")
                
        except Exception as e:
            logger.error(f"Failed to authorize chat {chat_id}: {e}", exc_info=True)
            raise

    async def remove_chat(self, chat_id: int):
        """Remove a chat from the authorized list."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    delete(AuthorizedChat).filter(AuthorizedChat.chat_id == chat_id)
                )
                await session.commit()
                
                # Update cache
                self.auth_chats.discard(chat_id)
                
                if result.rowcount > 0:
                    logger.info(f"Deauthorized chat {chat_id}")
                else:
                    logger.info(f"Chat {chat_id} was not in authorized list")
                    
        except Exception as e:
            logger.error(f"Failed to deauthorize chat {chat_id}: {e}", exc_info=True)
            raise

    async def is_authorized(self, chat_id: int) -> bool:
        """Check if a chat is authorized (either admin or in auth list)."""
        # Ensure cache is loaded
        await self._load_cache()
        
        # Admins are always authorized
        if config.is_admin(chat_id):
            return True
        
        return chat_id in self.auth_chats

# Create global instance
auth_service = AuthService()

def authorized_only(func):
    """Decorator to restrict commands to authorized users only."""
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if not await auth_service.is_authorized(message.chat.id):
            await message.reply_text(
                "🔒 **Access Denied**\n\n"
                "You are not authorized to use this bot.\n\n"
                "📧 Please contact the bot administrator to request access."
            )
            return
        return await func(client, message, *args, **kwargs)
    return wrapper
