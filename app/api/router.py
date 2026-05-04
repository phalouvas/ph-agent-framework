import logging
from typing import Any

from fastapi import Body, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.dependencies import get_tool_context
from app.core.errors import (
    AuthenticationError,
    ErpNextConnectionError,
    ToolExecutionError,
    ToolNotFoundError,
)
from app.core.registry import ToolRegistry

logger = logging.getLogger(__name__)


def _make_handler(tool_entry, tool_registry: ToolRegistry):
    """Closure that creates a FastAPI endpoint handler for a registered tool."""

    async def handler(
        request: Request,
        body: Any = Body(...),
        ctx=Depends(get_tool_context),
    ):
        request_model = tool_entry.request_model

        try:
            parsed = request_model.model_validate(body)
        except ValidationError as e:
            raise
        except Exception as e:
            raise ToolExecutionError(f"Invalid request: {e}")

        try:
            result = await tool_entry.handler(parsed, ctx)
            return result
        except Exception as e:
            logger.exception("Tool '%s' execution failed", tool_entry.name)
            raise ToolExecutionError(str(e))

    handler.__name__ = tool_entry.name
    return handler


def build_routes(app: FastAPI, registry: ToolRegistry) -> None:
    for entry in registry.get_all():
        handler = _make_handler(entry, registry)

        summary = " ".join(word.capitalize() for word in entry.name.split("_"))

        app.add_api_route(
            path=f"/tools/{entry.name}",
            endpoint=handler,
            methods=["POST"],
            operation_id=entry.name,
            summary=summary,
            description=entry.description,
            tags=entry.tags,
            response_model=entry.response_model,
        )

    logger.info("Registered %d tool routes", len(registry))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ToolNotFoundError)
    async def tool_not_found(request: Request, exc: ToolNotFoundError):
        return JSONResponse(status_code=404, content={"code": 404, "message": str(exc)})

    @app.exception_handler(AuthenticationError)
    async def auth_error(request: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content={"code": 401, "message": str(exc)})

    @app.exception_handler(ErpNextConnectionError)
    async def erpnext_conn_error(request: Request, exc: ErpNextConnectionError):
        return JSONResponse(status_code=502, content={"code": 502, "message": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_error(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={"code": 422, "message": str(exc.errors(include_url=False))},
        )

    @app.exception_handler(ToolExecutionError)
    async def tool_exec_error(request: Request, exc: ToolExecutionError):
        return JSONResponse(status_code=500, content={"code": 500, "message": str(exc)})
