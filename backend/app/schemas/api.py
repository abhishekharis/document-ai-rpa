from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class UploadResponse(BaseModel):
    document_id: str
    status: str


class InvoiceResponse(BaseModel):
    document_id: str
    original_filename: str
    status: str
    vendor: Dict[str, Any]
    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    currency: str
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    line_items: List[Dict[str, Any]] = []
    extraction: Dict[str, Any]
    validation: Dict[str, Any]
    review: Dict[str, Any]
    rpa: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class InvoiceListResponse(BaseModel):
    invoices: List[InvoiceResponse]
    count: int


class BulkActionRequest(BaseModel):
    document_ids: List[str] = Field(..., min_length=1)


class BulkActionResult(BaseModel):
    document_id: str
    success: bool
    status: Optional[str] = None
    message: str


class BulkActionResponse(BaseModel):
    results: List[BulkActionResult]
    succeeded: int
    failed: int


class ApprovalRequest(BaseModel):
    document_id: str
    reviewed_by: str
    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    document_id: str
    reviewed_by: str
    reason: str


class RPAQueueResponse(BaseModel):
    invoices: List[InvoiceResponse]
    count: int


class RPAStartRequest(BaseModel):
    document_id: str
    api_key: str


class RPAResultRequest(BaseModel):
    document_id: str
    api_key: str
    success: bool
    accounting_record_id: Optional[str] = None
    message: Optional[str] = None


class RPAResultResponse(BaseModel):
    success: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    mongodb_connected: bool
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: str
