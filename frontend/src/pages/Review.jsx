import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ExternalLink, FileText, AlertCircle, AlertTriangle, Save, Check, X } from 'lucide-react';
import { invoiceAPI } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import LoadingState from '../components/ui/LoadingState';
import Alert from '../components/ui/Alert';

function Review() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    vendor_name: '',
    invoice_number: '',
    invoice_date: '',
    due_date: '',
    currency: 'USD',
    subtotal: '',
    tax: '',
    total: '',
  });
  const [reviewedBy, setReviewedBy] = useState('');
  const [notes, setNotes] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadInvoice();
  }, [documentId]);

  const loadInvoice = async () => {
    try {
      const data = await invoiceAPI.getById(documentId);
      setInvoice(data);
      
      // Populate form with current data
      setFormData({
        vendor_name: data.vendor?.name || '',
        invoice_number: data.invoice_number || '',
        invoice_date: data.invoice_date || '',
        due_date: data.due_date || '',
        currency: data.currency || 'USD',
        subtotal: data.subtotal || '',
        tax: data.tax || '',
        total: data.total || '',
      });
    } catch (err) {
      setError('Failed to load invoice details.');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSave = async () => {
    setSubmitting(true);
    setError('');

    try {
      await invoiceAPI.update(documentId, {
        vendor: { name: formData.vendor_name },
        invoice_number: formData.invoice_number,
        invoice_date: formData.invoice_date,
        due_date: formData.due_date,
        currency: formData.currency,
        subtotal: formData.subtotal ? parseFloat(formData.subtotal) : null,
        tax: formData.tax ? parseFloat(formData.tax) : null,
        total: formData.total ? parseFloat(formData.total) : null,
        line_items: [],
      });
      alert('Changes saved successfully!');
    } catch (err) {
      setError('Failed to save changes.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async () => {
    if (!reviewedBy) {
      setError('Please enter your name for approval.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      // First save any changes
      await handleSave();
      
      // Then approve
      await invoiceAPI.approve(documentId, reviewedBy, notes);
      navigate(`/invoice/${documentId}`);
    } catch (err) {
      setError('Failed to approve invoice.');
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!reviewedBy) {
      setError('Please enter your name for rejection.');
      return;
    }
    if (!reason) {
      setError('Please provide a reason for rejection.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      await invoiceAPI.reject(documentId, reviewedBy, reason);
      navigate(`/invoice/${documentId}`);
    } catch (err) {
      setError('Failed to reject invoice.');
      setSubmitting(false);
    }
  };

  if (loading) {
    return <LoadingState label="Loading invoice..." />;
  }

  if (error && !invoice) {
    return (
      <Alert type="error" title={error}>
        <Link to="/" className="link mt-1 inline-block">
          Return to Dashboard
        </Link>
      </Alert>
    );
  }

  return (
    <div>
      <PageHeader
        backTo={`/invoice/${documentId}`}
        backLabel="Back to Details"
        title="Review Invoice"
        description="Review and correct extracted data before approval."
      />

      {error && <Alert type="error" className="mb-6">{error}</Alert>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Edit Form */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Edit Invoice Fields</h3>
            </div>
            <div className="p-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="sm:col-span-2">
                <label className="label">Vendor Name</label>
                <input
                  type="text"
                  name="vendor_name"
                  value={formData.vendor_name}
                  onChange={handleInputChange}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Invoice Number</label>
                <input
                  type="text"
                  name="invoice_number"
                  value={formData.invoice_number}
                  onChange={handleInputChange}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Invoice Date</label>
                <input
                  type="date"
                  name="invoice_date"
                  value={formData.invoice_date}
                  onChange={handleInputChange}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Due Date</label>
                <input
                  type="date"
                  name="due_date"
                  value={formData.due_date}
                  onChange={handleInputChange}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Currency</label>
                <select
                  name="currency"
                  value={formData.currency}
                  onChange={handleInputChange}
                  className="input"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="CAD">CAD</option>
                </select>
              </div>
              <div>
                <label className="label">Subtotal</label>
                <input
                  type="number"
                  step="0.01"
                  name="subtotal"
                  value={formData.subtotal}
                  onChange={handleInputChange}
                  className="input tabular-nums"
                />
              </div>
              <div>
                <label className="label">Tax</label>
                <input
                  type="number"
                  step="0.01"
                  name="tax"
                  value={formData.tax}
                  onChange={handleInputChange}
                  className="input tabular-nums"
                />
              </div>
              <div>
                <label className="label">Total</label>
                <input
                  type="number"
                  step="0.01"
                  name="total"
                  value={formData.total}
                  onChange={handleInputChange}
                  className="input tabular-nums"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end border-t border-slate-100 pt-5">
              <button
                onClick={handleSave}
                disabled={submitting}
                className="btn-secondary w-full sm:w-auto"
              >
                <Save className="h-4 w-4" />
                {submitting ? 'Saving...' : 'Save Corrections'}
              </button>
            </div>
            </div>
          </div>
        </div>

        {/* Review Actions */}
        <div className="space-y-6">
          {/* Original Document Preview */}
          <div className="card p-6">
            <h3 className="card-title mb-4">Original Document</h3>
            <div className="flex items-center gap-3 rounded-lg bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white ring-1 ring-slate-200">
                <FileText className="h-4 w-4 text-slate-500" />
              </div>
              <p className="min-w-0 truncate text-sm font-medium text-slate-700">{invoice?.original_filename}</p>
            </div>
            <a
              href={`/api/invoices/${documentId}/document`}
              target="_blank"
              rel="noopener noreferrer"
              className="link mt-3 inline-flex items-center gap-1.5 text-sm"
            >
              Open original document
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>

          {/* Confidence Display */}
          <div className="card p-6">
            <h3 className="card-title mb-4">Extraction Confidence</h3>
            <div className="mb-4">
              <p className="field-label mb-1">Overall Confidence</p>
              <p className="text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">
                {(invoice?.extraction?.overall_confidence || 0).toFixed(2)}
              </p>
            </div>
            
            {invoice?.validation?.errors && invoice.validation.errors.length > 0 && (
              <div className="mb-4">
                <p className="field-label mb-2">Validation Errors</p>
                <ul className="space-y-2">
                  {invoice.validation.errors.map((error, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-red-700">
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                      <span>{error}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {invoice?.validation?.warnings && invoice.validation.warnings.length > 0 && (
              <div>
                <p className="field-label mb-2">Validation Warnings</p>
                <ul className="space-y-2">
                  {invoice.validation.warnings.map((warning, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-amber-700">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Approval/Rejection */}
          <div className="card p-6">
            <h3 className="card-title mb-4">Review Decision</h3>
            
            <div className="space-y-4">
              <div>
                <label className="label">Reviewed By</label>
                <input
                  type="text"
                  value={reviewedBy}
                  onChange={(e) => setReviewedBy(e.target.value)}
                  className="input"
                  placeholder="Your name"
                />
              </div>
              
              <div>
                <label className="label">Notes <span className="font-normal text-slate-400">(Optional)</span></label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="input"
                  rows="2"
                  placeholder="Any additional notes..."
                />
              </div>
              
              <div>
                <label className="label">Rejection Reason <span className="font-normal text-slate-400">(if rejecting)</span></label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="input"
                  rows="2"
                  placeholder="Reason for rejection..."
                />
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-3">
              <button
                onClick={handleApprove}
                disabled={submitting}
                className="btn-success py-2.5"
              >
                <Check className="h-4 w-4" />
                {submitting ? 'Processing...' : 'Approve Invoice'}
              </button>
              
              <button
                onClick={handleReject}
                disabled={submitting}
                className="btn bg-white text-red-600 border border-red-200 hover:bg-red-50 py-2.5"
              >
                <X className="h-4 w-4" />
                {submitting ? 'Processing...' : 'Reject Invoice'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Review;
