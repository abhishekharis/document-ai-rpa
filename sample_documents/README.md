# Sample Test Documents

This directory contains sample invoice documents for testing the invoice processing system.

## Document Categories

### normal/
Clean, well-formatted invoices with all fields clearly visible.
- **Expected behavior:** High OCR confidence, automatic approval

### poor_quality/
Invoices with low resolution, noise, or poor scanning quality.
- **Expected behavior:** Lower OCR confidence, may need review

### missing_fields/
Invoices with missing required fields (invoice number, date, total, etc.).
- **Expected behavior:** Validation errors, requires manual review

### invalid/
Invoices with invalid data (incorrect totals, impossible dates, etc.).
- **Expected behavior:** Validation errors, may be rejected

## Required Sample Documents

### Document 1: Normal Invoice (normal/)
- Clean digital PDF invoice
- All required fields present
- Standard invoice format
- **Expected:** High confidence (>0.90), auto-approved

### Document 2: Image Invoice (normal/)
- High-quality image (PNG/JPG) of invoice
- Clear text, good contrast
- **Expected:** High confidence (>0.85), auto-approved

### Document 3: Multi-page Invoice (normal/)
- PDF with 2-3 pages
- Line items spread across pages
- **Expected:** High confidence, auto-approved

### Document 4: Poor Quality (poor_quality/)
- Low resolution or scanned image
- Some text blurry or faded
- **Expected:** Lower confidence (0.60-0.80), needs review

### Document 5: Missing Invoice Number (missing_fields/)
- Invoice without invoice number field
- Other fields present
- **Expected:** Validation error, needs review

### Document 6: Incorrect Totals (invalid/)
- Subtotal + tax ≠ total
- Mathematical inconsistency
- **Expected:** Validation warning, needs review

### Document 7: Duplicate Invoice (normal/)
- Same vendor and invoice number as Document 1
- Different date or amount
- **Expected:** Duplicate detection warning, needs review

### Document 8: Alternative Layout (normal/)
- Non-standard invoice layout
- Different field labels
- **Expected:** May have lower confidence, needs review

## Creating Sample Documents

### Using Existing Invoices
1. Redact sensitive information (real vendor names, addresses, amounts)
2. Replace with realistic dummy data
3. Ensure all fields are clearly readable
4. Save in appropriate category directory

### Using Invoice Generators
- Use online invoice generators (e.g., Invoice Simple, FreshBooks)
- Create invoices with specific characteristics for each test case
- Export as PDF or image
- Place in appropriate category

### Manual Creation
- Create invoices in Word/Excel
- Export to PDF
- Add intentional variations for test cases
- Save in appropriate category

## Naming Convention

Use descriptive filenames:
- `normal_invoice_001.pdf`
- `poor_quality_scan_001.jpg`
- `missing_invoice_number_001.pdf`
- `incorrect_totals_001.pdf`

## Testing with Sample Documents

### Upload Test
1. Navigate to Upload page
2. Select document from sample_documents directory
3. Upload and observe processing
4. Verify expected behavior

### OCR Accuracy Test
1. Upload normal invoices
2. Check extraction confidence scores
3. Verify all fields extracted correctly
4. Compare with expected results

### Validation Test
1. Upload invoices from missing_fields/ and invalid/
2. Check validation errors/warnings
3. Verify routing to review queue
4. Test manual correction

### Duplicate Detection Test
1. Upload Document 1
2. Upload Document 7 (duplicate)
3. Verify duplicate warning
4. Check both invoices in system

## Notes

- Do not commit actual invoice files to Git (they're in .gitignore)
- These are for development and testing only
- Use realistic but fictitious data
- Ensure documents are varied enough to test different scenarios
