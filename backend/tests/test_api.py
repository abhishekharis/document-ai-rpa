import pytest
from fastapi.testclient import TestClient
from app.main import app
from io import BytesIO
import json


client = TestClient(app)


@pytest.fixture
def test_file():
    """Create a test PDF file."""
    # In a real test, you'd use an actual PDF file
    # For now, we'll create a dummy file
    file_content = b"%PDF-1.4\n%fake pdf for testing"
    return BytesIO(file_content)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "mongodb_connected" in data
        assert "timestamp" in data


class TestInvoiceUpload:
    def test_upload_invalid_file_type(self):
        files = {"file": ("test.docx", BytesIO(b"fake docx"), "application/docx")}
        response = client.post("/api/invoices/upload", files=files)
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_upload_oversized_file(self):
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)
        files = {"file": ("test.pdf", BytesIO(large_content), "application/pdf")}
        response = client.post("/api/invoices/upload", files=files)
        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()
    
    def test_upload_no_file(self):
        response = client.post("/api/invoices/upload")
        assert response.status_code == 422  # Unprocessable Entity


class TestInvoiceRetrieval:
    def test_get_all_invoices(self):
        response = client.get("/api/invoices")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert "count" in data
        assert isinstance(data["invoices"], list)
    
    def test_get_invoices_with_status_filter(self):
        response = client.get("/api/invoices?status_filter=APPROVED")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
    
    def test_get_invoices_invalid_status(self):
        response = client.get("/api/invoices?status_filter=INVALID_STATUS")
        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]
    
    def test_get_invoice_by_id_not_found(self):
        response = client.get("/api/invoices/NONEXISTENT-ID")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestInvoiceUpdate:
    def test_update_invoice_not_found(self):
        update_data = {
            "vendor": {"name": "Test Vendor"},
            "invoice_number": "INV-001"
        }
        response = client.put("/api/invoices/NONEXISTENT-ID", json=update_data)
        assert response.status_code == 404


class TestInvoiceApproval:
    def test_approve_invoice_not_found(self):
        approval_data = {
            "document_id": "NONEXISTENT-ID",
            "reviewed_by": "Test User",
            "notes": "Test approval"
        }
        response = client.post("/api/invoices/NONEXISTENT-ID/approve", json=approval_data)
        assert response.status_code == 404
    
    def test_reject_invoice_not_found(self):
        rejection_data = {
            "document_id": "NONEXISTENT-ID",
            "reviewed_by": "Test User",
            "reason": "Test rejection"
        }
        response = client.post("/api/invoices/NONEXISTENT-ID/reject", json=rejection_data)
        assert response.status_code == 404


class TestRPAEndpoints:
    def test_get_rpa_queue(self):
        response = client.get("/api/rpa/queue")
        assert response.status_code == 200
        data = response.json()
        assert "invoices" in data
        assert "count" in data
    
    def test_start_rpa_invalid_api_key(self):
        start_data = {
            "document_id": "TEST-ID",
            "api_key": "wrong-key"
        }
        response = client.post("/api/rpa/TEST-ID/start", json=start_data)
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_rpa_result_invalid_api_key(self):
        result_data = {
            "document_id": "TEST-ID",
            "api_key": "wrong-key",
            "success": True
        }
        response = client.post("/api/rpa/TEST-ID/result", json=result_data)
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
