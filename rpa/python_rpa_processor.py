#!/usr/bin/env python3
"""
Python-based RPA processor for macOS
Polls the invoice queue and processes invoices into the accounting application
"""

import requests
import time
import logging
from typing import Optional, Dict, Any
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RPAProcessor:
    """Python RPA processor for invoice automation"""
    
    def __init__(self, api_base_url: str, api_key: str, accounting_app_url: str):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.accounting_app_url = accounting_app_url
        self.api_session = requests.Session()
        self.api_session.headers.update({'Content-Type': 'application/json'})
        self.accounting_session = requests.Session()
    
    def get_rpa_queue(self) -> Dict[str, Any]:
        """Get invoices from RPA queue"""
        try:
            response = self.api_session.get(f"{self.api_base_url}/api/rpa/queue")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get RPA queue: {e}")
            return {"invoices": [], "count": 0}
    
    def start_rpa_processing(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Start RPA processing for an invoice"""
        try:
            payload = {
                "document_id": document_id,
                "api_key": self.api_key
            }
            response = self.api_session.post(
                f"{self.api_base_url}/api/rpa/{document_id}/start",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to start RPA processing for {document_id}: {e}")
            return None
    
    def submit_to_accounting_app(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Submit invoice to accounting application"""
        try:
            # Prepare JSON data for accounting app
            json_data = {
                'vendor': invoice_data.get('vendor', {}).get('name', ''),
                'invoice_number': invoice_data.get('invoice_number', ''),
                'invoice_date': invoice_data.get('invoice_date', ''),
                'due_date': invoice_data.get('due_date', ''),
                'currency': invoice_data.get('currency', 'USD'),
                'subtotal': invoice_data.get('subtotal'),
                'tax': invoice_data.get('tax'),
                'total': invoice_data.get('total'),
                'line_items': ''  # Simplified - line items not fully implemented
            }
            
            # Submit to accounting app as JSON
            response = self.accounting_session.post(
                f"{self.accounting_app_url}/new-invoice",
                json=json_data
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    accounting_id = result.get('accounting_id')
                    logger.info(f"Successfully submitted to accounting app. ID: {accounting_id}")
                    return accounting_id
                else:
                    logger.error(f"Accounting app returned error: {result.get('error')}")
                    return None
            else:
                logger.error(f"Failed to submit to accounting app: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to submit to accounting app: {e}")
            return None
    
    def report_rpa_result(self, document_id: str, success: bool, 
                         accounting_record_id: Optional[str] = None, 
                         message: str = "") -> bool:
        """Report RPA processing result"""
        try:
            payload = {
                "document_id": document_id,
                "api_key": self.api_key,
                "success": success,
                "accounting_record_id": accounting_record_id,
                "message": message
            }
            response = self.api_session.post(
                f"{self.api_base_url}/api/rpa/{document_id}/result",
                json=payload
            )
            response.raise_for_status()
            logger.info(f"Successfully reported RPA result for {document_id}")
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to report RPA result for {document_id}: {e}")
            return False
    
    def process_invoice(self, document_id: str, invoice_data: Dict[str, Any]) -> bool:
        """Process a single invoice through the complete workflow"""
        logger.info(f"Processing invoice: {document_id}")
        
        # Step 1: Start RPA processing
        logger.info(f"Starting RPA processing for {document_id}")
        start_result = self.start_rpa_processing(document_id)
        if not start_result:
            logger.error(f"Failed to start RPA processing for {document_id}")
            self.report_rpa_result(document_id, False, message="Failed to start RPA processing")
            return False
        
        # Step 2: Submit to accounting app
        logger.info(f"Submitting invoice {document_id} to accounting app")
        accounting_id = self.submit_to_accounting_app(invoice_data)
        
        if accounting_id:
            # Step 3: Report success
            logger.info(f"Reporting success for {document_id}")
            success = self.report_rpa_result(
                document_id, 
                True, 
                accounting_record_id=accounting_id,
                message=f"Invoice successfully entered into accounting system. ID: {accounting_id}"
            )
            return success
        else:
            # Step 3: Report failure
            logger.error(f"Reporting failure for {document_id}")
            self.report_rpa_result(
                document_id, 
                False, 
                message="Failed to submit invoice to accounting application"
            )
            return False
    
    def run(self, poll_interval: int = 30):
        """Main processing loop"""
        logger.info("Starting RPA processor")
        logger.info(f"API Base URL: {self.api_base_url}")
        logger.info(f"Accounting App URL: {self.accounting_app_url}")
        logger.info(f"Poll interval: {poll_interval} seconds")
        
        while True:
            try:
                # Get queue
                queue_data = self.get_rpa_queue()
                invoice_count = queue_data.get("count", 0)
                
                if invoice_count > 0:
                    logger.info(f"Found {invoice_count} invoice(s) in queue")
                    
                    # Process first invoice
                    invoice = queue_data["invoices"][0]
                    document_id = invoice["document_id"]
                    
                    self.process_invoice(document_id, invoice)
                else:
                    logger.info("No invoices in queue, waiting...")
                
                # Wait before next poll
                time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down RPA processor")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(poll_interval)


def main():
    """Main entry point"""
    import os
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load environment variables - try parent directory first, then current directory
    env_paths = [
        Path(__file__).parent.parent / ".env",  # Project root .env
        Path(__file__).parent / ".env"  # RPA directory .env
    ]
    load_dotenv(env_paths[0]) if env_paths[0].exists() else None
    load_dotenv(env_paths[1]) if env_paths[1].exists() else None
    
    # Configuration
    api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    api_key = os.getenv("RPA_API_KEY", "change-me")
    accounting_app_url = os.getenv("ACCOUNTING_APP_URL", "http://localhost:3001")
    poll_interval = int(os.getenv("RPA_POLL_INTERVAL", "30"))
    
    # Create and run processor
    processor = RPAProcessor(api_base_url, api_key, accounting_app_url)
    processor.run(poll_interval)


if __name__ == "__main__":
    main()