from __future__ import annotations
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# ── Build the DB URL ────────────────────────────────────────────────────────
_url = settings.database_url

# Convert postgres:// / postgresql:// → postgresql+asyncpg://
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+asyncpg://", 1)

# Fallback: if URL is empty or still has placeholder text → use local SQLite
_IS_SQLITE = False
_PLACEHOLDER_PHRASES = ["[YOUR-PASSWORD]", "[YOUR-PROJECT-REF]", "change_me", ""]
if not _url or any(p in _url for p in _PLACEHOLDER_PHRASES):
    _db_path = os.path.join(os.path.dirname(__file__), "..", "..", "privatebrain_dev.db")
    _db_path = os.path.abspath(_db_path)
    _url = f"sqlite+aiosqlite:///{_db_path}"
    _IS_SQLITE = True
    print(f"[PrivateBrain] ⚠ No Postgres configured — using SQLite dev DB: {_db_path}")

# ── Engine ───────────────────────────────────────────────────────────────────
_engine_kwargs: dict = {
    "echo": settings.environment == "development",
}
if not _IS_SQLITE:
    _engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 300,
    })

engine = create_async_engine(_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables (safe to call on every startup — idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
