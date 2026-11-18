import fakeredis.aioredis
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

from app.main import app
from app.models.invoice import Invoice, InvoiceStatus, Vendor, Extraction
from app.services.job_queue import JobQueue
from app.services.repository import InvoiceRepository
from app import worker
from app.worker import recovery_sweep


@pytest.fixture
def job_queue():
    return JobQueue(fakeredis.aioredis.FakeRedis(decode_responses=True))


@pytest_asyncio.fixture
async def repo(test_db_name):
    """Repository on its own Motor client, bound to this test's event loop."""
    motor_client = AsyncIOMotorClient(settings.mongodb_uri)
    yield InvoiceRepository(motor_client[test_db_name])
    motor_client.close()


def pdf_upload():
    return {"file": ("invoice.pdf", b"%PDF-1.4 fake", "application/pdf")}


@pytest.mark.asyncio
async def test_queue_is_first_in_first_out(job_queue):
    await job_queue.enqueue("DOC-1")
    await job_queue.enqueue("DOC-2")
    assert await job_queue.size() == 2
    assert await job_queue.dequeue(timeout=1) == "DOC-1"
    assert await job_queue.dequeue(timeout=1) == "DOC-2"
    assert await job_queue.dequeue(timeout=1) is None


class TestQueuedUpload:
    def test_upload_returns_processing_and_queues_job(self, client, job_queue, monkeypatch):
        monkeypatch.setattr(app.state, "job_queue", job_queue)
        response = client.post("/api/invoices/upload", files=pdf_upload())
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "PROCESSING"

        invoice = client.get(f"/api/invoices/{body['document_id']}").json()
        assert invoice["status"] == "PROCESSING"

    def test_queue_failure_marks_invoice_error(self, client, monkeypatch):
        class BrokenQueue:
            async def enqueue(self, document_id):
                raise ConnectionError("redis down")

            async def close(self):
                pass

        monkeypatch.setattr(app.state, "job_queue", BrokenQueue())
        response = client.post("/api/invoices/upload", files=pdf_upload())
        assert response.status_code == 201
        assert response.json()["status"] == "ERROR"


class FakeProcessingService:
    async def process_invoice(self, content, filename, document_id):
        return {
            "status": "NEEDS_REVIEW",
            "vendor": {"name": "Worker Vendor"},
            "invoice_number": "INV-1",
            "invoice_date": "2026-01-01",
            "due_date": None,
            "currency": "USD",
            "subtotal": None,
            "tax": None,
            "total": 10.0,
            "extraction": Extraction(overall_confidence=0.5, fields={}, raw_ocr_text="x", page_count=1).model_dump(),
            "validation": {"is_valid": True, "errors": [], "warnings": []},
        }


class TestWorker:
    @pytest.mark.asyncio
    async def test_process_job_runs_pipeline(self, repo, monkeypatch, tmp_path):
        from app.storage.file_storage import file_storage

        await repo.create(Invoice(
            document_id="DOC-W1", original_filename="a.pdf", status=InvoiceStatus.PROCESSING,
            vendor=Vendor(name=""), invoice_number="", invoice_date="",
            extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
        ))
        stored = tmp_path / "a.pdf"
        stored.write_bytes(b"pdf")
        monkeypatch.setattr(file_storage, "get_original_file", lambda document_id: stored)

        await worker.process_job(repo, FakeProcessingService(), "DOC-W1")

        assert (await repo.get_by_document_id("DOC-W1")).status == InvoiceStatus.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_process_job_skips_documents_not_processing(self, repo):

        await repo.create(Invoice(
            document_id="DOC-W2", original_filename="a.pdf", status=InvoiceStatus.APPROVED,
            vendor=Vendor(name="Keep"), invoice_number="", invoice_date="",
            extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
        ))
        await worker.process_job(repo, FakeProcessingService(), "DOC-W2")
        assert (await repo.get_by_document_id("DOC-W2")).status == InvoiceStatus.APPROVED

    @pytest.mark.asyncio
    async def test_recovery_sweep_requeues_unclaimed_processing(self, repo, job_queue):
        for doc_id, st in (("DOC-W3", InvoiceStatus.PROCESSING), ("DOC-W4", InvoiceStatus.APPROVED)):
            await repo.create(Invoice(
                document_id=doc_id, original_filename="a.pdf", status=st,
                vendor=Vendor(name=""), invoice_number="", invoice_date="",
                extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
            ))
        assert await recovery_sweep(repo, job_queue) == 1
        assert await job_queue.dequeue(timeout=1) == "DOC-W3"

    @pytest.mark.asyncio
    async def test_recovery_sweep_skips_freshly_claimed(self, repo, job_queue):
        """A recently-claimed PROCESSING invoice is not swept — it is still in flight."""
        await repo.create(Invoice(
            document_id="DOC-W5", original_filename="a.pdf", status=InvoiceStatus.PROCESSING,
            vendor=Vendor(name=""), invoice_number="", invoice_date="",
            extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
        ))
        # Claim it now (fresh token, well within the timeout window)
        token = await repo.claim_ocr_job("DOC-W5", stale_threshold_minutes=15)
        assert token is not None
        # Sweep should leave it alone
        assert await recovery_sweep(repo, job_queue) == 0
        assert await job_queue.dequeue(timeout=1) is None

    @pytest.mark.asyncio
    async def test_two_concurrent_process_job_calls_run_pipeline_once(
        self, repo, monkeypatch, tmp_path
    ):
        """Two concurrent workers both see the same PROCESSING document; only one should run the pipeline."""
        from app.storage.file_storage import file_storage

        await repo.create(Invoice(
            document_id="DOC-W6", original_filename="a.pdf", status=InvoiceStatus.PROCESSING,
            vendor=Vendor(name=""), invoice_number="", invoice_date="",
            extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
        ))
        stored = tmp_path / "a.pdf"
        stored.write_bytes(b"pdf")
        monkeypatch.setattr(file_storage, "get_original_file", lambda document_id: stored)

        # Run two process_job calls concurrently
        await asyncio.gather(
            worker.process_job(repo, FakeProcessingService(), "DOC-W6"),
            worker.process_job(repo, FakeProcessingService(), "DOC-W6"),
        )

        # Only one PROCESSING_COMPLETE audit entry should exist
        from pymongo import MongoClient
        from app.config import settings
        client = MongoClient(settings.mongodb_uri)
        db_name = repo.collection.database.name
        logs = list(client[db_name].audit_logs.find({"document_id": "DOC-W6", "event": "PROCESSING_COMPLETE"}))
        client.close()
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_stale_token_write_is_noop(self, repo, monkeypatch, tmp_path):
        """A late finisher with an old token should not overwrite the invoice."""
        from app.storage.file_storage import file_storage
        from app.services.pipeline import run_processing

        await repo.create(Invoice(
            document_id="DOC-W7", original_filename="a.pdf", status=InvoiceStatus.PROCESSING,
            vendor=Vendor(name=""), invoice_number="", invoice_date="",
            extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
        ))

        # Claim it and immediately mark as approved (simulating another worker finishing first)
        stale_token = await repo.claim_ocr_job("DOC-W7", stale_threshold_minutes=15)
        assert stale_token is not None
        await repo.update_status("DOC-W7", InvoiceStatus.APPROVED, InvoiceStatus.PROCESSING)

        # Now try to finish with the stale token — should be a no-op
        from app.models.invoice import Extraction as Ext
        landed = await repo.finish_ocr_job(
            document_id="DOC-W7",
            token=stale_token,
            invoice_fields={"vendor": {"name": "Late"}, "invoice_number": "X", "invoice_date": "2026-01-01",
                            "due_date": None, "currency": "USD", "subtotal": None, "tax": None, "total": None,
                            "line_items": []},
            extraction=Ext(overall_confidence=0.9).model_dump(),
            validation={"is_valid": True, "errors": [], "warnings": []},
            final_status=InvoiceStatus.NEEDS_REVIEW,
        )
        assert not landed
        # Invoice should still be APPROVED, not overwritten
        assert (await repo.get_by_document_id("DOC-W7")).status == InvoiceStatus.APPROVED
