# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (including dev deps for tests)
pip install -e ".[dev]"

# Run the server (dev mode)
uvicorn app.main:app --reload --port 8000

# Docker
INITIAL_API_KEYS="sk-your-secret:admin" docker compose -f docker/docker-compose.yml up -d

# Run all tests
pytest

# Run a single test file
pytest tests/test_health.py

# Run a specific test
pytest tests/test_health.py::test_openapi_schema

# Run with verbose output
pytest -v
```

## Architecture

This is a FastAPI tool server backend for [Open WebUI](https://docs.openwebui.com/). Open WebUI owns the LLM conversation and calls this server at `POST /tools/{tool_name}` when the LLM triggers a function call. Tools are auto-registered as FastAPI routes from the `ToolRegistry`; their `operationId`, `description`, and Pydantic model `Field(description=...)` values become the function schema Open WebUI reads from `/openapi.json`.

### Request flow

1. `POST /tools/{tool_name}` arrives with `X-API-Key` header
2. `get_tool_context` dependency validates the API key (SHA-256 hash lookup in SQLite), resolves an ERPNext tenant if one is mapped to that key, and builds a `ToolContext`
3. `_make_handler` closure parses the body into the tool's `request_model`, calls the async handler with `(parsed_request, context)`, and returns the `response_model`
4. Error handlers map `ToolNotFoundError` → 404, `AuthenticationError` → 401, `ErpNextConnectionError` → 502, `ToolExecutionError` → 500

### Key layers

- **`app/main.py`** — App factory (`create_app`) with lifespan that init's DB, bootstraps API keys, loads plugins, and builds routes. Module-level `app = create_app()` serves as the uvicorn entry point.
- **`app/config.py`** — `Settings` is a `pydantic_settings.BaseSettings`. YAML values from `config/config.yaml` are loaded first, then env vars override them.
- **`app/core/registry.py`** — `ToolRegistry` is a dict of `ToolEntry` dataclasses (name, description, handler, request_model, response_model, tags). Tools are looked up by name at request time.
- **`app/core/plugin_loader.py`** — Reads `config/plugins.yaml`, imports `app.plugins.{name}` for each enabled plugin, calls its `register(registry)` function.
- **`app/api/router.py`** — `build_routes()` iterates the registry and calls `app.add_api_route()` for each tool, wiring up the handler closure with the `get_tool_context` dependency.
- **`app/api/dependencies.py`** — `get_tool_context` is the FastAPI dependency chain: `get_db` → `get_api_key` (validates `X-API-Key`) → `resolve_tenant` (looks up `tenant_mappings`). Every tool handler receives the resulting `ToolContext`.
- **`app/db/`** — Async SQLAlchemy with aiosqlite. Two tables: `api_keys` (SHA-256 hashed) and `tenant_mappings` (maps an API key to an ERPNext URL + credentials). `init_db()` is called once at startup and creates tables via `Base.metadata.create_all`.
- **`app/plugins/interface.py`** — The plugin contract: `PluginRegisterFn = Callable[[ToolRegistry], None]`. Every plugin package must expose a `register` function matching this signature.

### Plugins

Each plugin lives under `app/plugins/{name}/` and contains:
- `__init__.py` — exposes `register(registry: ToolRegistry)` that calls `registry.register(...)` for each tool
- `tools.py` — Pydantic request/response models and async handler functions

**system** — `system_ping`, `system_info` (psutil), `random_number`
**erpnext** — `erpnext_get_doc`, `erpnext_search_docs`. Uses `ErpNextClient` (httpx, token auth) resolved per-tenant via `tenant_mappings`. The ERPNext router at `app/plugins/erpnext/router.py` is called from the dependencies layer, not from handlers directly.
**utility** — `text_transform`, `generate_id`

### Adding a new tool

1. Create `app/plugins/{name}/__init__.py` with a `register(registry)` function
2. Create `app/plugins/{name}/tools.py` with Pydantic models and async handler
3. Add `{name}: {enabled: true}` to `config/plugins.yaml`
4. Restart — routes appear in `/openapi.json` automatically

### Configuration

| Source | Purpose |
|---|---|
| `config/config.yaml` | App settings (host, port, log_level, database_path) |
| `config/plugins.yaml` | Plugin enable/disable + per-plugin config |
| `.env` / env vars | Secrets (`INITIAL_API_KEYS`, `LOG_LEVEL`) |

Environment variables override YAML values. Secrets must never go in YAML files.

## Testing

pytest with `asyncio_mode = "auto"` (configured in pyproject.toml). Tests use an in-memory SQLite database and `fastapi.testclient.TestClient`.

`conftest.py` provides three key fixtures:
- `test_db` — session-scoped, creates an in-memory SQLite with tables, inserts a test API key (`sk-test-secret`) and tenant mapping
- `test_app` — calls `create_app()` with overridden DB and a temp `plugins.yaml` (enables system + erpnext, disables utility)
- `client` — `TestClient` wrapping `test_app`
- `auth_headers` — `{"X-API-Key": "sk-test-secret"}`

When adding tests for a new plugin, update the `plugins_config` dict in `conftest.py`'s `test_app` fixture to enable it.

## ERPNext schema maintenance

Write-path rule of truth:

- Curated fieldsets in `app/plugins/erpnext/fieldsets.py` are advisory.
- Live doctype metadata from ERPNext is authoritative for create/update validation.

Manual refresh workflow:

```bash
erpnext-refresh-fieldsets
# or python scripts/refresh_erpnext_fieldsets.py
```

Expected artifacts:

- `scripts/artifacts/upstream_doctype_snapshots.json`
- `scripts/artifacts/fieldset_refresh_report.json`

Safe rollout sequence for schema updates:

1. Run refresh workflow and review report deltas.
2. Update curated fieldsets in focused module batches (Accounts/Buying, then Stock, then HR/CRM, then Manufacturing).
3. Add or update tests for validation and write error semantics.
4. Verify with `pytest` before merge.
