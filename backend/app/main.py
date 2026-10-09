from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from app.config import settings
from app.database import db, get_database
from app.services.repository import InvoiceRepository
from app.services.processing_service import ProcessingService
from app.storage.file_storage import file_storage
from app.models.invoice import Invoice, InvoiceStatus, Vendor, Extraction, ExtractionField, LineItem, InvoiceUpdate
from app.models.audit_log import AuditLog
from app.schemas.api import (
    UploadResponse, InvoiceResponse, InvoiceListResponse,
    ApprovalRequest, RejectionRequest, RPAQueueResponse,
    RPAStartRequest, RPAResultRequest, RPAResultResponse,
    HealthResponse, BulkActionRequest, BulkActionResult, BulkActionResponse
)
from app.utils.validators import (
    validate_file_type, validate_file_size, sanitize_string
)
from app.validation.state_transitions import StateTransitionValidator
from motor.motor_asyncio import AsyncIOMotorDatabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.connect()
    database = db.get_database()
    repo = InvoiceRepository(database)
    await repo.create_indexes()
    print("Application startup complete")
    yield
    # Shutdown
    db.close()
    print("Application shutdown")


app = FastAPI(
    title="Document AI RPA",
    description="Invoice Processing & RPA Automation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check
@app.get("/api/health", response_model=HealthResponse)
async def health_check(database: AsyncIOMotorDatabase = Depends(get_database)):
    """Health check endpoint."""
    try:
        # Test MongoDB connection
        await database.command("ping")
        mongodb_connected = True
    except Exception:
        mongodb_connected = False
    
    from datetime import datetime
    return HealthResponse(
        status="healthy" if mongodb_connected else "unhealthy",
        mongodb_connected=mongodb_connected,
        timestamp=datetime.utcnow()
    )


# Document Upload
@app.post("/api/invoices/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    file: UploadFile = File(...),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Upload an invoice document for processing."""
    # Validate file type
    allowed_types = ["pdf", "png", "jpg", "jpeg"]
    if not validate_file_type(file.filename or "", allowed_types):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if not validate_file_size(len(content), settings.max_upload_size_mb):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )
    
    # Create invoice record
    repo = InvoiceRepository(database)
    document_id = repo.generate_document_id()
    
    # Save file
    file_storage.save_original(document_id, file.filename or "document", content)
    
    # Create initial invoice record with PROCESSING status
    invoice = Invoice(
        document_id=document_id,
        original_filename=file.filename or "document",
        status=InvoiceStatus.PROCESSING,
        vendor=Vendor(name=""),
        invoice_number="",
        invoice_date="",
        extraction=Extraction(
            overall_confidence=0.0,
            fields={},
            raw_ocr_text="",
            page_count=0
        )
    )
    
    await repo.create(invoice)
    
    # Log upload event
    await repo.create_audit_log(AuditLog(
        document_id=document_id,
        event="UPLOAD",
        message=f"Document uploaded: {file.filename}"
    ))
    
    # Process the document (OCR + extraction + validation)
    final_status = await run_processing(repo, ProcessingService(), document_id, content, file.filename or "document")
    return UploadResponse(document_id=document_id, status=final_status.value)


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


# Get All Invoices
@app.get("/api/invoices", response_model=InvoiceListResponse)
async def get_invoices(
    status_filter: Optional[str] = None,
    limit: int = 100,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all invoices, optionally filtered by status."""
    repo = InvoiceRepository(database)
    
    invoice_status = None
    if status_filter:
        try:
            invoice_status = InvoiceStatus(status_filter.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    
    invoices = await repo.get_all(status=invoice_status, limit=limit)
    
    return InvoiceListResponse(
        invoices=[InvoiceResponse(**inv.model_dump()) for inv in invoices],
        count=len(invoices)
    )


# Statuses where the document is mid-pipeline and must not be deleted
DELETE_BLOCKED_STATUSES = {InvoiceStatus.PROCESSING, InvoiceStatus.RPA_PROCESSING}
REPROCESSABLE_STATUSES = {InvoiceStatus.ERROR, InvoiceStatus.REJECTED, InvoiceStatus.NEEDS_REVIEW}


def build_bulk_response(results: list[BulkActionResult]) -> BulkActionResponse:
    succeeded = sum(1 for r in results if r.success)
    return BulkActionResponse(results=results, succeeded=succeeded, failed=len(results) - succeeded)


# Bulk Delete
@app.post("/api/invoices/bulk-delete", response_model=BulkActionResponse)
async def bulk_delete_invoices(
    request: BulkActionRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Permanently delete invoices and their stored files. Audit logs are kept."""
    repo = InvoiceRepository(database)
    results = []
    
    for document_id in dict.fromkeys(request.document_ids):
        try:
            invoice = await repo.get_by_document_id(document_id)
            if not invoice:
                results.append(BulkActionResult(document_id=document_id, success=False, message="Document not found"))
                continue
            if invoice.status in DELETE_BLOCKED_STATUSES:
                results.append(BulkActionResult(
                    document_id=document_id, success=False, status=invoice.status.value,
                    message=f"Cannot delete while status is {invoice.status.value}"
                ))
                continue
            
            await repo.delete(document_id)
            file_storage.delete_document(document_id)
            
            await repo.create_audit_log(AuditLog(
                document_id=document_id,
                event="DOCUMENT_DELETED",
                old_status=invoice.status.value,
                message=f"Document deleted: {invoice.original_filename}"
            ))
            results.append(BulkActionResult(document_id=document_id, success=True, message="Deleted"))
        except Exception as e:
            results.append(BulkActionResult(document_id=document_id, success=False, message=f"Delete failed: {str(e)}"))
    
    return build_bulk_response(results)


# Bulk Reprocess
@app.post("/api/invoices/bulk-reprocess", response_model=BulkActionResponse)
async def bulk_reprocess_invoices(
    request: BulkActionRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Re-run the processing pipeline on eligible invoices using their stored original files."""
    repo = InvoiceRepository(database)
    processing_service = ProcessingService()
    results = []
    
    for document_id in dict.fromkeys(request.document_ids):
        try:
            invoice = await repo.get_by_document_id(document_id)
            if not invoice:
                results.append(BulkActionResult(document_id=document_id, success=False, message="Document not found"))
                continue
            if invoice.status not in REPROCESSABLE_STATUSES:
                results.append(BulkActionResult(
                    document_id=document_id, success=False, status=invoice.status.value,
                    message=f"Not eligible for reprocessing (status: {invoice.status.value})"
                ))
                continue
            
            file_path = file_storage.get_original_file(document_id)
            if not file_path or not file_path.exists():
                results.append(BulkActionResult(
                    document_id=document_id, success=False, status=invoice.status.value,
                    message="Original file not found"
                ))
                continue
            content = file_path.read_bytes()
            
            if not await repo.reset_for_reprocessing(document_id, invoice.status):
                results.append(BulkActionResult(
                    document_id=document_id, success=False,
                    message="Document status changed; not reprocessed"
                ))
                continue
            
            await repo.create_audit_log(AuditLog(
                document_id=document_id,
                event="REPROCESS_STARTED",
                old_status=invoice.status.value,
                new_status=InvoiceStatus.PROCESSING.value,
                message="Document reprocessing started"
            ))
            
            final_status = await run_processing(repo, processing_service, document_id, content, invoice.original_filename)
            results.append(BulkActionResult(
                document_id=document_id, success=True, status=final_status.value,
                message=f"Reprocessed - status: {final_status.value}"
            ))
        except Exception as e:
            results.append(BulkActionResult(document_id=document_id, success=False, message=f"Reprocess failed: {str(e)}"))
    
    return build_bulk_response(results)


# Get Invoice by Document ID
@app.get("/api/invoices/{document_id}", response_model=InvoiceResponse)
async def get_invoice(
    document_id: str,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get invoice by document ID."""
    repo = InvoiceRepository(database)
    invoice = await repo.get_by_document_id(document_id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {document_id}"
        )
    
    return InvoiceResponse(**invoice.model_dump())


# Get Document File
@app.get("/api/invoices/{document_id}/document")
async def get_document(document_id: str):
    """Get the original document file."""
    file_path = file_storage.get_original_file(document_id)
    
    if not file_path or not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document file not found: {document_id}"
        )
    
    return FileResponse(file_path)


# Update Invoice
@app.put("/api/invoices/{document_id}", response_model=InvoiceResponse)
async def update_invoice(
    document_id: str,
    update_data: dict,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update invoice fields (for manual correction)."""
    repo = InvoiceRepository(database)
    
    # Check if invoice exists
    invoice = await repo.get_by_document_id(document_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {document_id}"
        )
    
    # Update invoice
    from app.models.invoice import InvoiceUpdate
    update_obj = InvoiceUpdate(**update_data)
    updated = await repo.update(document_id, update_obj)
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update invoice"
        )
    
    # Log correction event
    await repo.create_audit_log(AuditLog(
        document_id=document_id,
        event="MANUAL_CORRECTION",
        message="Invoice fields manually corrected"
    ))
    
    return InvoiceResponse(**updated.model_dump())


# Approve Invoice
@app.post("/api/invoices/{document_id}/approve", response_model=InvoiceResponse)
async def approve_invoice(
    document_id: str,
    request: ApprovalRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Approve an invoice for RPA processing."""
    repo = InvoiceRepository(database)
    
    invoice = await repo.get_by_document_id(document_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {document_id}"
        )
    
    # Validate state transition
    can_transition, error_msg = StateTransitionValidator.validate_transition(
        invoice.status, InvoiceStatus.APPROVED
    )
    if not can_transition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # An invoice already APPROVED (e.g. queueing previously failed) skips straight to queueing
    if invoice.status != InvoiceStatus.APPROVED:
        success = await repo.update_status(document_id, InvoiceStatus.APPROVED, invoice.status)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Invoice status changed; not approved"
            )

        await repo.update_review(document_id, request.reviewed_by)

        await repo.create_audit_log(AuditLog(
            document_id=document_id,
            event="APPROVED",
            actor=request.reviewed_by,
            old_status=invoice.status.value,
            new_status=InvoiceStatus.APPROVED.value,
            message=request.notes
        ))

    if not await queue_approved_invoice(repo, document_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice approved but could not be queued for RPA; approve again to retry"
        )
    
    # Get updated invoice
    updated = await repo.get_by_document_id(document_id)
    return InvoiceResponse(**updated.model_dump())


# Reject Invoice
@app.post("/api/invoices/{document_id}/reject", response_model=InvoiceResponse)
async def reject_invoice(
    document_id: str,
    request: RejectionRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Reject an invoice."""
    repo = InvoiceRepository(database)
    
    invoice = await repo.get_by_document_id(document_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {document_id}"
        )
    
    # Validate state transition
    can_transition, error_msg = StateTransitionValidator.validate_transition(
        invoice.status, InvoiceStatus.REJECTED
    )
    if not can_transition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Update status
    success = await repo.update_status(document_id, InvoiceStatus.REJECTED, invoice.status)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reject invoice"
        )
    
    # Log rejection event
    await repo.create_audit_log(AuditLog(
        document_id=document_id,
        event="REJECTED",
        actor=request.reviewed_by,
        old_status=invoice.status.value,
        new_status=InvoiceStatus.REJECTED.value,
        message=request.reason
    ))
    
    # Get updated invoice
    updated = await repo.get_by_document_id(document_id)
    return InvoiceResponse(**updated.model_dump())


# Get RPA Queue
@app.get("/api/rpa/queue", response_model=RPAQueueResponse)
async def get_rpa_queue(database: AsyncIOMotorDatabase = Depends(get_database)):
    """Get invoices queued for RPA processing."""
    repo = InvoiceRepository(database)
    invoices = await repo.get_rpa_queue()
    
    return RPAQueueResponse(
        invoices=[InvoiceResponse(**inv.model_dump()) for inv in invoices],
        count=len(invoices)
    )


# Start RPA Processing
@app.post("/api/rpa/{document_id}/start", response_model=InvoiceResponse)
async def start_rpa(
    document_id: str,
    request: RPAStartRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Start RPA processing for an approved invoice."""
    # Validate API key
    if request.api_key != settings.rpa_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    repo = InvoiceRepository(database)
    invoice = await repo.get_by_document_id(document_id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {document_id}"
        )
    
    # Validate state transition
    can_transition, error_msg = StateTransitionValidator.validate_transition(
        invoice.status, InvoiceStatus.RPA_PROCESSING
    )
    if not can_transition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Update status to RPA_PROCESSING
    success = await repo.update_status(document_id, InvoiceStatus.RPA_PROCESSING, invoice.status)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to start RPA processing"
        )
    
    # Update RPA status
    from datetime import datetime
    await repo.update_rpa_status(document_id, {
        "eligible": True,
        "status": "PROCESSING",
        "job_id": f"JOB-{document_id}",
        "message": "RPA processing started",
        "processed_at": datetime.utcnow().isoformat()
    })
    
    # Log RPA start event
    await repo.create_audit_log(AuditLog(
        document_id=document_id,
        event="RPA_STARTED",
        message="RPA processing started"
    ))
    
    # Get updated invoice
    updated = await repo.get_by_document_id(document_id)
    return InvoiceResponse(**updated.model_dump())


# RPA Result Callback
@app.post("/api/rpa/{document_id}/result", response_model=RPAResultResponse)
async def rpa_result(
    document_id: str,
    request: RPAResultRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Receive RPA processing result from UiPath."""
    # Validate API key
    if request.api_key != settings.rpa_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    repo = InvoiceRepository(database)
    invoice = await repo.get_by_document_id(document_id)
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice not found: {document_id}"
        )
    
    # Determine new status based on result
    new_status = InvoiceStatus.RPA_COMPLETED if request.success else InvoiceStatus.RPA_FAILED
    
    # Validate state transition
    can_transition, error_msg = StateTransitionValidator.validate_transition(
        invoice.status, new_status
    )
    if not can_transition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Update status
    success = await repo.update_status(document_id, new_status, invoice.status)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update RPA result"
        )
    
    # Update RPA status
    from datetime import datetime
    await repo.update_rpa_status(document_id, {
        "eligible": True,
        "status": "COMPLETED" if request.success else "FAILED",
        "job_id": invoice.rpa.job_id,
        "message": request.message or ("RPA completed successfully" if request.success else "RPA failed"),
        "processed_at": datetime.utcnow().isoformat()
    })
    
    # Log RPA completion event
    await repo.create_audit_log(AuditLog(
        document_id=document_id,
        event="RPA_COMPLETED" if request.success else "RPA_FAILED",
        message=request.message or ("RPA completed successfully" if request.success else "RPA failed")
    ))
    
    return RPAResultResponse(
        success=True,
        message="RPA result recorded successfully"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
