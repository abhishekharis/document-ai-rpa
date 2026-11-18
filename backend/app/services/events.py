import asyncio
import json
from datetime import datetime, timedelta
from typing import AsyncIterator, Awaitable, Callable

from app.services.repository import InvoiceRepository


def sse_message(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# De-duplication window: query a bit behind the cursor to catch events whose
# DB-commit timestamp is slightly earlier than the last event we saw (clock skew
# between the API process and the OCR worker, or a slow MongoDB write).
SSE_OVERLAP_SECONDS = 5.0


async def invoice_event_stream(
    repo: InvoiceRepository,
    is_disconnected: Callable[[], Awaitable[bool]],
    poll_interval: float = 1.0,
    heartbeat_every: float = 15.0,
    shutting_down: bool = False,
) -> AsyncIterator[str]:
    """Yield a Server-Sent Event whenever an invoice's status or contents change.

    Changes are read from MongoDB rather than in-process hooks because OCR runs in a
    separate worker process. A comment heartbeat keeps proxies from closing idle streams.

    The query window is extended backwards by SSE_OVERLAP_SECONDS to tolerate clock skew
    between the API and OCR worker processes. Events that have already been sent are
    de-duplicated on (document_id, updated_at).
    """
    cursor = datetime.utcnow()
    # emitted maps document_id → updated_at of the last event sent for that invoice
    emitted: dict[str, datetime] = {}
    idle = 0.0
    yield ": connected\n\n"
    while not shutting_down and not await is_disconnected():
        # Query from (cursor - overlap) to catch late-arriving events from other processes
        since = cursor - timedelta(seconds=SSE_OVERLAP_SECONDS)
        changes = [
            c for c in await repo.list_changed_since(since)
            if emitted.get(c["document_id"]) != c["updated_at"]
        ]
        for change in changes:
            emitted[change["document_id"]] = change["updated_at"]
            cursor = max(cursor, change["updated_at"])
            yield sse_message("invoice", {"document_id": change["document_id"], "status": change["status"]})
        # Keep emitted entries only within the overlap window; older ones are past the
        # de-duplication horizon and can be pruned to prevent unbounded growth.
        window_start = cursor - timedelta(seconds=SSE_OVERLAP_SECONDS)
        emitted = {k: v for k, v in emitted.items() if v >= window_start}
        if changes:
            idle = 0.0
        else:
            idle += poll_interval
            if idle >= heartbeat_every:
                idle = 0.0
                yield ": keep-alive\n\n"
        await asyncio.sleep(poll_interval)
