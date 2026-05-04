def test_system_ping(client, auth_headers):
    response = client.post("/tools/system_ping", json={}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["pong"] is True
    assert "timestamp" in data


def test_system_info(client, auth_headers):
    response = client.post("/tools/system_info", json={}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert isinstance(data["cpu_percent"], (int, float))


def test_random_number(client, auth_headers):
    response = client.post(
        "/tools/random_number",
        json={"min": 1, "max": 10},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert 1 <= data["value"] <= 10


def test_random_number_default_range(client, auth_headers):
    response = client.post("/tools/random_number", json={}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert 0 <= data["value"] <= 100
