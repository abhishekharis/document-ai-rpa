# Document AI RPA - Invoice Processing & Automation Platform

An end-to-end invoice automation system that uses OCR to extract data from invoices, validates the information, and uses UiPath RPA to automatically enter approved invoices into an accounting system.

## Overview

This system demonstrates the integration of **Document AI/OCR** with **RPA automation**:
- **PaddleOCR** performs real OCR on PDF/image invoices
- **Document processing** extracts structured invoice fields with confidence scores
- **Validation** checks data integrity and routes invoices based on confidence
- **Human review** interface allows correction of low-confidence extractions
- **Documents page** provides bulk management (select, search, filter, delete, reprocess)
- **UiPath RPA** (or included Python processor) automatically enters approved invoices into the accounting system
- **Simulated accounting application** provides a real target for RPA automation

## Architecture

```
User → React Frontend → FastAPI API → MongoDB
                          ↓
                    Document Storage
                          ↓
                    PyMuPDF Processing
                          ↓
                    OpenCV Preprocessing
                          ↓
                    PaddleOCR
                          ↓
                Invoice Field Extraction
                          ↓
                Confidence + Validation
                          ↓
              Human Review (if needed)
                          ↓
                    RPA Queue
                          ↓
                    UiPath Robot
                          ↓
            Simulated Accounting App
                          ↓
                    Result Callback
                          ↓
                    MongoDB
```

## Technology Stack

### Backend
- **Python 3.10-3.13** (PaddleOCR doesn't support 3.14 yet)
- **FastAPI** - Web framework
- **PyMongo/Motor** - MongoDB async driver
- **PaddleOCR** - OCR engine
- **PyMuPDF** - PDF processing
- **OpenCV** - Image preprocessing

### Database
- **MongoDB 7.0** - Document storage

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **Axios** - HTTP client

### RPA
- **UiPath Studio** - RPA development (Windows)
- **UiPath Robot** - RPA execution

### Simulated Accounting App
- **Flask** - Web framework
- **Python** - Backend

### Infrastructure
- **Docker Compose** - MongoDB containerization

## Prerequisites

- Python 3.10-3.13 (PaddleOCR doesn't support 3.14 yet)
- Node.js 18+
- MongoDB 7.0 (or Docker)
- (Optional) UiPath Studio Community Edition (Windows only)

## Installation

### 1. Clone the Repository

```bash
cd /Users/abhishek/CascadeProjects/document-ai-rpa
```

### 2. Environment Setup

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=document_ai_rpa
STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=10
CONFIDENCE_THRESHOLD=0.80
API_HOST=127.0.0.1
API_PORT=8000
ACCOUNTING_APP_URL=http://localhost:3001
RPA_API_KEY=change-me-in-production
```

Additional settings (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | `staging`/`production` refuse to start with a default or short (<16 chars) `RPA_API_KEY` or localhost `CORS_ORIGINS` |
| `LOG_LEVEL` | `INFO` | Log level; logs are JSON outside development |
| `CORS_ORIGINS` | localhost dev ports | JSON list of allowed origins, e.g. `["https://app.example.com"]` |
| `UPLOAD_RATE_LIMIT_PER_MINUTE` | `30` | Per-IP upload limit (in-memory, single process) |
| `RPA_RATE_LIMIT_PER_MINUTE` | `120` | Per-IP limit on the RPA start/result endpoints |

See `.env.production.example` for a production starting point.

### 3. Start MongoDB

Using Docker Compose (recommended):
```bash
docker-compose up -d
```

Or start MongoDB manually:
```bash
mongod --dbpath ./mongodb_data
```

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 6. Simulated Accounting App Setup

```bash
cd simulated-accounting-app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 7. UiPath Setup (Optional, for RPA)

1. Install UiPath Studio Community Edition (Windows only)
2. Open UiPath Studio
3. Create a new process in `rpa/UiPath/InvoiceProcessor/`
4. Follow the workflow guide in `rpa/UiPath/InvoiceProcessor/Workflow_Guide.md`

## Running the System

### Start MongoDB
```bash
docker-compose up -d
```

### Start Backend
```bash
cd backend
source venv/bin/activate
python -m app.main
```

Backend will be available at `http://127.0.0.1:8000`

API Documentation: `http://127.0.0.1:8000/docs`

### Run the Full Stack in Docker

```bash
export RPA_API_KEY=<a-secret-of-16+-characters>
docker compose -f docker-compose.full.yml up --build
```

The UI is served at http://localhost:8080 and nginx proxies `/api` to the backend. The stack uses its own MongoDB container and volumes, separate from the development `docker-compose.yml`. Set `ENVIRONMENT=production` and `CORS_ORIGINS` for real deployments.

### Start Frontend
```bash
cd frontend
npm run dev
```

Frontend will be available at `http://localhost:3000`

### Start Simulated Accounting App
```bash
cd simulated-accounting-app
source venv/bin/activate
python app.py
```

Accounting app will be available at `http://localhost:3001`

### Start UiPath Workflow (Optional)
1. Open the workflow in UiPath Studio
2. Click "Debug" or "Run"
3. The workflow will poll the RPA queue and process invoices

## Usage

### 1. Upload an Invoice

1. Navigate to `http://localhost:3000`
2. Click "Upload" in the navigation
3. Select a PDF or image invoice file
4. Click "Upload Invoice"
5. The system will:
   - Process the document with OCR
   - Extract invoice fields
   - Validate the data
   - Route based on confidence

### 2. Review Invoice Details

1. From the dashboard, click "View" on any invoice
2. View extracted fields, confidence scores, and validation results
3. See the original document
4. Check RPA status

### 3. Review and Approve

1. For invoices with "NEEDS_REVIEW" status, click "Review"
2. Edit any incorrect fields
3. Click "Save Corrections"
4. Enter your name and any notes
5. Click "Approve Invoice" or "Reject Invoice"

### 4. Manage Documents

1. Navigate to "Documents" in the sidebar
2. Search by vendor or invoice number, or filter by status/date
3. Select documents with checkboxes (or Select All)
4. Use "Bulk Actions" to delete or reprocess selected documents
5. Deletion removes the record and files but preserves audit logs; reprocessing is allowed for ERROR, REJECTED, and NEEDS_REVIEW documents

### 5. RPA Processing

Once approved:
- Invoice enters RPA queue
- RPA workflow picks up the invoice (UiPath on Windows, or `rpa/python_rpa_processor.py` on macOS/Linux)
- Opens accounting application
- Enters invoice data
- Verifies success
- Reports result back to backend

## API Endpoints

### Health
- `GET /api/health` - Health check

### Invoices
- `POST /api/invoices/upload` - Upload invoice document
- `GET /api/invoices` - Get all invoices
- `GET /api/invoices/{document_id}` - Get invoice by ID
- `GET /api/invoices/{document_id}/document` - Get original document file
- `PUT /api/invoices/{document_id}` - Update invoice fields
- `POST /api/invoices/{document_id}/approve` - Approve invoice
- `POST /api/invoices/{document_id}/reject` - Reject invoice
- `POST /api/invoices/bulk-delete` - Delete documents and stored files (audit logs preserved)
- `POST /api/invoices/bulk-reprocess` - Re-run eligible documents (ERROR, REJECTED, NEEDS_REVIEW) through the pipeline

### RPA
- `GET /api/rpa/queue` - Get RPA queue
- `POST /api/rpa/{document_id}/start` - Start RPA processing
- `POST /api/rpa/{document_id}/result` - Report RPA result

## Invoice Data Model

```json
{
  "document_id": "DOC-12345",
  "original_filename": "invoice.pdf",
  "status": "APPROVED",
  "vendor": {
    "name": "Example Supplies LLC",
    "address": "123 Main Street"
  },
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
      "invoice_number": {
        "value": "INV-1001",
        "confidence": 0.98
      }
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
    "status": "NOT_STARTED",
    "job_id": null,
    "message": null,
    "processed_at": null
  },
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## Processing States

- `UPLOADED` - Document uploaded
- `PROCESSING` - OCR/extraction in progress
- `PROCESSED` - Processing complete
- `NEEDS_REVIEW` - Low confidence or validation warnings
- `APPROVED` - Approved for RPA
- `REJECTED` - Rejected by reviewer
- `RPA_QUEUED` - In RPA queue
- `RPA_PROCESSING` - RPA in progress
- `RPA_COMPLETED` - RPA successful
- `RPA_FAILED` - RPA failed
- `ERROR` - Processing error

## Testing

### Run Unit Tests
```bash
cd backend
source venv/bin/activate
pytest tests/
```

### Run API Tests
```bash
cd backend
pytest tests/test_api.py
```

The API and RPA integration tests need MongoDB running on `localhost:27017`; without it the suite hangs waiting for the database.

### Coverage
```bash
cd backend
pytest tests/ --cov=app --cov-report=term
```

CI (`.github/workflows/ci.yml`) runs the backend tests and the frontend build on every push to `main` and on pull requests.

### Run E2E Tests
```bash
# Ensure all services are running
pytest tests/e2e/test_workflow.py
```

## Sample Documents

Place sample invoices in `sample_documents/`:
- `normal/` - Clean invoices
- `poor_quality/` - Low quality scans
- `missing_fields/` - Invoices missing required fields
- `invalid/` - Invoices with invalid data

See `sample_documents/README.md` for details.

## Troubleshooting

### Create a Verified Local Backup

1. Pause the backend and RPA worker so the database and file archive are consistent; leave MongoDB running.
2. From the project root, run `bash ./backup_project_data.sh`.
3. Backups are stored in `~/Backups/document-ai-rpa/<UTC timestamp>/` by default. Each folder contains `mongodb.archive.gz`, `documents.tar.gz`, and `SHA256SUMS`. The script verifies both archives and keeps the seven most recent managed backups.
4. Verify a backup with `cd ~/Backups/document-ai-rpa/<timestamp> && shasum -a 256 -c SHA256SUMS`.

### Restore a Backup

`bash ./restore_project_data.sh ~/Backups/document-ai-rpa/<timestamp>` verifies `SHA256SUMS`, then restores into a **scratch** database (`document_ai_rpa_restore`) and `<backup>/restored-documents`, so live data is never touched. It refuses to overwrite a non-empty target without `--force`.

To replace live data, stop the backend and RPA worker, then run `TARGET_DATABASE=document_ai_rpa TARGET_DOCUMENTS_DIR=backend/storage/documents bash ./restore_project_data.sh <backup-dir> --force`. Test a restore into the scratch database regularly; a backup that has never been restored is unverified.

Backups contain invoice data. The script restricts file permissions but does not encrypt archives; use an encrypted disk or FileVault. For restore guidance and WiredTiger recovery, see [the MongoDB recovery guide](docs/investigation-mongodb-wiredtiger-checksum-error.md).

### MongoDB Connection Failed
- Ensure MongoDB is running: `docker-compose ps`
- Check MongoDB URI in `.env`
- Verify MongoDB is accessible: `mongosh mongodb://localhost:27017`

### PaddleOCR Initialization Failed
- Ensure PaddleOCR is installed: `pip list | grep paddleocr`
- First run may download models (can take time)
- Check internet connection for model download

### File Upload Failed
- Check file size limit in `.env` (default 10MB)
- Verify file type is supported (PDF, PNG, JPG, JPEG)
- Check storage directory permissions

### Frontend Cannot Connect to Backend
- Ensure backend is running on port 8000
- Check CORS configuration in backend
- Verify API proxy in `vite.config.js`

### RPA Not Processing
- Ensure invoice status is `APPROVED`
- Check RPA API key in `.env` matches UiPath workflow
- Verify backend RPA endpoints are accessible
- Check UiPath workflow logs

### Accounting App Not Accessible
- Ensure Flask app is running on port 3001
- Check ACCOUNTING_APP_URL in `.env`
- Verify no port conflicts

## Limitations

- **UiPath requires Windows** - RPA workflow development requires Windows OS
- **Single-user demo** - No authentication/authorization implemented
- **In-memory accounting app** - Data resets on restart
- **PaddleOCR accuracy** - Depends on document quality and layout
- **English only** - OCR optimized for English documents

## Demo Procedure

1. Start all services (MongoDB, backend, frontend, accounting app)
2. Open browser to `http://localhost:3000`
3. Upload a sample invoice
4. Wait for processing (OCR + extraction + validation)
5. Review extracted fields and confidence scores
6. If needed, correct fields and approve
7. (Optional) Start UiPath workflow
8. Verify invoice appears in accounting app
9. Check invoice status changes to `RPA_COMPLETED`

## Project Structure

```
document-ai-rpa/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # MongoDB connection
│   │   ├── models/              # Data models
│   │   ├── schemas/             # API schemas
│   │   ├── api/                 # API routes
│   │   ├── services/            # Business logic
│   │   ├── document_ai/         # OCR & extraction
│   │   ├── validation/          # Validation logic
│   │   ├── storage/             # File storage
│   │   └── utils/               # Utilities
│   ├── storage/documents/       # Uploaded document storage
│   ├── tests/                   # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   └── services/            # API client
│   └── package.json
├── simulated-accounting-app/
│   ├── app.py                   # Flask application
│   ├── templates/               # HTML templates
│   └── requirements.txt
├── rpa/
│   ├── UiPath/InvoiceProcessor/ # UiPath workflow
│   └── README.md                # RPA documentation
├── sample_documents/           # Test invoices
├── tests/e2e/                   # E2E tests
├── docker-compose.yml           # MongoDB container
├── .env.example                 # Environment template
└── README.md
```

## Security Considerations

- **API Key**: Change `RPA_API_KEY` in production
- **File Upload**: Validates file type and size
- **Path Traversal**: Sanitizes filenames
- **CORS**: Configured for specific origins
- **Input Validation**: Pydantic models validate all inputs

## Future Enhancements

- Add user authentication
- Implement real accounting system integration (SAP, QuickBooks)
- Add support for multi-language OCR
- Implement advanced duplicate detection
- Add email notifications for RPA failures
- Implement audit log export
- Add invoice template learning
- Support for batch upload

## License

This is a portfolio project for demonstration purposes.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `/docs` endpoint
3. Check logs in each service
4. Verify all services are running
