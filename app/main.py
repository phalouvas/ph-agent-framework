import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.health import router as health_router
from app.api.router import build_routes, register_error_handlers
from app.config import Settings, get_settings
from app.core.plugin_loader import load_plugins
from app.core.registry import ToolRegistry
from app.core.security import bootstrap_api_keys
from app.db.engine import close_db, get_db, init_db

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
    get_db_override: async_sessionmaker[AsyncSession] | None = None,
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
        import app.db.engine as db_engine

        if get_db_override is not None:
            db_engine._session_factory = get_db_override

            async def _test_get_db():
                async with get_db_override() as s:
                    yield s

            db_engine.get_db = _test_get_db
        else:
            logger.info("Initializing database...")
            await init_db(settings.database_path)

            async for db in get_db():
                try:
                    if settings.initial_api_keys:
                        await bootstrap_api_keys(db, settings.initial_api_keys)
                finally:
                    await db.close()
                break

        logger.info("Loading plugins...")
        load_plugins(tool_registry, _config_dir / "plugins.yaml")

        logger.info("Building tool routes...")
        build_routes(app, tool_registry)

        logger.info("Startup complete — %d tools registered", len(tool_registry))
        yield
        logger.info("Shutting down...")
        await close_db()

    app = FastAPI(
        title="PH Agent Framework",
        version="0.1.0",
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

    return app


app = create_app()
