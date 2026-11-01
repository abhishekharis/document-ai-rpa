from io import BytesIO

import pytest

import app.main as main
from app.models.invoice import Extraction, Invoice, InvoiceStatus, Review, Vendor
from tests.conftest import TEST_RPA_API_KEY


def seed_invoice(mongo, document_id="DOC-TEST0001", status=InvoiceStatus.NEEDS_REVIEW):
    invoice = Invoice(
        document_id=document_id,
        original_filename="invoice.pdf",
        status=status,
        vendor=Vendor(name="Acme Supplies"),
        invoice_number="INV-1001",
        invoice_date="2026-01-05",
        subtotal=100.0,
        tax=8.0,
        total=108.0,
        extraction=Extraction(overall_confidence=0.6),
        review=Review(required=True),
    )
    doc = invoice.model_dump()
    doc["status"] = status.value
    mongo.invoices.insert_one(doc)
    return document_id


def approve(client, document_id, reviewer="Jane Reviewer"):
    return client.post(
        f"/api/invoices/{document_id}/approve",
        json={"document_id": document_id, "reviewed_by": reviewer, "notes": "Checked totals"},
    )


def audit_events(mongo, document_id):
    return [log["event"] for log in mongo.audit_logs.find({"document_id": document_id}).sort("timestamp", 1)]


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "mongodb_connected" in data
        assert "timestamp" in data


class TestInvoiceUpload:
    def test_upload_invalid_file_type(self, client):
        files = {"file": ("test.docx", BytesIO(b"fake docx"), "application/docx")}
        response = client.post("/api/invoices/upload", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_upload_oversized_file(self, client):
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("test.pdf", BytesIO(large_content), "application/pdf")}
        response = client.post("/api/invoices/upload", files=files)
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()
    
    def test_upload_no_file(self, client):
        response = client.post("/api/invoices/upload")
        assert response.status_code == 422

    def test_auto_approved_upload_is_queued_with_rpa_metadata(self, client, mongo, monkeypatch, tmp_path):
        class FakeProcessingService:
            async def process_invoice(self, content, filename, document_id):
                return {
                    "vendor": {"name": "Acme Supplies"},
                    "invoice_number": "INV-2001",
                    "invoice_date": "2026-01-05",
                    "due_date": None,
                    "currency": "USD",
                    "subtotal": 100.0,
                    "tax": 8.0,
                    "total": 108.0,
                    "extraction": {"overall_confidence": 0.95, "fields": {}, "raw_ocr_text": "", "page_count": 1},
                    "validation": {"is_valid": True, "errors": [], "warnings": []},
                    "status": "PROCESSED",
                }

        monkeypatch.setattr(main, "ProcessingService", FakeProcessingService)
        monkeypatch.setattr(main.file_storage, "documents_path", tmp_path)

        files = {"file": ("invoice.pdf", BytesIO(b"%PDF-1.4 test"), "application/pdf")}
        response = client.post("/api/invoices/upload", files=files)

        assert response.status_code == 201
        assert response.json()["status"] == "RPA_QUEUED"
        document_id = response.json()["document_id"]
        doc = mongo.invoices.find_one({"document_id": document_id})
        assert doc["rpa"]["status"] == "QUEUED"
        assert doc["rpa"]["eligible"] is True
        assert doc["rpa"]["queued_at"] is not None
        assert audit_events(mongo, document_id) == ["UPLOAD", "PROCESSING_COMPLETE", "AUTO_APPROVED", "RPA_QUEUED"]


class TestInvoiceRetrieval:
    def test_get_all_invoices(self, client):
        response = client.get("/api/invoices")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert "count" in data
        assert isinstance(data["invoices"], list)
    
    def test_get_invoices_with_status_filter(self, client):
        response = client.get("/api/invoices?status_filter=APPROVED")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
    
    def test_get_invoices_invalid_status(self, client):
        response = client.get("/api/invoices?status_filter=INVALID_STATUS")
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
    
    def test_get_invoice_by_id_not_found(self, client):
        response = client.get("/api/invoices/NONEXISTENT-ID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestInvoiceUpdate:
    def test_update_invoice_not_found(self, client):
        update_data = {
            "vendor": {"name": "Test Vendor"},
            "invoice_number": "INV-001"
        }
        response = client.put("/api/invoices/NONEXISTENT-ID", json=update_data)
        assert response.status_code == 404


class TestInvoiceApproval:
    def test_approve_invoice_not_found(self, client):
        response = approve(client, "NONEXISTENT-ID")
        assert response.status_code == 404
    
    def test_reject_invoice_not_found(self, client):
        rejection_data = {
            "document_id": "NONEXISTENT-ID",
            "reviewed_by": "Test User",
            "reason": "Test rejection"
        }
        response = client.post("/api/invoices/NONEXISTENT-ID/reject", json=rejection_data)
        assert response.status_code == 404

    def test_manual_approval_queues_invoice_for_rpa(self, client, mongo):
        document_id = seed_invoice(mongo)

        response = approve(client, document_id)

        assert response.status_code == 200
        assert response.json()["status"] == "RPA_QUEUED"
        doc = mongo.invoices.find_one({"document_id": document_id})
        assert doc["status"] == "RPA_QUEUED"
        assert doc["rpa"]["eligible"] is True
        assert doc["rpa"]["status"] == "QUEUED"
        assert doc["rpa"]["queued_at"] is not None
        assert doc["review"]["reviewed_by"] == "Jane Reviewer"
        assert doc["review"]["reviewed_at"] is not None
        assert doc["review"]["required"] is False
        assert audit_events(mongo, document_id) == ["APPROVED", "RPA_QUEUED"]
        approved_log = mongo.audit_logs.find_one({"document_id": document_id, "event": "APPROVED"})
        assert approved_log["actor"] == "Jane Reviewer"
        assert approved_log["message"] == "Checked totals"

        queue = client.get("/api/rpa/queue").json()
        assert [inv["document_id"] for inv in queue["invoices"]] == [document_id]

    def test_duplicate_approval_does_not_queue_twice(self, client, mongo):
        document_id = seed_invoice(mongo)
        assert approve(client, document_id).status_code == 200

        response = approve(client, document_id)

        assert response.status_code == 400
        assert client.get("/api/rpa/queue").json()["count"] == 1
        assert audit_events(mongo, document_id).count("RPA_QUEUED") == 1

    def test_approving_an_unqueued_approved_invoice_queues_it(self, client, mongo):
        document_id = seed_invoice(mongo, status=InvoiceStatus.APPROVED)

        response = approve(client, document_id)

        assert response.status_code == 200
        assert response.json()["status"] == "RPA_QUEUED"
        assert audit_events(mongo, document_id) == ["RPA_QUEUED"]

    def test_rejected_invoice_cannot_be_approved(self, client, mongo):
        document_id = seed_invoice(mongo, status=InvoiceStatus.REJECTED)

        response = approve(client, document_id)

        assert response.status_code == 400
        assert mongo.invoices.find_one({"document_id": document_id})["status"] == "REJECTED"
        assert client.get("/api/rpa/queue").json()["count"] == 0


class TestRPAEndpoints:
    def test_get_rpa_queue(self, client):
        response = client.get("/api/rpa/queue")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert "count" in data
    
    def test_start_rpa_invalid_api_key(self, client):
        start_data = {
            "document_id": "TEST-ID",
            "api_key": "wrong-key"
        }
        response = client.post("/api/rpa/TEST-ID/start", json=start_data)
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_rpa_result_invalid_api_key(self, client):
        result_data = {
            "document_id": "TEST-ID",
            "api_key": "wrong-key",
            "success": True
        }
        response = client.post("/api/rpa/TEST-ID/result", json=result_data)
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_manual_approval_through_rpa_completion(self, client, mongo):
        document_id = seed_invoice(mongo)
        assert approve(client, document_id).json()["status"] == "RPA_QUEUED"

        start = client.post(
            f"/api/rpa/{document_id}/start",
            json={"document_id": document_id, "api_key": TEST_RPA_API_KEY},
        )
        assert start.status_code == 200
        assert start.json()["status"] == "RPA_PROCESSING"
        assert client.get("/api/rpa/queue").json()["count"] == 0

        result = client.post(
            f"/api/rpa/{document_id}/result",
            json={
                "document_id": document_id,
                "api_key": TEST_RPA_API_KEY,
                "success": True,
                "accounting_record_id": "ACC-TEST",
                "message": "Entered as ACC-TEST",
            },
        )
        assert result.status_code == 200

        doc = mongo.invoices.find_one({"document_id": document_id})
        assert doc["status"] == "RPA_COMPLETED"
        assert doc["rpa"]["status"] == "COMPLETED"
        assert doc["rpa"]["job_id"] == f"JOB-{document_id}"
        assert doc["rpa"]["accounting_record_id"] == "ACC-TEST"
        assert client.get(f"/api/invoices/{document_id}").json()["rpa"]["accounting_record_id"] == "ACC-TEST"
        assert audit_events(mongo, document_id) == ["APPROVED", "RPA_QUEUED", "RPA_STARTED", "RPA_COMPLETED"]


class TestRejectionWorkflow:
    def test_reject_invoice_success(self, client, mongo):
        document_id = seed_invoice(mongo, status=InvoiceStatus.NEEDS_REVIEW)
        rejection_data = {
            "document_id": document_id,
            "reviewed_by": "Senior Reviewer",
            "reason": "Amount mismatch on line items",
        }
        response = client.post(f"/api/invoices/{document_id}/reject", json=rejection_data)
        assert response.status_code == 200
        assert response.json()["status"] == "REJECTED"

        doc = mongo.invoices.find_one({"document_id": document_id})
        assert doc["status"] == "REJECTED"

        events = audit_events(mongo, document_id)
        assert "REJECTED" in events
        reject_log = mongo.audit_logs.find_one({"document_id": document_id, "event": "REJECTED"})
        assert reject_log["actor"] == "Senior Reviewer"
        assert reject_log["message"] == "Amount mismatch on line items"

        # Rejected invoices must not be in RPA queue
        queue = client.get("/api/rpa/queue").json()
        assert document_id not in [inv["document_id"] for inv in queue["invoices"]]

    def test_cannot_reject_approved_or_completed_invoice(self, client, mongo):
        doc_approved = seed_invoice(mongo, document_id="DOC-APP01", status=InvoiceStatus.APPROVED)
        res1 = client.post(
            f"/api/invoices/{doc_approved}/reject",
            json={"document_id": doc_approved, "reviewed_by": "Reviewer", "reason": "Too late"},
        )
        assert res1.status_code == 400
        assert "Invalid transition" in res1.json()["detail"]

        doc_completed = seed_invoice(mongo, document_id="DOC-COMP01", status=InvoiceStatus.RPA_COMPLETED)
        res2 = client.post(
            f"/api/invoices/{doc_completed}/reject",
            json={"document_id": doc_completed, "reviewed_by": "Reviewer", "reason": "Already done"},
        )
        assert res2.status_code == 400


class TestBulkDeleteWorkflow:
    def test_bulk_delete_eligible_invoices_removes_docs_and_files_keeps_audit(self, client, mongo, tmp_path, monkeypatch):
        monkeypatch.setattr(main.file_storage, "documents_path", tmp_path)

        doc1 = seed_invoice(mongo, document_id="DOC-DEL01", status=InvoiceStatus.REJECTED)
        doc2 = seed_invoice(mongo, document_id="DOC-DEL02", status=InvoiceStatus.APPROVED)

        # Save files
        main.file_storage.save_original(doc1, "invoice1.pdf", b"%PDF-1.4 file1")
        main.file_storage.save_original(doc2, "invoice2.pdf", b"%PDF-1.4 file2")
        assert main.file_storage.get_original_file(doc1) is not None
        assert main.file_storage.get_original_file(doc2) is not None

        response = client.post("/api/invoices/bulk-delete", json={"document_ids": [doc1, doc2]})
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == 2
        assert data["failed"] == 0

        # MongoDB records removed
        assert mongo.invoices.find_one({"document_id": doc1}) is None
        assert mongo.invoices.find_one({"document_id": doc2}) is None

        # Files on disk removed
        assert main.file_storage.get_original_file(doc1) is None
        assert main.file_storage.get_original_file(doc2) is None

        # Audit logs preserved
        assert "DOCUMENT_DELETED" in audit_events(mongo, doc1)
        assert "DOCUMENT_DELETED" in audit_events(mongo, doc2)

    def test_bulk_delete_blocked_when_processing(self, client, mongo, tmp_path, monkeypatch):
        monkeypatch.setattr(main.file_storage, "documents_path", tmp_path)

        doc_processing = seed_invoice(mongo, document_id="DOC-PROC01", status=InvoiceStatus.PROCESSING)
        main.file_storage.save_original(doc_processing, "proc.pdf", b"%PDF-1.4 proc")

        response = client.post("/api/invoices/bulk-delete", json={"document_ids": [doc_processing]})
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == 0
        assert data["failed"] == 1
        assert "Cannot delete while status is PROCESSING" in data["results"][0]["message"]

        # Invoice and file preserved
        assert mongo.invoices.find_one({"document_id": doc_processing}) is not None
        assert main.file_storage.get_original_file(doc_processing) is not None

    def test_bulk_delete_nonexistent(self, client, mongo):
        response = client.post("/api/invoices/bulk-delete", json={"document_ids": ["DOC-NONEXISTENT"]})
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == 0
        assert data["failed"] == 1
        assert "Document not found" in data["results"][0]["message"]


class TestBulkReprocessWorkflow:
    def test_bulk_reprocess_eligible_invoice_success(self, client, mongo, tmp_path, monkeypatch):
        monkeypatch.setattr(main.file_storage, "documents_path", tmp_path)

        class FakeProcessingService:
            async def process_invoice(self, content, filename, document_id):
                return {
                    "vendor": {"name": "Reprocessed Vendor Inc"},
                    "invoice_number": "INV-REPROC-99",
                    "invoice_date": "2026-03-01",
                    "due_date": None,
                    "currency": "USD",
                    "subtotal": 300.0,
                    "tax": 24.0,
                    "total": 324.0,
                    "extraction": {"overall_confidence": 0.98, "fields": {}, "raw_ocr_text": "", "page_count": 1},
                    "validation": {"is_valid": True, "errors": [], "warnings": []},
                    "status": "PROCESSED",
                }

        monkeypatch.setattr(main, "ProcessingService", FakeProcessingService)

        doc_id = seed_invoice(mongo, document_id="DOC-REPROC01", status=InvoiceStatus.REJECTED)
        main.file_storage.save_original(doc_id, "invoice.pdf", b"%PDF-1.4 reprocess content")

        response = client.post("/api/invoices/bulk-reprocess", json={"document_ids": [doc_id]})
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == 1
        assert data["failed"] == 0
        assert data["results"][0]["status"] == "RPA_QUEUED"
        assert "Reprocessed" in data["results"][0]["message"]

        # Check document in Mongo
        doc = mongo.invoices.find_one({"document_id": doc_id})
        assert doc["status"] == "RPA_QUEUED"
        assert doc["vendor"]["name"] == "Reprocessed Vendor Inc"
        assert doc["invoice_number"] == "INV-REPROC-99"

        # Check audit trail
        events = audit_events(mongo, doc_id)
        assert "REPROCESS_STARTED" in events
        assert "PROCESSING_COMPLETE" in events
        assert "AUTO_APPROVED" in events
        assert "RPA_QUEUED" in events

        # Appears in RPA queue
        queue = client.get("/api/rpa/queue").json()
        assert doc_id in [inv["document_id"] for inv in queue["invoices"]]

    def test_bulk_reprocess_ineligible_status_blocked(self, client, mongo, tmp_path, monkeypatch):
        monkeypatch.setattr(main.file_storage, "documents_path", tmp_path)

        doc_completed = seed_invoice(mongo, document_id="DOC-COMP02", status=InvoiceStatus.RPA_COMPLETED)
        main.file_storage.save_original(doc_completed, "comp.pdf", b"%PDF-1.4 comp")

        response = client.post("/api/invoices/bulk-reprocess", json={"document_ids": [doc_completed]})
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == 0
        assert data["failed"] == 1
        assert "Not eligible for reprocessing" in data["results"][0]["message"]

        # Status unchanged
        doc = mongo.invoices.find_one({"document_id": doc_completed})
        assert doc["status"] == "RPA_COMPLETED"

    def test_bulk_reprocess_missing_original_file(self, client, mongo, tmp_path, monkeypatch):
        monkeypatch.setattr(main.file_storage, "documents_path", tmp_path)

        doc_nofile = seed_invoice(mongo, document_id="DOC-NOFILE01", status=InvoiceStatus.REJECTED)

        response = client.post("/api/invoices/bulk-reprocess", json={"document_ids": [doc_nofile]})
        assert response.status_code == 200
        data = response.json()
        assert data["succeeded"] == 0
        assert data["failed"] == 1
        assert "Original file not found" in data["results"][0]["message"]

        doc = mongo.invoices.find_one({"document_id": doc_nofile})
        assert doc["status"] == "REJECTED"


class TestRateLimiting:
    def test_upload_rate_limit_returns_429(self, client, monkeypatch):
        from app.main import upload_limiter
        monkeypatch.setattr(upload_limiter, "max_requests", 2)
        files = {"file": ("bad.txt", b"x", "text/plain")}
        statuses = [client.post("/api/invoices/upload", files=files).status_code for _ in range(3)]
        assert statuses == [400, 400, 429]
