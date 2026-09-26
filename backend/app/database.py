from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from typing import Optional


class Database:
    client: Optional[AsyncIOMotorClient] = None
    database = None

    def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.database = self.client[settings.mongodb_database]
        print(f"Connected to MongoDB at {settings.mongodb_uri}")

    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("Closed MongoDB connection")

    def get_database(self):
        """Get database instance."""
        if self.database is None:
            self.connect()
        return self.database


db = Database()


async def get_database():
    """Dependency for FastAPI to get database."""
    return db.get_database()
