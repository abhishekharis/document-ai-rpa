import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database():
    """Create a test database connection."""
    # Use a separate test database
    test_client = AsyncIOMotorClient(settings.mongodb_uri)
    test_db = test_client[settings.mongodb_database + "_test"]
    
    yield test_db
    
    # Cleanup
    await test_client.drop_database(settings.mongodb_database + "_test")
    test_client.close()


@pytest.fixture
async def clean_database(test_database):
    """Clean database before each test."""
    # Clean collections
    await test_database.invoices.delete_many({})
    await test_database.audit_logs.delete_many({})
    
    yield test_database
    
    # Clean up after test
    await test_database.invoices.delete_many({})
    await test_database.audit_logs.delete_many({})
