import asyncio
import json
from datetime import datetime
from typing import AsyncIterator, Awaitable, Callable

from app.services.repository import InvoiceRepository


def sse_message(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def invoice_event_stream(
    repo: InvoiceRepository,
    is_disconnected: Callable[[], Awaitable[bool]],
    poll_interval: float = 1.0,
    heartbeat_every: float = 15.0,
) -> AsyncIterator[str]:
    """Yield a Server-Sent Event whenever an invoice's status or contents change.

    Changes are read from MongoDB rather than in-process hooks because OCR runs in a
    separate worker process. A comment heartbeat keeps proxies from closing idle streams.
    """
    cursor = datetime.utcnow()
    emitted: dict[str, datetime] = {}
    idle = 0.0
    yield ": connected\n\n"
    while not await is_disconnected():
        changes = [c for c in await repo.list_changed_since(cursor) if emitted.get(c["document_id"]) != c["updated_at"]]
        for change in changes:
            emitted[change["document_id"]] = change["updated_at"]
            cursor = max(cursor, change["updated_at"])
            yield sse_message("invoice", {"document_id": change["document_id"], "status": change["status"]})
        # Only entries at the cursor can be returned again by the $gte query
        emitted = {k: v for k, v in emitted.items() if v >= cursor}
        if changes:
            idle = 0.0
        else:
            idle += poll_interval
            if idle >= heartbeat_every:
                idle = 0.0
                yield ": keep-alive\n\n"
        await asyncio.sleep(poll_interval)
