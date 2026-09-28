# Python RPA Processor for macOS

This is a Python-based RPA processor that provides an alternative to UiPath for macOS environments. It polls the invoice queue and automatically processes invoices into the accounting application.

## Why This Exists

UiPath Studio is Windows-only and cannot run on macOS. This Python-based RPA processor provides the same functionality for macOS development environments.

## Prerequisites

- Python 3.8+
- Backend API running at `http://127.0.0.1:8000`
- Simulated accounting application running at `http://localhost:3001`

## Installation

1. Create a virtual environment:
```bash
cd rpa
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Set environment variables or create a `.env` file:

```bash
API_BASE_URL=http://127.0.0.1:8000
RPA_API_KEY=change-me
ACCOUNTING_APP_URL=http://localhost:3001
RPA_POLL_INTERVAL=30
```

## Running the RPA Processor

```bash
cd rpa
source venv/bin/activate
python python_rpa_processor.py
```

The processor will:
1. Poll the RPA queue every 30 seconds (configurable)
2. Process queued invoices automatically
3. Submit invoice data to the accounting application
4. Report results back to the backend API
5. Continue running until interrupted (Ctrl+C)

## How It Works

1. **Queue Polling**: Checks `/api/rpa/queue` for pending invoices
2. **Start Processing**: Calls `/api/rpa/{document_id}/start` to mark invoice as RPA_PROCESSING
3. **Accounting Integration**: Submits invoice data to accounting app via JSON API
4. **Result Reporting**: Calls `/api/rpa/{document_id}/result` with success/failure status
5. **Loop**: Continues polling for more invoices

## Workflow

The complete workflow for each invoice:
```
RPA_QUEUED → RPA_PROCESSING → Accounting App → RPA_COMPLETED
```

## Key Features

- **Automatic queue polling**: No manual intervention required
- **Error handling**: Graceful failure handling with detailed logging
- **Configurable intervals**: Adjust polling frequency via environment variables
- **Cross-platform**: Works on macOS, Linux, and Windows
- **JSON API integration**: Uses REST APIs for both backend and accounting app

## Monitoring

The processor logs all activities:
- Queue polling status
- Invoice processing steps
- API call results
- Error messages
- Accounting record IDs

## Testing

Test the processor by:
1. Uploading a valid invoice through the web interface
2. Starting the RPA processor
3. Monitoring the logs for processing activity
4. Checking the accounting application for the new record
5. Verifying the invoice status changes to RPA_COMPLETED

## Differences from UiPath

- **No browser automation**: Uses direct HTTP API calls instead of UI automation
- **Simpler deployment**: Just run the Python script instead of setting up UiPath Studio
- **No Windows dependency**: Works on any platform with Python
- **Faster processing**: Direct API calls are faster than browser automation

## Production Considerations

For production use, consider:
- Running as a systemd service or supervisor daemon
- Adding monitoring and alerting
- Implementing retry logic with exponential backoff
- Adding database persistence for accounting records
- Implementing authentication for accounting app API
- Adding rate limiting for API calls