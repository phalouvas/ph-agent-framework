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
    registry.register(
        name="system_info",
        description="Get current system information including CPU usage percentage, memory usage percentage, disk usage, and uptime.",
        handler=tools.system_info_handler,
        request_model=tools.SystemInfoRequest,
        response_model=tools.SystemInfoResponse,
        tags=["system"],
    )
    registry.register(
        name="random_number",
        description="Generate a random integer between a specified minimum and maximum value (inclusive).",
        handler=tools.random_number_handler,
        request_model=tools.RandomNumberRequest,
        response_model=tools.RandomNumberResponse,
        tags=["system"],
    )
