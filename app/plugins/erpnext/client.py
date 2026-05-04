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

    async def get_doc(self, doctype: str, name: str) -> dict[str, Any]:
        data = await self._request("GET", f"/api/resource/{doctype}/{name}")
        return data.get("data", data)

    async def search_docs(
        self,
        doctype: str,
        filters: list | None = None,
        fields: list[str] | None = None,
        limit_page_length: int = 20,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "limit_page_length": limit_page_length,
        }
        if filters:
            params["filters"] = str(filters)
        if fields:
            params["fields"] = str(fields)
        if order_by:
            params["order_by"] = order_by

        data = await self._request("GET", f"/api/resource/{doctype}", params=params)
        return data.get("data", data)

    async def create_doc(self, doctype: str, data: dict[str, Any]) -> dict[str, Any]:
        result = await self._request("POST", f"/api/resource/{doctype}", json=data)
        return result.get("data", result)

    async def run_method(
        self, method_path: str, args: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        result = await self._request(
            "POST", f"/api/method/{method_path}", json=args or {}
        )
        return result.get("message", result)
