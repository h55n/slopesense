"""
SlopeSense — Database session for SQLite-compatible local dev.
"""
from typing import AsyncIterator, Optional
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

def _get_db_url() -> str:
    raw = os.environ.get("DATABASE_URL", "sqlite:///./slopesense.db")
    if raw.startswith("sqlite://") and not raw.startswith("sqlite+aiosqlite://"):
        return raw.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if raw.startswith("postgresql://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


_db_url = _get_db_url()

_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}
# SQLite doesn't support pool_size / max_overflow
if not _db_url.startswith("sqlite"):
    _engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600,
    })

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[Optional[AsyncSession]]:
    """Yield one async database session for a request.
    
    Always yields exactly once. Yields None if session creation fails,
    allowing endpoints to degrade gracefully without DB access.
    """
    session: Optional[AsyncSession] = None
    try:
        session = AsyncSessionLocal()
        yield session
    finally:
        if session is not None:
            try:
                await session.close()
            except Exception:
                pass
