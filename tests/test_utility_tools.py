def test_text_transform(client, auth_headers):
    response = client.post(
        "/tools/text_transform",
        json={"text": "hello", "operation": "uppercase"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "HELLO"


def test_generate_id(client, auth_headers):
    response = client.post(
        "/tools/generate_id",
        json={"kind": "uuid"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["kind"] == "uuid"


def test_server_datetime(client, auth_headers):
    response = client.post(
        "/tools/server_datetime", json={}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "datetime" in data
    assert data["timezone"] == "UTC"
    assert "date" in data
    assert "time" in data
    assert "day_of_week" in data


def test_server_datetime_custom_timezone(client, auth_headers):
    response = client.post(
        "/tools/server_datetime",
        json={"timezone": "Asia/Tokyo"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "Asia/Tokyo"
    assert "datetime" in data


def test_server_datetime_invalid_timezone_falls_back(client, auth_headers):
    response = client.post(
        "/tools/server_datetime",
        json={"timezone": "Not/A_Real_Zone"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["timezone"] == "UTC"
    assert "datetime" in data
