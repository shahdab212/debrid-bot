"""File list service for storing and retrieving torrent file lists."""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models import TorrentFileList
from database import AsyncSessionLocal
from config import settings

logger = logging.getLogger(__name__)


async def create_file_list(torrent_id: str, torrent_name: str, files: List[Dict[str, Any]]) -> str:
    """
    Create a file list entry in the database.
    
    Args:
        torrent_id: The torrent ID
        torrent_name: The torrent name
        files: List of file objects with 'name', 'size', 'downloadUrl', etc.
        
    Returns:
        str: UUID of the created file list
    """
    file_list_id = str(uuid.uuid4())
    files_json = json.dumps(files)
    
    async with AsyncSessionLocal() as session:
        try:
            file_list = TorrentFileList(
                id=file_list_id,
                torrent_id=torrent_id,
                torrent_name=torrent_name,
                files_json=files_json,
                created_at=datetime.utcnow()
            )
            session.add(file_list)
            await session.commit()
            
            logger.info(f"Created file list {file_list_id} for torrent {torrent_id} with {len(files)} files")
            return file_list_id
            
        except Exception as e:
            logger.error(f"Error creating file list: {e}")
            await session.rollback()
            raise


async def get_file_list(file_list_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a file list from the database.
    
    Args:
        file_list_id: UUID of the file list
        
    Returns:
        Dict with 'torrent_id', 'torrent_name', 'files', 'created_at', or None if not found/expired
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(TorrentFileList).where(TorrentFileList.id == file_list_id)
            result = await session.execute(stmt)
            file_list = result.scalar_one_or_none()
            
            if not file_list:
                logger.warning(f"File list {file_list_id} not found")
                return None
            
            # Check if expired
            expiry_time = file_list.created_at + timedelta(hours=settings.FILE_LIST_EXPIRY_HOURS)
            if datetime.utcnow() > expiry_time:
                logger.warning(f"File list {file_list_id} expired")
                return None
            
            # Parse files JSON
            files = json.loads(file_list.files_json)
            
            return {
                'torrent_id': file_list.torrent_id,
                'torrent_name': file_list.torrent_name,
                'files': files,
                'created_at': file_list.created_at
            }
            
        except Exception as e:
            logger.error(f"Error retrieving file list {file_list_id}: {e}")
            return None


async def cleanup_old_entries() -> int:
    """
    Delete file list entries older than the expiry time.
    
    Returns:
        int: Number of deleted entries
    """
    async with AsyncSessionLocal() as session:
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=settings.FILE_LIST_EXPIRY_HOURS)
            
            stmt = delete(TorrentFileList).where(TorrentFileList.created_at < cutoff_time)
            result = await session.execute(stmt)
            await session.commit()
            
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired file list entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            await session.rollback()
            return 0
