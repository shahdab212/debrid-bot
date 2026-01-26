"""Bot settings and configuration with validation."""

from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class BotSettings(BaseSettings):
    """Bot configuration with environment variable support and validation."""
    
    # Telegram Bot Settings
    API_ID: int = Field(..., description="Telegram API ID")
    API_HASH: str = Field(..., description="Telegram API Hash")
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    
    # Debrid-Link Settings
    DEBRID_API_KEY: str = Field(..., validation_alias='DEBRID_KEY', description="Debrid-Link API Key")
    
    # Admin Settings
    ADMIN_IDS: Union[List[int], str] = Field(default_factory=list, description="Comma-separated admin user IDs")
    
    @field_validator('ADMIN_IDS', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        """Parse ADMIN_IDS from comma-separated string or list."""
        if isinstance(v, str):
            if not v.strip():
                return []
            # Parse comma-separated values
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        return v
    
    # Download Settings
    MAX_FILES_DISPLAY: int = Field(default=20, description="Maximum files to display in messages")
    AUTO_ZIP_THRESHOLD: int = Field(default=15, description="Auto-create ZIP for torrents with N+ files")
    
    # Progress Monitoring
    PROGRESS_UPDATE_INTERVAL: int = Field(default=5, description="Seconds between progress updates")
    STATUS_ITEMS_PER_PAGE: int = Field(default=5, description="Number of downloads to show per page in status message")

    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: str = Field(default="bot.log", description="Log file path")
    MAX_LOG_LINES: int = Field(default=1000, description="Maximum log lines for /log command")
    
    # Health Check Settings
    HEALTH_CHECK_PORT: int = Field(default=8080, description="Health check server port")
    
    # Database Settings
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/bot.db",
        description="Database connection URL"
    )
    
    # Cloudflare Worker (URL Proxy)
    WORKER_URL: str = Field(default="", description="Cloudflare Worker URL for proxying")
    
    # Feature Flags
    ENABLE_SEARCH: bool = Field(default=True, description="Enable /search command")
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    ENABLE_DOWNLOAD_HISTORY: bool = Field(default=True, description="Enable download history tracking")
    
    # Rate Limiting (for retry logic)
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts for failed operations")
    RETRY_BASE_DELAY: float = Field(default=1.0, description="Base delay for exponential backoff (seconds)")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env
    
    def is_admin(self, user_id: int) -> bool:
        """Check if a user ID is an admin."""
        return user_id in self.ADMIN_IDS


# Global settings instance
settings = BotSettings()
