from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = 'simulated-accounting-app-secret-key'

# In-memory storage for accounting records
accounting_records = []


@app.route('/')
def dashboard():
    """Dashboard showing all accounting records."""
    return render_template('dashboard.html', records=accounting_records)


@app.route('/new-invoice', methods=['GET', 'POST'])
def new_invoice():
    """Form to create a new invoice in the accounting system."""
    if request.method == 'POST':
        try:
            # Handle both form data and JSON (for RPA automation)
            if request.is_json:
                data = request.get_json()
                vendor = data.get('vendor')
                invoice_number = data.get('invoice_number')
                invoice_date = data.get('invoice_date')
                due_date = data.get('due_date')
                currency = data.get('currency', 'USD')
                subtotal = data.get('subtotal')
                tax = data.get('tax')
                total = data.get('total')
                line_items_description = data.get('line_items', '')
                return_json = True
            else:
                # Extract form data
                vendor = request.form.get('vendor')
                invoice_number = request.form.get('invoice_number')
                invoice_date = request.form.get('invoice_date')
                due_date = request.form.get('due_date')
                currency = request.form.get('currency', 'USD')
                subtotal = request.form.get('subtotal')
                tax = request.form.get('tax')
                total = request.form.get('total')
                line_items_description = request.form.get('line_items', '')
                return_json = False
            
            # Generate accounting record ID
            accounting_id = f"ACC-{uuid.uuid4().hex[:8].upper()}"
            
            # Create record
            record = {
                'accounting_id': accounting_id,
                'vendor': vendor,
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,
                'due_date': due_date,
                'currency': currency,
                'subtotal': float(subtotal) if subtotal else None,
                'tax': float(tax) if tax else None,
                'total': float(total) if total else None,
                'line_items': line_items_description,
                'created_at': datetime.utcnow().isoformat()
            }
            
            accounting_records.append(record)
            
            if return_json:
                # Return JSON response for RPA automation
                return jsonify({
                    'success': True,
                    'accounting_id': accounting_id,
                    'message': f'Invoice successfully created. Accounting Record ID: {accounting_id}',
                    'record': record
                })
            else:
                # Show success page for manual submission
                flash(f'Invoice successfully created. Accounting Record ID: {accounting_id}', 'success')
                return render_template('success.html', accounting_id=accounting_id, record=record)
            
        except Exception as e:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            else:
                flash(f'Error creating invoice: {str(e)}', 'error')
                return render_template('new_invoice.html')
    
    return render_template('new_invoice.html')


@app.route('/record/<accounting_id>')
def view_record(accounting_id):
    """View a specific accounting record."""
    record = next((r for r in accounting_records if r['accounting_id'] == accounting_id), None)
    if record:
        return render_template('view_record.html', record=record)
    else:
        flash('Record not found', 'error')
        return redirect(url_for('dashboard'))


@app.route('/api/records', methods=['GET'])
def get_records():
    """API endpoint to get all accounting records."""
    return jsonify({'records': accounting_records, 'count': len(accounting_records)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=True)
