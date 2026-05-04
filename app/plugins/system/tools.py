import random
from datetime import datetime, timezone

import psutil
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


class SystemInfoRequest(BaseModel):
    """No parameters needed for system info."""

    pass


class SystemInfoResponse(BaseModel):
    cpu_percent: float = Field(..., description="Current CPU utilization percentage")
    memory_percent: float = Field(..., description="Current memory utilization percentage")
    disk_percent: float = Field(..., description="Root disk utilization percentage")
    uptime_seconds: float = Field(..., description="System uptime in seconds")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the reading")


async def system_info_handler(request: SystemInfoRequest, context: ToolContext) -> SystemInfoResponse:
    return SystemInfoResponse(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage("/").percent,
        uptime_seconds=psutil.boot_time(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


class RandomNumberRequest(BaseModel):
    min: int = Field(0, description="Minimum value (inclusive)")
    max: int = Field(100, description="Maximum value (inclusive)")


class RandomNumberResponse(BaseModel):
    value: int = Field(..., description="The generated random number")


async def random_number_handler(
    request: RandomNumberRequest, context: ToolContext
) -> RandomNumberResponse:
    return RandomNumberResponse(value=random.randint(request.min, request.max))
