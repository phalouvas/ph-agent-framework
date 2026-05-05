from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas.tool_context import ToolContext


class PingRequest(BaseModel):
    """No parameters needed for ping."""

    pass


class PingResponse(BaseModel):
    pong: bool = Field(..., description="Always true if the system is healthy")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the response")


async def ping_handler(request: PingRequest, context: ToolContext) -> PingResponse:
    return PingResponse(pong=True, timestamp=datetime.now(timezone.utc).isoformat())
