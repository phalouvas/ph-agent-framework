"""
title: ERPNext File Upload Bridge
author: PH Agent Framework
description: Bridges Open WebUI file uploads to the ph-agent-framework ERPNext tool server. Receives __files__ from chat attachments, reads the content, and forwards it to the erpnext_upload_file endpoint.
version: 0.1.0
licence: MIT
required_open_webui_version: 0.6.0
"""

import base64
import json
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
        __files__: list[dict] = [],
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
            file_info = f.get("file", {})
            name = file_name or f.get("name", "uploaded_file")
            file_id = file_info.get("id", "")
            filename = file_info.get("filename", name)

            # Read file bytes — try filesystem first, fall back to inline content
            file_bytes: bytes | None = None
            disk_path = Path(f"/app/backend/data/uploads/{file_id}_{filename}")
            if disk_path.exists():
                file_bytes = disk_path.read_bytes()
            else:
                content = file_info.get("data", {}).get("content")
                if content:
                    file_bytes = content.encode("utf-8")

            if file_bytes is None:
                results.append(f"Warning: Could not read content of '{name}'")
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
            except Exception as e:
                results.append(f"Error uploading '{name}': {e}")

            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"Finished '{name}'", "done": True},
                })

        return "\n".join(results)
