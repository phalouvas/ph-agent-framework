"""
title: ERPNext File Upload Bridge
author: PH Agent Framework
description: Bridges Open WebUI file uploads to the ph-agent-framework ERPNext tool server. Receives __files__ from chat attachments, reads the content, and forwards it to the erpnext_upload_file endpoint.
version: 1.0.0
licence: MIT
required_open_webui_version: 0.6.0
"""

import base64
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        api_url: str = Field(
            "http://ph-agent-framework:8000",
            description="Base URL of the ph-agent-framework server",
        )
        api_key: str = Field(
            "",
            description="API key for the ph-agent-framework server (e.g. sk-your-secret)",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def upload_file_to_erpnext(
        self,
        doctype: str,
        docname: str,
        file_name: str = "",
        is_private: bool = True,
        folder: str = "",
        __files__: list[Any] = [],
        __event_emitter__: Any = None,
    ) -> str:
        """Upload an attached file to ERPNext via the ph-agent-framework server.

        :param doctype: ERPNext doctype to attach the file to, e.g. 'Customer', 'Sales Invoice'
        :param docname: Document name to attach the file to, e.g. 'Test Corp'
        :param file_name: Optional override for the file name; uses the attached file's name if empty
        :param is_private: If true, only users with permission can access the file
        :param folder: Optional target folder in ERPNext, e.g. 'Home/Attachments'
        """

        if not __files__:
            return (
                "Error: No files attached to the message. "
                "Attach a file in the chat before asking me to upload it."
            )

        if not self.valves.api_key:
            return (
                "Error: API key not configured. Open this tool's Valves in Open WebUI "
                "and set 'api_key' to a valid ph-agent-framework API key."
            )

        headers = {
            "X-API-Key": self.valves.api_key,
            "Content-Type": "application/json",
        }
        url = f"{self.valves.api_url.rstrip('/')}/tools/erpnext_upload_file"

        results: list[str] = []

        for i, f in enumerate(__files__):
            if isinstance(f, str):
                results.append(f"Warning: Unexpected string in __files__[{i}]: {f[:200]}")
                continue
            if not isinstance(f, dict):
                results.append(f"Warning: Unexpected type in __files__[{i}]: {type(f).__name__}")
                continue

            name = file_name or f.get("name", "uploaded_file")

            file_bytes = self._read_file_bytes(f, name)

            if file_bytes is None:
                # Debug: show available keys so we can fix the structure
                top_keys = list(f.keys())
                file_val = f.get("file")
                if isinstance(file_val, dict):
                    file_keys = list(file_val.keys())
                    results.append(
                        f"Warning: Could not read content of '{name}'. "
                        f"__files__[{i}] keys: {top_keys}, file keys: {file_keys}"
                    )
                else:
                    results.append(
                        f"Warning: Could not read content of '{name}'. "
                        f"__files__[{i}] keys: {top_keys}, file type: {type(file_val).__name__}"
                    )
                continue

            content_base64 = base64.b64encode(file_bytes).decode("utf-8")

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {
                        "description": f"Uploading '{name}' ({len(file_bytes)} bytes) to {doctype} {docname}...",
                        "done": False,
                    },
                })

            payload: dict[str, Any] = {
                "file_name": name,
                "content_base64": content_base64,
                "doctype": doctype,
                "docname": docname,
                "is_private": is_private,
            }
            if folder:
                payload["folder"] = folder

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        results.append(
                            f"Uploaded '{name}' to {doctype} {docname}: {data.get('file_url', 'OK')}"
                        )
                    else:
                        results.append(
                            f"Error uploading '{name}': {data.get('error', resp.text)}"
                        )
                else:
                    results.append(
                        f"Error uploading '{name}': server returned {resp.status_code}: {resp.text[:300]}"
                    )
            except httpx.ConnectError:
                return (
                    f"Error: Could not connect to ph-agent-framework at {self.valves.api_url}. "
                    "Check that the server is running and the api_url Valve is correct."
                )
            except Exception as exc:
                results.append(f"Error uploading '{name}': {exc}")

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"Finished '{name}'", "done": True},
                })

        return "\n".join(results) if results else "No files were processed."

    def _read_file_bytes(self, f: dict[str, Any], fallback_name: str) -> bytes | None:
        """Try every known way to extract file bytes from an __files__ entry."""

        # 'file' key can be a nested dict OR a string ID depending on OWUI version
        file_info = f.get("file")
        if isinstance(file_info, str):
            file_id = file_info
            filename = fallback_name
            data_content = None
        elif isinstance(file_info, dict):
            file_id = file_info.get("id", "")
            filename = file_info.get("filename", fallback_name)
            data = file_info.get("data")
            data_content = data.get("content") if isinstance(data, dict) else None
        else:
            file_id = ""
            filename = fallback_name
            data_content = None

        # Attempt 1: read from filesystem
        candidates = []
        if file_id:
            candidates.append(Path(f"/app/backend/data/uploads/{file_id}_{filename}"))
            candidates.append(Path(f"/app/backend/data/uploads/{file_id}"))
        candidates.append(Path(f"/app/backend/data/uploads/{filename}"))

        for disk_path in candidates:
            if disk_path.exists():
                return disk_path.read_bytes()

        # Attempt 2: inline content from file.data.content
        if data_content:
            return data_content.encode("utf-8")

        # Attempt 3: top-level 'content' or 'data' key (some versions)
        top_content = f.get("content")
        if isinstance(top_content, str) and top_content.strip():
            return top_content.encode("utf-8")

        top_data = f.get("data")
        if isinstance(top_data, dict):
            inner = top_data.get("content")
            if isinstance(inner, str) and inner.strip():
                return inner.encode("utf-8")

        # Attempt 4: 'url' key — try to fetch
        url = f.get("url")
        if isinstance(url, str) and url.startswith("http"):
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=30) as resp:
                    return resp.read()
            except Exception:
                pass

        return None
