from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from app.schemas.tool_context import ToolContext


class ServerDateTimeRequest(BaseModel):
    timezone: str = Field(
        "UTC",
        description="IANA timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo'). Defaults to UTC.",
    )


class ServerDateTimeResponse(BaseModel):
    datetime: str = Field(..., description="Full ISO 8601 timestamp with timezone")
    timezone: str = Field(..., description="Timezone used for the response")
    date: str = Field(..., description="Current date in YYYY-MM-DD format")
    time: str = Field(..., description="Current time in HH:MM:SS format")
    day_of_week: str = Field(..., description="Day of the week (e.g., Monday)")


async def server_datetime_handler(
    request: ServerDateTimeRequest, context: ToolContext
) -> ServerDateTimeResponse:
    try:
        tz = ZoneInfo(request.timezone)
        tz_name = request.timezone
    except Exception:
        tz = timezone.utc
        tz_name = "UTC"
    now = datetime.now(tz)
    return ServerDateTimeResponse(
        datetime=now.isoformat(),
        timezone=tz_name,
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M:%S"),
        day_of_week=now.strftime("%A"),
    )
