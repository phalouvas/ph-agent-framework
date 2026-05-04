from app.core.registry import ToolRegistry

from . import tools


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="text_transform",
        description="Transform text using various operations: uppercase, lowercase, title case, reverse, or trim whitespace.",
        handler=tools.text_transform_handler,
        request_model=tools.TextTransformRequest,
        response_model=tools.TextTransformResponse,
        tags=["utility"],
    )
    registry.register(
        name="generate_id",
        description="Generate a unique identifier. Supports UUID v4, sortable timestamp-based IDs, and short 8-character hex IDs.",
        handler=tools.generate_id_handler,
        request_model=tools.GenerateIdRequest,
        response_model=tools.GenerateIdResponse,
        tags=["utility"],
    )
    registry.register(
        name="server_datetime",
        description="Get the current server date and time in UTC. Returns ISO 8601 timestamp, date, time, and day of week.",
        handler=tools.server_datetime_handler,
        request_model=tools.ServerDateTimeRequest,
        response_model=tools.ServerDateTimeResponse,
        tags=["utility"],
    )
