"""Download history tracking service."""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import DownloadHistory
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class HistoryService:
    """Service for tracking and querying download history."""
    
    async def create_download(
        self,
        user_id: int,
        username: Optional[str],
        torrent_name: str,
        download_type: str,
        torrent_id: Optional[str] = None,
        size_bytes: Optional[int] = None,
        custom_filename: Optional[str] = None
    ) -> DownloadHistory:
        """
        Create a new download history entry.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            torrent_name: Name of the torrent/file
            download_type: Type of download ('magnet', 'torrent', 'hoster')
            torrent_id: Optional torrent ID from Debrid-Link
            size_bytes: Optional file size in bytes
            custom_filename: Optional custom filename provided by user
            
        Returns:
            Created DownloadHistory object
        """
        async with AsyncSessionLocal() as session:
            download = DownloadHistory(
                user_id=user_id,
                username=username,
                torrent_name=torrent_name,
                download_type=download_type,
                torrent_id=torrent_id,
                size_bytes=size_bytes,
                custom_filename=custom_filename,
                status='pending',
                download_started=datetime.utcnow()
            )
            
            session.add(download)
            await session.commit()
            await session.refresh(download)
            
            logger.info(f"Created download history entry: {download.id} for user {user_id}")
            return download
    
    async def update_status(
        self,
        download_id: int,
        status: str,
        error_message: Optional[str] = None,
        created_zip: bool = False
    ):
        """
        Update download status.
        
        Args:
            download_id: ID of download history entry
            status: New status ('downloading', 'completed', 'failed', 'cancelled')
            error_message: Optional error message if failed
            created_zip: Whether a ZIP was created
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DownloadHistory).where(DownloadHistory.id == download_id)
            )
            download = result.scalar_one_or_none()
            
            if download:
                download.status = status
                if error_message:
                    download.error_message = error_message
                if status == 'completed':
                    download.download_completed = datetime.utcnow()
                download.created_zip = created_zip
                
                await session.commit()
                logger.info(f"Updated download {download_id} status to {status}")
    
    async def get_user_history(
        self,
        user_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> list[DownloadHistory]:
        """
        Get download history for a user.
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of records to return
            offset: Pagination offset
            
        Returns:
            List of DownloadHistory objects
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DownloadHistory)
                .where(DownloadHistory.user_id == user_id)
                .order_by(DownloadHistory.download_started.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())
    
    async def get_user_stats(self, user_id: int) -> dict:
        """
        Get statistics for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with user statistics
        """
        async with AsyncSessionLocal() as session:
            # Total downloads
            total_result = await session.execute(
                select(func.count(DownloadHistory.id))
                .where(DownloadHistory.user_id == user_id)
            )
            total_downloads = total_result.scalar()
            
            # Completed downloads
            completed_result = await session.execute(
                select(func.count(DownloadHistory.id))
                .where(
                    DownloadHistory.user_id == user_id,
                    DownloadHistory.status == 'completed'
                )
            )
            completed_downloads = completed_result.scalar()
            
            # Total size
            size_result = await session.execute(
                select(func.sum(DownloadHistory.size_bytes))
                .where(
                    DownloadHistory.user_id == user_id,
                    DownloadHistory.status == 'completed'
                )
            )
            total_size = size_result.scalar() or 0
            
            return {
                'total_downloads': total_downloads,
                'completed_downloads': completed_downloads,
                'failed_downloads': total_downloads - completed_downloads,
                'total_size_bytes': total_size
            }
    
    async def get_global_stats(self) -> dict:
        """
        Get global bot statistics.
        
        Returns:
            Dictionary with global statistics
        """
        async with AsyncSessionLocal() as session:
            # Total downloads
            total_result = await session.execute(
                select(func.count(DownloadHistory.id))
            )
            total_downloads = total_result.scalar()
            
            # Completed downloads
            completed_result = await session.execute(
                select(func.count(DownloadHistory.id))
                .where(DownloadHistory.status == 'completed')
            )
            completed_downloads = completed_result.scalar()
            
            # Unique users
            users_result = await session.execute(
                select(func.count(func.distinct(DownloadHistory.user_id)))
            )
            unique_users = users_result.scalar()
            
            # Total size
            size_result = await session.execute(
                select(func.sum(DownloadHistory.size_bytes))
                .where(DownloadHistory.status == 'completed')
            )
            total_size = size_result.scalar() or 0
            
            # Downloads by type
            type_result = await session.execute(
                select(
                    DownloadHistory.download_type,
                    func.count(DownloadHistory.id)
                )
                .group_by(DownloadHistory.download_type)
            )
            downloads_by_type = dict(type_result.all())
            
            return {
                'total_downloads': total_downloads,
                'completed_downloads': completed_downloads,
                'failed_downloads': total_downloads - completed_downloads,
                'unique_users': unique_users,
                'total_size_bytes': total_size,
                'downloads_by_type': downloads_by_type
            }


# Global instance
history_service = HistoryService()
