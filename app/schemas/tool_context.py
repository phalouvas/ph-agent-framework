from dataclasses import dataclass, field


@dataclass
class ErpNextTenant:
    url: str
    api_key: str
    api_secret: str


@dataclass
class ToolContext:
    api_key_id: str
    api_key_name: str
    tenant: ErpNextTenant | None = None
    extra: dict = field(default_factory=dict)
