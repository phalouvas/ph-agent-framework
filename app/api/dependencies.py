from fastapi import Depends, Request

from app.core.errors import AuthenticationError
from app.core.security import validate_api_key
from app.plugins.erpnext.router import resolve_tenant
from app.schemas.tool_context import ToolContext


async def get_api_key(request: Request):
    try:
        return await validate_api_key(request)
    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(str(e))


async def get_tool_context(
    request: Request,
    api_key=Depends(get_api_key),
) -> ToolContext:
    tenant = resolve_tenant(api_key)
    return ToolContext(
        api_key_id=api_key["id"],
        api_key_name=api_key["name"],
        tenant=tenant,
    )
