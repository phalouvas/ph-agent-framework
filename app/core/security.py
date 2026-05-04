import logging

from fastapi import Request

from app.core.errors import AuthenticationError
from app.core.hashing import hash_api_key
from app.core.keys_config import lookup_key

logger = logging.getLogger(__name__)


def _extract_api_key(request: Request) -> str | None:
    """Extract API key from X-API-Key or Authorization: Bearer header."""
    if key := request.headers.get("X-API-Key"):
        return key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def validate_api_key(request: Request):
    """FastAPI dependency: extract and validate the API key."""
    api_key = _extract_api_key(request)
    if not api_key:
        raise AuthenticationError("Missing X-API-Key or Authorization: Bearer header")

    key_hash = hash_api_key(api_key)
    key_info = lookup_key(key_hash)

    if key_info is None:
        raise AuthenticationError("Invalid API key")

    return key_info
