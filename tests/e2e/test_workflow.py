"""
End-to-end test for the invoice processing workflow.

This test simulates the complete workflow:
1. Upload an invoice
2. Wait for processing (OCR + extraction + validation)
3. Check the invoice status
4. If needs review, approve it
5. Verify it enters RPA queue
6. Simulate RPA processing
7. Verify RPA completion

Note: This test requires:
- MongoDB running
- Backend API running
- A sample invoice file
"""

import pytest
import time
import httpx
from pathlib import Path


class TestE2EWorkflow:
    """End-to-end workflow tests."""
    
    @pytest.fixture
    def api_base_url(self):
        return "http://127.0.0.1:8000"
    
    @pytest.fixture
    def sample_invoice_path(self):
        """Path to a sample invoice file."""
        # This should be updated to point to an actual test invoice
        return Path(__file__).parent.parent.parent / "sample_documents" / "normal" / "test_invoice.pdf"
    
    def test_health_check(self, api_base_url):
        """Test that the API is healthy."""
        response = httpx.get(f"{api_base_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["mongodb_connected"] is True
    
    def test_upload_and_process_invoice(self, api_base_url, sample_invoice_path):
        """Test uploading and processing an invoice."""
        # Skip if sample file doesn't exist
        if not sample_invoice_path.exists():
            pytest.skip(f"Sample invoice not found at {sample_invoice_path}")
        
        # Upload invoice
        with open(sample_invoice_path, "rb") as f:
            files = {"file": (sample_invoice_path.name, f, "application/pdf")}
            response = httpx.post(f"{api_base_url}/api/invoices/upload", files=files)
        
        assert response.status_code in [200, 201]
        upload_data = response.json()
        document_id = upload_data["document_id"]
        
        # Wait for processing (OCR can take time)
        max_wait = 30  # seconds
        for i in range(max_wait):
            response = httpx.get(f"{api_base_url}/api/invoices/{document_id}")
            assert response.status_code == 200
            invoice_data = response.json()
            
            status = invoice_data["status"]
            if status not in ["UPLOADED", "PROCESSING"]:
                break
            time.sleep(1)
        
        # Verify invoice was processed
        assert status in ["PROCESSED", "NEEDS_REVIEW", "APPROVED", "REJECTED", "ERROR"]
        
        # Check extraction results
        assert "extraction" in invoice_data
        assert "overall_confidence" in invoice_data["extraction"]
        
        # Check validation results
        assert "validation" in invoice_data
        assert "is_valid" in invoice_data["validation"]
        
        return document_id, invoice_data
    
    def test_approval_workflow(self, api_base_url, sample_invoice_path):
        """Test the approval workflow for invoices that need review."""
        # Upload and get invoice
        document_id, invoice_data = self.test_upload_and_process_invoice(api_base_url, sample_invoice_path)
        
        # If invoice needs review, approve it
        if invoice_data["status"] == "NEEDS_REVIEW":
            approval_data = {
                "document_id": document_id,
                "reviewed_by": "E2E Test User",
                "notes": "Approved during E2E test"
            }
            response = httpx.post(f"{api_base_url}/api/invoices/{document_id}/approve", json=approval_data)
            assert response.status_code == 200
            
            # Verify status changed
            response = httpx.get(f"{api_base_url}/api/invoices/{document_id}")
            updated_invoice = response.json()
            assert updated_invoice["status"] == "APPROVED"
    
    def test_rpa_queue_workflow(self, api_base_url):
        """Test the RPA queue and processing workflow."""
        # Get RPA queue
        response = httpx.get(f"{api_base_url}/api/rpa/queue")
        assert response.status_code == 200
        queue_data = response.json()
        
        # If there are approved invoices, test RPA processing
        if queue_data["count"] > 0:
            invoice = queue_data["invoices"][0]
            document_id = invoice["document_id"]
            
            # Start RPA processing
            start_data = {
                "document_id": document_id,
                "api_key": "change-me"  # Use the default API key from .env
            }
            response = httpx.post(f"{api_base_url}/api/rpa/{document_id}/start", json=start_data)
            assert response.status_code == 200
            
            # Verify status changed to RPA_PROCESSING
            response = httpx.get(f"{api_base_url}/api/invoices/{document_id}")
            invoice_data = response.json()
            assert invoice_data["status"] == "RPA_PROCESSING"
            
            # Simulate RPA completion
            result_data = {
                "document_id": document_id,
                "api_key": "change-me",
                "success": True,
                "accounting_record_id": "ACC-E2E-TEST",
                "message": "E2E test RPA completion"
            }
            response = httpx.post(f"{api_base_url}/api/rpa/{document_id}/result", json=result_data)
            assert response.status_code == 200
            
            # Verify status changed to RPA_COMPLETED
            response = httpx.get(f"{api_base_url}/api/invoices/{document_id}")
            final_invoice = response.json()
            assert final_invoice["status"] == "RPA_COMPLETED"
    
    def test_complete_workflow(self, api_base_url, sample_invoice_path):
        """Test the complete workflow from upload to RPA completion."""
        # Upload and process
        document_id, invoice_data = self.test_upload_and_process_invoice(api_base_url, sample_invoice_path)
        
        # Approve if needed
        if invoice_data["status"] == "NEEDS_REVIEW":
            approval_data = {
                "document_id": document_id,
                "reviewed_by": "E2E Test User",
                "notes": "Approved during complete E2E test"
            }
            httpx.post(f"{api_base_url}/api/invoices/{document_id}/approve", json=approval_data)
        
        # Start RPA
        start_data = {
            "document_id": document_id,
            "api_key": "change-me"
        }
        httpx.post(f"{api_base_url}/api/rpa/{document_id}/start", json=start_data)
        
        # Complete RPA
        result_data = {
            "document_id": document_id,
            "api_key": "change-me",
            "success": True,
            "accounting_record_id": "ACC-E2E-COMPLETE",
            "message": "Complete E2E test successful"
        }
        httpx.post(f"{api_base_url}/api/rpa/{document_id}/result", json=result_data)
        
        # Verify final state
        response = httpx.get(f"{api_base_url}/api/invoices/{document_id}")
        final_invoice = response.json()
        assert final_invoice["status"] == "RPA_COMPLETED"
        assert final_invoice["rpa"]["status"] == "COMPLETED"


if __name__ == "__main__":
    """Run E2E tests manually."""
    import sys
    
    # This allows running the test directly: python tests/e2e/test_workflow.py
    pytest.main([__file__, "-v", "-s"])
