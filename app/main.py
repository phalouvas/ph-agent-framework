import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.health import router as health_router
from app.api.router import build_routes, register_error_handlers
from app.config import Settings, get_settings
from app.core.keys_config import bootstrap_keys_yaml, load_keys_config
from app.core.plugin_loader import load_plugins
from app.core.registry import ToolRegistry

logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        logger.info(
            "%s %s %s %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def _get_config_dir() -> Path:
    return Path(__file__).parent.parent / "config"


def create_app(
    settings: Settings | None = None,
    config_dir: Path | None = None,
) -> FastAPI:
    if settings is None:
        settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    tool_registry = ToolRegistry()
    _config_dir = config_dir or _get_config_dir()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Loading API keys configuration...")
        load_keys_config(settings.keys_yaml_path)
        if settings.initial_api_keys:
            bootstrap_keys_yaml(settings.keys_yaml_path, settings.initial_api_keys)

        logger.info("Loading plugins...")
        load_plugins(tool_registry, _config_dir / "plugins.yaml")

        logger.info("Building tool routes...")
        build_routes(app, tool_registry)

        logger.info("Startup complete — %d tools registered", len(tool_registry))
        yield
        logger.info("Shutting down...")

    app = FastAPI(
        title="PH Agent Framework",
        version="1.0.0",
        description="Tool server backend for Open WebUI. Provides pluggable tool modules including ERPNext integration with multi-tenant routing.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health_router)
    register_error_handlers(app)

    bridges_dir = Path(__file__).parent.parent / "bridges"
    if bridges_dir.is_dir():
        app.mount("/bridges", StaticFiles(directory=str(bridges_dir)), name="bridges")

    return app


app = create_app()
