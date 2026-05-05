from app.core.registry import ToolRegistry

from . import tools


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="server_datetime",
        description="Get the current server date and time in UTC. Returns ISO 8601 timestamp, date, time, and day of week.",
        handler=tools.server_datetime_handler,
        request_model=tools.ServerDateTimeRequest,
        response_model=tools.ServerDateTimeResponse,
        tags=["utility"],
    )
