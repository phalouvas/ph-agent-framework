import logging

from app.core.keys_config import lookup_tenant
from app.schemas.tool_context import ErpNextTenant

logger = logging.getLogger(__name__)


def resolve_tenant(api_key: dict) -> ErpNextTenant | None:
    return lookup_tenant(api_key["id"])
