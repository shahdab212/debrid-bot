"""Configuration package."""

from .settings import settings, BotSettings

# Backward compatibility alias
config = settings

__all__ = ['settings', 'BotSettings', 'config']
