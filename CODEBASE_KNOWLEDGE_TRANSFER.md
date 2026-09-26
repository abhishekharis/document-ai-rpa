# Codebase Knowledge Transfer / Developer Handoff Document

## Executive Summary

This is a Document AI and RPA automation system that processes invoices through OCR, extracts structured data, validates it, and routes it for either human review or automated RPA processing. The system demonstrates the integration of AI-powered document processing with robotic process automation.

**Architecture**: React Frontend → FastAPI Backend → MongoDB Database + PaddleOCR/PyMuPDF Processing → UiPath RPA → Simulated Accounting App

**Technology Stack**: Python 3.10-3.13, FastAPI, MongoDB, PaddleOCR, PyMuPDF, OpenCV, React, Vite, Tailwind CSS, Docker Compose, Flask (accounting app)

**Main Workflow**: Upload document → PDF/image processing → OCR → Field extraction → Validation → Confidence-based routing → Human review (if needed) → RPA automation → Accounting system entry

**Database**: MongoDB with `invoices` and `audit_logs` collections, indexed on document_id, vendor+invoice_number, status, and timestamps

**OCR**: PaddleOCR with OpenCV preprocessing (deskewing, contrast enhancement, denoising) and PyMuPDF for PDF processing

**Frontend**: Modern React dashboard with Tailwind CSS, drag-and-drop upload, invoice details page, review interface

**Backend**: FastAPI with async MongoDB operations via Motor, comprehensive validation service, state transition enforcement

**RPA**: UiPath workflow documentation (Windows-only), API endpoints for queue management and result callbacks

**Local Development**: Docker Compose for MongoDB, Python virtual environment, npm for frontend, Flask for accounting app

---

## 1. Project Overview

### What the Application Does
The system automatically processes invoice documents (PDFs and images) by:
1. Accepting file uploads via web interface
2. Converting documents to images using PyMuPDF
3. Preprocessing images with OpenCV (deskewing, contrast enhancement, denoising)
4. Running OCR using PaddleOCR to extract text
5. Extracting structured invoice fields (vendor, invoice number, dates, amounts)
6. Validating extracted data against business rules
7. Routing documents based on confidence scores and validation results
8. Providing human review interface for low-confidence extractions
9. Enabling RPA automation to enter approved invoices into accounting system

### Main Problem Solved
Automates the manual data entry of invoice information into accounting systems while maintaining data quality through confidence-based routing and human oversight.

### Complete End-to-End Workflow
1. User uploads invoice PDF/image via React frontend
2. FastAPI validates file type and size, stores file locally
3. ProcessingService orchestrates: PDF conversion → Image preprocessing → OCR → Field extraction → Validation
4. MongoDB stores invoice with extracted data, confidence scores, and validation results
5. Status determined: APPROVED (high confidence), NEEDS_REVIEW (low confidence/warnings), REJECTED (errors)
6. For NEEDS_REVIEW: human can correct fields and approve/reject
7. For APPROVED: invoice enters RPA queue
8. UiPath workflow picks up invoice, enters data into simulated accounting app
9. Accounting app returns record ID, RPA reports result back to backend
10. Final status: RPA_COMPLETED or RPA_FAILED

### What Happens When User Uploads Document
1. Frontend sends POST /api/invoices/upload with file
2. Backend validates file (PDF/PNG/JPG/JPEG, max 10MB)
3. Generates unique document_id (DOC-XXXXXXXXXXXX)
4. Stores original file in storage/documents/{document_id}/original/
5. Creates initial invoice record with PROCESSING status
6. ProcessingService runs complete pipeline
7. Updates invoice with extraction results, validation, and final status
8. Returns document_id and status to frontend
9. Frontend redirects to invoice details page

### What Happens After OCR
1. OCR returns raw text and confidence scores per text segment
2. InvoiceExtractor uses regex patterns to identify structured fields
3. Maps extracted text to field names (vendor_name, invoice_number, etc.)
4. Calculates confidence per field based on OCR confidence of matching text
5. Returns structured data with field-level confidence scores

### How Extracted Information is Processed
1. ValidationService checks required fields exist and have values
2. Validates confidence scores against threshold (default 0.80)
3. Validates date sequences (due date not before invoice date)
4. Validates amount arithmetic (subtotal + tax ≈ total)
5. Returns validation result with errors/warnings
6. Final status determined: REJECTED (errors), NEEDS_REVIEW (low confidence/warnings), APPROVED (valid + high confidence)

### How Validation Works
- **Required fields**: vendor_name, invoice_number, invoice_date, total, currency
- **Confidence threshold**: 0.80 (configurable via CONFIDENCE_THRESHOLD)
- **Date validation**: Due date cannot be before invoice date
- **Amount validation**: Subtotal + tax should approximately equal total
- **Business rules**: Non-negative amounts, valid date formats

### How Human Review Works
1. NEEDS_REVIEW invoices show "Review" button in dashboard
2. Review page displays extracted fields in editable form
3. Shows extraction confidence and validation errors/warnings
4. User can correct fields and save changes
5. User enters name and optionally notes
6. User can approve (moves to APPROVED status) or reject (moves to REJECTED status)
7. Audit logs track all review actions

### How RPA/Accounting Portion Works
1. APPROVED invoices automatically move to RPA_QUEUED status
2. UiPath workflow polls GET /api/rpa/queue
3. For each invoice, calls POST /api/rpa/{document_id}/start with API key
4. Status changes to RPA_PROCESSING
5. UiPath opens simulated accounting app at http://localhost:3001
6. Automates form entry with invoice data
7. Receives accounting record ID (ACC-XXXXXXXX)
8. Calls POST /api/rpa/{document_id}/result with success/failure
9. Status changes to RPA_COMPLETED or RPA_FAILED
10. Audit logs track entire RPA process

### What Parts Are Real vs Simulated
- **Real**: FastAPI backend, MongoDB database, OCR processing, validation logic, React frontend, file storage, state management
- **Simulated**: Accounting application (Flask, in-memory storage), UiPath workflow (documentation only, requires manual implementation)
- **Not implemented**: PostgreSQL, Redis/Celery, Tesseract, Google Document AI, external vendor databases, external monitoring

### Major System Components
- **Backend API**: FastAPI application with async MongoDB operations
- **Document AI Pipeline**: PyMuPDF → OpenCV → PaddleOCR → Regex extraction
- **Validation Service**: Business rules and confidence-based routing
- **State Management**: Invoice status transitions with enforcement
- **Frontend**: React dashboard with modern Tailwind CSS design
- **RPA Integration**: API endpoints for UiPath workflow
- **Simulated Accounting**: Flask app demonstrating target system

### High-Level Architecture Diagram
```
React Frontend (port 3000/3001)
    ↓ HTTP requests
FastAPI Backend (port 8000)
    ↓ File storage
Local File System (storage/documents/)
    ↓ Processing Pipeline
PyMuPDF → OpenCV → PaddleOCR → InvoiceExtractor → ValidationService
    ↓ Data persistence
MongoDB (port 27017, Docker)
    ↓ RPA triggers
UiPath Workflow (Windows, external)
    ↓ Data entry
Simulated Accounting App (port 3001, Flask)
    ↓ Result callbacks
FastAPI Backend
```

---

## 2. Technology Stack

| Technology | Version | What It Is | Why Used | Where Used |
|------------|---------|-------------|-----------|------------|
| Python | 3.10-3.13 | Programming language | PaddleOCR compatibility, async support | Backend |
| FastAPI | 0.104.1+ | Modern async web framework | Fast development, automatic docs, async MongoDB | Backend API |
| Uvicorn | 0.24.0+ | ASGI server | Runs FastAPI application | Backend server |
| Pydantic | 2.5.0+ | Data validation | Request/response models, configuration | Backend |
| PyMongo | 4.6.0+ | MongoDB driver | Synchronous MongoDB operations | Backend |
| Motor | 3.3.2+ | Async MongoDB driver | Async database operations | Backend |
| PaddleOCR | 2.7.0.3 | OCR engine | Real OCR with confidence scores | Document AI |
| PyMuPDF | 1.23.0+ | PDF processing | Convert PDF pages to images | Document AI |
| OpenCV | 4.8.0+ | Image processing | Preprocessing (deskewing, contrast, denoising) | Document AI |
| Pillow | 10.2.0+ | Image manipulation | PIL Image operations | Document AI |
| NumPy | 1.24.0+ | Numerical computing | Array operations for OpenCV | Document AI |
| React | 18.2.0 | Frontend framework | Modern UI, component-based | Frontend |
| React Router | 6.20.0 | Routing | Client-side navigation | Frontend |
| Axios | 1.6.2 | HTTP client | API communication | Frontend |
| Vite | 5.0.8 | Build tool | Fast development, hot reload | Frontend |
| Tailwind CSS | 3.4.19 | CSS framework | Modern styling without custom CSS | Frontend |
| MongoDB | 7.0 | Document database | Flexible document storage | Database |
| Docker Compose | - | Container orchestration | MongoDB containerization | Infrastructure |
| Flask | - | Web framework | Simulated accounting app | Accounting App |
| UiPath | - | RPA platform | Automates accounting entry | RPA (external) |

### Technologies NOT Used (but mentioned in some docs)
- PostgreSQL (removed in favor of MongoDB only)
- Redis/Celery (removed, using synchronous processing)
- Tesseract (removed, using PaddleOCR only)
- Google Document AI (removed, using local OCR)
- External vendor databases (removed, using local processing)
- Sentry, Slack alerts (removed, using simple logging)

---

## 3. Repository Structure

```
document-ai-rpa/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── config.py                  # Pydantic settings from .env
│   │   ├── database.py                # MongoDB connection singleton
│   │   ├── models/                    # Pydantic data models
│   │   │   ├── invoice.py             # Invoice, InvoiceStatus, related models
│   │   │   └── audit_log.py           # AuditLog model
│   │   ├── schemas/                   # API request/response schemas
│   │   │   └── api.py                 # UploadResponse, InvoiceResponse, etc.
│   │   ├── services/                  # Business logic layer
│   │   │   ├── repository.py          # MongoDB CRUD operations
│   │   │   └── processing_service.py # OCR/extraction orchestration
│   │   ├── document_ai/              # OCR and extraction pipeline
│   │   │   ├── pdf_processor.py      # PyMuPDF PDF→image conversion
│   │   │   ├── image_preprocessor.py # OpenCV image enhancement
│   │   │   ├── ocr_service.py        # PaddleOCR text extraction
│   │   │   └── invoice_extractor.py   # Regex-based field extraction
│   │   ├── validation/                # Validation and state management
│   │   │   ├── validation_service.py # Business rule validation
│   │   │   └── state_transitions.py   # Invoice status transition rules
│   │   ├── storage/                   # File storage management
│   │   │   └── file_storage.py        # Local file system operations
│   │   └── utils/                     # Utility functions
│   │       └── validators.py         # Date/amount parsing/validation
│   ├── tests/                         # Backend tests
│   │   ├── test_api.py                # API integration tests
│   │   ├── test_invoice_extractor.py  # Extraction logic tests
│   │   ├── test_validation_service.py # Validation logic tests
│   │   ├── test_state_transitions.py  # State transition tests
│   │   └── test_validators.py        # Validator function tests
│   └── requirements.txt               # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # React Router + main layout
│   │   ├── main.jsx                   # React entry point
│   │   ├── index.css                  # Tailwind CSS + custom styles
│   │   ├── components/
│   │   │   └── Sidebar.jsx             # Navigation sidebar
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx          # Statistics + invoice table
│   │   │   ├── Upload.jsx              # Drag-and-drop upload interface
│   │   │   ├── InvoiceDetails.jsx     # Invoice view with extraction data
│   │   │   └── Review.jsx              # Edit + approve/reject interface
│   │   └── services/
│   │       └── api.js                 # Axios API client
│   ├── index.html                     # HTML entry point
│   ├── package.json                   # Node dependencies
│   ├── vite.config.js                 # Vite configuration + proxy
│   ├── tailwind.config.js             # Tailwind theme + colors
│   └── postcss.config.js              # PostCSS plugins
├── simulated-accounting-app/
│   ├── app.py                         # Flask application
│   ├── requirements.txt               # Python dependencies
│   └── templates/                     # HTML templates
│       ├── base.html                  # Base template
│       ├── dashboard.html             # Record listing
│       ├── new_invoice.html           # Invoice creation form
│       ├── success.html               # Success page with record ID
│       └── view_record.html           # Record details
├── rpa/
│   └── UiPath/
│       └── InvoiceProcessor/
│           └── Workflow_Guide.md     # UiPath implementation guide
├── sample_documents/                 # Test invoice samples
│   ├── normal/                        # Clean invoices
│   ├── poor_quality/                 # Low quality scans
│   ├── missing_fields/                # Invoices missing required fields
│   └── invalid/                      # Invoices with invalid data
├── storage/                           # Local file storage
│   └── documents/                     # Uploaded documents
├── tests/
│   └── e2e/
│       └── test_workflow.py            # End-to-end test
├── docker-compose.yml                  # MongoDB container configuration
├── .env.example                       # Environment variable template
├── .gitignore                         # Git ignore rules
├── README.md                          # Project documentation
└── SETUP.md                           # Setup instructions (Python version requirements)

### Important Directory Explanations

**backend/app/main.py**: FastAPI application entry point. Defines all API endpoints, CORS middleware, startup/shutdown lifecycle for MongoDB connection and index creation. Depends on config, database, services, models, schemas. Called by `python -m app.main`.

**backend/app/config.py**: Pydantic settings class that loads environment variables from .env file. Defines MongoDB URI, database name, storage paths, confidence threshold, API settings, RPA configuration, CORS origins. Used throughout application for configuration.

**backend/app/database.py**: MongoDB connection singleton. Manages AsyncIOMotorClient lifecycle, provides database instance, get_database() dependency for FastAPI. Called during app startup and by all services needing database access.

**backend/app/services/repository.py**: MongoDB CRUD operations. Implements InvoiceRepository class with async methods for create, read, update, status changes, duplicate detection, RPA queue management, audit logging. Creates indexes on startup. Used by all API endpoints.

**backend/app/services/processing_service.py**: Orchestrates complete invoice processing pipeline. Coordinates PDFProcessor, ImagePreprocessor, OCRService, InvoiceExtractor, ValidationService. Implements process_invoice() method that runs all steps and returns final status. Called by upload endpoint.

**backend/app/document_ai/**: OCR and extraction pipeline.
- **pdf_processor.py**: PyMuPDF-based PDF to image conversion at 300 DPI
- **image_preprocessor.py**: OpenCV preprocessing (grayscale, deskewing, contrast enhancement, denoising)
- **ocr_service.py**: PaddleOCR wrapper with lazy initialization, confidence extraction
- **invoice_extractor.py**: Regex-based field extraction with confidence mapping

**backend/app/validation/**: Business rules and state management.
- **validation_service.py**: Validates required fields, confidence thresholds, date sequences, amount arithmetic
- **state_transitions.py**: Defines VALID_TRANSITIONS dict, enforces allowed status changes

**backend/app/storage/file_storage.py**: Local file system operations. Manages storage/documents/{document_id}/ directory structure, sanitizes filenames, provides save/get/delete methods. Used by upload endpoint.

**frontend/src/App.jsx**: React Router configuration. Defines routes for Dashboard, Upload, InvoiceDetails, Review pages. Wraps Sidebar component and main content area with responsive layout.

**frontend/src/services/api.js**: Axios HTTP client. Defines invoiceAPI and rpaAPI objects with methods for upload, getAll, getById, update, approve, reject, getDocument, getQueue, start, result. Configured with base URL /api (proxied to backend port 8000).

**simulated-accounting-app/app.py**: Flask application simulating accounting system. In-memory storage for accounting records. Routes: / (dashboard), /new-invoice (form), /record/<id> (view). Runs on port 3001. Used as RPA target.

**docker-compose.yml**: MongoDB 7.0 container configuration. Defines single service with image mongo:7.0, port 27017, volume for data persistence, environment variable for database name. Fixed version compatibility issue (changed from 8.0 to 7.0).

---

## 4. Backend Architecture

### Application Entry Point
**File**: `backend/app/main.py`
**Function**: Application startup with FastAPI, CORS middleware, database connection, index creation
**Entry**: `python -m app.main` (runs uvicorn server on configured host/port)

### FastAPI Initialization
- Creates FastAPI app with title, description, version, lifespan context manager
- Lifespan: connects to MongoDB, creates indexes on startup, closes connection on shutdown
- CORS middleware: allows requests from configured origins (localhost:3000, 5173)
- All endpoints defined as async functions with dependency injection

### Routers/Endpoints
All endpoints defined directly in `main.py` (no separate router files):
- **GET /api/health**: Health check, tests MongoDB connection
- **POST /api/invoices/upload**: Upload and process document
- **GET /api/invoices**: List all invoices (optional status filter)
- **GET /api/invoices/{document_id}**: Get specific invoice
- **GET /api/invoices/{document_id}/document**: Download original file
- **PUT /api/invoices/{document_id}**: Update invoice fields
- **POST /api/invoices/{document_id}/approve**: Approve for RPA
- **POST /api/invoices/{document_id}/reject**: Reject invoice
- **GET /api/rpa/queue**: Get RPA queue
- **POST /api/rpa/{document_id}/start**: Start RPA processing
- **POST /api/rpa/{document_id}/result**: Receive RPA result

### Services
**ProcessingService** (`backend/app/services/processing_service.py`): Orchestrates complete pipeline. Coordinates PDF conversion, image preprocessing, OCR, extraction, validation. Called by upload endpoint.

**InvoiceRepository** (`backend/app/services/repository.py`): MongoDB CRUD operations. All database access goes through this service. Provides async methods for all data operations.

### Models
**Invoice** (`backend/app/models/invoice.py`): Pydantic model with all invoice fields, nested models for Vendor, Extraction, Validation, Review, RPAStatus. Includes InvoiceStatus enum with 11 states.

**AuditLog** (`backend/app/models/audit_log.py`): Pydantic model for audit trail. Tracks document_id, event, actor, old_status, new_status, message, timestamp.

### Schemas
**API Schemas** (`backend/app/schemas/api.py`): Pydantic models for API requests/responses. Includes UploadResponse, InvoiceResponse, InvoiceListResponse, ApprovalRequest, RejectionRequest, RPAQueueResponse, RPAStartRequest, RPAResultRequest, RPAResultResponse, HealthResponse.

### Database/Repository Layer
**Database** (`backend/app/database.py`): Singleton MongoDB connection manager. Provides AsyncIOMotorClient instance, database accessor, get_database() dependency for FastAPI.

**InvoiceRepository** (`backend/app/services/repository.py`): Repository pattern implementation. Wraps Motor async operations, provides business-level methods (create_indexes, find_duplicates, get_rpa_queue, etc.). Used by all API endpoints.

### OCR/Document-Processing Layer
**Document AI** (`backend/app/document_ai/`):
- **PDFProcessor**: PyMuPDF wrapper, converts PDF pages to PIL Images at 300 DPI
- **ImagePreprocessor**: OpenCV wrapper, deskewing, contrast enhancement, denoising, quality estimation
- **OCRService**: PaddleOCR wrapper, lazy initialization, confidence extraction, multi-page support
- **InvoiceExtractor**: Regex-based field extraction, confidence mapping from OCR results

### Validation Layer
**Validation** (`backend/app/validation/`):
- **ValidationService**: Business rule validation (required fields, confidence thresholds, date sequences, amount arithmetic)
- **StateTransitionValidator**: Enforces allowed status transitions per VALID_TRANSITIONS dict

### Storage Handling
**FileStorage** (`backend/app/storage/file_storage.py`): Local file system operations. Manages directory structure storage/documents/{document_id}/{original,pages/}, sanitizes filenames, provides save/get/delete methods.

### Configuration
**Settings** (`backend/app/config.py`): Pydantic settings loaded from .env. Defines MongoDB URI, database name, storage path, upload size limit, confidence threshold, API host/port, accounting app URL, RPA API key, CORS origins.

### Error Handling
- HTTPException for 4xx errors (invalid file, not found, invalid transitions)
- Try/catch in processing pipeline, sets ERROR status on failure
- Audit logging for all errors and recovery attempts
- Generic error responses returned to frontend

### Logging/Audit Functionality
- Python logging throughout application
- AuditLog model tracks all state changes and user actions
- Audit logs stored in MongoDB audit_logs collection
- Indexed on document_id and timestamp
- Every status change, approval, rejection, RPA action logged

---

## 5. Backend Request/Data Flow

### Document Upload Workflow

**Frontend** (`frontend/src/pages/Upload.jsx`):
- User selects file or drags to upload area
- Validates file type (PDF/PNG/JPG/JPEG) and size (max 10MB)
- Calls `invoiceAPI.upload(file)`

**→ HTTP POST /api/invoices/upload**

**Backend** (`backend/app/main.py`):
- Endpoint: `upload_invoice()`
- Validates file type and size using validator functions
- Calls `repo.generate_document_id()` for unique ID
- Calls `file_storage.save_original(document_id, filename, content)`
- Creates initial Invoice with PROCESSING status
- Calls `repo.create(invoice)` to save to MongoDB
- Calls `repo.create_audit_log()` for UPLOAD event
- Calls `processing_service.process_invoice(content, filename, document_id)`

**→ ProcessingService.process_invoice()** (`backend/app/services/processing_service.py`):
- **Step 1**: `pdf_processor.process_document(file_bytes, filename)` → returns PIL Images
- **Step 2**: `image_preprocessor.preprocess(image)` for each page → returns enhanced images
- **Step 3**: `ocr_service.extract_text_from_images(preprocessed_images)` → returns text + confidence
- **Step 4**: `invoice_extractor.extract(ocr_text, raw_results)` → returns structured fields + confidence
- **Step 5**: `validation_service.validate(extracted_fields)` → returns errors/warnings
- **Step 6**: `validation_service.determine_status(validation, confidence)` → returns final status

**→ Repository Updates**:
- `repo.update(document_id, InvoiceUpdate)` with extracted data
- `repo.update_extraction(document_id, extraction_data)`
- `repo.update_validation(document_id, validation_data)`
- `repo.update_status(document_id, final_status, PROCESSING)`
- `repo.create_audit_log()` for PROCESSING_COMPLETE event

**→ Response**: UploadResponse with document_id and status

**→ Frontend Behavior**:
- Shows success message with document_id
- Navigates to `/invoice/{document_id}` after 1.5 seconds

### Invoice Approval Workflow

**Frontend** (`frontend/src/pages/Review.jsx`):
- User corrects fields and clicks "Approve Invoice"
- Enters name and optional notes
- Calls `invoiceAPI.approve(documentId, reviewedBy, notes)`

**→ HTTP POST /api/invoices/{document_id}/approve**

**Backend** (`backend/app/main.py`):
- Endpoint: `approve_invoice()`
- Validates API key if provided (not used by frontend)
- Calls `repo.get_by_document_id(document_id)` to get current invoice
- Calls `StateTransitionValidator.validate_transition(current_status, APPROVED)`
- Calls `repo.update_status(document_id, APPROVED, current_status)`
- Calls `repo.update(document_id, InvoiceUpdate)` to preserve current data
- Calls `repo.create_audit_log()` for APPROVED event with actor and notes

**→ Response**: Updated InvoiceResponse

**→ Frontend Behavior**:
- Navigates to `/invoice/{document_id}` to show updated status

### RPA Queue Processing Workflow

**UiPath Workflow** (external):
- Polls `GET /api/rpa/queue`
- For each invoice in queue:
  - Calls `POST /api/rpa/{document_id}/start` with API key
  - Opens accounting app at ACCOUNTING_APP_URL
  - Automates form entry
  - Receives accounting record ID
  - Calls `POST /api/rpa/{document_id}/result` with success/failure

**→ Backend RPA Endpoints** (`backend/app/main.py`):
- **GET /api/rpa/queue**: Returns invoices with RPA_QUEUED status
- **POST /api/rpa/{document_id}/start**: Validates API key, updates status to RPA_PROCESSING, sets RPA job info
- **POST /api/rpa/{document_id}/result**: Validates API key, updates status to RPA_COMPLETED or RPA_FAILED, updates RPA status with message

**→ Database Updates**:
- Status transitions enforced by StateTransitionValidator
- RPA status updated with job_id, message, processed_at timestamp
- Audit logs track RPA_STARTED, RPA_COMPLETED, RPA_FAILED events

---

## 6. API Documentation

| Method | Path | Purpose | Request Body/Parameters | Response Structure | Important Status/Error Responses | Backend File/Function | Frontend Caller |
|--------|------|---------|----------------------|-------------------|--------------------------------|---------------------|----------------|
| GET | /api/health | Health check | None | HealthResponse (status, mongodb_connected, timestamp) | 200: healthy/unhealthy | main.py: health_check() | - |
| POST | /api/invoices/upload | Upload document | FormData with 'file' | UploadResponse (document_id, status) | 400: invalid file/size, 500: processing error | main.py: upload_invoice() | api.js: upload() |
| GET | /api/invoices | List invoices | Optional: status_filter, limit | InvoiceListResponse (invoices[], count) | 200: success, 404: not found | main.py: get_invoices() | api.js: getAll() |
| GET | /api/invoices/{document_id} | Get invoice | Path parameter: document_id | InvoiceResponse (full invoice object) | 404: invoice not found | main.py: get_invoice() | api.js: getById() |
| GET | /api/invoices/{document_id}/document | Download file | Path parameter: document_id | File (original document) | 404: file not found | main.py: get_document() | - |
| PUT | /api/invoices/{document_id} | Update invoice | Path: document_id, JSON body with fields | InvoiceResponse (updated invoice) | 404: not found, 400: invalid transition | main.py: update_invoice() | api.js: update() |
| POST | /api/invoices/{document_id}/approve | Approve invoice | Path: document_id, JSON: {document_id, reviewed_by, notes} | InvoiceResponse (updated invoice) | 404: not found, 400: invalid transition | main.py: approve_invoice() | api.js: approve() |
| POST | /api/invoices/{document_id}/reject | Reject invoice | Path: document_id, JSON: {document_id, reviewed_by, reason} | InvoiceResponse (updated invoice) | 404: not found, 400: invalid transition | main.py: reject_invoice() | api.js: reject() |
| GET | /api/rpa/queue | Get RPA queue | None | RPAQueueResponse (invoices[], count) | 200: success | main.py: get_rpa_queue() | api.js: getQueue() |
| POST | /api/rpa/{document_id}/start | Start RPA | Path: document_id, JSON: {document_id, api_key} | InvoiceResponse (updated invoice) | 401: invalid API key, 404: not found, 400: invalid transition | main.py: start_rpa() | api.js: start() |
| POST | /api/rpa/{document_id}/result | RPA result | Path: document_id, JSON: {document_id, api_key, success, accounting_record_id, message} | RPAResultResponse (success, message) | 401: invalid API key, 404: not found, 400: invalid transition | main.py: rpa_result() | api.js: result() |

---

## 7. Database

### MongoDB Implementation
**Database Name**: `document_ai_rpa` (configurable via MONGODB_DATABASE)
**Connection**: MongoDB via Motor (async driver) on localhost:27017
**Choice Reason**: Flexible document schema for varying invoice structures, natural fit for JSON-like invoice data, good for development without strict schema migrations

### Collections
**invoices**: Stores all invoice documents with full processing results
**audit_logs**: Stores audit trail of all state changes and user actions

### Document Structures

**Invoice Document** (simplified):
```json
{
  "document_id": "DOC-ABC123DEF456",
  "original_filename": "invoice.pdf",
  "status": "APPROVED",
  "vendor": {"name": "Example Supplies LLC", "address": null},
  "invoice_number": "INV-1001",
  "invoice_date": "2024-01-01",
  "due_date": "2024-01-30",
  "currency": "USD",
  "subtotal": 1000.00,
  "tax": 80.00,
  "total": 1080.00,
  "line_items": [],
  "extraction": {
    "overall_confidence": 0.94,
    "fields": {
      "vendor_name": {"value": "Example Supplies LLC", "confidence": 0.98},
      "invoice_number": {"value": "INV-1001", "confidence": 0.95}
    },
    "raw_ocr_text": "...",
    "page_count": 1
  },
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  },
  "review": {
    "required": false,
    "reviewed_by": null,
    "reviewed_at": null
  },
  "rpa": {
    "eligible": true,
    "status": "RPA_COMPLETED",
    "job_id": "JOB-DOC-ABC123",
    "message": "RPA completed successfully",
    "processed_at": "2024-01-01T12:00:00"
  },
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**AuditLog Document** (simplified):
```json
{
  "id": "audit-uuid",
  "document_id": "DOC-ABC123DEF456",
  "event": "APPROVED",
  "actor": "John Doe",
  "old_status": "NEEDS_REVIEW",
  "new_status": "APPROVED",
  "message": "Invoice approved after review",
  "timestamp": "2024-01-01T12:00:00"
}
```

### Important Fields
**document_id**: Unique identifier (format: DOC-XXXXXXXXXXXX)
**status**: Invoice status from InvoiceStatus enum (11 possible states)
**extraction.overall_confidence**: 0.0-1.0 average of field confidences
**extraction.fields**: Dict of field_name → {value, confidence}
**validation.is_valid**: Boolean validation result
**validation.errors**: List of critical validation failures
**validation.warnings**: List of non-critical issues
**rpa.eligible**: Whether invoice qualifies for RPA
**rpa.status**: RPA processing stage

### Relationships/References
- AuditLog documents reference document_id (not foreign key, just string)
- No explicit foreign key relationships (MongoDB document database)
- RPA job_id stored in invoice.rpa.job_id for tracking

### Indexes
**invoices collection**:
- document_id (unique)
- vendor.name + invoice_number (compound)
- status
- created_at

**audit_logs collection**:
- document_id
- timestamp

### Repository/Database Functions
**InvoiceRepository** (`backend/app/services/repository.py`):
- `create_indexes()`: Creates all MongoDB indexes on startup
- `create(invoice)`: Inserts new invoice document
- `get_by_document_id(document_id)`: Finds invoice by document_id
- `get_all(status, limit)`: Returns invoices with optional status filter
- `update(document_id, update_data)`: Updates invoice fields
- `update_status(document_id, new_status, old_status)`: Changes status with validation
- `update_extraction/update_validation/update_rpa_status()`: Updates specific sections
- `find_duplicates(vendor_name, invoice_number)`: Finds potential duplicates
- `get_rpa_queue()`: Returns invoices with RPA_QUEUED status
- `create_audit_log(audit_log)`: Inserts audit log entry
- `get_audit_logs(document_id)`: Returns audit trail for document

### Database Flow (Beginner-Friendly)
1. Application starts → Database singleton connects to MongoDB
2. Indexes created on first startup (idempotent)
3. Upload endpoint creates invoice document with PROCESSING status
4. Processing updates document with extraction, validation, final status
5. All updates use MongoDB $set operations with timestamp
6. Audit logs created for every state change
7. Frontend queries by document_id or filters by status
8. Repository methods use Motor async operations (await)

---

## 8. Document AI / OCR Pipeline

### Exact Processing Steps for Uploaded PDF/Image

**File Validation** (`main.py: upload_invoice()`):
- Validates MIME type: application/pdf, image/png, image/jpeg, image/jpg
- Validates file size: max 10MB (configurable via MAX_UPLOAD_SIZE_MB)
- Returns 400 error if validation fails

**PDF Handling** (`pdf_processor.py: PDFProcessor`):
- `process_document(file_bytes, filename)`: Routes to pdf_to_images() or image_to_image()
- `pdf_to_images()`: Opens PDF with PyMuPDF, iterates pages, renders to 300 DPI images
- `image_to_image()`: Opens image bytes with PIL, returns as single-item list
- Returns tuple: (list of PIL Images, page_count)

**Image Conversion** (`pdf_processor.py`):
- PyMuPDF page.get_pixmap(dpi=300) converts PDF page to image
- pix.tobytes("png") converts to PNG bytes
- PIL.Image.open() creates PIL Image from bytes
- Supports PDF, PNG, JPG, JPEG, TIFF, BMP formats

**Image Preprocessing** (`image_preprocessor.py: ImagePreprocessor`):
- Converts PIL Image to OpenCV grayscale format
- `preprocess()` method runs pipeline:
  - Quality estimation using Laplacian variance
  - Deskewing using contour analysis and rotation matrix
  - Contrast enhancement using CLAHE (Contrast Limited Adaptive Histogram Equalization)
  - Denoising using median blur (if quality < 0.5)
- Returns preprocessed PIL Image

**OCR** (`ocr_service.py: OCRService`):
- Lazy initialization of PaddleOCR (use_angle_cls=True, lang='en')
- Converts PIL Image to OpenCV BGR format
- `ocr.ocr(cv_image, cls=True)` returns text with confidence and bounding boxes
- Returns dict: {text, raw_results[{text, confidence, bbox}], confidence_mean, confidence_min, engine: 'paddle'}

**Text Extraction** (`ocr_service.py: extract_text_from_images()`):
- Processes multiple pages sequentially
- Combines text from all pages with newlines
- Aggregates confidences across all pages
- Returns combined results with page_count

**Field Extraction** (`invoice_extractor.py: InvoiceExtractor`):
- Uses regex patterns to identify structured fields from OCR text
- Patterns defined in __init__ for invoice_number, dates, vendor, amounts, currency
- `_extract_vendor()`: Checks first 5 lines for company name patterns
- `_extract_invoice_number()`: Matches Invoice #, Bill #, INV- patterns
- `_extract_invoice_date()`: Matches date patterns after keywords
- `_extract_total()`: Matches total, grand total, amount due patterns
- `_find_confidence_for_text()`: Maps extracted text to OCR confidence scores
- Returns dict: {fields: {field_name: {value, confidence}}, overall_confidence}

**Confidence Scores**:
- OCR provides per-text-segment confidence (0.0-1.0)
- Field confidence = average confidence of matching OCR text segments
- Overall confidence = average of all field confidences
- Default confidence = 0.7 if no match found

**Missing Fields**:
- If regex pattern doesn't match, field not included in results
- ValidationService checks required fields, generates error if missing
- Low confidence doesn't exclude field but may trigger NEEDS_REVIEW

**Poor-Quality Documents**:
- ImagePreprocessor estimates quality using Laplacian variance
- If quality < 0.5, applies denoising to improve OCR
- Low confidence scores may still result from poor scans
- Validation may flag warnings but doesn't automatically reject

**Validation** (`validation_service.py: ValidationService`):
- Checks required fields exist and have values
- Checks confidence against threshold (default 0.80)
- Validates date sequences (due date not before invoice date)
- Validates amount arithmetic (subtotal + tax ≈ total)
- Returns {is_valid: bool, errors: [], warnings: []}

**Error Handling**:
- ProcessingService wraps entire pipeline in try/catch
- On error, sets invoice status to ERROR
- Creates audit log with PROCESSING_ERROR event
- Returns error status to frontend

### OCR vs Document Preprocessing vs Information Extraction vs Validation
- **OCR**: Converting image pixels to text characters (PaddleOCR)
- **Document preprocessing**: Enhancing image quality for better OCR (OpenCV)
- **Information/field extraction**: Converting unstructured text to structured fields (regex patterns)
- **Validation**: Checking extracted data against business rules (ValidationService)

### PaddleOCR Usage in This Codebase
- Lazy initialization in `_get_ocr_engine()` method
- Used with `use_angle_cls=True` for better text detection
- English language only (`lang='en'`)
- Returns confidence scores per text segment
- Multi-page support by processing images sequentially
- No custom model training, uses pre-trained models

---

## 9. Invoice Extraction

### Fields Extracted
- vendor_name: Company name (first 5 lines, company suffix patterns)
- invoice_number: Invoice identifier (Invoice #, Bill #, INV- patterns)
- invoice_date: Invoice date (date patterns, normalized format)
- due_date: Payment due date (due date patterns, normalized format)
- total: Total amount (total, grand total, amount due patterns)
- currency: Currency code (USD, EUR, GBP, CAD or symbol detection)
- subtotal: Subtotal amount (subtotal pattern)
- tax: Tax amount (tax, vat, gst, hst patterns)

### Extraction Rules/Logic
**InvoiceExtractor** (`backend/app/document_ai/invoice_extractor.py`):
- Uses multiple regex patterns per field for robustness
- Vendor: checks first 5 lines for company patterns (LLC, Inc, Corp, Ltd)
- Invoice number: must contain both letters and numbers
- Dates: normalized to YYYY-MM-DD format via parse_date()
- Amounts: cleaned of commas, converted to float
- Currency: detects codes (USD, EUR) or symbols ($, €, £, ¥)
- Confidence: average of OCR confidences for matching text segments

### Confidence Handling
- Each field gets confidence from matching OCR text segments
- `_find_confidence_for_text()` searches raw OCR results for matching text
- If no match found, defaults to 0.7
- Overall confidence = average of all field confidences
- ValidationService compares field confidence against threshold (0.80)

### Missing Fields
- If regex doesn't match, field omitted from results
- ValidationService adds error: "Missing required field: {field}"
- Invoice cannot be APPROVED with missing required fields
- Status becomes REJECTED if validation fails

### Invalid Values
- Invalid dates filtered out by parse_date() returning None
- Invalid amounts filtered out by float() conversion raising ValueError
- Negative amounts flagged as error by ValidationService
- Date sequence errors flagged as error (due date before invoice date)

### Totals/Dates/Vendor Handling
- **Totals**: Extracted from patterns like "Total: $100.00", converted to float
- **Dates**: Multiple patterns (MM/DD/YYYY, YYYY-MM-DD), normalized via parse_date()
- **Vendor**: Extracted from document start, looks for company suffixes
- **Currency**: Extracted from context or defaults to USD

### Assumptions
- English documents only (PaddleOCR lang='en')
- Invoice number contains both letters and numbers
- Company name in first 5 lines with business suffix
- Date in common formats
- Amounts with standard formatting ($1,000.00, 1000.00)
- Single currency per document

### Simple Example
**Raw OCR text**: "Invoice #INV-1234\nDate: 01/15/2024\nVendor: ABC Corp\nTotal: $500.00"
**Extraction logic**: Regex patterns match each field → extract values → map to OCR confidence
**Structured object**: {vendor_name: {value: "ABC Corp", confidence: 0.95}, invoice_number: {value: "INV-1234", confidence: 0.92}, invoice_date: {value: "2024-01-15", confidence: 0.88}, total: {value: 500.0, confidence: 0.90}}

---

## 10. Validation and State Management

### Validation Rules
**ValidationService** (`backend/app/validation/validation_service.py`):
- **Required fields**: vendor_name, invoice_number, invoice_date, total, currency
- **Confidence threshold**: Default 0.80, configurable via CONFIDENCE_THRESHOLD
- **Date validation**: Due date cannot be before invoice date
- **Amount validation**: Subtotal + tax should approximately equal total (within tolerance)
- **Negative amounts**: Not allowed, flagged as error

### Validation Service
**File**: `backend/app/validation/validation_service.py`
**Class**: ValidationService
**Methods**:
- `validate(extracted_fields)`: Runs all validation rules, returns {is_valid, errors, warnings}
- `determine_status(validation_result, overall_confidence)`: Returns APPROVED/NEEDS_REVIEW/REJECTED based on results

### State Transition Logic
**StateTransitionValidator** (`backend/app/validation/state_transitions.py`):
- **VALID_TRANSITIONS dict**: Defines allowed status changes
- **Example**: UPLOADED → PROCESSING, PROCESSING → PROCESSED/NEEDS_REVIEW/ERROR
- **validate_transition()**: Returns (is_valid, error_message) for transition
- Enforced in all status update endpoints (approve, reject, RPA endpoints)

### Invoice/Document States
**InvoiceStatus enum** (`backend/app/models/invoice.py`):
- UPLOADED: Initial state after file received
- PROCESSING: OCR/extraction in progress
- PROCESSED: Extraction complete (intermediate state)
- NEEDS_REVIEW: Low confidence or validation warnings
- APPROVED: Valid and high confidence, ready for RPA
- REJECTED: Validation errors
- RPA_QUEUED: In RPA queue waiting for UiPath
- RPA_PROCESSING: UiPath actively processing
- RPA_COMPLETED: RPA entered data successfully
- RPA_FAILED: RPA processing failed
- ERROR: Processing pipeline failed

### Allowed State Transitions
- UPLOADED → PROCESSING, ERROR
- PROCESSING → PROCESSED, NEEDS_REVIEW, ERROR
- PROCESSED → NEEDS_REVIEW, APPROVED, REJECTED
- NEEDS_REVIEW → APPROVED, REJECTED
- APPROVED → RPA_QUEUED
- REJECTED → (no transitions allowed)
- RPA_QUEUED → RPA_PROCESSING
- RPA_PROCESSING → RPA_COMPLETED, RPA_FAILED
- RPA_COMPLETED → (no transitions allowed)
- RPA_FAILED → RPA_QUEUED (retry)
- ERROR → PROCESSING (retry)

### Review Triggers
- **Low confidence**: overall_confidence < 0.80
- **Validation warnings**: Any warning from ValidationService
- **Validation errors**: Status becomes REJECTED (not review)

### Confidence Thresholds
- **Default**: 0.80 (configurable via CONFIDENCE_THRESHOLD)
- **Field-level**: Each field must have confidence >= threshold to avoid warning
- **Overall**: Average of all field confidences
- **Purpose**: Routes low-confidence extractions to human review

### Invalid Document Handling
- **Validation errors**: Status becomes REJECTED, cannot be approved
- **Processing errors**: Status becomes ERROR, can be retried
- **Missing required fields**: Validation error, status REJECTED
- **Negative amounts**: Validation error, status REJECTED

### State Diagram
```
UPLOADED → PROCESSING → PROCESSED → NEEDS_REVIEW → APPROVED → RPA_QUEUED → RPA_PROCESSING → RPA_COMPLETED
                           ↓               ↓          ↓
                         ERROR          REJECTED    (no transitions)
```

---

## 11. Frontend Architecture

### React Application Entry Point
**File**: `frontend/src/main.jsx`
- Renders App component into root DOM element
- Imports CSS for Tailwind and custom styles

### Vite Configuration
**File**: `frontend/vite.config.js`
- Configures proxy for /api requests to backend port 8000
- React plugin enabled
- Dev server on port 3000 (or 3001 if occupied)

### Routing
**File**: `frontend/src/App.jsx`
- React Router with BrowserRouter
- Routes: / (Dashboard), /upload (Upload), /invoice/:documentId (InvoiceDetails), /review/:documentId (Review)
- Navigation handled by Sidebar component

### Pages
**Dashboard** (`frontend/src/pages/Dashboard.jsx`):
- Displays statistics cards (total, processing, needs review, approved, RPA completed, RPA failed)
- Shows invoice table with status badges and action links
- Provides upload CTA and empty state guidance

**Upload** (`frontend/src/pages/Upload.jsx`):
- Drag-and-drop file upload interface
- File validation (type, size)
- Upload progress and processing pipeline explanation
- Auto-redirect to invoice details on success

**InvoiceDetails** (`frontend/src/pages/InvoiceDetails.jsx`):
- Displays invoice information, extraction results, validation results, RPA status
- Shows confidence indicators with color coding
- Provides review link if status is NEEDS_REVIEW

**Review** (`frontend/src/pages/Review.jsx`):
- Editable form for invoice fields
- Shows extraction confidence and validation errors/warnings
- Approval/rejection actions with name and notes/reason
- Links to original document

### Components
**Sidebar** (`frontend/src/components/Sidebar.jsx`):
- Navigation menu with icons
- Active page highlighting
- Mobile-responsive with hamburger menu
- User profile section

### API Service Layer
**File**: `frontend/src/services/api.js`
- Axios instance configured with base URL /api
- invoiceAPI object: upload, getAll, getById, update, approve, reject, getDocument
- rpaAPI object: getQueue, start, result
- healthAPI object: check

### State Management
- Local component state using useState hooks
- No global state management (Redux, Context API not used)
- Data fetched on component mount via useEffect
- Simple, component-level state is sufficient for this application

### CSS/Tailwind/Styling System
- Tailwind CSS v3.4.19 for utility-first styling
- Custom primary color palette (indigo/violet shades) in tailwind.config.js
- PostCSS with Tailwind and Autoprefixer plugins
- Modern, clean design with subtle borders and shadows
- Responsive design with mobile sidebar

### Forms
- Controlled components using useState
- Form validation before submission
- Error handling with user-friendly messages
- Loading states during async operations

### Upload Workflow
- Drag-and-drop interface with visual feedback
- File type and size validation
- Upload progress indication
- Processing pipeline explanation
- Auto-redirect to details on success

### Review Workflow
- Pre-populated form with current extraction data
- Field editing with validation
- Confidence display with color coding
- Approval/rejection with required fields (reviewed_by, reason)
- Audit trail integration

### Dashboard
- Statistics cards with counts by status
- Invoice table with status badges and action links
- Empty state with clear CTA
- Quick access to upload functionality

### Invoice Details
- Two-column layout (main content + sidebar)
- Invoice information with all fields
- Extraction results with confidence indicators
- Validation results with errors/warnings
- RPA status tracking
- Action buttons based on status

### Frontend-Backend Communication
- Axios HTTP client with base URL /api
- Vite proxy forwards /api requests to http://127.0.0.1:8000
- JSON request/response bodies
- File uploads as FormData with multipart/form-data
- Error handling with try/catch and user messages

---

## 12. Frontend → Backend Communication

### Document Upload
**Frontend** (`frontend/src/pages/Upload.jsx` → `invoiceAPI.upload(file)`)
→ **HTTP POST /api/invoices/upload** (FormData with file)
→ **Backend** (`main.py: upload_invoice()`) → ProcessingService → Repository → MongoDB
→ **Response**: UploadResponse {document_id, status}
→ **Frontend**: Shows success, redirects to `/invoice/{document_id}`

### Get Invoice List
**Frontend** (`frontend/src/pages/Dashboard.jsx` → `invoiceAPI.getAll()`)
→ **HTTP GET /api/invoices** (optional status_filter, limit params)
→ **Backend** (`main.py: get_invoices()`) → Repository.get_all() → MongoDB
→ **Response**: InvoiceListResponse {invoices[], count}
→ **Frontend**: Updates state, displays table

### Get Invoice Details
**Frontend** (`frontend/src/pages/InvoiceDetails.jsx` → `invoiceAPI.getById(documentId)`)
→ **HTTP GET /api/invoices/{document_id}`
→ **Backend** (`main.py: get_invoice()`) → Repository.get_by_document_id() → MongoDB
→ **Response**: InvoiceResponse (full invoice object)
→ **Frontend**: Displays invoice details with extraction/validation

### Update Invoice
**Frontend** (`frontend/src/pages/Review.jsx` → `invoiceAPI.update(documentId, data)`)
→ **HTTP PUT /api/invoices/{document_id}` (JSON body with fields)
→ **Backend** (`main.py: update_invoice()`) → Repository.update() → MongoDB
→ **Response**: InvoiceResponse (updated invoice)
→ **Frontend**: Shows success alert, keeps user on review page

### Approve Invoice
**Frontend** (`frontend/src/pages/Review.jsx` → `invoiceAPI.approve(documentId, reviewedBy, notes)`)
→ **HTTP POST /api/invoices/{document_id}/approve` (JSON with document_id, reviewed_by, notes)
→ **Backend** (`main.py: approve_invoice()`) → StateTransitionValidator → Repository.update_status() → Repository.create_audit_log() → MongoDB
→ **Response**: InvoiceResponse (updated invoice)
→ **Frontend**: Navigates to invoice details page

### Reject Invoice
**Frontend** (`frontend/src/pages/Review.jsx` → `invoiceAPI.reject(documentId, reviewedBy, reason)`)
→ **HTTP POST /api/invoices/{document_id}/reject` (JSON with document_id, reviewed_by, reason)
→ **Backend** (`main.py: reject_invoice()`) → StateTransitionValidator → Repository.update_status() → Repository.create_audit_log() → MongoDB
→ **Response**: InvoiceResponse (updated invoice)
→ **Frontend**: Navigates to invoice details page

### Get RPA Queue
**Frontend**: (not used in current frontend, available for UiPath)
→ **HTTP GET /api/rpa/queue**
→ **Backend** (`main.py: get_rpa_queue()`) → Repository.get_rpa_queue() → MongoDB
→ **Response**: RPAQueueResponse {invoices[], count}

### Start RPA Processing
**Frontend**: (not used in current frontend, available for UiPath)
→ **HTTP POST /api/rpa/{document_id}/start` (JSON with document_id, api_key)
→ **Backend** (`main.py: start_rpa()`) → StateTransitionValidator → Repository.update_status() → Repository.update_rpa_status() → MongoDB
→ **Response**: InvoiceResponse (updated invoice)

### RPA Result Callback
**Frontend**: (not used in current frontend, available for UiPath)
→ **HTTP POST /api/rpa/{document_id}/result` (JSON with document_id, api_key, success, accounting_record_id, message)
→ **Backend** (`main.py: rpa_result()`) → StateTransitionValidator → Repository.update_status() → Repository.update_rpa_status() → Repository.create_audit_log() → MongoDB
→ **Response**: RPAResultResponse {success, message}

---

## 13. Docker and Local Infrastructure

### Docker Compose Configuration
**File**: `docker-compose.yml`
**Service**: Single MongoDB 7.0 container
**Image**: mongo:7.0
**Container Name**: document-ai-rpa-mongodb
**Ports**: 27017:27017 (host:container)
**Volumes**: mongodb_data (persists database data)
**Environment**: MONGO_INITDB_DATABASE=document_ai_rpa
**Version**: Removed 'version: 3.8' field (obsolete in Docker Compose)

### What Docker Is Doing
- Running MongoDB in a container instead of local installation
- Persisting database data in Docker volume
- Exposing MongoDB on localhost:27017
- Isolating database from host system

### Docker vs Docker Desktop vs Docker Engine vs Docker CLI vs Docker Compose vs Container vs Image
- **Docker**: Containerization platform
- **Docker Desktop**: Mac/Windows application that includes Docker Engine, CLI, Compose
- **Docker Engine**: Background service that runs containers
- **Docker CLI**: Command-line interface (docker, docker-compose commands)
- **Docker Compose**: Tool for defining multi-container applications (docker-compose.yml)
- **Container**: Running instance of an image (MongoDB container)
- **Image**: Read-only template for containers (mongo:7.0 image)

### In This Project
- **Docker Compose**: Orchestrates MongoDB container
- **Docker Image**: mongo:7.0 (downgraded from 8.0 for compatibility)
- **Docker Container**: document-ai-rpa-mongodb (running MongoDB)
- **Docker Volume**: mongodb_data (data persistence)

### What Docker Is NOT Responsible For
- Not running FastAPI backend (runs directly via Python)
- Not running React frontend (runs directly via npm/Vite)
- Not running Flask accounting app (runs directly via Python)
- Not running UiPath (external Windows application)

### What Happens When Running `docker compose up -d`
1. Docker Compose reads docker-compose.yml
2. Pulls mongo:7.0 image if not present locally
3. Creates container named document-ai-rpa-rpa-mongodb
4. Maps host port 27017 to container port 27017
5. Creates volume mongodb_data for data persistence
6. Sets environment variable MONGO_INITDB_DATABASE
7. Starts MongoDB in background (-d flag)
8. Container continues running until `docker compose down`

### What Happens When Stopping/Restarting Docker Desktop
- **Stop**: All containers stop, but data persists in volumes
- **Restart**: Containers restart, data persists in volumes
- **Data loss**: Only if volumes are deleted (`docker compose down -v` removes volumes)

---

## 14. Environment Variables and Configuration

### Important Configuration Values
**File**: `.env` (not committed to git, copy from .env.example)

```bash
MONGODB_URI=mongodb://localhost:27017          # MongoDB connection string
MONGODB_DATABASE=document_ai_rpa              # Database name
STORAGE_PATH=./storage                      # Local file storage path
MAX_UPLOAD_SIZE_MB=10                        # Maximum file upload size
CONFIDENCE_THRESHOLD=0.80                     # OCR confidence threshold for routing
API_HOST=127.0.0.1                             # Backend server host
API_PORT=8000                                  # Backend server port
ACCOUNTING_APP_URL=http://localhost:3001    # Simulated accounting app URL
RPA_API_KEY=change-me                          # API key for RPA endpoints (SECRET)
```

### Backend Configuration
**File**: `backend/app/config.py`
- Settings class loads from .env using pydantic-settings
- Default values provided for all configuration
- CORS origins configured for frontend development ports

### Frontend Configuration
**File**: `frontend/vite.config.js`
- Proxy configured: /api → http://127.0.0.1:8000
- Dev server port: 3000 (may use 3001 if occupied)

### Database Connection
- MONGODB_URI: Connection string for MongoDB
- MONGODB_DATABASE: Database name within MongoDB

### Ports
- Backend: 8000 (configurable via API_HOST/API_PORT)
- Frontend: 3000 (Vite default, may use 3001 if occupied)
- MongoDB: 27017 (Docker)
- Accounting App: 3001 (Flask)

### Storage Paths
- STORAGE_PATH: ./storage (base path for file storage)
- Documents stored in: storage/documents/{document_id}/original/

### Upload Limits
- MAX_UPLOAD_SIZE_MB: 10 (maximum file size in megabytes)

### OCR Confidence Thresholds
- CONFIDENCE_THRESHOLD: 0.80 (default threshold for routing decisions)

### Accounting Application URL
- ACCOUNTING_APP_URL: http://localhost:3001 (target for RPA automation)

### Secrets
- **RPA_API_KEY**: MUST be changed in production, validates RPA requests
- **.env file**: MUST NOT be committed to git (in .gitignore)

---

## 15. RPA / UiPath

### Purpose of RPA Workflow
Automate data entry of approved invoices into accounting system, eliminating manual data entry for high-confidence extractions.

### RPA Code/Configuration Location
**Directory**: `rpa/UiPath/InvoiceProcessor/`
**File**: `Workflow_Guide.md` (step-by-step implementation guide)
**Status**: Documentation only, requires manual UiPath Studio implementation

### What UiPath Does
- Polls GET /api/rpa/queue for APPROVED invoices
- Calls POST /api/rpa/{document_id}/start to begin processing
- Opens simulated accounting app at ACCOUNTING_APP_URL
- Automates form entry with invoice data (vendor, invoice number, dates, amounts)
- Submits form and receives accounting record ID
- Calls POST /api/rpa/{document_id}/result with success/failure and record ID

### What Triggers the Workflow
- Invoice status changes to APPROVED
- Invoice automatically becomes eligible for RPA (rpa.eligible = true)
- External UiPath workflow polls queue and processes

### Information Passed to It
- Invoice data: vendor, invoice_number, invoice_date, due_date, currency, subtotal, tax, total
- Document ID for tracking
- API key for authentication
- Accounting app URL for form automation

### Interaction with Simulated Accounting App
- Opens http://localhost:3001/new-invoice
- Fills form fields with invoice data
- Submits form
- Receives accounting record ID (ACC-XXXXXXXX)
- Returns record ID via RPA result callback

### What Is Simulated vs Real
- **Simulated**: Accounting application (Flask, in-memory storage)
- **Simulated**: UiPath workflow (documentation only, requires manual implementation)
- **Real**: Backend API endpoints for RPA integration
- **Real**: Status transitions and audit logging

### Important Workflow Steps
1. Initialize configuration (API base URL, API key, accounting app URL)
2. While loop polling RPA queue
3. For each invoice: GET /api/rpa/queue
4. If invoice available: POST /api/rpa/{document_id}/start
5. Open accounting app, automate form entry
6. Submit form, capture accounting record ID
7. POST /api/rpa/{document_id}/result with success=true and accounting_record_id
8. Wait 30 seconds, continue polling

### Assumptions/Limitations
- UiPath Studio Community Edition required (Windows only)
- Manual implementation required (only documentation provided)
- Accounting app must be running on port 3001
- API key must match RPA_API_KEY configuration
- No retry logic for failed RPA attempts (manual retry required)

---

## 16. Simulated Accounting Application

### Why It Exists
Provides a realistic target system for RPA automation demonstration without requiring real accounting system access or credentials.

### Technology Used
**Framework**: Flask (Python web framework)
**Python**: 3.10-3.13 (same as backend)
**Storage**: In-memory Python list (resets on restart)
**Port**: 3001

### How It Starts
**Command**: `python app.py` (from simulated-accounting-app directory)
**Virtual environment**: Required (python3 -m venv venv, source venv/bin/activate)
**Dependencies**: Flask only (minimal requirements.txt)

### Important Routes/Pages
- **GET /**: Dashboard showing all accounting records
- **GET /new-invoice**: Form to create new invoice
- **POST /new-invoice**: Creates record, generates ACC-XXXXXXXX ID, shows success page
- **GET /record/<accounting_id>**: View specific accounting record

### How Invoices Are Created/Viewed
- **Created**: Via form at /new-invoice, user enters all invoice fields
- **Record ID**: Generated as ACC-{uuid hex[:8].upper()}
- **Viewed**: Via /record/<accounting_id> page shows all record details
- **Storage**: In-memory list (accounting_records), resets on app restart

### How RPA Interacts with It
- UiPath workflow POSTs to /new-invoice with form data
- Accounting app validates and creates record
- Returns success page with accounting record ID
- RPA workflow captures ID and reports back to backend

### How It Fits into Overall Project
- Demonstrates RPA target system without requiring real accounting credentials
- Provides realistic form automation target for UiPath workflow
- Allows end-to-end testing of complete automation pipeline
- Data flows: Backend → RPA → Accounting App → Backend

---

## 17. Testing

### Testing Architecture
**Unit Tests**: Test individual functions and classes in isolation
**Integration Tests**: Test API endpoints against test database
**End-to-End Tests**: Test complete workflows through all components

### Important Test Files
**backend/tests/test_validators.py**: Tests validator functions (parse_date, parse_amount, validate_date_sequence, validate_amounts)
**backend/tests/test_invoice_extractor.py**: Tests InvoiceExtractor regex patterns and confidence calculation
**backend/tests/test_validation_service.py**: Tests ValidationService rules and status determination
**backend/tests/test_state_transitions.py**: Tests StateTransitionValidator allowed transitions
**backend/tests/test_api.py**: Tests API endpoints with test database
**tests/e2e/test_workflow.py**: End-to-end workflow test

### What Each Group Verifies
- **Unit tests**: Validator functions, extraction logic, validation rules, state transitions
- **Integration tests**: API endpoints, database operations, error handling
- **E2E tests**: Complete upload → processing → validation → approval workflow

### How Tests Are Run
```bash
cd backend
source venv/bin/activate
pytest tests/              # Run all unit tests
pytest tests/test_api.py     # Run API integration tests
pytest tests/e2e/           # Run end-to-end tests
```

### Important Fixtures
**backend/tests/conftest.py**: Pytest configuration, provides test database setup/teardown

### External Services Required
- MongoDB (for integration and E2E tests)
- No external services required for unit tests

### Test Coverage
- **Strong coverage**: Validators, extraction logic, validation service, state transitions
- **Limited coverage**: OCR service (requires heavy PaddleOCR), image preprocessing (requires models)
- **No coverage**: RPA workflow (external UiPath), accounting app (manual testing only)

---

## 18. Dependencies

### Backend Dependencies (requirements.txt)
**Core Framework**:
- **fastapi**: Modern async web framework
- **uvicorn**: ASGI server to run FastAPI
- **pydantic**: Data validation and settings management
- **pydantic-settings**: Load configuration from .env

**Database**:
- **pymongo**: Synchronous MongoDB driver (used for some operations)
- **motor**: Async MongoDB driver for FastAPI async operations

**OCR & Document Processing**:
- **paddleocr**: OCR engine with confidence scores
- **opencv-python**: Image preprocessing
- **pymupdf**: PDF to image conversion
- **Pillow**: PIL Image operations
- **numpy**: Array operations for OpenCV

**API Clients**:
- **httpx**: HTTP client (not directly used, axios used in frontend)

**Configuration & Environment**:
- **python-dotenv**: Load .env file
- **python-multipart**: Multipart form data handling

**Testing**:
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **httpx[pytest]**: HTTP client for API tests

### Frontend Dependencies (package.json)
**Runtime**:
- **react**: UI framework
- **react-dom**: React DOM rendering
- **react-router-dom**: Client-side routing
- **axios**: HTTP client for API communication

**Development**:
- **vite**: Build tool and dev server
- **@vitejs/plugin-react**: React plugin for Vite
- **tailwindcss**: CSS framework
- **postcss**: PostCSS processing
- **autoprefixer**: CSS vendor prefixing

### Development vs Runtime Dependencies
- **Development**: tailwindcss, postcss, autoprefixer, vite, @vitejs/plugin-react, pytest
- **Runtime**: fastapi, uvicorn, pydantic, pymongo, motor, paddleocr, opencv-python, pymupdf, Pillow, numpy, react, react-dom, react-router-dom, axios, python-dotenv, python-multipart

---

## 19. Git / .gitignore

### Files to Commit
- All source code files
- Configuration files (docker-compose.yml, tailwind.config.js, vite.config.js, postcss.config.js)
- Documentation files (README.md, SETUP.md, Workflow_Guide.md)
- Package files (package.json, package-lock.json, requirements.txt)
- Template files (.env.example)

### Files NOT to Commit
- **.env**: Contains secrets (RPA_API_KEY) and local configuration
- **venv/**: Python virtual environment (large, regenerated per machine)
- **node_modules/**: Node.js dependencies (large, regenerated per machine)
- **storage/documents/**: Uploaded documents (user data, should not be in git)
- **__pycache__/**: Python bytecode cache (regenerated)
- **.pytest_cache/**: Pytest cache (regenerated)
- **dist/**: Frontend build output (regenerated)
- **.DS_Store**: macOS metadata files

### Why Specific Rules
- **.env ignored**: Contains RPA_API_KEY secret and local configuration differences
- **venv ignored**: Virtual environment is machine-specific and large
- **node_modules ignored**: Dependencies are large and regenerated by npm install
- **storage/documents ignored**: Contains user-uploaded documents (privacy, disk space)
- **Generated files ignored**: Build artifacts and cache files are regenerated

### Additional Important Rules
- **Uploaded documents**: Excluded to prevent committing user data
- **Build artifacts**: Excluded to keep repository clean
- **Cache files**: Excluded to avoid conflicts

---

## 20. Important Design Decisions

### MongoDB vs PostgreSQL
**Decision**: MongoDB as sole database
**Reason**: Master specification explicitly required MongoDB only, PostgreSQL removed
**Alternatives**: PostgreSQL with relational schema
**Tradeoffs**: MongoDB offers flexible schema for varying invoice structures, but lacks ACID guarantees of relational databases

### Synchronous vs Async Processing
**Decision**: Synchronous FastAPI processing, no Redis/Celery
**Reason**: Master specification explicitly forbade Redis/Celery, simplified architecture
**Alternatives**: Redis + Celery for background task processing
**Tradeoffs**: Simpler deployment but processing blocks HTTP requests during OCR

### PaddleOCR vs Tesseract/Google Document AI
**Decision**: PaddleOCR only
**Reason**: Master specification required PaddleOCR only, others removed
**Alternatives**: Tesseract (fallback OCR), Google Document AI (cloud service)
**Tradeoffs**: PaddleOCR provides good accuracy with confidence scores, but requires heavy installation

### PyMuPDF vs pdf2image
**Decision**: PyMuPDF for PDF processing
**Reason**: Master specification required PyMuPDF, pdf2image removed
**Alternatives**: pdf2image (requires external Ghostscript)
**Tradeoffs**: PyMuPDF is self-contained, pdf2image requires system Ghostscript installation

### FastAPI vs Flask/Django
**Decision**: FastAPI for backend API
**Reason**: Modern async framework, automatic documentation, async MongoDB support
**Alternatives**: Flask (synchronous), Django (opinionated, heavier)
**Tradeoffs**: FastAPI is lighter and more modern, but Django has more built-in features

### React vs Vanilla JS/Vue/Angular
**Decision**: React for frontend
**Reason**: Modern component-based framework, good ecosystem, Tailwind CSS integration
**Alternatives**: Vanilla JS (no components), Vue (simpler but smaller ecosystem), Angular (opinionated)
**Tradeoffs**: React has larger ecosystem but steeper learning curve than vanilla JS

### Docker vs Local MongoDB
**Decision**: Docker Compose for MongoDB containerization
**Reason**: Consistent environment, easy setup, data persistence
**Alternatives**: Local MongoDB installation (system-specific setup)
**Tradeoffs**: Docker adds overhead but provides consistency; local installation is faster but system-specific

### Simulated vs Real Accounting System
**Decision**: Simulated Flask app
**Reason**: No access to real accounting system credentials, demonstration purposes
**Alternatives: Real SAP/QuickBooks integration (requires credentials)
**Tradeoffs**: Simulated app resets on restart, real system would provide persistence

### Regex vs ML/Template-Based Extraction
**Decision**: Regex patterns for field extraction
**Reason**: Simpler implementation, no training data required, reasonable accuracy for structured invoices
**Alternatives**: Machine learning models, template matching
**Tradeoffs**: Regex is brittle but interpretable; ML requires training data and is less transparent

### Confidence-Based vs Fixed Threshold Routing
**Decision**: Confidence-based routing (0.80 threshold)
**Reason**: Master specification required confidence-based routing, not fixed amount threshold
**Alternatives**: Fixed amount threshold ($10,000), manual review for all
**Tradeoffs**: Confidence-based adapts to extraction quality but requires threshold tuning

### State Machine vs Boolean Flags
**Decision**: State machine with explicit transitions (StateTransitionValidator)
**Reason**: Enforces valid business logic, prevents invalid state changes
**Alternatives**: Boolean flags (is_approved, is_reviewed)
**Tradeoffs**: State machine is more complex but prevents invalid states

### Local File Storage vs Cloud Storage
**Decision**: Local file system (storage/documents/)
**Reason**: Simpler setup, no external service dependencies
**Alternatives**: S3, Azure Blob Storage, Google Cloud Storage
**Tradeoffs**: Local storage is simpler but not scalable or durable

---

## 21. Problems Encountered During Development

### Python Version Compatibility
**Problem**: Python 3.14 not supported by PaddleOCR, old dependency versions incompatible
**Cause**: PaddleOCR only supports Python 3.8-3.13, old package versions (Pillow 10.1.0, PyMuPDF<1.21.0) incompatible with Python 3.14
**Diagnosis**: Dependency installation failures, "KeyError: '__version__'" during Pillow build
**Fix**: Downgraded to Python 3.10-3.13 requirement, updated dependencies to use minimum compatible versions (no strict version pinning)
**Lesson**: Check Python version compatibility for heavy dependencies before installation

### Docker MongoDB Image Compatibility
**Problem**: MongoDB 8.0 image caused "unexpected end of JSON input" error
**Cause**: Docker daemon/network issues with newer MongoDB 8.0 image
**Diagnosis**: Docker Compose error when pulling mongo:8.0 image
**Fix**: Downgraded to MongoDB 7.0 image, removed obsolete 'version' field from docker-compose.yml
**Lesson**: Use stable, tested Docker images rather than latest versions

### Tailwind CSS v4 PostCSS Error
**Problem**: "PostCSS plugin has moved to separate package" error with Tailwind v4
**Cause**: Tailwind CSS v4 changed PostCSS plugin structure, configuration was using v3 syntax
**Diagnosis**: npm run dev failed with PostCSS error about direct usage
**Fix**: Downgraded to Tailwind CSS v3.4.19, kept existing PostCSS configuration
**Lesson**: Major version changes often require configuration updates

### Docker Compose Syntax Error
**Problem**: YAML parsing error due to invalid character at end of environment section
**Cause**: Extraneous 'l' character after MONGO_INITDB_DATABASE line
**Diagnosis**: docker-compose up failed with YAML parsing error
**Fix**: Removed invalid character, cleaned up YAML structure
**Lesson**: YAML syntax errors can be subtle, validate configuration files

### Pydantic Database Truth Value Testing
**Problem**: MongoDB database objects don't support truth value testing in Python 3.14
**Cause**: Attempted to use database in boolean context (if not self.database)
**Diagnosis**: "NotImplementedError: Database objects do not implement truth value testing"
**Fix**: Changed from `if not self.database` to `if self.database is None`
**Lesson**: MongoDB Motor objects require None comparison, not boolean evaluation

### Virtual Environment Installation Failure
**Problem**: Externally-managed-environment error on pip install
**Cause**: Python 3.14's PEP 668 prevents system-wide package installations
**Diagnosis**: pip install failed with PEP 668 error about externally-managed-environment
**Fix**: Created virtual environment with python3 -m venv venv, activated before installing
**Lesson**: Always use virtual environments for Python projects to avoid system-wide package conflicts

---

## 22. Important Things a Beginner Developer Should Understand

### Concepts I Should Understand Before Modifying This Project

**HTTP**: Protocol for communication between frontend and backend. Frontend sends HTTP requests (GET, POST, PUT) to backend endpoints.

**REST APIs**: Architectural style used in FastAPI. Resources (invoices) are accessed via HTTP methods with meaningful URLs (/api/invoices/{id}).

**FastAPI**: Modern Python web framework. Defines endpoints as async functions, automatic OpenAPI documentation at /docs, dependency injection for database access.

**React**: Frontend framework. Components, hooks (useState, useEffect), JSX syntax, client-side routing with React Router.

**JavaScript/JSX**: React uses JSX (JavaScript XML) to define component structure. Must be transpiled by Vite before browser execution.

**Python Packages/Modules**: Backend organized into modules (app.models, app.services, etc.). Import statements load code from other files.

**MongoDB**: Document database used for storage. Stores JSON-like documents in collections (invoices, audit_logs). No fixed schema, indexes for performance.

**Docker**: Containerization platform. Runs MongoDB in isolated container with data persistence via volumes.

**Docker Compose**: Tool for defining multi-container applications. Uses docker-compose.yml to define services (MongoDB).

**OCR**: Optical Character Recognition. Converting image pixels to text characters. PaddleOCR used here with confidence scores.

**Image Preprocessing**: Enhancing images before OCR to improve accuracy. OpenCV used for deskewing, contrast enhancement, denoising.

**JSON**: Data format for API requests/responses and MongoDB documents. Lightweight, human-readable, language-agnostic.

**Environment Variables**: Configuration stored in .env file. Loaded by pydantic-settings, not committed to git.

**Async/Synchronous Execution**: Backend uses async/await for non-blocking database operations. Frontend uses async for API calls.

**HTTP Status Codes**: 200 (success), 400 (client error), 404 (not found), 401 (unauthorized), 500 (server error). Used throughout API.

**Pydantic Models**: Data validation and serialization. Defines request/response schemas, configuration. Converts between JSON and Python objects.

**Repositories/Services**: Repository pattern for database access, service layer for business logic. Separates data access from API endpoints.

**State Machines/State Transitions**: Invoice status follows defined state machine. StateTransitionValidator enforces valid transitions.

---

## 23. Important Code Vocabulary

### Project-Specific Technical Terms

**API Endpoint**: HTTP route that accepts requests (e.g., POST /api/invoices/upload)
**Router**: In this project, routes are defined directly in main.py (no separate router files)
**Service**: Business logic layer (ProcessingService, ValidationService, OCRService, etc.)
**Repository**: Data access layer (InvoiceRepository wraps MongoDB operations)
**Schema**: Pydantic model for API requests/responses (UploadResponse, InvoiceResponse, etc.)
**Model**: Pydantic model for data structures (Invoice, AuditLog, InvoiceStatus, etc.)
**DTO**: Not explicitly used; Pydantic schemas serve as DTOs
**OCR**: Optical Character Recognition - converting images to text using PaddleOCR
**Confidence Score**: 0.0-1.0 value indicating extraction reliability
**State Transition**: Change from one invoice status to another (e.g., PROCESSING → APPROVED)
**Middleware**: Software that processes requests before/after endpoints (CORS middleware in this project)
**Dependency Injection**: FastAPI's Depends() provides database instances to endpoints
**Container**: Running instance of a Docker image (MongoDB container)
**Image**: Read-only template for containers (mongo:7.0 image)
**Volume**: Persistent storage for Docker containers (mongodb_data volume)

---

## 24. "If I Ask You About This Project Later"

### Important File Paths
- **Backend entry**: `backend/app/main.py`
- **Backend config**: `backend/app/config.py`
- **Database**: `backend/app/database.py`
- **Repository**: `backend/app/services/repository.py`
- **Processing service**: `backend/app/services/processing_service.py`
- **Validation service**: `backend/app/validation/validation_service.py`
- **State transitions**: `backend/app/validation/state_transitions.py`
- **Invoice models**: `backend/app/models/invoice.py`
- **OCR service**: `backend/app/document_ai/ocr_service.py`
- **PDF processor**: `backend/app/document_ai/pdf_processor.py`
- **Invoice extractor**: `backend/app/document_ai/invoice_extractor.py`
- **Frontend entry**: `frontend/src/main.jsx`
- **Frontend App**: `frontend/src/App.jsx`
- **Frontend API client**: `frontend/src/services/api.js`
- **Dashboard**: `frontend/src/pages/Dashboard.jsx`
- **Upload**: `frontend/src/pages/Upload.jsx`
- **Invoice details**: `frontend/src/pages/InvoiceDetails.jsx`
- **Review**: `frontend/src/pages/Review.jsx`
- **Sidebar**: `frontend/src/components/Sidebar.jsx`
- **Accounting app**: `simulated-accounting-app/app.py`
- **Docker config**: `docker-compose.yml`
- **Environment template**: `.env.example`

### Important Classes
- **InvoiceRepository**: `backend/app/services/repository.py` - MongoDB CRUD operations
- **ProcessingService**: `backend/app/services/processing_service.py` - OCR/extraction orchestration
- **ValidationService**: `backend/app/validation/validation_service.py` - Business rule validation
- **StateTransitionValidator**: `backend/app/validation/state_transitions.py` - State transition enforcement
- **InvoiceExtractor**: `backend/app/document_ai/invoice_extractor.py` - Regex-based field extraction
- **OCRService**: `backend/app/document_ai/ocr_service.py` - PaddleOCR wrapper
- **PDFProcessor**: `backend/app/document_ai/pdf_processor.py` - PyMuPDF wrapper
- **ImagePreprocessor**: `backend/app/document_ai/image_preprocessor.py` - OpenCV wrapper
- **FileStorage**: `backend/app/storage/file_storage.py` - Local file system operations

### Important Functions
- **process_invoice()**: ProcessingService.process_invoice() - Main pipeline orchestration
- **validate()**: ValidationService.validate() - Business rule validation
- **determine_status()**: ValidationService.determine_status() - Confidence-based routing
- **can_transition()**: StateTransitionValidator.can_transition() - Transition validation
- **extract()**: InvoiceExtractor.extract() - Field extraction with confidence
- **extract_text_from_images()**: OCRService.extract_text_from_images() - Multi-page OCR
- **upload_invoice()**: main.py upload_invoice() - Document upload endpoint
- **approve_invoice()**: main.py approve_invoice() - Approval endpoint
- **reject_invoice()**: main.py reject_invoice() - Rejection endpoint

### Important API Endpoints
- **POST /api/invoices/upload**: Upload and process document
- **GET /api/invoices**: List all invoices
- **GET /api/invoices/{document_id}**: Get specific invoice
- **PUT /api/invoices/{document_id}**: Update invoice fields
- **POST /api/invoices/{document_id}/approve**: Approve for RPA
- **POST /api/invoices/{document_id}/reject**: Reject invoice
- **GET /api/rpa/queue**: Get RPA queue
- **POST /api/rpa/{document_id}/start**: Start RPA processing
- **POST /api/rpa/{document_id}/result**: Report RPA result

### Important Database Collections
- **invoices**: Stores all invoice documents with full processing results
- **audit_logs**: Stores audit trail of state changes and user actions

### Important Configuration
- **CONFIDENCE_THRESHOLD**: 0.80 (confidence threshold for routing)
- **MAX_UPLOAD_SIZE_MB**: 10 (maximum file upload size)
- **API_PORT**: 8000 (backend server port)
- **RPA_API_KEY**: Must be changed in production (secures RPA endpoints)

### Important Technologies
- **FastAPI**: Backend web framework
- **MongoDB**: Document database
- **PaddleOCR**: OCR engine
- **PyMuPDF**: PDF processing
- **OpenCV**: Image preprocessing
- **React**: Frontend framework
- **Tailwind CSS**: Styling framework
- **Vite**: Build tool

### Important Workflows
- **Upload → Processing → Validation → Routing**: Complete document processing pipeline
- **ProcessingService orchestration**: PDF → Image preprocessing → OCR → Extraction → Validation
- **State transitions**: Enforced by StateTransitionValidator
- **RPA flow**: APPROVED → RPA_QUEUED → RPA_PROCESSING → RPA_COMPLETED
- **Audit logging**: All state changes and user actions tracked

### Known Limitations
- **Python version**: Requires 3.10-3.13 (PaddleOCR limitation)
- **RPA**: UiPath workflow is documentation only, requires manual Windows implementation
- **Accounting app**: Simulated Flask app with in-memory storage (resets on restart)
- **OCR**: English only (PaddleOCR lang='en')
- **File storage**: Local file system (not scalable)
- **No authentication**: No user authentication implemented
- **Single-user demo**: Designed for demonstration, not production use

### Known Bugs
- None currently known in stable implementation

### Important Architectural Relationships
- **Frontend → Backend**: Axios HTTP calls via /api proxy (Vite proxy to port 8000)
- **Backend → MongoDB**: Motor async driver for database operations
- **Backend → ProcessingService**: Coordinates document AI pipeline
- **ProcessingService → Document AI modules**: Calls PDFProcessor, ImagePreprocessor, OCRService, InvoiceExtractor
- **ProcessingService → ValidationService**: Validates extraction results
- **Backend → Repository**: All database access goes through InvoiceRepository
- **ValidationService → StateTransitionValidator**: Enforces state transition rules
- **RPA → Backend**: UiPath calls backend API endpoints for queue and results
- **Backend → Accounting App**: RPA automates form entry in Flask app

---

## The 20 Most Important Things I Should Know

1. **Python Version**: Must use Python 3.10-3.13 (PaddleOCR doesn't support 3.14)
2. **MongoDB**: Database runs in Docker container via `docker-compose up -d` on port 27017
3. **Backend Entry**: Run with `cd backend && source venv/bin/activate && python -m app.main` on port 8000
4. **Frontend Entry**: Run with `cd frontend && npm run dev` on port 3000 (or 3001 if occupied)
5. **Accounting App**: Run with `cd simulated-accounting-app && source venv/bin/activate && python app.py` on port 3001
6. **Configuration**: Copy .env.example to .env and configure before running
7. **Main Upload Flow**: Upload → PDF→Image→OCR→Extraction→Validation→Routing (all synchronous in upload endpoint)
8. **Confidence Threshold**: 0.80 determines if invoice needs review (lower threshold = more manual review)
9. **State Machine**: 11 invoice states, transitions enforced by StateTransitionValidator
10. **PaddleOCR**: Lazy initialization on first OCR call, downloads models (~200MB)
11. **File Storage**: Local filesystem in storage/documents/{document_id}/, not in git
12. **RPA Integration**: API endpoints exist but UiPath workflow requires manual implementation
13. **Accounting App**: Simulated Flask app, in-memory storage, resets on restart
14. **Audit Logging**: All state changes and user actions tracked in MongoDB audit_logs collection
15. **Dependencies**: Backend requires virtual environment, frontend requires npm install
16. **Docker**: Only runs MongoDB, not backend/frontend (those run directly)
17. **API Proxy**: Vite proxies /api requests to http://127.0.0.1:8000
18. **Frontend Design**: Modern Tailwind CSS redesign with sidebar, drag-and-drop upload, responsive layout
19. **Testing**: Unit tests for validators/extraction/validation/integration, no OCR/RPA tests
20. **Master Specification**: This implementation follows Master Specification exactly (MongoDB only, no Redis/Celery, PaddleOCR only, no external services)