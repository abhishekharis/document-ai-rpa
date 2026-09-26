# UiPath RPA Workflow for Invoice Processing

This directory contains the UiPath workflow for automating invoice entry into the simulated accounting application.

## Prerequisites

- **UiPath Studio Community Edition** (or Studio 2023.10+)
- Windows operating system (UiPath Studio is Windows-only)
- Backend API running at `http://127.0.0.1:8000`
- Simulated accounting application running at `http://localhost:3001`

## Workflow Overview

The UiPath workflow automates the following process:

1. **Retrieve Approved Invoice**: Call backend API to get next invoice from RPA queue
2. **Mark Processing**: Update invoice status to RPA_PROCESSING
3. **Open Accounting App**: Navigate to the simulated accounting application
4. **Enter Invoice Data**: Fill in all invoice fields
5. **Submit Invoice**: Click save button
6. **Verify Success**: Check for success message and accounting record ID
7. **Report Result**: Call backend API with success/failure status

## API Endpoints Used

### Get RPA Queue
```
GET http://127.0.0.1:8000/api/rpa/queue
```

### Start RPA Processing
```
POST http://127.0.0.1:8000/api/rpa/{document_id}/start
Content-Type: application/json

{
  "document_id": "DOC-12345",
  "api_key": "change-me"
}
```

### Report RPA Result
```
POST http://127.0.0.1:8000/api/rpa/{document_id}/result
Content-Type: application/json

{
  "document_id": "DOC-12345",
  "api_key": "change-me",
  "success": true,
  "accounting_record_id": "ACC-12345",
  "message": "Invoice successfully entered into accounting system"
}
```

## Workflow Steps

### Step 1: Initialize
- Set API base URL: `http://127.0.0.1:8000`
- Set API key from environment variable or config
- Set accounting app URL: `http://localhost:3001`

### Step 2: Get Next Invoice
- HTTP Request to `/api/rpa/queue`
- Parse JSON response
- Check if queue has invoices
- If empty, wait 30 seconds and retry
- If invoice available, extract document_id

### Step 3: Start RPA Processing
- HTTP POST to `/api/rpa/{document_id}/start`
- Include API key in request body
- Verify response status is 200
- Extract invoice data from response

### Step 4: Open Accounting Application
- Open browser (Chrome or Edge recommended)
- Navigate to `http://localhost:3001/new-invoice`
- Wait for page to load

### Step 5: Enter Invoice Data
For each field:
- Find input element by ID or name
- Type value into field
- Wait for field to accept input

Fields to enter:
- Vendor: `invoice.vendor.name`
- Invoice Number: `invoice.invoice_number`
- Invoice Date: `invoice.invoice_date`
- Due Date: `invoice.due_date` (if present)
- Currency: `invoice.currency`
- Subtotal: `invoice.subtotal` (if present)
- Tax: `invoice.tax` (if present)
- Total: `invoice.total`
- Line Items: Concatenate line item descriptions

### Step 6: Submit Invoice
- Find "Save Invoice" button
- Click button
- Wait for page to navigate to success page

### Step 7: Verify Success
- Check if page contains "Invoice Successfully Created"
- Extract accounting record ID from success message
- Format: "Accounting Record ID: ACC-XXXXX"

### Step 8: Report Result
- If success:
  - HTTP POST to `/api/rpa/{document_id}/result`
  - Set `success: true`
  - Include `accounting_record_id`
  - Include success message
- If failure:
  - HTTP POST to `/api/rpa/{document_id}/result`
  - Set `success: false`
  - Include error message

### Step 9: Loop
- Return to Step 2 to process next invoice
- Implement delay between iterations (e.g., 5 seconds)

## Error Handling

### API Errors
- If API call fails, log error
- Retry up to 3 times with exponential backoff
- If still failing, mark invoice as RPA_FAILED

### Browser Automation Errors
- If element not found, wait up to 10 seconds
- If still not found, log error and mark as RPA_FAILED
- Use Try-Catch blocks around UI interactions

### Accounting App Errors
- If accounting app not accessible, log error
- Mark invoice as RPA_FAILED
- Do not retry immediately (might be app issue)

## Configuration

Create a config file or use UiPath Orchestrator assets:

```
API_BASE_URL = "http://127.0.0.1:8000"
API_KEY = "change-me-in-production"
ACCOUNTING_APP_URL = "http://localhost:3001"
RETRY_COUNT = 3
RETRY_DELAY_SECONDS = 5
QUEUE_POLL_INTERVAL_SECONDS = 30
```

## Testing the Workflow

### Manual Testing
1. Ensure backend is running
2. Ensure accounting app is running
3. Upload and approve an invoice via the web UI
4. Run the UiPath workflow
5. Verify invoice appears in accounting app
6. Verify invoice status changes to RPA_COMPLETED

### Automated Testing
Use UiPath Test Manager or create test cases:
- Test with valid invoice data
- Test with missing optional fields
- Test with accounting app unavailable
- Test with backend API unavailable

## Deployment

### Development
- Run workflow from UiPath Studio
- Use debug mode to step through process
- Check logs for errors

### Production
- Publish to UiPath Orchestrator
- Schedule as background process
- Set up monitoring and alerts
- Configure retry policies

## Security Considerations

- Store API key securely (Orchestrator assets or environment variables)
- Use HTTPS in production
- Implement authentication if needed
- Log all RPA operations for audit trail

## Troubleshooting

### Workflow not starting
- Check UiPath Robot service is running
- Verify API endpoints are accessible
- Check API key is correct

### Invoice not appearing in accounting app
- Verify accounting app is running
- Check browser automation is finding elements
- Review UI selectors (may need adjustment)
- Check field values are being passed correctly

### API calls failing
- Verify backend is running
- Check API base URL is correct
- Verify API key matches backend configuration
- Check network connectivity

### Status not updating
- Verify API result endpoint is being called
- Check document_id is correct
- Review API response for errors
- Check backend logs

## Notes

- This workflow is designed for the simulated accounting application
- For real accounting systems (SAP, QuickBooks, etc.), adapt the UI automation steps
- The backend API remains the same regardless of accounting system
- Consider adding email notifications for RPA failures in production
