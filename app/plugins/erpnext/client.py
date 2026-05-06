import asyncio
import base64
import io
import json
import logging
import time
from typing import Any

import httpx

from app.core.errors import ErpNextConnectionError

logger = logging.getLogger(__name__)


class ErpNextClient:
    """Async HTTP client for the ERPNext/Frappe REST API.

    Uses a class-level connection pool for HTTP keep-alive, DNS caching,
    and TLS session reuse across all client instances and requests.
    """

    _pool: httpx.AsyncClient | None = None
    _pool_lock: asyncio.Lock | None = None
    _meta_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _meta_cache_ttl: float = 300.0
    _rate_limiter: asyncio.Semaphore | None = None
    _max_concurrent: int = 5

    def __init__(self, url: str, api_key: str, api_secret: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.auth_header = f"token {api_key}:{api_secret}"
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

    # ── Pool management ──────────────────────────────────────────────

    @classmethod
    def _get_pool(cls) -> httpx.AsyncClient:
        if cls._pool is None:
            cls._pool = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return cls._pool

    @classmethod
    async def close_pool(cls) -> None:
        if cls._pool is not None:
            await cls._pool.aclose()
            cls._pool = None

    # ── Rate limiting ────────────────────────────────────────────────

    @classmethod
    def _get_rate_limiter(cls) -> asyncio.Semaphore:
        if cls._rate_limiter is None:
            cls._rate_limiter = asyncio.Semaphore(cls._max_concurrent)
        return cls._rate_limiter

    # ── Metadata cache ───────────────────────────────────────────────

    @classmethod
    def invalidate_meta_cache(cls, doctype: str | None = None) -> None:
        if doctype:
            stale = [k for k in cls._meta_cache if k.endswith(f"::{doctype}")]
            for key in stale:
                cls._meta_cache.pop(key, None)
        else:
            cls._meta_cache.clear()

    @classmethod
    def invalidate_meta_cache_for_tenant(cls, base_url: str, doctype: str | None = None) -> None:
        prefix = base_url.rstrip("/") + "::"
        if doctype:
            cls._meta_cache.pop(f"{prefix}{doctype}", None)
            return
        stale = [k for k in cls._meta_cache if k.startswith(prefix)]
        for key in stale:
            cls._meta_cache.pop(key, None)

    # ── Error parsing ────────────────────────────────────────────────

    @staticmethod
    def _extract_server_messages(raw_messages: str) -> list[str]:
        try:
            messages = json.loads(raw_messages)
        except (ValueError, json.JSONDecodeError):
            return []

        cleaned: list[str] = []
        for item in messages:
            if isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    cleaned.append(str(parsed.get("message") or parsed))
                except (ValueError, json.JSONDecodeError):
                    cleaned.append(item)
            elif isinstance(item, dict):
                cleaned.append(str(item.get("message") or item))
        return cleaned

    @classmethod
    def _parse_error_details(cls, response: httpx.Response | None) -> dict[str, Any]:
        """Extract normalized error details from ERPNext responses."""
        if response is None:
            return {
                "status_code": None,
                "category": "unknown",
                "exc_type": None,
                "message": "Unknown ERPNext error",
                "details": {},
            }

        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError):
            return {
                "status_code": response.status_code,
                "category": "http",
                "exc_type": None,
                "message": f"ERPNext returned {response.status_code}: {response.text[:300]}",
                "details": {},
            }

        exc_type = body.get("exc_type", "")
        exception_text = body.get("exception", "")
        category = "validation" if "validation" in str(exc_type).lower() else "server"

        if exc_type and exception_text:
            lines = exception_text.split("\n")
            clean_lines = [
                l for l in lines
                if l.strip() and not l.startswith("Traceback") and not l.startswith("  File")
            ]
            message = clean_lines[-1] if clean_lines else exception_text
            details: dict[str, Any] = {}
            if "_server_messages" in body:
                details["server_messages"] = cls._extract_server_messages(str(body["_server_messages"]))
            return {
                "status_code": response.status_code,
                "category": category,
                "exc_type": exc_type,
                "message": f"ERPNext {exc_type}: {message[:300]}",
                "details": details,
            }

        if "message" in body:
            return {
                "status_code": response.status_code,
                "category": category,
                "exc_type": exc_type or None,
                "message": f"ERPNext error: {str(body['message'])[:300]}",
                "details": {},
            }

        if "_server_messages" in body:
            cleaned = cls._extract_server_messages(str(body["_server_messages"]))
            return {
                "status_code": response.status_code,
                "category": "validation",
                "exc_type": exc_type or None,
                "message": "ERPNext validation: " + "; ".join(cleaned)[:300],
                "details": {"server_messages": cleaned},
            }

        return {
            "status_code": response.status_code,
            "category": category,
            "exc_type": exc_type or None,
            "message": f"ERPNext returned {response.status_code}: {response.text[:300]}",
            "details": {},
        }

    @classmethod
    def _parse_error_response(cls, response: httpx.Response | None) -> str:
        details = cls._parse_error_details(response)
        return str(details["message"])

    # ── HTTP properties ──────────────────────────────────────────────

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": self.auth_header,
            "Accept": "application/json",
        }

    # ── Core request ─────────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self.url}{path}"
        limiter = self._get_rate_limiter()
        async with limiter:
            try:
                client = self._get_pool()
                response = await client.request(
                    method, url, headers=self._headers, **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                raise ErpNextConnectionError(
                    f"ERPNext at {self.url} did not respond within {self.timeout}s. "
                    "The server may be overloaded or the network is slow. Try again later."
                )
            except httpx.ConnectError:
                raise ErpNextConnectionError(
                    f"Cannot reach ERPNext at {self.url}. "
                    "Verify the ERPNext server is running and the URL is correct in the tenant configuration."
                )
            except httpx.HTTPStatusError as e:
                detail = self._parse_error_response(e.response)
                raise ErpNextConnectionError(detail)

    # ── Document CRUD ────────────────────────────────────────────────

    async def get_doc(
        self,
        doctype: str,
        name: str,
        fields: list[str] | None = None,
        expand_links: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if fields:
            params["fields"] = json.dumps(fields)
        if expand_links:
            params["expand_links"] = "true"
        data = await self._request(
            "GET", f"/api/resource/{doctype}/{name}", params=params or None
        )
        return data.get("data", data)

    async def search_docs(
        self,
        doctype: str,
        filters: list | None = None,
        or_filters: list | None = None,
        fields: list[str] | None = None,
        limit_page_length: int = 20,
        limit_start: int = 0,
        order_by: str | None = None,
        expand: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "limit_page_length": limit_page_length,
        }
        if limit_start:
            params["limit_start"] = limit_start
        if filters:
            params["filters"] = json.dumps(filters)
        if or_filters:
            params["or_filters"] = json.dumps(or_filters)
        if fields:
            params["fields"] = json.dumps(fields)
        if order_by:
            params["order_by"] = order_by
        if expand:
            params["expand"] = json.dumps(expand)

        data = await self._request("GET", f"/api/resource/{doctype}", params=params)
        return data.get("data", data)

    async def create_doc(self, doctype: str, data: dict[str, Any]) -> dict[str, Any]:
        result = await self._request("POST", f"/api/resource/{doctype}", json=data)
        return result.get("data", result)

    async def update_doc(
        self, doctype: str, name: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        result = await self._request(
            "PUT", f"/api/resource/{doctype}/{name}", json=data
        )
        return result.get("data", result)

    async def delete_doc(self, doctype: str, name: str) -> dict[str, Any]:
        result = await self._request("DELETE", f"/api/resource/{doctype}/{name}")
        return result

    # ── Count documents ──────────────────────────────────────────────

    async def count_docs(
        self,
        doctype: str,
        filters: list | None = None,
        or_filters: list | None = None,
    ) -> int:
        """Return the total number of documents matching the given filters.

        Uses frappe.desk.reportview.get_count, the standard whitelisted
        Frappe method for counting documents server-side.
        """
        all_filters = list(filters) if filters else []
        args: dict[str, Any] = {"doctype": doctype}
        if all_filters:
            args["filters"] = json.dumps(all_filters)

        count_result = await self.run_method(
            "frappe.desk.reportview.get_count", args=args
        )
        if isinstance(count_result, int):
            return count_result
        if isinstance(count_result, dict):
            return count_result.get("message", count_result.get("value", 0))
        return int(count_result) if count_result is not None else 0

    # ── Document lifecycle ────────────────────────────────────────────

    async def submit_doc(self, doctype: str, name: str) -> dict[str, Any]:
        result = await self.run_method(
            "frappe.client.submit",
            args={"doctype": doctype, "name": name},
        )
        return result if isinstance(result, dict) else {}

    async def cancel_doc(self, doctype: str, name: str) -> dict[str, Any]:
        result = await self.run_method(
            "frappe.client.cancel",
            args={"doctype": doctype, "name": name},
        )
        return result if isinstance(result, dict) else {}

    async def amend_doc(
        self, doctype: str, name: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        # Get the cancelled doc to use as base for amendment
        doc = await self.get_doc(doctype, name)
        doc.pop("name", None)
        doc.pop("owner", None)
        doc.pop("creation", None)
        doc.pop("modified", None)
        doc.pop("modified_by", None)
        doc["amended_from"] = name
        doc["docstatus"] = 0
        if data:
            doc.update(data)
        return await self.create_doc(doctype, doc)

    # ── Doctype metadata ─────────────────────────────────────────────

    async def get_doctype_meta(self, doctype: str, force_refresh: bool = False) -> dict[str, Any]:
        cache_key = f"{self.url}::{doctype}"
        now = time.time()
        cached = self._meta_cache.get(cache_key)
        if (not force_refresh) and cached and (now - cached[0]) < self._meta_cache_ttl:
            return cached[1]

        data = await self._request("GET", f"/api/resource/DocType/{doctype}")
        result = data.get("data", data)
        self._meta_cache[cache_key] = (now, result)
        return result

    async def list_doctypes(
        self,
        query: str | None = None,
        module: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        filters = []
        if query:
            filters.append(["name", "like", f"%{query}%"])
        if module:
            filters.append(["module", "=", module])
        params: dict[str, Any] = {
            "limit_page_length": limit,
            "fields": json.dumps(["name", "module", "issingle", "istable"]),
        }
        if filters:
            params["filters"] = json.dumps(filters)
        data = await self._request("GET", "/api/resource/DocType", params=params)
        return data.get("data", data)

    # ── File operations ──────────────────────────────────────────────

    async def upload_file(
        self,
        file_name: str,
        content_base64: str | None = None,
        content: str | None = None,
        doctype: str | None = None,
        docname: str | None = None,
        is_private: bool = True,
        folder: str | None = None,
    ) -> dict[str, Any]:
        if content_base64:
            file_bytes = base64.b64decode(content_base64)
        elif content:
            file_bytes = content.encode("utf-8")
        else:
            raise ValueError("Either content_base64 or content must be provided")
        files = {"file": (file_name, io.BytesIO(file_bytes), "application/octet-stream")}
        data_fields: dict[str, Any] = {
            "is_private": int(is_private),
        }
        if doctype:
            data_fields["doctype"] = doctype
        if docname:
            data_fields["docname"] = docname
        if folder:
            data_fields["folder"] = folder
        result = await self._request(
            "POST", "/api/method/upload_file", files=files, data=data_fields
        )
        return result.get("message", result)

    async def get_file(self, file_url: str) -> dict[str, Any]:
        """Get file metadata from ERPNext by file URL."""
        filters = [["file_url", "=", file_url]]
        params: dict[str, Any] = {
            "filters": json.dumps(filters),
            "fields": json.dumps([
                "name", "file_name", "file_url", "file_size",
                "content_hash", "attached_to_doctype", "attached_to_name",
                "is_private",
            ]),
            "limit_page_length": 1,
        }
        result = await self._request("GET", "/api/resource/File", params=params)
        data = result.get("data", result)
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}

    async def list_files(
        self,
        doctype: str | None = None,
        docname: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List files, optionally filtered by attached doctype/document."""
        filters: list = []
        if doctype:
            filters.append(["attached_to_doctype", "=", doctype])
        if docname:
            filters.append(["attached_to_name", "=", docname])
        params: dict[str, Any] = {
            "limit_page_length": limit,
            "fields": json.dumps([
                "name", "file_name", "file_url", "file_size",
                "content_hash", "is_private",
            ]),
        }
        if filters:
            params["filters"] = json.dumps(filters)
        result = await self._request("GET", "/api/resource/File", params=params)
        return result.get("data", result)

    # ── User / System ────────────────────────────────────────────────

    async def get_current_user(self) -> dict[str, Any]:
        result = await self._request(
            "GET", "/api/method/frappe.auth.get_logged_user"
        )
        return result.get("message", result)

    async def get_system_info(self) -> dict[str, Any]:
        result = await self._request(
            "POST", "/api/method/frappe.utils.change_log.get_versions"
        )
        return result.get("message", result)

    async def ping(self) -> dict[str, Any]:
        """Quick health check — returns latency and availability."""
        start = time.monotonic()
        try:
            result = await self._request("GET", "/api/method/frappe.ping")
            elapsed = time.monotonic() - start
            return {
                "available": True,
                "latency_ms": round(elapsed * 1000, 1),
                "message": result.get("message", "pong") if isinstance(result, dict) else str(result),
            }
        except ErpNextConnectionError:
            elapsed = time.monotonic() - start
            return {
                "available": False,
                "latency_ms": round(elapsed * 1000, 1),
            }

    # ── Reports ──────────────────────────────────────────────────────

    async def run_report(
        self,
        report_name: str,
        filters: dict[str, Any] | None = None,
        file_format: str = "HTML",
    ) -> dict[str, Any]:
        result = await self._request(
            "POST",
            "/api/method/frappe.desk.query_report.run",
            json={
                "report_name": report_name,
                "filters": filters or {},
                "file_format": file_format,
            },
        )
        return result.get("message", result)

    async def list_reports(
        self,
        query: str | None = None,
        report_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        filters = [["is_standard", "=", "Yes"]]
        if query:
            filters.append(["name", "like", f"%{query}%"])
        if report_type:
            filters.append(["report_type", "=", report_type])
        params: dict[str, Any] = {
            "limit_page_length": limit,
            "fields": json.dumps(["name", "report_type", "module", "ref_doctype"]),
            "filters": json.dumps(filters),
        }
        data = await self._request("GET", "/api/resource/Report", params=params)
        return data.get("data", data)

    # ── Generic method call ──────────────────────────────────────────

    async def run_method(
        self,
        method_path: str,
        args: dict[str, Any] | None = None,
        http_method: str = "POST",
    ) -> dict[str, Any]:
        if http_method.upper() == "GET":
            result = await self._request("GET", f"/api/method/{method_path}")
        else:
            result = await self._request(
                "POST", f"/api/method/{method_path}", json=args or {}
            )
        return result.get("message", result)
