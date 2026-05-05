def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_openapi_schema(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    assert "info" in data
    assert data["info"]["title"] == "PH Agent Framework"
    # Verify tool endpoints are registered
    paths = data["paths"]
    assert "/tools/system_ping" in paths
    assert "/tools/erpnext_get_doc" in paths
    assert "/tools/erpnext_search_docs" in paths
