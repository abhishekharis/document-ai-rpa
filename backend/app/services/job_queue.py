import logging
from typing import Optional

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "document_ai_rpa:ocr_jobs"


class JobQueue:
    """Redis list of document IDs waiting for OCR processing."""

    def __init__(self, client: "redis.Redis"):
        self.client = client

    async def enqueue(self, document_id: str) -> None:
        await self.client.lpush(QUEUE_KEY, document_id)

    async def dequeue(self, timeout: int = 5) -> Optional[str]:
        """Block up to `timeout` seconds for the next document ID; None if the queue stayed empty."""
        item = await self.client.brpop(QUEUE_KEY, timeout=timeout)
        return item[1] if item else None

    async def size(self) -> int:
        return await self.client.llen(QUEUE_KEY)

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self.client.aclose()


def create_job_queue() -> Optional[JobQueue]:
    """Build the queue from REDIS_URL, or None when unset (documents are then processed inline)."""
    if not settings.redis_url:
        return None
    return JobQueue(redis.from_url(settings.redis_url, decode_responses=True))
