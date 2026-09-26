import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { invoiceAPI } from '../services/api';

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
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-primary-600 rounded-full animate-bounce"></div>
          <div className="w-4 h-4 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-4 h-4 bg-primary-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    );
  }

  if (error && !invoice) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <div className="flex items-center">
          <span className="text-red-600 mr-3 text-2xl">⚠️</span>
          <div>
            <p className="text-red-700 font-medium">{error}</p>
            <Link to="/" className="text-primary-600 hover:text-primary-800 mt-2 inline-block text-sm">
              Return to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <Link to={`/invoice/${documentId}`} className="text-primary-600 hover:text-primary-800 text-sm font-medium mb-2 inline-block">
          ← Back to Details
        </Link>
        <h1 className="text-3xl font-semibold text-gray-900 mb-2">Review Invoice</h1>
        <p className="text-gray-600">Review and correct extracted data before approval.</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center">
            <span className="text-red-600 mr-2">⚠️</span>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Edit Form */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-6">Edit Invoice Fields</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Vendor Name</label>
                <input
                  type="text"
                  name="vendor_name"
                  value={formData.vendor_name}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Invoice Number</label>
                <input
                  type="text"
                  name="invoice_number"
                  value={formData.invoice_number}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Invoice Date</label>
                <input
                  type="date"
                  name="invoice_date"
                  value={formData.invoice_date}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Due Date</label>
                <input
                  type="date"
                  name="due_date"
                  value={formData.due_date}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Currency</label>
                <select
                  name="currency"
                  value={formData.currency}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="GBP">GBP</option>
                  <option value="CAD">CAD</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Subtotal</label>
                <input
                  type="number"
                  step="0.01"
                  name="subtotal"
                  value={formData.subtotal}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tax</label>
                <input
                  type="number"
                  step="0.01"
                  name="tax"
                  value={formData.tax}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Total</label>
                <input
                  type="number"
                  step="0.01"
                  name="total"
                  value={formData.total}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>

            <button
              onClick={handleSave}
              disabled={submitting}
              className="mt-6 w-full bg-gray-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-gray-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? 'Saving...' : 'Save Corrections'}
            </button>
          </div>
        </div>

        {/* Review Actions */}
        <div className="space-y-6">
          {/* Original Document Preview */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Original Document</h3>
            <p className="text-sm text-gray-600 mb-3">{invoice?.original_filename}</p>
            <a
              href={`/api/invoices/${documentId}/document`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center text-primary-600 hover:text-primary-800 text-sm font-medium"
            >
              <span className="mr-2">📄</span>
              Open original document
            </a>
          </div>

          {/* Confidence Display */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Extraction Confidence</h3>
            <div className="mb-4">
              <label className="text-sm font-medium text-gray-500 block mb-2">Overall Confidence</label>
              <p className="text-3xl font-bold text-gray-900">
                {(invoice?.extraction?.overall_confidence || 0).toFixed(2)}
              </p>
            </div>
            
            {invoice?.validation?.errors && invoice.validation.errors.length > 0 && (
              <div className="mb-4">
                <label className="text-sm font-medium text-gray-500 block mb-2">Validation Errors</label>
                <ul className="space-y-2">
                  {invoice.validation.errors.map((error, idx) => (
                    <li key={idx} className="text-sm text-red-600 flex items-start">
                      <span className="mr-2">•</span>
                      <span>{error}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {invoice?.validation?.warnings && invoice.validation.warnings.length > 0 && (
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-2">Validation Warnings</label>
                <ul className="space-y-2">
                  {invoice.validation.warnings.map((warning, idx) => (
                    <li key={idx} className="text-sm text-amber-600 flex items-start">
                      <span className="mr-2">•</span>
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Approval/Rejection */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Review Decision</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Reviewed By</label>
                <input
                  type="text"
                  value={reviewedBy}
                  onChange={(e) => setReviewedBy(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Your name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Notes (Optional)</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  rows="2"
                  placeholder="Any additional notes..."
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Rejection Reason (if rejecting)</label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  rows="2"
                  placeholder="Reason for rejection..."
                />
              </div>
            </div>

            <div className="mt-6 space-y-3">
              <button
                onClick={handleApprove}
                disabled={submitting}
                className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? 'Processing...' : 'Approve Invoice'}
              </button>
              
              <button
                onClick={handleReject}
                disabled={submitting}
                className="w-full bg-red-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
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
