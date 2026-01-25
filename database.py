"""Database connection and initialization."""
import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from models import Base

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# If no DATABASE_URL is set, use SQLite
if not DATABASE_URL:
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    DATABASE_URL = "sqlite+aiosqlite:///data/bot.db"
    logger.info(f"Using SQLite database: {DATABASE_URL}")
else:
    # PostgreSQL support - ensure asyncpg driver is used
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    logger.info(f"Using PostgreSQL database")

# Create async engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration for async operations
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # Create async engine with proper configuration
    # For Render.com PostgreSQL (uses pgbouncer), disable prepared statements
    connect_args = {}
    if DATABASE_URL.startswith("postgresql"):
        # Disable prepared statements for pgbouncer compatibility
        connect_args = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0
        }
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=connect_args
    )

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

import asyncio

async def init_database():
    """Initialize database tables with retry logic."""
    max_retries = 12
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database initialization failed (Attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s... Error: {e}")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to initialize database after {max_retries} attempts: {e}", exc_info=True)
                raise

async def get_session() -> AsyncSession:
    """Get a database session."""
    async with AsyncSessionLocal() as session:
        yield session
