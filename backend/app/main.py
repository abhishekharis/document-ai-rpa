from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from contextlib import asynccontextmanager
import secrets
from pathlib import Path
from typing import Optional

import logging
import time

from app.config import settings
from app.logging_config import configure_logging
from app.database import db, get_database
from app.services.repository import InvoiceRepository
from app.services.processing_service import ProcessingService
from app.services.pipeline import run_processing, queue_approved_invoice
from app.services.events import invoice_event_stream
from app.services.job_queue import JobQueue, create_job_queue
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
from app.utils.rate_limit import RateLimiter
from motor.motor_asyncio import AsyncIOMotorDatabase


configure_logging(settings.log_level, json_logs=settings.environment != "development")
logger = logging.getLogger(__name__)

upload_limiter = RateLimiter(settings.upload_rate_limit_per_minute, 60)
rpa_limiter = RateLimiter(settings.rpa_rate_limit_per_minute, 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.connect()
    database = db.get_database()
    repo = InvoiceRepository(database)
    await repo.create_indexes()
    app.state.job_queue = create_job_queue()
    logger.info("Application startup complete (environment=%s, background_ocr=%s)",
                settings.environment, app.state.job_queue is not None)
    yield
    # Shutdown
    if app.state.job_queue:
        await app.state.job_queue.close()
    db.close()
    logger.info("Application shutdown")


app = FastAPI(
    title="Document AI RPA",
    description="Invoice Processing & RPA Automation Platform",
    version="1.0.0",
    lifespan=lifespan
)

@app.middleware("http")
async def log_requests(request, call_next):
    started = time.monotonic()
    response = await call_next(request)
    logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path,
                response.status_code, (time.monotonic() - started) * 1000)
    return response


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
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
@app.post("/api/invoices/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED,
          dependencies=[Depends(upload_limiter)])
async def upload_invoice(
    request: Request,
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
    
    # Read in chunks so an oversized upload is rejected without buffering all of it
    chunks = []
    total_size = 0
    while chunk := await file.read(1024 * 1024):
        total_size += len(chunk)
        if not validate_file_size(total_size, settings.max_upload_size_mb):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
            )
        chunks.append(chunk)
    content = b"".join(chunks)
    
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
    
    final_status = await process_or_enqueue(
        request.app.state.job_queue, repo, document_id, content, file.filename or "document"
    )
    return UploadResponse(document_id=document_id, status=final_status.value)


async def process_or_enqueue(
    job_queue: Optional[JobQueue],
    repo: InvoiceRepository,
    document_id: str,
    content: bytes,
    filename: str
) -> InvoiceStatus:
    """Hand the document to the OCR worker if Redis is configured, else process it inline."""
    if job_queue is None:
        return await run_processing(repo, ProcessingService(), document_id, content, filename)
    try:
        await job_queue.enqueue(document_id)
    except Exception as e:
        logger.error("Could not queue %s for processing: %s", document_id, e)
        await repo.update_status(document_id, InvoiceStatus.ERROR, InvoiceStatus.PROCESSING)
        await repo.create_audit_log(AuditLog(
            document_id=document_id,
            event="PROCESSING_ERROR",
            message=f"Could not queue document for processing: {e}"
        ))
        return InvoiceStatus.ERROR
    await repo.create_audit_log(AuditLog(
        document_id=document_id,
        event="PROCESSING_QUEUED",
        message="Document queued for background processing"
    ))
    return InvoiceStatus.PROCESSING


# Live invoice updates (Server-Sent Events)
@app.get("/api/events")
async def invoice_events(request: Request, database: AsyncIOMotorDatabase = Depends(get_database)):
    """Stream an `invoice` event ({document_id, status}) each time an invoice changes."""
    return StreamingResponse(
        invoice_event_stream(InvoiceRepository(database), request.is_disconnected),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
    http_request: Request,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Re-run the processing pipeline on eligible invoices using their stored original files."""
    repo = InvoiceRepository(database)
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
            
            final_status = await process_or_enqueue(
                http_request.app.state.job_queue, repo, document_id, content, invoice.original_filename
            )
            results.append(BulkActionResult(
                document_id=document_id, success=True, status=final_status.value,
                message=("Reprocessing queued" if final_status == InvoiceStatus.PROCESSING
                         else f"Reprocessed - status: {final_status.value}")
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
@app.post("/api/rpa/{document_id}/start", response_model=InvoiceResponse, dependencies=[Depends(rpa_limiter)])
async def start_rpa(
    document_id: str,
    request: RPAStartRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Start RPA processing for an approved invoice."""
    # Validate API key
    if not secrets.compare_digest(request.api_key.encode(), settings.rpa_api_key.encode()):
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
@app.post("/api/rpa/{document_id}/result", response_model=RPAResultResponse, dependencies=[Depends(rpa_limiter)])
async def rpa_result(
    document_id: str,
    request: RPAResultRequest,
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Receive RPA processing result from UiPath."""
    # Validate API key
    if not secrets.compare_digest(request.api_key.encode(), settings.rpa_api_key.encode()):
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
        "accounting_record_id": request.accounting_record_id if request.success else None,
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
