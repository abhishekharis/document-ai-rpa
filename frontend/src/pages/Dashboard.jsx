import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Loader, Eye, CheckCircle2, Bot, XCircle, Upload, ArrowRight, Sparkles } from 'lucide-react';
import { invoiceAPI } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import StatCard from '../components/ui/StatCard';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingState from '../components/ui/LoadingState';
import EmptyState from '../components/ui/EmptyState';

function Dashboard() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    processing: 0,
    needsReview: 0,
    approved: 0,
    rpaCompleted: 0,
    rpaFailed: 0,
  });

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async () => {
    try {
      const data = await invoiceAPI.getAll();
      setInvoices(data.invoices);
      
      // Calculate stats
      const stats = {
        total: data.count,
        processing: data.invoices.filter(i => i.status === 'PROCESSING').length,
        needsReview: data.invoices.filter(i => i.status === 'NEEDS_REVIEW').length,
        approved: data.invoices.filter(i => i.status === 'APPROVED').length,
        rpaCompleted: data.invoices.filter(i => i.status === 'RPA_COMPLETED').length,
        rpaFailed: data.invoices.filter(i => i.status === 'RPA_FAILED').length,
      };
      setStats(stats);
    } catch (error) {
      console.error('Failed to load invoices:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingState label="Loading dashboard..." />;
  }

  return (
    <div>
      <PageHeader
        title="Document Intelligence"
        description="Upload, process, and extract structured information from your documents."
        actions={
          <Link to="/upload" className="btn-primary">
            <Upload className="h-4 w-4" />
            Upload Document
          </Link>
        }
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <StatCard label="Total Documents" value={stats.total} icon={FileText} tone="slate" />
        <StatCard label="Processing" value={stats.processing} icon={Loader} tone="blue" />
        <StatCard label="Needs Review" value={stats.needsReview} icon={Eye} tone="amber" />
        <StatCard label="Approved" value={stats.approved} icon={CheckCircle2} tone="emerald" />
        <StatCard label="RPA Completed" value={stats.rpaCompleted} icon={Bot} tone="primary" />
        <StatCard label="RPA Failed" value={stats.rpaFailed} icon={XCircle} tone="red" />
      </div>

      {/* Upload CTA */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 p-6 sm:p-8 mb-8 shadow-card">
        <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-white/10 blur-2xl" />
        <div className="relative flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-4">
            <div className="hidden sm:flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white/15 ring-1 ring-white/20">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Process a New Document</h2>
              <p className="mt-1 text-sm text-primary-100">Upload invoices, receipts, or other documents for AI-powered extraction.</p>
            </div>
          </div>
          <Link
            to="/upload"
            className="btn bg-white text-primary-700 hover:bg-primary-50 shadow-sm"
          >
            Upload Document
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* Documents Table */}
      <div className="card overflow-hidden">
        <div className="card-header">
          <h3 className="card-title">Recent Documents</h3>
          {invoices.length > 0 && (
            <Link to="/documents" className="link inline-flex items-center gap-1 text-sm">
              View all
              <ArrowRight className="h-4 w-4" />
            </Link>
          )}
        </div>
        
        {invoices.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No documents yet"
            description="Upload your first document to begin extracting structured data."
            action={
              <Link to="/upload" className="btn-primary">
                <Upload className="h-4 w-4" />
                Upload Document
              </Link>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50/80 border-b border-slate-100">
                <tr>
                  <th className="table-th">Document ID</th>
                  <th className="table-th">Vendor</th>
                  <th className="table-th">Invoice #</th>
                  <th className="table-th text-right">Total</th>
                  <th className="table-th">Status</th>
                  <th className="table-th">Created</th>
                  <th className="table-th text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((invoice) => (
                  <tr key={invoice.document_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="table-td font-mono text-xs font-medium text-slate-900">
                      {invoice.document_id}
                    </td>
                    <td className="table-td font-medium text-slate-700">
                      {invoice.vendor?.name || '-'}
                    </td>
                    <td className="table-td">
                      {invoice.invoice_number || '-'}
                    </td>
                    <td className="table-td text-right tabular-nums">
                      {invoice.total ? `${invoice.currency} ${invoice.total.toFixed(2)}` : '-'}
                    </td>
                    <td className="table-td">
                      <StatusBadge status={invoice.status} />
                    </td>
                    <td className="table-td">
                      {new Date(invoice.created_at).toLocaleDateString()}
                    </td>
                    <td className="table-td text-right">
                      <div className="inline-flex items-center gap-3">
                        <Link to={`/invoice/${invoice.document_id}`} className="link">
                          View
                        </Link>
                        {invoice.status === 'NEEDS_REVIEW' && (
                          <Link
                            to={`/review/${invoice.document_id}`}
                            className="font-medium text-amber-600 hover:text-amber-700"
                          >
                            Review
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
