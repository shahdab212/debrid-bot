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

AUTH_FILE = "auth_chats.txt"

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

    async def migrate_from_file(self):
        """Migrate authorized chats from text file to database."""
        if not os.path.exists(AUTH_FILE):
            logger.info("No auth_chats.txt file found, skipping migration")
            return
        
        logger.info("Starting migration from auth_chats.txt to database")
        migrated_count = 0
        
        try:
            # Read chat IDs from file
            chat_ids = []
            with open(AUTH_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            chat_ids.append(int(line))
                        except ValueError:
                            logger.warning(f"Invalid chat ID in file: {line}")
            
            # Get first admin ID for "authorized_by" field
            admin_ids = config.get_admin_list()
            default_admin = admin_ids[0] if admin_ids else None
            
            # Insert into database
            async with AsyncSessionLocal() as session:
                for chat_id in chat_ids:
                    try:
                        # Check if already exists
                        result = await session.execute(
                            select(AuthorizedChat).filter(AuthorizedChat.chat_id == chat_id)
                        )
                        existing = result.scalar_one_or_none()
                        
                        if not existing:
                            new_chat = AuthorizedChat(
                                chat_id=chat_id,
                                authorized_by=default_admin
                            )
                            session.add(new_chat)
                            migrated_count += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate chat {chat_id}: {e}")
                
                await session.commit()
            
            # Rename the file to prevent re-migration
            backup_file = f"{AUTH_FILE}.migrated"
            os.rename(AUTH_FILE, backup_file)
            
            logger.info(f"Migration complete: {migrated_count} chats migrated to database")
            logger.info(f"Backup saved as: {backup_file}")
            
            # Reload cache
            self._cache_loaded = False
            await self._load_cache()
            
        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            raise

# Create global instance
auth_service = AuthService()

def authorized_only(func):
    """Decorator to restrict commands to authorized users only."""
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if not await auth_service.is_authorized(message.chat.id):
            await message.reply_text(
                "🔒 **Access Denied**\\n\\n"
                "You are not authorized to use this bot.\\n\\n"
                "📧 Please contact the bot administrator to request access."
            )
            return
        return await func(client, message, *args, **kwargs)
    return wrapper
