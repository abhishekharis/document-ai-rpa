from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models.invoice import Invoice, InvoiceStatus, Vendor, Extraction
from app.services.events import invoice_event_stream, sse_message, SSE_OVERLAP_SECONDS
from app.services.repository import InvoiceRepository


@pytest_asyncio.fixture
async def repo(test_db_name):
    motor_client = AsyncIOMotorClient(settings.mongodb_uri)
    yield InvoiceRepository(motor_client[test_db_name])
    motor_client.close()


def make_invoice(document_id, status=InvoiceStatus.PROCESSING):
    return Invoice(
        document_id=document_id, original_filename="a.pdf", status=status,
        vendor=Vendor(name=""), invoice_number="", invoice_date="",
        extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
    )


def test_sse_message_format():
    assert sse_message("invoice", {"a": 1}) == 'event: invoice\ndata: {"a": 1}\n\n'


@pytest.mark.asyncio
async def test_stream_emits_only_changes_after_connect(repo):
    old = make_invoice("DOC-OLD")
    old.updated_at = datetime.utcnow() - timedelta(hours=1)
    await repo.create(old)

    polls = 0

    async def is_disconnected():
        nonlocal polls
        polls += 1
        if polls == 2:
            await repo.create(make_invoice("DOC-NEW"))
        if polls == 3:
            await repo.update_status("DOC-NEW", InvoiceStatus.NEEDS_REVIEW, InvoiceStatus.PROCESSING)
        return polls > 4

    messages = [m async for m in invoice_event_stream(repo, is_disconnected, poll_interval=0.01)]
    events = [m for m in messages if m.startswith("event:")]

    assert messages[0] == ": connected\n\n"
    assert all("DOC-OLD" not in m for m in events)
    assert 'DOC-NEW", "status": "PROCESSING"' in events[0]
    assert 'DOC-NEW", "status": "NEEDS_REVIEW"' in events[-1]
    assert len(events) == 2


@pytest.mark.asyncio
async def test_stream_sends_heartbeat_when_idle(repo):
    polls = 0

    async def is_disconnected():
        nonlocal polls
        polls += 1
        return polls > 3

    messages = [m async for m in invoice_event_stream(repo, is_disconnected, poll_interval=0.01, heartbeat_every=0.02)]
    assert ": keep-alive\n\n" in messages


@pytest.mark.asyncio
async def test_stream_deduplicates_within_overlap_window(repo):
    """An invoice that appears in two consecutive polls (due to overlap) is only emitted once."""
    inv = make_invoice("DOC-ONCE")
    await repo.create(inv)
    polls = 0

    async def is_disconnected():
        nonlocal polls
        polls += 1
        return polls > 3

    messages = [m async for m in invoice_event_stream(repo, is_disconnected, poll_interval=0.01)]
    events = [m for m in messages if m.startswith("event:")]
    # Only one event for this invoice despite overlap queries repeating it
    doc_events = [e for e in events if "DOC-ONCE" in e]
    assert len(doc_events) == 1


@pytest.mark.asyncio
async def test_stream_stops_when_shutting_down(repo):
    """shutting_down=True causes the stream to exit immediately (after the initial connected notice)."""
    async def is_disconnected():
        return False  # never disconnects — only shutdown exits

    messages = []
    async for chunk in invoice_event_stream(repo, is_disconnected, poll_interval=0.01, shutting_down=True):
        messages.append(chunk)
        # Safety: bail if somehow we get more than a few messages
        if len(messages) > 5:
            break

    assert messages[0] == ": connected\n\n"
    # The loop condition checks shutting_down before polling; at most the connected notice arrives
    assert len(messages) == 1
