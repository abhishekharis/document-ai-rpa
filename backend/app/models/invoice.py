from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class InvoiceStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RPA_QUEUED = "RPA_QUEUED"
    RPA_PROCESSING = "RPA_PROCESSING"
    RPA_COMPLETED = "RPA_COMPLETED"
    RPA_FAILED = "RPA_FAILED"
    ERROR = "ERROR"


class Vendor(BaseModel):
    name: str
    address: Optional[str] = None


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class ExtractionField(BaseModel):
    value: Any
    confidence: float


class Extraction(BaseModel):
    overall_confidence: float
    fields: Dict[str, ExtractionField] = {}
    raw_ocr_text: str = ""
    page_count: int = 1


class Validation(BaseModel):
    is_valid: bool = True
    errors: List[str] = []
    warnings: List[str] = []
    duplicate_of: Optional[str] = None


class Review(BaseModel):
    required: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class RPAStatus(BaseModel):
    eligible: bool = False
    status: str = "NOT_STARTED"
    job_id: Optional[str] = None
    accounting_record_id: Optional[str] = None
    message: Optional[str] = None
    queued_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class Invoice(BaseModel):
    document_id: str
    original_filename: str
    status: InvoiceStatus = InvoiceStatus.UPLOADED
    
    vendor: Vendor
    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    
    currency: str = "USD"
    
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    
    line_items: List[LineItem] = []
    
    extraction: Extraction
    validation: Validation = Validation()
    review: Review = Review()
    rpa: RPAStatus = RPAStatus()
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class InvoiceCreate(BaseModel):
    original_filename: str
    vendor: Vendor
    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    line_items: List[LineItem] = []


class InvoiceUpdate(BaseModel):
    vendor: Optional[Vendor] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    line_items: Optional[List[LineItem]] = None
