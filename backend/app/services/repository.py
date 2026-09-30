from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.invoice import Invoice, InvoiceStatus, InvoiceUpdate, Vendor, Extraction, Validation, Review, RPAStatus
from app.models.audit_log import AuditLog
import uuid


class InvoiceRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.invoices
        self.audit_collection = database.audit_logs
    
    async def create_indexes(self):
        """Create MongoDB indexes for invoices."""
        await self.collection.create_index("document_id", unique=True)
        await self.collection.create_index([("vendor.name", 1), ("invoice_number", 1)])
        await self.collection.create_index("status")
        await self.collection.create_index("created_at")
        await self.audit_collection.create_index("document_id")
        await self.audit_collection.create_index("timestamp")
    
    async def create(self, invoice: Invoice) -> Invoice:
        """Create a new invoice."""
        invoice_dict = invoice.model_dump()
        invoice_dict["status"] = invoice.status.value
        await self.collection.insert_one(invoice_dict)
        return invoice
    
    async def get_by_document_id(self, document_id: str) -> Optional[Invoice]:
        """Get invoice by document ID."""
        doc = await self.collection.find_one({"document_id": document_id})
        if doc:
            doc.pop("_id", None)
            return Invoice(**doc)
        return None
    
    async def get_all(self, status: Optional[InvoiceStatus] = None, limit: int = 100) -> List[Invoice]:
        """Get all invoices, optionally filtered by status."""
        query = {}
        if status:
            query["status"] = status.value
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        invoices = []
        async for doc in cursor:
            doc.pop("_id", None)
            invoices.append(Invoice(**doc))
        return invoices
    
    async def update(self, document_id: str, update_data: InvoiceUpdate) -> Optional[Invoice]:
        """Update invoice fields."""
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.update_one(
            {"document_id": document_id},
            {"$set": update_dict}
        )
        
        if result.modified_count > 0:
            return await self.get_by_document_id(document_id)
        return None
    
    async def update_status(self, document_id: str, new_status: InvoiceStatus, old_status: Optional[InvoiceStatus] = None) -> bool:
        """Update invoice status with optional old status validation."""
        query = {"document_id": document_id}
        if old_status:
            query["status"] = old_status.value
        
        result = await self.collection.update_one(
            query,
            {
                "$set": {
                    "status": new_status.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def delete(self, document_id: str) -> bool:
        """Delete an invoice record."""
        result = await self.collection.delete_one({"document_id": document_id})
        return result.deleted_count > 0
    
    async def reset_for_reprocessing(self, document_id: str, old_status: InvoiceStatus) -> bool:
        """Clear extracted data and move the invoice back to PROCESSING, only if it is still in old_status."""
        result = await self.collection.update_one(
            {"document_id": document_id, "status": old_status.value},
            {
                "$set": {
                    "status": InvoiceStatus.PROCESSING.value,
                    "vendor": Vendor(name="").model_dump(),
                    "invoice_number": "",
                    "invoice_date": "",
                    "due_date": None,
                    "currency": "USD",
                    "subtotal": None,
                    "tax": None,
                    "total": None,
                    "line_items": [],
                    "extraction": Extraction(overall_confidence=0.0, page_count=0).model_dump(),
                    "validation": Validation().model_dump(),
                    "review": Review().model_dump(),
                    "rpa": RPAStatus().model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def update_extraction(self, document_id: str, extraction_data: dict) -> bool:
        """Update extraction results."""
        result = await self.collection.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "extraction": extraction_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def update_validation(self, document_id: str, validation_data: dict) -> bool:
        """Update validation results."""
        result = await self.collection.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "validation": validation_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def update_rpa_status(self, document_id: str, rpa_data: dict) -> bool:
        """Update RPA status."""
        result = await self.collection.update_one(
            {"document_id": document_id},
            {
                "$set": {
                    "rpa": rpa_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    async def find_duplicates(self, vendor_name: str, invoice_number: str) -> List[Invoice]:
        """Find potential duplicate invoices."""
        cursor = self.collection.find({
            "vendor.name": vendor_name,
            "invoice_number": invoice_number
        })
        duplicates = []
        async for doc in cursor:
            doc.pop("_id", None)
            duplicates.append(Invoice(**doc))
        return duplicates
    
    async def get_rpa_queue(self) -> List[Invoice]:
        """Get all invoices in RPA queue."""
        cursor = self.collection.find({
            "status": InvoiceStatus.RPA_QUEUED.value
        }).sort("created_at", 1)
        
        invoices = []
        async for doc in cursor:
            doc.pop("_id", None)
            invoices.append(Invoice(**doc))
        return invoices
    
    async def create_audit_log(self, audit_log: AuditLog) -> AuditLog:
        """Create an audit log entry."""
        audit_dict = audit_log.model_dump()
        await self.audit_collection.insert_one(audit_dict)
        return audit_log
    
    async def get_audit_logs(self, document_id: str) -> List[AuditLog]:
        """Get audit logs for a document."""
        cursor = self.audit_collection.find({"document_id": document_id}).sort("timestamp", -1)
        logs = []
        async for doc in cursor:
            doc.pop("_id", None)
            logs.append(AuditLog(**doc))
        return logs
    
    def generate_document_id(self) -> str:
        """Generate a unique document ID."""
        return f"DOC-{uuid.uuid4().hex[:12].upper()}"
