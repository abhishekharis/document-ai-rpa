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
    async def test_requeue_interrupted_documents(self, repo, job_queue):

        for doc_id, st in (("DOC-W3", InvoiceStatus.PROCESSING), ("DOC-W4", InvoiceStatus.APPROVED)):
            await repo.create(Invoice(
                document_id=doc_id, original_filename="a.pdf", status=st,
                vendor=Vendor(name=""), invoice_number="", invoice_date="",
                extraction=Extraction(overall_confidence=0.0, fields={}, raw_ocr_text="", page_count=0),
            ))
        assert await worker.requeue_interrupted(repo, job_queue) == 1
        assert await job_queue.dequeue(timeout=1) == "DOC-W3"
