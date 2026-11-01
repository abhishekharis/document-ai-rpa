import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle2, XCircle, AlertCircle, AlertTriangle, ClipboardCheck, FileText } from 'lucide-react';
import { invoiceAPI } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingState from '../components/ui/LoadingState';
import Alert from '../components/ui/Alert';

function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      <dt className="field-label">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-slate-900 break-words">{children}</dd>
    </div>
  );
}

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

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-amber-600';
    return 'text-red-600';
  };

  if (loading) {
    return <LoadingState label="Loading invoice..." />;
  }

  if (error || !invoice) {
    return (
      <Alert type="error" title={error || 'Invoice not found.'}>
        <Link to="/" className="link mt-1 inline-block">
          Return to Dashboard
        </Link>
      </Alert>
    );
  }

  const overallConfidence = invoice.extraction?.overall_confidence || 0;

  return (
    <div>
      <PageHeader
        backTo="/"
        backLabel="Back to Dashboard"
        title="Invoice Details"
        description={<>Document ID: <span className="font-mono text-slate-700">{invoice.document_id}</span></>}
        actions={<StatusBadge status={invoice.status} size="lg" />}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Invoice Information */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Invoice Information</h3>
            </div>
            <div className="p-6">
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-5">
                <Field label="Original Filename" className="sm:col-span-2">
                  <span className="inline-flex items-center gap-2">
                    <FileText className="h-4 w-4 text-slate-400" />
                    {invoice.original_filename}
                  </span>
                </Field>
                <Field label="Vendor">{invoice.vendor?.name || '-'}</Field>
                <Field label="Invoice Number">{invoice.invoice_number || '-'}</Field>
                <Field label="Invoice Date">{invoice.invoice_date || '-'}</Field>
                <Field label="Due Date">{invoice.due_date || '-'}</Field>
                <Field label="Currency">{invoice.currency}</Field>
                <Field label="Subtotal"><span className="tabular-nums">{invoice.subtotal ? `${invoice.subtotal.toFixed(2)}` : '-'}</span></Field>
                <Field label="Tax"><span className="tabular-nums">{invoice.tax ? `${invoice.tax.toFixed(2)}` : '-'}</span></Field>
              </dl>
              <div className="mt-6 flex items-center justify-between rounded-lg bg-slate-50 px-5 py-4 ring-1 ring-inset ring-slate-200">
                <span className="text-sm font-medium text-slate-600">Total</span>
                <span className="text-2xl font-semibold tracking-tight text-slate-900 tabular-nums">
                  {invoice.total ? `${invoice.total.toFixed(2)}` : '-'}
                </span>
              </div>
            </div>
          </div>

          {/* Extraction Results */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Extraction Results</h3>
            </div>
            <div className="p-6">
              <div className="mb-6">
                <p className="field-label mb-2">Overall Confidence</p>
                <div className="flex items-center gap-4">
                  <p className={`text-3xl font-semibold tabular-nums ${getConfidenceColor(overallConfidence)}`}>
                    {overallConfidence.toFixed(2)}
                  </p>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${getConfidenceColor(overallConfidence).replace('text-', 'bg-')}`}
                      style={{ width: `${overallConfidence * 100}%` }}
                    ></div>
                  </div>
                </div>
              </div>
              
              {Object.keys(invoice.extraction?.fields || {}).length > 0 && (
                <div>
                  <p className="field-label mb-3">Field-Level Confidence</p>
                  <div className="space-y-3">
                    {Object.entries(invoice.extraction?.fields || {}).map(([fieldName, fieldData]) => (
                      <div key={fieldName} className="grid grid-cols-[minmax(0,10rem)_1fr_3rem] items-center gap-4">
                        <span className="truncate text-sm font-medium text-slate-700 capitalize">{fieldName.replace(/_/g, ' ')}</span>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${getConfidenceColor(fieldData.confidence).replace('text-', 'bg-')}`}
                            style={{ width: `${fieldData.confidence * 100}%` }}
                          />
                        </div>
                        <span className={`text-right text-sm font-semibold tabular-nums ${getConfidenceColor(fieldData.confidence)}`}>
                          {(fieldData.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <div className="mt-6 pt-5 border-t border-slate-100 flex items-center justify-between">
                <span className="field-label">Page Count</span>
                <span className="text-sm font-medium text-slate-900">{invoice.extraction?.page_count || 0} pages</span>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Validation Results */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Validation Results</h3>
            </div>
            <div className="p-6 space-y-5">
              <div className={`flex items-center justify-between rounded-lg px-4 py-3 ring-1 ring-inset ${
                invoice.validation?.is_valid ? 'bg-emerald-50 ring-emerald-200' : 'bg-red-50 ring-red-200'
              }`}>
                <span className="text-sm font-medium text-slate-700">Valid</span>
                <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${invoice.validation?.is_valid ? 'text-emerald-700' : 'text-red-700'}`}>
                  {invoice.validation?.is_valid
                    ? <><CheckCircle2 className="h-4 w-4" /> Yes</>
                    : <><XCircle className="h-4 w-4" /> No</>}
                </span>
              </div>
              
              {invoice.validation?.errors && invoice.validation.errors.length > 0 && (
                <div>
                  <p className="field-label mb-2">Errors</p>
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
              
              {invoice.validation?.warnings && invoice.validation.warnings.length > 0 && (
                <div>
                  <p className="field-label mb-2">Warnings</p>
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
          </div>

          {/* RPA Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">RPA Status</h3>
            </div>
            <dl className="divide-y divide-slate-100 px-6">
              <div className="flex items-center justify-between py-3">
                <dt className="text-sm text-slate-500">Eligible</dt>
                <dd className="text-sm font-medium text-slate-900">{invoice.rpa?.eligible ? 'Yes' : 'No'}</dd>
              </div>
              <div className="flex items-center justify-between py-3">
                <dt className="text-sm text-slate-500">Status</dt>
                <dd className="text-sm font-medium text-slate-900">{invoice.rpa?.status || 'NOT_STARTED'}</dd>
              </div>
              {invoice.rpa?.accounting_record_id && (
                <div className="flex items-center justify-between py-3">
                  <dt className="text-sm text-slate-500">Accounting record</dt>
                  <dd className="text-sm font-medium">
                    <a
                      href={`/accounting/record/${invoice.rpa.accounting_record_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="link font-mono"
                    >
                      {invoice.rpa.accounting_record_id}
                    </a>
                  </dd>
                </div>
              )}
              {invoice.rpa?.job_id && (
                <div className="py-3">
                  <dt className="text-sm text-slate-500 mb-1">Job ID</dt>
                  <dd className="text-sm text-slate-900 font-mono break-all">{invoice.rpa.job_id}</dd>
                </div>
              )}
              {invoice.rpa?.message && (
                <div className="py-3">
                  <dt className="text-sm text-slate-500 mb-1">Message</dt>
                  <dd className="text-sm text-slate-900">{invoice.rpa.message}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Action Buttons */}
          {invoice.status === 'NEEDS_REVIEW' && (
            <Link
              to={`/review/${documentId}`}
              className="btn-primary w-full py-3"
            >
              <ClipboardCheck className="h-4 w-4" />
              Review & Approve
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default InvoiceDetails;
