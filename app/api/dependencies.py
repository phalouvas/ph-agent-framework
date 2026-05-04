from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError
from app.core.security import validate_api_key
from app.db.engine import get_db
from app.plugins.erpnext.router import resolve_tenant
from app.schemas.tool_context import ToolContext


async def get_api_key(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        return await validate_api_key(request, db)
    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(str(e))


async def get_tool_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
    api_key=Depends(get_api_key),
) -> ToolContext:
    tenant = await resolve_tenant(api_key, db)
    return ToolContext(
        api_key_id=api_key.id,
        api_key_name=api_key.name,
        tenant=tenant,
    )
