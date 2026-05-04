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
