import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { invoiceAPI } from '../services/api';

function InvoiceDetails() {
  const { documentId } = useParams();
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadInvoice();
  }, [documentId]);

  const loadInvoice = async () => {
    try {
      const data = await invoiceAPI.getById(documentId);
      setInvoice(data);
    } catch (err) {
      setError('Failed to load invoice details.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusStyle = (status) => {
    const styles = {
      'UPLOADED': 'bg-gray-100 text-gray-700 border-gray-200',
      'PROCESSING': 'bg-blue-50 text-blue-700 border-blue-200',
      'PROCESSED': 'bg-green-50 text-green-700 border-green-200',
      'NEEDS_REVIEW': 'bg-amber-50 text-amber-700 border-amber-200',
      'APPROVED': 'bg-green-50 text-green-700 border-green-200',
      'REJECTED': 'bg-red-50 text-red-700 border-red-200',
      'RPA_QUEUED': 'bg-purple-50 text-purple-700 border-purple-200',
      'RPA_PROCESSING': 'bg-blue-50 text-blue-700 border-blue-200',
      'RPA_COMPLETED': 'bg-green-50 text-green-700 border-green-200',
      'RPA_FAILED': 'bg-red-50 text-red-700 border-red-200',
      'ERROR': 'bg-red-50 text-red-700 border-red-200',
    };
    return styles[status] || 'bg-gray-100 text-gray-700 border-gray-200';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-amber-600';
    return 'text-red-600';
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

  if (error || !invoice) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6">
        <div className="flex items-center">
          <span className="text-red-600 mr-3 text-2xl">⚠️</span>
          <div>
            <p className="text-red-700 font-medium">{error || 'Invoice not found.'}</p>
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
      <div className="mb-8 flex justify-between items-start">
        <div>
          <Link to="/" className="text-primary-600 hover:text-primary-800 text-sm font-medium mb-2 inline-block">
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">Invoice Details</h1>
          <p className="text-gray-600">Document ID: {invoice.document_id}</p>
        </div>
        <span className={`px-4 py-2 text-sm font-medium rounded-full border ${getStatusStyle(invoice.status)}`}>
          {invoice.status.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Information */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-6">Invoice Information</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Original Filename</label>
                <p className="text-gray-900">{invoice.original_filename}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Vendor</label>
                <p className="text-gray-900">{invoice.vendor?.name || '-'}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Invoice Number</label>
                <p className="text-gray-900">{invoice.invoice_number || '-'}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Invoice Date</label>
                <p className="text-gray-900">{invoice.invoice_date || '-'}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Due Date</label>
                <p className="text-gray-900">{invoice.due_date || '-'}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Currency</label>
                <p className="text-gray-900">{invoice.currency}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Subtotal</label>
                <p className="text-gray-900">{invoice.subtotal ? `${invoice.subtotal.toFixed(2)}` : '-'}</p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-1">Tax</label>
                <p className="text-gray-900">{invoice.tax ? `${invoice.tax.toFixed(2)}` : '-'}</p>
              </div>
              
              <div className="md:col-span-2">
                <label className="text-sm font-medium text-gray-500 block mb-1">Total</label>
                <p className="text-2xl font-semibold text-gray-900">{invoice.total ? `${invoice.total.toFixed(2)}` : '-'}</p>
              </div>
            </div>
          </div>

          {/* Extraction Results */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-6">Extraction Results</h3>
            
            <div className="mb-6">
              <label className="text-sm font-medium text-gray-500 block mb-2">Overall Confidence</label>
              <div className="flex items-center space-x-3">
                <p className={`text-3xl font-semibold ${getConfidenceColor(invoice.extraction?.overall_confidence || 0)}`}>
                  {(invoice.extraction?.overall_confidence || 0).toFixed(2)}
                </p>
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getConfidenceColor(invoice.extraction?.overall_confidence || 0).replace('text-', 'bg-')}`}
                    style={{ width: `${(invoice.extraction?.overall_confidence || 0) * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>
            
            {Object.keys(invoice.extraction?.fields || {}).length > 0 && (
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-3">Field-Level Confidence</label>
                <div className="space-y-3">
                  {Object.entries(invoice.extraction?.fields || {}).map(([fieldName, fieldData]) => (
                    <div key={fieldName} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <span className="text-sm font-medium text-gray-700 capitalize">{fieldName.replace(/_/g, ' ')}</span>
                      <span className={`text-sm font-semibold ${getConfidenceColor(fieldData.confidence)}`}>
                        {(fieldData.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="mt-6 pt-6 border-t border-gray-200">
              <label className="text-sm font-medium text-gray-500 block mb-1">Page Count</label>
              <p className="text-gray-900">{invoice.extraction?.page_count || 0} pages</p>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Validation Results */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Validation Results</h3>
            
            <div className="mb-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-500">Valid</label>
                <span className={`text-lg font-semibold ${invoice.validation?.is_valid ? 'text-green-600' : 'text-red-600'}`}>
                  {invoice.validation?.is_valid ? '✓ Yes' : '✗ No'}
                </span>
              </div>
            </div>
            
            {invoice.validation?.errors && invoice.validation.errors.length > 0 && (
              <div className="mb-4">
                <label className="text-sm font-medium text-gray-500 block mb-2">Errors</label>
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
            
            {invoice.validation?.warnings && invoice.validation.warnings.length > 0 && (
              <div>
                <label className="text-sm font-medium text-gray-500 block mb-2">Warnings</label>
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

          {/* RPA Status */}
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">RPA Status</h3>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-500">Eligible</label>
                <span className="text-sm text-gray-900">{invoice.rpa?.eligible ? 'Yes' : 'No'}</span>
              </div>
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-gray-500">Status</label>
                <span className="text-sm text-gray-900">{invoice.rpa?.status || 'NOT_STARTED'}</span>
              </div>
              {invoice.rpa?.job_id && (
                <div>
                  <label className="text-sm font-medium text-gray-500 block mb-1">Job ID</label>
                  <p className="text-sm text-gray-900 font-mono">{invoice.rpa.job_id}</p>
                </div>
              )}
              {invoice.rpa?.message && (
                <div>
                  <label className="text-sm font-medium text-gray-500 block mb-1">Message</label>
                  <p className="text-sm text-gray-900">{invoice.rpa.message}</p>
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          {invoice.status === 'NEEDS_REVIEW' && (
            <Link
              to={`/review/${documentId}`}
              className="block w-full bg-primary-600 text-white py-3 px-6 rounded-xl font-medium hover:bg-primary-700 transition-colors text-center"
            >
              Review & Approve
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default InvoiceDetails;
