import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models.invoice import Invoice, InvoiceStatus, Vendor, Extraction
from app.services.pipeline import run_processing
from app.services.repository import InvoiceRepository
from app.utils.duplicates import duplicate_reason, normalize_invoice_number, vendor_similarity


def inv(vendor="Acme Office Supplies Inc.", number="INV-1001", date="2026-01-05", total=120.0):
    return {"vendor_name": vendor, "invoice_number": number, "invoice_date": date, "total": total}


class TestDuplicateReason:
    def test_same_vendor_and_number(self):
        assert duplicate_reason(inv(), inv()) == "same vendor and invoice number"

    def test_number_formatting_and_vendor_suffix_are_ignored(self):
        assert duplicate_reason(inv(vendor="ACME Office Supplies"), inv(number="inv 1001"))

    def test_ocr_misread_vendor_still_matches(self):
        assert duplicate_reason(inv(vendor="Acme Offce Supplies Inc"), inv())

    def test_same_date_and_total_without_number(self):
        assert duplicate_reason(inv(number=""), inv()) == "same vendor, date and total"

    def test_different_vendor_same_number_is_not_duplicate(self):
        assert duplicate_reason(inv(vendor="Globex Corporation"), inv()) is None

    def test_same_vendor_different_number_and_total(self):
        assert duplicate_reason(inv(number="INV-2000", total=5.0), inv()) is None

    def test_helpers(self):
        assert normalize_invoice_number(" inv-10/01 ") == "INV1001"
        assert vendor_similarity("", "Acme") == 0.0


class FakeProcessingService:
    def __init__(self, **fields):
        self.fields = {"vendor": "Acme Office Supplies Inc.", "number": "INV-1001", "total": 120.0, **fields}

    async def process_invoice(self, content, filename, document_id):
        return {
            "status": "PROCESSED",
            "vendor": {"name": self.fields["vendor"]},
            "invoice_number": self.fields["number"],
            "invoice_date": "2026-01-05",
            "due_date": None,
            "currency": "USD",
            "subtotal": None,
            "tax": None,
            "total": self.fields["total"],
            "extraction": Extraction(overall_confidence=0.95, fields={}, raw_ocr_text="x", page_count=1).model_dump(),
            "validation": {"is_valid": True, "errors": [], "warnings": []},
        }


@pytest_asyncio.fixture
async def repo(test_db_name):
    motor_client = AsyncIOMotorClient(settings.mongodb_uri)
    yield InvoiceRepository(motor_client[test_db_name])
    motor_client.close()


async def create_processing(repo, document_id):
    await repo.create(Invoice(
        document_id=document_id, original_filename="a.pdf", status=InvoiceStatus.PROCESSING,
        vendor=Vendor(name=""), invoice_number="", invoice_date="",
        extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
    ))


@pytest.mark.asyncio
async def test_second_copy_is_flagged_and_not_auto_approved(repo):
    await create_processing(repo, "DOC-A")
    assert await run_processing(repo, FakeProcessingService(), "DOC-A", b"x", "a.pdf") == InvoiceStatus.RPA_QUEUED

    await create_processing(repo, "DOC-B")
    status = await run_processing(repo, FakeProcessingService(vendor="ACME Office Supplies"), "DOC-B", b"x", "b.pdf")

    assert status == InvoiceStatus.NEEDS_REVIEW
    second = await repo.get_by_document_id("DOC-B")
    assert second.validation.duplicate_of == "DOC-A"
    assert "Possible duplicate of DOC-A" in second.validation.warnings[0]
    events = [log async for log in repo.audit_collection.find({"document_id": "DOC-B", "event": "DUPLICATE_DETECTED"})]
    assert len(events) == 1


@pytest.mark.asyncio
async def test_distinct_invoices_are_not_flagged(repo):
    await create_processing(repo, "DOC-A")
    await run_processing(repo, FakeProcessingService(), "DOC-A", b"x", "a.pdf")
    await create_processing(repo, "DOC-C")
    status = await run_processing(repo, FakeProcessingService(number="INV-2002", total=999.0), "DOC-C", b"x", "c.pdf")
    assert status == InvoiceStatus.RPA_QUEUED
    assert (await repo.get_by_document_id("DOC-C")).validation.duplicate_of is None
