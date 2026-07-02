from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from typing import Optional
import logging

from config.settings import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    global _client, _db
    try:
        _client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )

        # Verify connection
        await _client.admin.command("ping")

        _db = _client[settings.MONGODB_DB_NAME]

        await _create_indexes()

        logger.info(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


async def disconnect_db() -> None:
    global _client

    if _client:
        _client.close()
        logger.info("MongoDB disconnected")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _db


async def _create_indexes() -> None:
    db = get_db()

    # sessions collection
    await db.sessions.create_indexes([
        IndexModel([("session_id", ASCENDING)], unique=True),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("updated_at", DESCENDING)]),
    ])

    # messages collection
    await db.messages.create_indexes([
        IndexModel([("session_id", ASCENDING), ("created_at", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("role", ASCENDING)]),
    ])

    # users collection (new)
    await db.users.create_indexes([
        IndexModel([("user_id", ASCENDING)], unique=True),
        IndexModel([("company_id", ASCENDING)]),
    ])

    # companies collection (new)
    await db.companies.create_indexes([
        IndexModel([("company_id", ASCENDING)], unique=True),
        IndexModel([("name", ASCENDING)]),
    ])

    # meetings collection (new)
    await db.meetings.create_indexes([
        IndexModel([("session_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # journeys collection (new)
    await db.journeys.create_indexes([
        IndexModel([("session_id", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # travel_searches collection
    await db.travel_searches.create_indexes([
        IndexModel([("session_id", ASCENDING)]),
        IndexModel([("search_type", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("origin", ASCENDING), ("destination", ASCENDING)]),
        # Added from new version
        IndexModel([("session_id", ASCENDING), ("search_type", ASCENDING)]),
    ])

    # cached_results collection
    await db.cached_results.create_indexes([
        IndexModel([("cache_key", ASCENDING)], unique=True),
        IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
    ])

    # preferences collection
    await db.preferences.create_indexes([
        IndexModel([("session_id", ASCENDING)], unique=True),
    ])

    # analytics collection
    await db.analytics.create_indexes([
        IndexModel([("event_type", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    logger.info("Database indexes created")