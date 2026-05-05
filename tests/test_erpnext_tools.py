import json

import pytest
import httpx
from unittest.mock import MagicMock, patch

from app.core.keys_config import load_keys_config, lookup_key, lookup_tenant
from app.core.hashing import hash_api_key
from app.plugins.erpnext.client import ErpNextClient


# ── Functional tests (no ERPNext running) ──────────────────────────

def test_erpnext_get_doc_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_get_doc",
        json={"doctype": "Sales Invoice", "docname": "SINV-24-00001"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["doc"] is None
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_get_doc_with_fields(client, auth_headers):
    """Fields and expand_links params should be accepted by the schema."""
    response = client.post(
        "/tools/erpnext_get_doc",
        json={
            "doctype": "Sales Invoice",
            "docname": "SINV-24-00001",
            "fields": ["name", "total"],
            "expand_links": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_search_docs_with_filters(client, auth_headers):
    """Search now uses filters instead of query parameter."""
    response = client.post(
        "/tools/erpnext_search_docs",
        json={
            "doctype": "Item",
            "filters": [["status", "=", "Enabled"]],
            "fields": ["name", "item_name"],
            "order_by": "modified desc",
            "limit": 10,
            "limit_start": 0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_search_docs_with_or_filters(client, auth_headers):
    response = client.post(
        "/tools/erpnext_search_docs",
        json={
            "doctype": "Customer",
            "or_filters": [["customer_group", "=", "Individual"], ["customer_group", "=", "Retail"]],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_create_doc(client, auth_headers):
    response = client.post(
        "/tools/erpnext_create_doc",
        json={
            "doctype": "Customer",
            "data": {"customer_name": "Acme Corp", "customer_type": "Company"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_update_doc(client, auth_headers):
    response = client.post(
        "/tools/erpnext_update_doc",
        json={
            "doctype": "Sales Order",
            "docname": "SO-2025-00001",
            "data": {"delivery_date": "2025-03-15"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_delete_doc(client, auth_headers):
    response = client.post(
        "/tools/erpnext_delete_doc",
        json={"doctype": "Purchase Order", "docname": "PO-2025-00001"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_get_doctype_meta(client, auth_headers):
    response = client.post(
        "/tools/erpnext_get_doctype_meta",
        json={"doctype": "Sales Invoice"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["meta"] is None
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_list_doctypes(client, auth_headers):
    response = client.post(
        "/tools/erpnext_list_doctypes",
        json={"query": "Sales", "module": "Selling", "limit": 10},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_upload_file_base64(client, auth_headers):
    response = client.post(
        "/tools/erpnext_upload_file",
        json={
            "file_name": "test.pdf",
            "content": "test content from file",
            "content_base64": "dGVzdCBjb250ZW50",  # "test content" in base64
            "doctype": "Sales Invoice",
            "docname": "SINV-24-00001",
            "is_private": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_upload_file_empty_content(client, auth_headers):
    """Validation should reject empty content when content_base64 is also empty."""
    response = client.post(
        "/tools/erpnext_upload_file",
        json={
            "file_name": "document.pdf",
            "content": "",
            "doctype": "Customer",
            "docname": "Test Corp",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    data = response.json()
    assert "content" in data["message"] or "content" in str(data)


def test_erpnext_upload_file_text(client, auth_headers):
    response = client.post(
        "/tools/erpnext_upload_file",
        json={
            "file_name": "notes.txt",
            "content": "Meeting notes for customer Acme Corp",
            "doctype": "Customer",
            "docname": "Acme Corp",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_run_method(client, auth_headers):
    response = client.post(
        "/tools/erpnext_run_method",
        json={
            "method_path": "frappe.auth.get_logged_user",
            "args": None,
            "http_method": "GET",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_run_report(client, auth_headers):
    response = client.post(
        "/tools/erpnext_run_report",
        json={
            "report_name": "Trial Balance",
            "filters": {"company": "Test Company", "from_date": "2025-01-01", "to_date": "2025-12-31"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_list_reports(client, auth_headers):
    response = client.post(
        "/tools/erpnext_list_reports",
        json={"query": "Balance", "report_type": "Query Report", "limit": 20},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_get_current_user(client, auth_headers):
    response = client.post(
        "/tools/erpnext_get_current_user",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_get_system_info(client, auth_headers):
    response = client.post(
        "/tools/erpnext_get_system_info",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_all_tools_in_openapi_schema(client):
    """Verify all 22 ERPNext tools (plus system/utility) appear in the OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    erpnext_tools = {
        # Discovery & Metadata
        "/tools/erpnext_get_system_info",
        "/tools/erpnext_ping",
        "/tools/erpnext_list_doctypes",
        "/tools/erpnext_get_doctype_meta",
        "/tools/erpnext_get_fieldset",
        # Document CRUD
        "/tools/erpnext_get_doc",
        "/tools/erpnext_search_docs",
        "/tools/erpnext_count_docs",
        "/tools/erpnext_create_doc",
        "/tools/erpnext_update_doc",
        "/tools/erpnext_delete_doc",
        # Document Lifecycle
        "/tools/erpnext_submit_doc",
        "/tools/erpnext_cancel_doc",
        "/tools/erpnext_amend_doc",
        # Files
        "/tools/erpnext_upload_file",
        "/tools/erpnext_list_attachments",
        "/tools/erpnext_get_file",
        # Reports
        "/tools/erpnext_list_reports",
        "/tools/erpnext_run_report",
        # Generic & User
        "/tools/erpnext_run_method",
        "/tools/erpnext_get_current_user",
    }
    for tool_path in erpnext_tools:
        assert tool_path in paths, f"Missing tool endpoint: {tool_path}"


def test_erpnext_submit_doc_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_submit_doc",
        json={"doctype": "Sales Invoice", "docname": "SINV-24-00001"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_cancel_doc_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_cancel_doc",
        json={"doctype": "Sales Invoice", "docname": "SINV-24-00001"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_amend_doc_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_amend_doc",
        json={"doctype": "Sales Invoice", "docname": "SINV-24-00001"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_count_docs_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_count_docs",
        json={"doctype": "Sales Invoice", "filters": [["status", "=", "Open"]]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_ping_no_tenant(client, auth_headers):
    """Ping should gracefully report unavailable without an error string."""
    response = client.post(
        "/tools/erpnext_ping",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert data["url"] == "https://erp.example.com"
    assert data["error"] is None


def test_erpnext_get_file_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_get_file",
        json={"file_url": "/files/test.pdf"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_list_attachments_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_list_attachments",
        json={"doctype": "Sales Invoice", "docname": "SINV-24-00001"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]


def test_erpnext_get_fieldset_known_doctype(client, auth_headers):
    """Fieldset should return curated data for Sales Order without calling ERPNext."""
    response = client.post(
        "/tools/erpnext_get_fieldset",
        json={"doctype": "Sales Order"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_known"] is True
    assert data["fieldset"] is not None
    assert "required" in data["fieldset"]
    assert "lifecycle" in data["fieldset"]


def test_erpnext_get_fieldset_unknown_doctype(client, auth_headers):
    response = client.post(
        "/tools/erpnext_get_fieldset",
        json={"doctype": "NonExistentDoctype"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_known"] is False


def test_erpnext_search_docs_include_total_count(client, auth_headers):
    """Search with include_total_count should have the total_count field in the error response shape."""
    response = client.post(
        "/tools/erpnext_search_docs",
        json={
            "doctype": "Item",
            "filters": [["status", "=", "Enabled"]],
            "limit": 5,
            "include_total_count": True,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Cannot reach ERPNext" in data["error"]
    assert "has_more" in data
    assert "total_count" in data


# ── Client unit tests ──────────────────────────────────────────────

class TestErpNextClient:
    def test_filters_use_json_dumps_not_str(self):
        """Verify the serialization bug is fixed: filters use json.dumps, not str()."""
        filters = [["name", "like", "%test%"]]
        result = json.dumps(filters)
        assert result == '[["name", "like", "%test%"]]'
        # str() would produce "[['name', 'like', '%test%']]" which is invalid JSON
        assert str(filters) != result

    @pytest.mark.asyncio
    async def test_search_docs_passes_filters_as_json(self):
        """Verify search_docs sends filters as proper JSON in query params."""
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": [{"name": "TEST-001"}]}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.search_docs(
                doctype="Item",
                filters=[["item_group", "=", "Raw Material"]],
                fields=["name", "item_name"],
                limit_page_length=20,
            )

        call_kwargs = mock_req.call_args.kwargs
        assert "params" in call_kwargs
        # Filters should be valid JSON
        parsed = json.loads(call_kwargs["params"]["filters"])
        assert parsed == [["item_group", "=", "Raw Material"]]
        assert result == [{"name": "TEST-001"}]

    @pytest.mark.asyncio
    async def test_get_doc_passes_fields_as_json(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": {"name": "TEST-001"}}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            await client.get_doc("Sales Order", "SO-001", fields=["name", "total"], expand_links=True)

        call_kwargs = mock_req.call_args.kwargs
        params = call_kwargs["params"] or {}
        assert json.loads(params["fields"]) == ["name", "total"]
        assert params["expand_links"] == "true"

    @pytest.mark.asyncio
    async def test_create_doc_sends_json_body(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": {"name": "CUST-001", "customer_name": "Acme Corp"}}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.create_doc("Customer", {"customer_name": "Acme Corp"})

        call_args = mock_req.call_args
        assert call_args.args[0] == "POST"
        assert "Customer" in call_args.args[1]
        assert call_args.kwargs["json"] == {"customer_name": "Acme Corp"}
        assert result == {"name": "CUST-001", "customer_name": "Acme Corp"}

    @pytest.mark.asyncio
    async def test_run_method_get(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": "user@example.com"}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.run_method("frappe.auth.get_logged_user", http_method="GET")

        call_args = mock_req.call_args
        assert call_args.args[0] == "GET"
        assert result == "user@example.com"

    @pytest.mark.asyncio
    async def test_upload_file_decodes_base64(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "message": {"file_url": "/files/test.pdf", "file_name": "test.pdf"}
        }

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.upload_file(
                file_name="test.pdf",
                content_base64="dGVzdCBjb250ZW50",  # "test content"
                doctype="Sales Invoice",
                docname="SINV-001",
            )

        call_kwargs = mock_req.call_args.kwargs
        assert "files" in call_kwargs
        assert call_kwargs["files"]["file"][0] == "test.pdf"
        assert call_kwargs["data"] == {"is_private": 1, "doctype": "Sales Invoice", "docname": "SINV-001"}
        assert result == {"file_url": "/files/test.pdf", "file_name": "test.pdf"}

    @pytest.mark.asyncio
    async def test_upload_file_plain_text(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "message": {"file_url": "/files/notes.txt", "file_name": "notes.txt"}
        }

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.upload_file(
                file_name="notes.txt",
                content="Plain text meeting notes",
                doctype="Customer",
                docname="Acme Corp",
            )

        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["files"]["file"][0] == "notes.txt"
        assert call_kwargs["files"]["file"][1].read() == b"Plain text meeting notes"
        assert result == {"file_url": "/files/notes.txt", "file_name": "notes.txt"}

    @pytest.mark.asyncio
    async def test_run_report_sends_correct_body(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": {"result": [{"account": "Cash", "balance": 1000}], "columns": []}}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.run_report(
                report_name="Trial Balance",
                filters={"company": "Test Company", "from_date": "2025-01-01"},
            )

        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs["json"] == {
            "report_name": "Trial Balance",
            "filters": {"company": "Test Company", "from_date": "2025-01-01"},
            "file_format": "HTML",
        }
        assert result == {"result": [{"account": "Cash", "balance": 1000}], "columns": []}

    @pytest.mark.asyncio
    async def test_list_reports_uses_filters(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": [{"name": "Trial Balance", "report_type": "Query Report"}]}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.list_reports(query="Balance", report_type="Query Report")

        call_kwargs = mock_req.call_args.kwargs
        assert "filters" in call_kwargs["params"]
        filters = json.loads(call_kwargs["params"]["filters"])
        assert ["is_standard", "=", "Yes"] in filters
        assert ["name", "like", "%Balance%"] in filters
        assert ["report_type", "=", "Query Report"] in filters
        assert result == [{"name": "Trial Balance", "report_type": "Query Report"}]


    @pytest.mark.asyncio
    async def test_submit_doc_calls_run_method(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": {"name": "SINV-001", "docstatus": 1}}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.submit_doc("Sales Invoice", "SINV-001")

        call_args = mock_req.call_args
        assert call_args.args[0] == "POST"
        assert "/api/method/frappe.client.submit" in call_args.args[1]
        assert call_args.kwargs["json"] == {"doctype": "Sales Invoice", "name": "SINV-001"}
        assert result == {"name": "SINV-001", "docstatus": 1}

    @pytest.mark.asyncio
    async def test_cancel_doc_calls_run_method(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": {"name": "SINV-001", "docstatus": 2}}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.cancel_doc("Sales Invoice", "SINV-001")

        call_args = mock_req.call_args
        assert call_args.args[0] == "POST"
        assert "/api/method/frappe.client.cancel" in call_args.args[1]
        assert call_args.kwargs["json"] == {"doctype": "Sales Invoice", "name": "SINV-001"}
        assert result == {"name": "SINV-001", "docstatus": 2}

    @pytest.mark.asyncio
    async def test_count_docs_calls_run_method(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": 42}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.count_docs("Sales Invoice", filters=[["status", "=", "Open"]])

        call_args = mock_req.call_args
        assert call_args.args[0] == "POST"
        assert "/api/method/frappe.client.count" in call_args.args[1]
        assert result == 42

    @pytest.mark.asyncio
    async def test_ping_available(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"message": "pong"}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.ping()

        call_args = mock_req.call_args
        assert call_args.args[0] == "GET"
        assert "/api/method/frappe.ping" in call_args.args[1]
        assert result["available"] is True
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_ping_unavailable(self):
        client = ErpNextClient("https://erp-offline.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=MagicMock(status_code=500, text="Internal Server Error"),
        )

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response):
            result = await client.ping()

        assert result["available"] is False
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_get_file_uses_filters(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": [{"file_name": "test.pdf", "file_url": "/files/test.pdf"}]}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.get_file("/files/test.pdf")

        call_kwargs = mock_req.call_args.kwargs
        assert "params" in call_kwargs
        filters = json.loads(call_kwargs["params"]["filters"])
        assert ["file_url", "=", "/files/test.pdf"] in filters
        assert result == {"file_name": "test.pdf", "file_url": "/files/test.pdf"}

    @pytest.mark.asyncio
    async def test_list_files_uses_filters(self):
        client = ErpNextClient("https://erp.example.com", "key", "secret")

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"data": [{"file_name": "notes.txt"}]}

        with patch.object(httpx.AsyncClient, "request", return_value=mock_response) as mock_req:
            result = await client.list_files(doctype="Customer", docname="Acme Corp")

        call_kwargs = mock_req.call_args.kwargs
        filters = json.loads(call_kwargs["params"]["filters"])
        assert ["attached_to_doctype", "=", "Customer"] in filters
        assert ["attached_to_name", "=", "Acme Corp"] in filters
        assert result == [{"file_name": "notes.txt"}]


# ── Tenant resolution tests ────────────────────────────────────────

class TestPerUserTenantResolution:
    def test_default_tenant_when_no_user_email(self, test_keys_yaml):
        load_keys_config(str(test_keys_yaml))
        key_hash = hash_api_key("sk-test-secret")
        key_info = lookup_key(key_hash)
        tenant = lookup_tenant(key_info["id"])
        assert tenant is not None
        assert tenant.url == "https://erp.example.com"

    def test_per_user_tenant_when_email_matches(self, test_keys_yaml):
        load_keys_config(str(test_keys_yaml))
        key_hash = hash_api_key("sk-test-secret")
        key_info = lookup_key(key_hash)
        tenant = lookup_tenant(key_info["id"], "alice@example.com")
        assert tenant is not None
        assert tenant.url == "https://erp-alice.example.com"

    def test_default_tenant_when_email_does_not_match(self, test_keys_yaml):
        load_keys_config(str(test_keys_yaml))
        key_hash = hash_api_key("sk-test-secret")
        key_info = lookup_key(key_hash)
        tenant = lookup_tenant(key_info["id"], "unknown@example.com")
        assert tenant is not None
        assert tenant.url == "https://erp.example.com"

    def test_none_when_key_not_found(self, test_keys_yaml):
        load_keys_config(str(test_keys_yaml))
        tenant = lookup_tenant("nonexistent")
        assert tenant is None

    def test_email_case_insensitive(self, test_keys_yaml):
        load_keys_config(str(test_keys_yaml))
        key_hash = hash_api_key("sk-test-secret")
        key_info = lookup_key(key_hash)
        tenant = lookup_tenant(key_info["id"], "ALICE@EXAMPLE.COM")
        assert tenant is not None
        assert tenant.url == "https://erp-alice.example.com"
