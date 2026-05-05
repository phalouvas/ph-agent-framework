import base64
import io
import json
import logging
from typing import Any

import httpx

from app.core.errors import ErpNextConnectionError

logger = logging.getLogger(__name__)


class ErpNextClient:
    def __init__(self, url: str, api_key: str, api_secret: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.auth_header = f"token {api_key}:{api_secret}"
        self.timeout = timeout

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": self.auth_header,
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{self.url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method, url, headers=self._headers, **kwargs
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            raise ErpNextConnectionError(f"Timeout connecting to ERPNext at {self.url}")
        except httpx.ConnectError:
            raise ErpNextConnectionError(
                f"Could not connect to ERPNext at {self.url}"
            )
        except httpx.HTTPStatusError as e:
            detail = e.response.text[:500] if e.response else str(e)
            raise ErpNextConnectionError(
                f"ERPNext returned {e.response.status_code}: {detail}"
            )

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

    async def get_doctype_meta(self, doctype: str) -> dict[str, Any]:
        data = await self._request("GET", f"/api/resource/DocType/{doctype}")
        return data.get("data", data)

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
        params: dict[str, Any] = {"limit_page_length": limit, "fields": json.dumps(["name", "module", "issingle", "istable"])}
        if filters:
            params["filters"] = json.dumps(filters)
        data = await self._request("GET", "/api/resource/DocType", params=params)
        return data.get("data", data)

    async def upload_file(
        self,
        file_name: str,
        content_base64: str,
        doctype: str | None = None,
        docname: str | None = None,
        is_private: bool = True,
        folder: str | None = None,
    ) -> dict[str, Any]:
        file_content = base64.b64decode(content_base64)
        files = {"file": (file_name, io.BytesIO(file_content), "application/octet-stream")}
        data_fields: dict[str, Any] = {"is_private": int(is_private)}
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
