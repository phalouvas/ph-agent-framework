def test_system_ping(client, auth_headers):
    response = client.post("/tools/system_ping", json={}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["pong"] is True
    assert "timestamp" in data
