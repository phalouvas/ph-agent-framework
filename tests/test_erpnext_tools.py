import pytest

from app.core.keys_config import load_keys_config, lookup_key, lookup_tenant
from app.core.hashing import hash_api_key


def test_erpnext_get_doc_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_get_doc",
        json={"doctype": "Sales Invoice", "docname": "SINV-24-00001"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Tenant is configured in test DB but ERPNext is not actually running
    assert data["doc"] is None
    assert data["error"] is not None
    assert "Could not connect to ERPNext" in data["error"]


def test_erpnext_search_docs_no_tenant(client, auth_headers):
    response = client.post(
        "/tools/erpnext_search_docs",
        json={"doctype": "Item", "query": "test"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Tenant is configured but ERPNext is not actually running
    assert data["count"] == 0
    assert data["error"] is not None
    assert "Could not connect to ERPNext" in data["error"]


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
