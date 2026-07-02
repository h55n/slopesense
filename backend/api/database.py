"""
SlopeSense — Database Engine and Session Management

Provides an async SQLAlchemy engine and session factory that works
with both PostgreSQL+PostGIS (production) and SQLite+aiosqlite (development/testing).

The DATABASE_URL environment variable controls which backend is used:
  - ``sqlite:///./slopesense.db``                              → SQLite (local dev)
  - ``postgresql://user:pass@host:5432/db``                   → PostgreSQL (production)
  - ``sqlite+aiosqlite:///./slopesense.db``                   → explicit aiosqlite
  - ``postgresql+asyncpg://user:pass@host:5432/db``           → explicit asyncpg

The module automatically rewrites plain ``sqlite://`` and ``postgresql://``
prefixes to their async-compatible equivalents.
"""

from typing import AsyncIterator, Optional
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


def _get_db_url() -> str:
    """Read DATABASE_URL from environment and rewrite to async driver prefix.

    Returns:
        A database URL with an async-compatible driver prefix
        (``sqlite+aiosqlite://`` or ``postgresql+asyncpg://``).
    """
    raw = os.environ.get("DATABASE_URL", "sqlite:///./slopesense.db")
    if not raw:
        raw = "sqlite:///./slopesense.db"
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
# SQLite does not support connection pooling parameters
if not _db_url.startswith("sqlite"):
    _engine_kwargs.update({
        "pool_size": 10,       # base pool size
        "max_overflow": 20,    # extra connections above pool_size
        "pool_recycle": 3600,  # recycle connections every hour
    })

engine = create_async_engine(_db_url, **_engine_kwargs)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[Optional[AsyncSession]]:
    """FastAPI dependency that yields one async database session per request.

    Yields ``None`` if session creation fails, allowing endpoints to degrade
    gracefully (e.g., fall back to synthetic / cached data) rather than raising
    an unhandled 500 error during cold-start or database maintenance windows.

    Usage::

        @app.get("/v1/example")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            if db is None:
                return {"data": _fallback_data()}
            result = await db.execute(select(MyModel))
            ...

    Yields:
        An open ``AsyncSession``, or ``None`` on failure.
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
