def test_missing_api_key_returns_401(client):
    response = client.post("/tools/system_ping", json={})
    assert response.status_code == 401
    assert "Missing X-API-Key" in response.json()["message"]


def test_invalid_api_key_returns_401(client):
    response = client.post(
        "/tools/system_ping",
        json={},
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["message"]


def test_valid_api_key_returns_200(client, auth_headers):
    response = client.post(
        "/tools/system_ping",
        json={},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["pong"] is True
