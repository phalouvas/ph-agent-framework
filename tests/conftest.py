import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.db.models import Base
from app.db.repositories import insert_api_key, insert_tenant_mapping

TEST_API_KEY = "sk-test-secret"
TEST_API_KEY_NAME = "test-user"
TEST_API_KEY_ID = None


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        api_key = await insert_api_key(session, TEST_API_KEY, TEST_API_KEY_NAME)
        await session.flush()
        global TEST_API_KEY_ID
        TEST_API_KEY_ID = api_key.id
        await insert_tenant_mapping(
            session,
            api_key_id=api_key.id,
            erpnext_url="https://erp.example.com",
            erpnext_api_key="erp-api-key",
            erpnext_api_secret="erp-api-secret",
        )
        await session.commit()

    yield session_factory
    await engine.dispose()


@pytest.fixture
def test_app(test_db, tmp_path):
    from app.main import create_app

    import yaml

    plugins_config = tmp_path / "plugins.yaml"
    plugins_config.write_text(
        yaml.dump(
            {
                "plugins": {
                    "system": {"enabled": True},
                    "erpnext": {"enabled": True},
                    "utility": {"enabled": False},
                }
            }
        )
    )

    settings = Settings(
        database_path=str(tmp_path / "test.db"),
        initial_api_keys="",
    )

    app = create_app(
        settings=settings,
        get_db_override=test_db,
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
