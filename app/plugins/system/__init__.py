from app.core.registry import ToolRegistry

from . import tools


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="system_ping",
        description="Check if the system is responsive. Returns a simple pong response with a timestamp.",
        handler=tools.ping_handler,
        request_model=tools.PingRequest,
        response_model=tools.PingResponse,
        tags=["system"],
    )
