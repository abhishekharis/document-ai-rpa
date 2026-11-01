import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, g
from werkzeug.middleware.proxy_fix import ProxyFix

import db


def create_app(db_path=None):
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'simulated-accounting-app-dev-secret')
    app.config['DB_PATH'] = db_path or os.getenv('ACCOUNTING_DB_PATH', 'accounting.db')
    # Honour X-Forwarded-Prefix so links work when served under e.g. /accounting/
    app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
    db.init_db(app.config['DB_PATH'])

    def get_conn():
        if 'conn' not in g:
            g.conn = db.connect(app.config['DB_PATH'])
        return g.conn

    @app.teardown_appcontext
    def close_conn(_exc):
        conn = g.pop('conn', None)
        if conn is not None:
            conn.close()

    @app.route('/')
    def dashboard():
        """Dashboard showing all accounting records."""
        return render_template('dashboard.html', records=db.list_records(get_conn()))

    @app.route('/new-invoice', methods=['GET', 'POST'])
    def new_invoice():
        """Form to create a new invoice in the accounting system."""
        if request.method == 'POST':
            return_json = request.is_json
            try:
                # Handle both form data and JSON (for RPA automation)
                data = request.get_json() if return_json else request.form
                external_reference = data.get('external_reference') or None
                conn = get_conn()

                # A retried submit for the same source document returns the existing record
                if external_reference:
                    existing = db.get_by_reference(conn, external_reference)
                    if existing:
                        if return_json:
                            return jsonify({
                                'success': True,
                                'duplicate': True,
                                'accounting_id': existing['accounting_id'],
                                'message': f"Invoice already recorded. Accounting Record ID: {existing['accounting_id']}",
                                'record': existing,
                            })
                        flash('Invoice already recorded.', 'success')
                        return render_template(
                            'success.html', accounting_id=existing['accounting_id'], record=existing
                        )

                subtotal = data.get('subtotal')
                tax = data.get('tax')
                total = data.get('total')
                accounting_id = f"ACC-{uuid.uuid4().hex[:8].upper()}"
                record = {
                    'accounting_id': accounting_id,
                    'external_reference': external_reference,
                    'vendor': data.get('vendor'),
                    'invoice_number': data.get('invoice_number'),
                    'invoice_date': data.get('invoice_date'),
                    'due_date': data.get('due_date'),
                    'currency': data.get('currency', 'USD'),
                    'subtotal': float(subtotal) if subtotal else None,
                    'tax': float(tax) if tax else None,
                    'total': float(total) if total else None,
                    'line_items': data.get('line_items', ''),
                    'created_at': datetime.utcnow().isoformat(),
                }
                db.insert_record(conn, record)

                if return_json:
                    return jsonify({
                        'success': True,
                        'accounting_id': accounting_id,
                        'message': f'Invoice successfully created. Accounting Record ID: {accounting_id}',
                        'record': record,
                    })
                flash(f'Invoice successfully created. Accounting Record ID: {accounting_id}', 'success')
                return render_template('success.html', accounting_id=accounting_id, record=record)

            except (ValueError, TypeError, sqlite3.Error) as e:
                if return_json:
                    return jsonify({'success': False, 'error': str(e)}), 400
                flash(f'Error creating invoice: {str(e)}', 'error')
                return render_template('new_invoice.html')

        return render_template('new_invoice.html')

    @app.route('/record/<accounting_id>')
    def view_record(accounting_id):
        """View a specific accounting record."""
        record = db.get_record(get_conn(), accounting_id)
        if record:
            return render_template('view_record.html', record=record)
        flash('Record not found', 'error')
        return redirect(url_for('dashboard'))

    @app.route('/api/records', methods=['GET'])
    def get_records():
        """API endpoint to get all accounting records."""
        records = db.list_records(get_conn())
        return jsonify({'records': records, 'count': len(records)})

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3001, debug=os.getenv('FLASK_DEBUG') == '1')
