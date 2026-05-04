import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

_engine = None
_session_factory: async_sessionmaker | None = None


async def init_db(database_path: str) -> None:
    global _engine, _session_factory

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    connection_string = f"sqlite+aiosqlite:///{database_path}"
    _engine = create_async_engine(connection_string, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    from app.db.models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized at %s", database_path)


async def get_db():
    async with _session_factory() as session:
        yield session


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
