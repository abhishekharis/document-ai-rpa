import logging

from app.models.audit_log import AuditLog
from app.models.invoice import InvoiceStatus, InvoiceUpdate, Vendor
from app.services.processing_service import ProcessingService
from app.services.repository import InvoiceRepository

logger = logging.getLogger(__name__)


async def queue_approved_invoice(repo: InvoiceRepository, document_id: str) -> bool:
    """Queue an APPROVED invoice for RPA and log it. Returns False if it was no longer APPROVED."""
    if not await repo.queue_for_rpa(document_id):
        return False
    await repo.create_audit_log(AuditLog(
        document_id=document_id,
        event="RPA_QUEUED",
        old_status=InvoiceStatus.APPROVED.value,
        new_status=InvoiceStatus.RPA_QUEUED.value,
        message="Document queued for RPA processing"
    ))
    return True


async def run_processing(
    repo: InvoiceRepository,
    processing_service: ProcessingService,
    document_id: str,
    content: bytes,
    filename: str
) -> InvoiceStatus:
    """Run the processing pipeline for an invoice in PROCESSING status and return its resulting status."""
    try:
        processing_result = await processing_service.process_invoice(
            content,
            filename,
            document_id
        )
        
        # Update invoice with processing results
        await repo.update(document_id, InvoiceUpdate(
            vendor=Vendor(**processing_result['vendor']),
            invoice_number=processing_result['invoice_number'],
            invoice_date=processing_result['invoice_date'],
            due_date=processing_result['due_date'],
            currency=processing_result['currency'],
            subtotal=processing_result['subtotal'],
            tax=processing_result['tax'],
            total=processing_result['total'],
            line_items=[]
        ))
        
        # Update extraction results
        await repo.update_extraction(document_id, processing_result['extraction'])
        
        # Update validation results
        await repo.update_validation(document_id, processing_result['validation'])
        
        # Update status based on processing result
        final_status = InvoiceStatus(processing_result['status'])
        await repo.update_status(document_id, final_status, InvoiceStatus.PROCESSING)
        
        # Log processing complete
        await repo.create_audit_log(AuditLog(
            document_id=document_id,
            event="PROCESSING_COMPLETE",
            message=f"Document processed successfully - status: {final_status.value}"
        ))
        
        # If processing succeeded and document is PROCESSED, automatically approve and queue for RPA
        if final_status == InvoiceStatus.PROCESSED:
            # Transition to APPROVED
            await repo.update_status(document_id, InvoiceStatus.APPROVED, InvoiceStatus.PROCESSED)
            await repo.create_audit_log(AuditLog(
                document_id=document_id,
                event="AUTO_APPROVED",
                message="Document automatically approved after successful processing"
            ))
            
            if await queue_approved_invoice(repo, document_id):
                return InvoiceStatus.RPA_QUEUED
            return InvoiceStatus.APPROVED
        
        return final_status
        
    except Exception as e:
        # Update status to ERROR
        await repo.update_status(document_id, InvoiceStatus.ERROR, InvoiceStatus.PROCESSING)
        
        # Log error
        await repo.create_audit_log(AuditLog(
            document_id=document_id,
            event="PROCESSING_ERROR",
            message=f"Processing failed: {str(e)}"
        ))
        
        return InvoiceStatus.ERROR
