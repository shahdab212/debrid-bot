"""Database models for the Debrid-Link bot."""
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AuthorizedChat(Base):
    """Model for storing authorized Telegram chat IDs."""
    __tablename__ = "authorized_chats"
    
    chat_id = Column(BigInteger, primary_key=True, index=True)
    authorized_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    authorized_by = Column(BigInteger, nullable=True)  # Admin user_id who authorized
    
    def __repr__(self):
        return f"<AuthorizedChat(chat_id={self.chat_id}, authorized_at={self.authorized_at})>"
