# UiPath Invoice Processor - Step-by-Step Implementation Guide

This guide provides detailed steps for implementing the invoice processing workflow in UiPath Studio.

## Project Setup

1. **Create New Project**
   - Open UiPath Studio
   - Click "New Project"
   - Select "Process"
   - Name: `InvoiceProcessor`
   - Location: Browse to this directory
   - Click "Create"

2. **Add Dependencies**
   - Open `Manage Packages`
   - Install:
     - `UiPath.WebAPI.Activities` (for HTTP requests)
     - `UiPath.UIAutomation.Activities` (for browser automation)
     - `UiPath.System.Activities` (for system operations)

## Workflow Structure

### Main Sequence

```
Main.xaml
├── Initialize Configuration
├── While Loop (Process Queue)
│   ├── Get Next Invoice from Queue
│   ├── If Invoice Available
│   │   ├── Start RPA Processing
│   │   ├── Open Accounting App
│   │   ├── Enter Invoice Data
│   │   ├── Submit Invoice
│   │   ├── Verify Success
│   │   └── Report Result
│   └── Else (No Invoice)
│       └── Wait 30 Seconds
└── End
```

## Detailed Implementation Steps

### 1. Initialize Configuration

**Variables:**
- `apiBaseUrl` (String) = "http://127.0.0.1:8000"
- `apiKey` (String) = "change-me"
- `accountingAppUrl` (String) = "http://localhost:3001"
- `retryCount` (Int32) = 3
- `retryDelay` (Int32) = 5

**Activities:**
- Assign activity to set configuration values
- Log message: "RPA Workflow Initialized"

### 2. Get Next Invoice from Queue

**Variables:**
- `queueResponse` (String)
- `queueData` (JObject)
- `invoiceAvailable` (Boolean)
- `documentId` (String)
- `invoiceData` (JObject)

**Activities:**
1. HTTP Request
   - Method: GET
   - URL: `apiBaseUrl + "/api/rpa/queue"`
   - Headers: Content-Type = application/json
   - Result: `queueResponse`

2. Deserialize JSON
   - Input: `queueResponse`
   - Result: `queueData`

3. Check if invoices available
   - Assign: `invoiceAvailable = queueData("count") > 0`
   - If available:
     - Assign: `documentId = queueData("invoices")(0)("document_id").ToString`
     - Assign: `invoiceData = queueData("invoices")(0)`

### 3. Start RPA Processing

**Activities:**
1. Build JSON body
   ```
   {
     "document_id": documentId,
     "api_key": apiKey
   }
   ```

2. HTTP Request
   - Method: POST
   - URL: `apiBaseUrl + "/api/rpa/" + documentId + "/start"`
   - Headers: Content-Type = application/json
   - Body: JSON from step 1
   - Result: `startResponse`

3. Deserialize response to get updated invoice data

### 4. Open Accounting Application

**Activities:**
1. Open Browser
   - Type: Chrome
   - URL: `accountingAppUrl + "/new-invoice"`

2. Wait for page load
   - Element: Body or any specific element
   - Wait for: Visible

### 5. Enter Invoice Data

**For each field:**

**Vendor:**
- Find Element: `<input id='vendor'>` or by name
- Type Into: `invoiceData("vendor")("name").ToString`

**Invoice Number:**
- Find Element: `<input id='invoice_number'>`
- Type Into: `invoiceData("invoice_number").ToString`

**Invoice Date:**
- Find Element: `<input id='invoice_date' type='date'>`
- Type Into: `invoiceData("invoice_date").ToString`

**Due Date:**
- If `invoiceData("due_date")` is not null/empty:
  - Find Element: `<input id='due_date' type='date'>`
  - Type Into: `invoiceData("due_date").ToString`

**Currency:**
- Find Element: `<select id='currency'>`
- Select Item: `invoiceData("currency").ToString`

**Subtotal:**
- If `invoiceData("subtotal")` is not null:
  - Find Element: `<input id='subtotal' type='number'>`
  - Type Into: `invoiceData("subtotal").ToString`

**Tax:**
- If `invoiceData("tax")` is not null:
  - Find Element: `<input id='tax' type='number'>`
  - Type Into: `invoiceData("tax").ToString`

**Total:**
- Find Element: `<input id='total' type='number'>`
- Type Into: `invoiceData("total").ToString`

**Line Items:**
- Find Element: `<textarea id='line_items'>`
- Type Into: Concatenate line item descriptions

### 6. Submit Invoice

**Activities:**
1. Find Element: `<button type='submit'>` or button with text "Save Invoice"
2. Click activity
3. Wait for page navigation (use Element Exists or Wait for Ready)

### 7. Verify Success

**Variables:**
- `success` (Boolean)
- `accountingRecordId` (String)
- `pageText` (String)

**Activities:**
1. Get Page Text
   - Scope: Browser
   - Output: `pageText`

2. Check for success message
   - Assign: `success = pageText.Contains("Invoice Successfully Created")`

3. If success:
   - Extract accounting ID using string manipulation or regex
   - Pattern: `Accounting Record ID: (ACC-\w+)`
   - Assign: `accountingRecordId` = match result

### 8. Report Result

**Activities:**
1. Build JSON body
   ```
   {
     "document_id": documentId,
     "api_key": apiKey,
     "success": success,
     "accounting_record_id": accountingRecordId (if success),
     "message": "Invoice successfully entered" (if success) or error message
   }
   ```

2. HTTP Request
   - Method: POST
   - URL: `apiBaseUrl + "/api/rpa/" + documentId + "/result"`
   - Headers: Content-Type = application/json
   - Body: JSON from step 1

3. Log result
   - If success: "Invoice processed successfully. Accounting ID: " + accountingRecordId
   - If failure: "Invoice processing failed"

### 9. Error Handling

Wrap critical sections in Try-Catch blocks:

**API Call Errors:**
- Catch: WebException
- Log: "API call failed: " + exception.Message
- Retry logic (use Retry Scope activity)

**UI Automation Errors:**
- Catch: SelectorNotFoundException
- Log: "UI element not found: " + exception.Message
- Mark as failure and report result

**General Errors:**
- Catch: Exception
- Log: "Unexpected error: " + exception.Message
- Report result with success=false

## UI Selectors

Use these selectors (may need adjustment based on actual HTML):

```
Vendor Input: <html app='chrome' title='Simulated Accounting System' /><webctrl id='vendor' tag='INPUT' />
Invoice Number Input: <html app='chrome' title='Simulated Accounting System' /><webctrl id='invoice_number' tag='INPUT' />
Invoice Date Input: <html app='chrome' title='Simulated Accounting System' /><webctrl id='invoice_date' tag='INPUT' />
Due Date Input: <html app='chrome' title='Simulated Accounting System' /><webctrl id='due_date' tag='INPUT' />
Currency Select: <html app='chrome' title='Simulated Accounting System' /><webctrl id='currency' tag='SELECT' />
Subtotal Input: <html app='chrome' title='Simulated Accounting System' /><webctrl id='subtotal' tag='INPUT' />
Tax Input: <html app='chrome' title='Simulated Accounting System' /><webctrl id='tax' tag='INPUT' />
Total Input: <html app='chrome' title='Simulated Accounting System' /><webctrl id='total' tag='INPUT' />
Line Items Textarea: <html app='chrome' title='Simulated Accounting System' /><webctrl id='line_items' tag='TEXTAREA' />
Submit Button: <html app='chrome' title='Simulated Accounting System' /><webctrl tag='BUTTON' type='submit' />
```

## Testing Checklist

- [ ] Workflow compiles without errors
- [ ] Can connect to backend API
- [ ] Can retrieve invoices from queue
- [ ] Can start RPA processing
- [ ] Can open accounting application
- [ ] Can enter all invoice fields
- [ ] Can submit invoice
- [ ] Can detect success message
- [ ] Can extract accounting record ID
- [ ] Can report success result
- [ ] Can report failure result
- [ ] Handles empty queue correctly
- [ ] Handles API errors correctly
- [ ] Handles UI automation errors correctly

## Running the Workflow

### From Studio
1. Open `Main.xaml`
2. Click "Debug" or "Run"
3. Monitor Output panel for logs
4. Check browser for automation

### From Orchestrator (Production)
1. Publish project to Orchestrator
2. Create environment
3. Add robot to environment
4. Create job or schedule trigger
5. Monitor from Orchestrator dashboard

## Notes

- This is a guide for implementing the workflow manually in UiPath Studio
- The actual .xaml file cannot be generated without UiPath Studio
- Adjust selectors based on the actual HTML of the accounting application
- Add logging throughout for debugging and monitoring
- Consider using Orchestrator queues for better scalability in production
