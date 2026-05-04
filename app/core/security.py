import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError
from app.core.hashing import hash_api_key
from app.db.repositories import get_api_key_by_hash

logger = logging.getLogger(__name__)


async def bootstrap_api_keys(db: AsyncSession, initial_keys: str) -> None:
    """Insert initial API keys from env var if the table is empty."""
    from app.db.repositories import insert_api_key

    existing = await get_api_key_by_hash(db, "placeholder")
    if existing is None:
        # Try a real check: count rows
        from sqlalchemy import select, func
        from app.db.models import ApiKey

        result = await db.execute(select(func.count()).select_from(ApiKey))
        count = result.scalar()
        if count > 0:
            return

        for entry in initial_keys.split(","):
            entry = entry.strip()
            if not entry or ":" not in entry:
                continue
            key, name = entry.split(":", 1)
            await insert_api_key(db, key.strip(), name.strip())
            logger.info("Bootstrapped API key: %s", name.strip())
        await db.commit()


def _extract_api_key(request: Request) -> str | None:
    """Extract API key from X-API-Key or Authorization: Bearer header."""
    if key := request.headers.get("X-API-Key"):
        return key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def validate_api_key(request: Request, db: AsyncSession):
    """FastAPI dependency: extract and validate the API key."""
    api_key = _extract_api_key(request)
    if not api_key:
        raise AuthenticationError("Missing X-API-Key or Authorization: Bearer header")

    key_hash = hash_api_key(api_key)
    key_record = await get_api_key_by_hash(db, key_hash)

    if key_record is None or not key_record.is_active:
        raise AuthenticationError("Invalid API key")

    if key_record.expires_at is not None:
        from datetime import datetime, timezone

        if key_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise AuthenticationError("API key has expired")

    return key_record
