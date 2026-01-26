"""Core business logic modules for the Debrid-Link bot."""

from .torrent_manager import (
    TRACKED_TORRENTS,
    FILE_PAGES,
    CONSOLIDATED_STATUS_MESSAGES,
    STATUS_CURRENT_PAGE,
    PREVIOUS_DOWNLOAD_COUNT,
    check_instant_cache,
    monitor_progress
)
from .message_builder import (
    send_completion_message,
    update_consolidated_status
)
from .file_manager import get_file_links

__all__ = [
    'TRACKED_TORRENTS',
    'FILE_PAGES',
    'CONSOLIDATED_STATUS_MESSAGES',
    'STATUS_CURRENT_PAGE',
    'PREVIOUS_DOWNLOAD_COUNT',
    'check_instant_cache',
    'monitor_progress',
    'send_completion_message',
    'update_consolidated_status',
    'get_file_links'
]


