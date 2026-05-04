from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hashing import hash_api_key
from app.db.models import ApiKey, TenantMapping


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    return result.scalar_one_or_none()


async def get_tenant_for_api_key(db: AsyncSession, api_key_id: str) -> TenantMapping | None:
    result = await db.execute(
        select(TenantMapping)
        .where(TenantMapping.api_key_id == api_key_id)
        .where(TenantMapping.is_default == True)
    )
    mapping = result.scalar_one_or_none()
    if mapping is None:
        result = await db.execute(
            select(TenantMapping).where(TenantMapping.api_key_id == api_key_id).limit(1)
        )
        mapping = result.scalar_one_or_none()
    return mapping


async def insert_api_key(db: AsyncSession, key: str, name: str) -> ApiKey:
    key_hash = hash_api_key(key)
    api_key = ApiKey(key_hash=key_hash, name=name)
    db.add(api_key)
    return api_key


async def insert_tenant_mapping(
    db: AsyncSession,
    api_key_id: str,
    erpnext_url: str,
    erpnext_api_key: str,
    erpnext_api_secret: str,
    is_default: bool = True,
) -> TenantMapping:
    mapping = TenantMapping(
        api_key_id=api_key_id,
        erpnext_url=erpnext_url,
        erpnext_api_key=erpnext_api_key,
        erpnext_api_secret=erpnext_api_secret,
        is_default=is_default,
    )
    db.add(mapping)
    return mapping
