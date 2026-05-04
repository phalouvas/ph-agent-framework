class ToolNotFoundError(Exception):
    """Raised when a requested tool name is not in the registry."""


class AuthenticationError(Exception):
    """Raised when API key validation fails."""


class ErpNextConnectionError(Exception):
    """Raised when the ERPNext instance is unreachable."""


class ToolExecutionError(Exception):
    """Raised when a tool handler fails during execution."""
