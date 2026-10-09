import uuid

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.config import settings
from app.database import db
from app.main import app

TEST_RPA_API_KEY = "test-rpa-key"


@pytest.fixture
def test_db_name(monkeypatch):
    """Point the app at a unique, disposable database and a test-only RPA key."""
    name = f"{settings.mongodb_database}_test_{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(settings, "mongodb_database", name)
    monkeypatch.setattr(settings, "rpa_api_key", TEST_RPA_API_KEY)
    sync_client = MongoClient(settings.mongodb_uri)
    yield name
    sync_client.drop_database(name)
    sync_client.close()


@pytest.fixture
def mongo(test_db_name):
    """Synchronous handle on the test database for seeding and assertions."""
    sync_client = MongoClient(settings.mongodb_uri)
    yield sync_client[test_db_name]
    sync_client.close()


@pytest.fixture
def client(test_db_name):
    """API client whose lifespan connects to the disposable test database only."""
    db.client = None
    db.database = None
    with TestClient(app) as test_client:
        yield test_client
    db.client = None
    db.database = None
