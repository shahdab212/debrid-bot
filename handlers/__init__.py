"""Command handlers for the Debrid-Link bot."""

# This module will be populated by specific handler modules
from .user_commands import *
from .admin_commands import *
from .callback_handlers import *

__all__ = [
    'setup_handlers',
]


def setup_handlers(app):
    """Register all command handlers with the Pyrogram app."""
    from . import user_commands, admin_commands, callback_handlers
    
    # User command handlers are registered via decorators
    # Admin command handlers are registered via decorators
    # Callback handlers are registered via decorators
    
    # This function exists for future extensibility
    pass
