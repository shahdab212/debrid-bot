"""Metrics collection and tracking service."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import Metrics
from database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for collecting and querying bot metrics."""
    
    async def record(
        self,
        metric_name: str,
        metric_value: float,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
        extra_data: Optional[str] = None
    ):
        """
        Record a metric.
        
        Args:
            metric_name: Name of the metric
            metric_value: Numeric value
            category: Optional category for grouping
            user_id: Optional user ID associated with metric
            extra_data: Optional JSON metadata (renamed from metadata)
        """
        async with AsyncSessionLocal() as session:
            metric = Metrics(
                metric_name=metric_name,
                metric_value=metric_value,
                category=category,
                user_id=user_id,
                extra_data=extra_data,
                timestamp=datetime.utcnow()
            )
            
            session.add(metric)
            await session.commit()
            
            logger.debug(f"Recorded metric: {metric_name} = {metric_value}")
    
    async def increment(
        self,
        metric_name: str,
        amount: float = 1.0,
        category: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """
        Increment a counter metric.
        
        Args:
            metric_name: Name of the counter
            amount: Amount to increment by (default 1.0)
            category: Optional category
            user_id: Optional user ID
        """
        await self.record(metric_name, amount, category, user_id)
    
    async def get_counter_total(
        self,
        metric_name: str,
        category: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> float:
        """
        Get total value for a counter metric.
        
        Args:
            metric_name: Name of the counter
            category: Optional category filter
            since: Optional datetime to count from
            
        Returns:
            Total value of counter
        """
        async with AsyncSessionLocal() as session:
            query = select(func.sum(Metrics.metric_value)).where(
                Metrics.metric_name == metric_name
            )
            
            if category:
                query = query.where(Metrics.category == category)
            
            if since:
                query = query.where(Metrics.timestamp >= since)
            
            result = await session.execute(query)
            total = result.scalar()
            return total or 0.0
    
    async def get_recent_values(
        self,
        metric_name: str,
        limit: int = 100,
        category: Optional[str] = None
    ) -> list[tuple[datetime, float]]:
        """
        Get recent values for a metric.
        
        Args:
            metric_name: Name of the metric
            limit: Maximum number of values to return
            category: Optional category filter
            
        Returns:
            List of (timestamp, value) tuples
        """
        async with AsyncSessionLocal() as session:
            query = select(Metrics.timestamp, Metrics.metric_value).where(
                Metrics.metric_name == metric_name
            ).order_by(Metrics.timestamp.desc()).limit(limit)
            
            if category:
                query = query.where(Metrics.category == category)
            
            result = await session.execute(query)
            return list(result.all())
    
    async def get_summary(self, hours: int = 24) -> dict:
        """
        Get summary of metrics for the last N hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with metric summaries
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get totals by category
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(
                    Metrics.category,
                    Metrics.metric_name,
                    func.sum(Metrics.metric_value),
                    func.count(Metrics.id)
                )
                .where(Metrics.timestamp >= since)
                .group_by(Metrics.category, Metrics.metric_name)
            )
            
            summary = {}
            for category, name, total, count in result.all():
                cat_key = category or 'general'
                if cat_key not in summary:
                    summary[cat_key] = {}
                summary[cat_key][name] = {
                    'total': total,
                    'count': count,
                    'average': total / count if count > 0 else 0
                }
            
            return summary


# Global instance
metrics_service = MetricsService()


# Convenience functions for common metrics
async def track_download_started(download_type: str, user_id: int):
    """Track a download start."""
    await metrics_service.increment(
        'downloads_started',
        category=download_type,
        user_id=user_id
    )


async def track_download_completed(download_type: str, user_id: int, size_bytes: int):
    """Track a download completion."""
    await metrics_service.increment(
        'downloads_completed',
        category=download_type,
        user_id=user_id
    )
    await metrics_service.record(
        'download_size_bytes',
        size_bytes,
        category=download_type,
        user_id=user_id
    )


async def track_download_failed(download_type: str, user_id: int, error_type: str):
    """Track a download failure."""
    await metrics_service.increment(
        'downloads_failed',
        category=download_type,
        user_id=user_id
    )
    await metrics_service.increment(
        'errors',
        category=error_type,
        user_id=user_id
    )


async def track_command_used(command: str, user_id: int):
    """Track command usage."""
    await metrics_service.increment(
        'command_usage',
        category=command,
        user_id=user_id
    )
