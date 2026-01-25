"""Database models for the bot."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuthorizedChat(Base):
    """Model for authorized chats/users."""
    __tablename__ = "authorized_chats"
    
    chat_id = Column(BigInteger, primary_key=True, index=True)
    authorized_by = Column(BigInteger, nullable=True)  # Admin who authorized
    authorized_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True)


class DownloadHistory(Base):
    """Model for tracking download history."""
    __tablename__ = "download_history"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String, nullable=True)
    
    # Download details
    torrent_id = Column(String, nullable=True, index=True)
    torrent_name = Column(String, nullable=False)
    download_type = Column(String, nullable=False)  # 'magnet', 'torrent', 'hoster'
    
    # Size and timing
    size_bytes = Column(BigInteger, nullable=True)
    download_started = Column(DateTime, default=datetime.utcnow, index=True)
    download_completed = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String, default='pending')  # 'pending', 'downloading', 'completed', 'failed', 'cancelled'
    error_message = Column(String, nullable=True)
    
    # ZIP flag
    created_zip = Column(Boolean, default=False)
    
    # Custom filename if provided
    custom_filename = Column(String, nullable=True)


class Metrics(Base):
    """Model for storing bot metrics and statistics."""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String, nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    category = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Optional metadata
    user_id = Column(BigInteger, nullable=True, index=True)
    extra_data = Column(String, nullable=True)  # JSON string for additional data (renamed from metadata)
