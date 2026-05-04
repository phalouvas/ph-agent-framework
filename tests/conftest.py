import asyncio
import os

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import Settings

TEST_API_KEY = "sk-test-secret"
TEST_API_KEY_NAME = "test-user"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_keys_yaml(tmp_path):
    yaml_path = tmp_path / "api_keys.yaml"
    data = {
        "api_keys": [
            {
                "key": TEST_API_KEY,
                "name": TEST_API_KEY_NAME,
                "tenant": {
                    "url": "https://erp.example.com",
                    "api_key": "erp-api-key",
                    "api_secret": "erp-api-secret",
                },
            }
        ]
    }
    with open(yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    return yaml_path


@pytest.fixture
def test_app(test_keys_yaml, tmp_path):
    from app.main import create_app

    plugins_config = tmp_path / "plugins.yaml"
    plugins_config.write_text(
        yaml.dump(
            {
                "plugins": {
                    "system": {"enabled": True},
                    "erpnext": {"enabled": True},
                    "utility": {"enabled": True},
                }
            }
        )
    )

    settings = Settings(
        keys_yaml_path=str(test_keys_yaml),
        initial_api_keys="",
    )

    app = create_app(
        settings=settings,
        config_dir=tmp_path,
    )
    return app


@pytest.fixture
def client(test_app):
    with TestClient(test_app) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"X-API-Key": TEST_API_KEY}
