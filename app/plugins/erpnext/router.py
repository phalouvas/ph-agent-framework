import logging

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_db
from app.db.models import ApiKey
from app.db.repositories import get_tenant_for_api_key
from app.schemas.tool_context import ErpNextTenant

logger = logging.getLogger(__name__)


async def resolve_tenant(
    api_key: ApiKey,
    db: AsyncSession,
) -> ErpNextTenant | None:
    mapping = await get_tenant_for_api_key(db, api_key.id)
    if mapping:
        return ErpNextTenant(
            url=mapping.erpnext_url,
            api_key=mapping.erpnext_api_key,
            api_secret=mapping.erpnext_api_secret,
        )
    return None
