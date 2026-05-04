from collections.abc import Callable

from app.core.registry import ToolRegistry

PluginRegisterFn = Callable[[ToolRegistry], None]
