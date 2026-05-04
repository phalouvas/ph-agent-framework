from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from hashlib import sha256
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.tool_context import ToolContext


class TextTransformRequest(BaseModel):
    text: str = Field(..., description="The input text to transform")
    operation: str = Field(
        "uppercase",
        description="Transformation to apply: 'uppercase', 'lowercase', 'title', 'reverse', or 'trim'",
    )


class TextTransformResponse(BaseModel):
    result: str = Field(..., description="The transformed text")


async def text_transform_handler(
    request: TextTransformRequest, context: ToolContext
) -> TextTransformResponse:
    ops = {
        "uppercase": str.upper,
        "lowercase": str.lower,
        "title": str.title,
        "reverse": lambda s: s[::-1],
        "trim": str.strip,
    }
    transform = ops.get(request.operation, str.upper)
    return TextTransformResponse(result=transform(request.text))


class GenerateIdRequest(BaseModel):
    kind: str = Field(
        "uuid",
        description="Type of ID to generate: 'uuid' (UUID v4), 'timestamp' (sortable with timestamp), or 'short' (8-char hex)",
    )


class GenerateIdResponse(BaseModel):
    id: str = Field(..., description="The generated unique identifier")
    kind: str = Field(..., description="The type of ID that was generated")


async def generate_id_handler(
    request: GenerateIdRequest, context: ToolContext
) -> GenerateIdResponse:
    now = datetime.now(timezone.utc)
    if request.kind == "timestamp":
        ts = now.strftime("%Y%m%d%H%M%S%f")
        return GenerateIdResponse(id=ts, kind=request.kind)
    elif request.kind == "short":
        return GenerateIdResponse(id=uuid4().hex[:8], kind=request.kind)
    else:
        return GenerateIdResponse(id=str(uuid4()), kind=request.kind)


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
