from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.errors import ToolNotFoundError


@dataclass
class ToolEntry:
    name: str
    description: str
    handler: Callable
    request_model: type
    response_model: type
    tags: list[str] = field(default_factory=list)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolEntry] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        request_model: type,
        response_model: type,
        tags: list[str] | None = None,
    ) -> None:
        self._tools[name] = ToolEntry(
            name=name,
            description=description,
            handler=handler,
            request_model=request_model,
            response_model=response_model,
            tags=tags or [],
        )

    def get(self, name: str) -> ToolEntry:
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool '{name}' not found")
        return self._tools[name]

    def get_all(self) -> list[ToolEntry]:
        return list(self._tools.values())

    def get_by_tag(self, tag: str) -> list[ToolEntry]:
        return [t for t in self._tools.values() if tag in t.tags]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
