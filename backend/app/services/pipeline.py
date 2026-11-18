import logging
from typing import Optional

from app.models.audit_log import AuditLog
from app.models.invoice import InvoiceStatus
from app.services.processing_service import ProcessingService
from app.services.repository import InvoiceRepository
from app.utils.duplicates import duplicate_reason

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


async def find_duplicate(repo: InvoiceRepository, document_id: str, processing_result: dict):
    """Return (document_id, reason) of an earlier invoice this one duplicates, or None."""
    new = {
        "vendor_name": processing_result["vendor"].get("name"),
        "invoice_number": processing_result["invoice_number"],
        "invoice_date": processing_result["invoice_date"],
        "total": processing_result["total"],
    }
    for candidate in await repo.find_duplicate_candidates(document_id, new["invoice_number"], new["total"]):
        existing = {
            "vendor_name": candidate.get("vendor", {}).get("name"),
            "invoice_number": candidate.get("invoice_number"),
            "invoice_date": candidate.get("invoice_date"),
            "total": candidate.get("total"),
        }
        reason = duplicate_reason(new, existing)
        if reason:
            return candidate["document_id"], reason
    return None


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
        
        # Flag likely duplicates so they are reviewed instead of auto-approved
        final_status = InvoiceStatus(processing_result['status'])
        duplicate = await find_duplicate(repo, document_id, processing_result)
        if duplicate:
            original_id, reason = duplicate
            validation = processing_result['validation']
            validation['warnings'] = validation.get('warnings', []) + [
                f"Possible duplicate of {original_id} ({reason})"
            ]
            validation['duplicate_of'] = original_id
            if final_status == InvoiceStatus.PROCESSED:
                final_status = InvoiceStatus.NEEDS_REVIEW

        # Build the flat field map for $set
        invoice_fields = {
            "vendor": processing_result['vendor'],
            "invoice_number": processing_result['invoice_number'],
            "invoice_date": processing_result['invoice_date'],
            "due_date": processing_result['due_date'],
            "currency": processing_result['currency'],
            "subtotal": processing_result['subtotal'],
            "tax": processing_result['tax'],
            "total": processing_result['total'],
            "line_items": [],
        }

        if processing_token:
            # Guarded path: one atomic write; if the claim was stolen, bail out silently
            landed = await repo.finish_ocr_job(
                document_id=document_id,
                token=processing_token,
                invoice_fields=invoice_fields,
                extraction=processing_result['extraction'],
                validation=processing_result['validation'],
                final_status=final_status,
            )
            if not landed:
                logger.warning(
                    "OCR result for %s discarded: processing_token no longer matches (superseded or status changed)",
                    document_id,
                )
                invoice = await repo.get_by_document_id(document_id)
                return invoice.status if invoice else InvoiceStatus.ERROR
        else:
            # Unguarded path (inline, no token): keep legacy behaviour
            from app.models.invoice import InvoiceUpdate, Vendor
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
            await repo.update_extraction(document_id, processing_result['extraction'])
            await repo.update_validation(document_id, processing_result['validation'])
            await repo.update_status(document_id, final_status, InvoiceStatus.PROCESSING)

        if duplicate:
            original_id, reason = duplicate
            await repo.create_audit_log(AuditLog(
                document_id=document_id,
                event="DUPLICATE_DETECTED",
                message=f"Possible duplicate of {original_id} ({reason})"
            ))

        await repo.create_audit_log(AuditLog(
            document_id=document_id,
            event="PROCESSING_COMPLETE",
            message=f"Document processed successfully - status: {final_status.value}"
        ))

        # Auto-approve and queue if confidence was high enough
        if final_status == InvoiceStatus.PROCESSED:
            approved = await repo.update_status(document_id, InvoiceStatus.APPROVED, InvoiceStatus.PROCESSED)
            if approved:
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
        # Clear the claim so the recovery sweep can re-queue if needed
        await repo.update_status(document_id, InvoiceStatus.ERROR, InvoiceStatus.PROCESSING)
        await repo.create_audit_log(AuditLog(
            document_id=document_id,
            event="PROCESSING_ERROR",
            message=f"Processing failed: {str(e)}"
        ))
        return InvoiceStatus.ERROR
