# PH Agent Framework

A production-ready, Dockerized tool server backend for [Open WebUI](https://docs.openwebui.com/). Exposes a pluggable suite of tools via an OpenAPI-compatible HTTP API. When the LLM triggers a function call, Open WebUI sends it here for execution.

## Architecture

```
Open WebUI (LLM + agent loop)
    │
    │  POST /tools/{tool_name}   (OpenAPI 3.1)
    │  Authorization: Bearer <api-key>
    ▼
┌──────────────────────────────────────┐
│         PH Agent Framework           │
│                                      │
│  FastAPI → Tool Registry → Plugins   │
│                │                     │
│  system ───────┤  ping, info, rng    │
│  erpnext ──────┤  get_doc, search    │
│  utility ──────┤  text_transform, id │
│  (your plugin)─┤  …                  │
│                                      │
│  YAML ───── API keys, tenant routing │
└──────────────────────────────────────┘
    │
    │  httpx (token auth)
    ▼
┌──────────┐   ┌──────────┐
│ ERPNext A│   │ ERPNext B│
└──────────┘   └──────────┘
```

- **Open WebUI** owns the LLM conversation and decides when to call a tool.
- **This backend** is a pure execution server — it receives tool requests, runs the corresponding Python handler, and returns the result.
- **ERPNext permissions** are enforced by ERPNext itself. This backend routes requests to the correct instance based on the API key used.

## Quick start

### 1. Clone and configure

```bash
git clone <repo-url> && cd ph-agent-framework
cp .env.example .env
# edit .env — set PH_AGENT_INITIAL_API_KEYS (format: key1:label1,key2:label2)
```

### 2. Docker (recommended)

Pre-built image from Docker Hub:

```bash
export PH_AGENT_INITIAL_API_KEYS="sk-your-secret:admin"
docker volume create ph-agent-data
docker compose -f docker/docker-compose.yml up -d
```

Or build locally with the included script:

```bash
cd docker
./build.sh          # build only
./build.sh --push   # build and push to Docker Hub
```

Verify:

```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0"}

curl http://localhost:8000/openapi.json | jq '.paths | keys'
# → ["/health","/tools/system_ping","/tools/system_info",…]
```

### 3. Local dev (no Docker)

```bash
pip install -r requirements.txt
INITIAL_API_KEYS="sk-dev:dev" uvicorn app.main:app --reload --port 8000
```

## Register in Open WebUI

1. Go to **Admin Settings → Tools → Add Tool Server**
2. URL: `http://<host>:8000` (use `http://ph-agent-framework:8000` when both containers share the same Docker network)
3. Auth: **Bearer Token** — paste your API key (e.g. `sk-your-secret`)
4. Open WebUI fetches `/openapi.json` and registers every tool

Each tool's `operationId` becomes the function name the LLM sees. The `description` and parameter `Field(description=…)` values are what the LLM reads to decide when and how to call the tool.

## File uploads to ERPNext

When a user attaches a file in chat and asks to upload it to ERPNext, Open WebUI's external tool servers don't receive file data automatically. To bridge this gap, a lightweight importable tool is included.

### 1. Import the bridge tool

1. In Open WebUI, go to **Workspace → Tools → Import Tool**
2. Enter the URL: `http://<host>:8000/bridges/erpnext_upload_bridge.py`
   - If both containers are on the same Docker network, use `http://ph-agent-framework:8000/bridges/erpnext_upload_bridge.py`
3. Click **Import**

### 2. Configure the bridge

After importing, open the tool and set its **Valves**:
- `api_url` — the ph-agent-framework server URL (default: `http://ph-agent-framework:8000`)
- `api_key` — your PH Agent Framework API key (e.g. `sk-your-secret`)

### 3. How it works

1. User attaches a file in chat: "Upload this file to Customer Test Corp"
2. The LLM calls the bridge tool `upload_file_to_erpnext` with `doctype` and `docname`
3. Open WebUI injects `__files__` with the uploaded file's content
4. The bridge reads the file, base64-encodes it, and forwards it to the ph-agent-framework server
5. The server uploads the file to ERPNext via the standard `upload_file` API

The bridge contains no business logic — all ERPNext operations stay in ph-agent-framework.

## Using the tools

Once registered, tools appear in the chat "+" menu. Example interactions:

| User says | LLM calls | Backend does |
|---|---|---|
| "Is the system up?" | `system_ping` | returns `{"pong": true}` |
| "What's the CPU at?" | `system_info` | returns CPU/mem/disk/uptime |
| "Pick a number 1–100" | `random_number` | returns random int |
| "Get invoice SINV-24-00001" | `erpnext_get_doc` | fetches from ERPNext |
| "Search items for 'widget'" | `erpnext_search_docs` | searches ERPNext |
| "Uppercase 'hello'" | `text_transform` | returns `"HELLO"` |
| "Generate an ID" | `generate_id` | returns UUID |

## Authentication

All `/tools/*` endpoints require `X-API-Key: <key>` (or `Authorization: Bearer <key>` sent by Open WebUI).

API keys are SHA-256 hashed and stored in a YAML file (`data/api_keys.yaml`). On first startup, if the file doesn't exist, it's bootstrapped from the `INITIAL_API_KEYS` env var:

```
INITIAL_API_KEYS=key1:label1,key2:label2
```

See `app/plugins/erpnext/api_keys.sample.yaml` for a documented example with ERPNext tenant mappings.

## ERPNext tenant routing

Map an API key to an ERPNext instance by adding a `tenant` block to the key's entry in `data/api_keys.yaml`:

```yaml
api_keys:
  - key: sk-abc123
    name: alice
    tenant:
      url: https://erp.example.com
      api_key: erp-api-key
      api_secret: erp-api-secret
```

The file is loaded into memory at startup. To apply changes, restart the server. When a request arrives with that API key, the ERPNext tool handler resolves the tenant and calls the correct ERPNext instance. ERPNext enforces its own permissions based on the ERPNext API key used.

## Adding a tool plugin

1. Create a package under `app/plugins/` with a `register()` function:

```python
# app/plugins/myplugin/__init__.py
from app.core.registry import ToolRegistry
from . import tools

def register(registry: ToolRegistry):
    registry.register(
        name="my_tool",
        description="What this tool does (the LLM reads this)",
        handler=tools.my_handler,
        request_model=tools.MyRequest,
        response_model=tools.MyResponse,
        tags=["myplugin"],
    )
```

2. Define the tool handler and Pydantic schemas in `tools.py`:

```python
# app/plugins/myplugin/tools.py
from pydantic import BaseModel, Field
from app.schemas.tool_context import ToolContext

class MyRequest(BaseModel):
    param: str = Field(..., description="A parameter description")

class MyResponse(BaseModel):
    result: str = Field(..., description="The result")

async def my_handler(request: MyRequest, context: ToolContext) -> MyResponse:
    return MyResponse(result=f"processed: {request.param}")
```

3. Enable it in `config/plugins.yaml`:

```yaml
plugins:
  myplugin:
    enabled: true
```

4. Restart the server. The tool appears in `/openapi.json` automatically.

## Configuration

| Source | Purpose | Example |
|---|---|---|
| `config/config.yaml` | App settings | host, port, log_level, keys_yaml_path |
| `config/plugins.yaml` | Plugin enable/disable + per-plugin config | `system: {enabled: true}` |
| `.env` / env vars | Secrets | `INITIAL_API_KEYS`, `LOG_LEVEL` |

Environment variables override YAML values. Secrets must never go in YAML files.

## Project structure

```
ph-agent-framework/
├── app/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── config.py            # Settings (YAML + env)
│   ├── api/                 # Route builder, health, dependencies
│   ├── core/                # Registry, security, plugin loader, errors
│   ├── plugins/             # Tool modules (system, erpnext, utility, …)
│   │   └── interface.py     # Plugin contract (register function signature)
│   └── schemas/             # Pydantic schemas (ToolContext, ErrorResponse, …)
├── config/                  # YAML config files (mounted read-only in Docker)
├── data/                    # API keys YAML file (Docker volume mount)
├── tests/                   # pytest suite (14 tests)
├── docker/                  # Dockerfile, compose file, build script
└── requirements.txt
```
