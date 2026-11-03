import { useState, useEffect, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Search, ChevronDown, Trash2, RefreshCw, FileText, SearchX, Upload, Loader2, AlertTriangle } from 'lucide-react';
import { invoiceAPI } from '../services/api';
import { useInvoices } from '../hooks/useInvoices';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingState from '../components/ui/LoadingState';
import EmptyState from '../components/ui/EmptyState';
import Alert from '../components/ui/Alert';

const STATUS_OPTIONS = [
  { value: 'ALL', label: 'All' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'ERROR', label: 'Error' },
];

const DATE_OPTIONS = [
  { value: 'ALL', label: 'All' },
  { value: '7', label: 'Last 7 days' },
  { value: '14', label: 'Last 14 days' },
  { value: '30', label: 'Last 30 days' },
];

const DAY_MS = 24 * 60 * 60 * 1000;

// Backend stores created_at in UTC without a timezone suffix
const parseCreatedAt = (value) => new Date(/(Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`);

const ACTIONS = {
  delete: {
    label: 'Delete',
    runningLabel: 'Deleting...',
    doneLabel: 'Deleted',
    description: 'This permanently removes the selected documents and their stored files. This cannot be undone.',
    run: invoiceAPI.bulkDelete,
  },
  reprocess: {
    label: 'Reprocess',
    runningLabel: 'Reprocessing...',
    doneLabel: 'Reprocessed',
    description: 'Documents with status Error, Rejected, or Needs Review are run through the processing pipeline again; others are skipped. This may take a while.',
    run: invoiceAPI.bulkReprocess,
  },
};

const pluralize = (count) => `${count} document${count === 1 ? '' : 's'}`;

function Documents() {
  const { data, isLoading: loading, isError, refetch } = useInvoices();
  const invoices = useMemo(() => data?.invoices ?? [], [data]);
  const loadError = isError ? 'Failed to load documents. Please try again.' : '';
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateFilter, setDateFilter] = useState('ALL');
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [menuOpen, setMenuOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [actionRunning, setActionRunning] = useState(false);
  const [notice, setNotice] = useState(null);
  const selectAllRef = useRef(null);
  const menuRef = useRef(null);

  const loadInvoices = async () => {
    setSelectedIds(new Set());
    await refetch();
  };

  const visibleInvoices = useMemo(() => {
    const term = search.trim().toLowerCase();
    const cutoff = dateFilter === 'ALL' ? null : Date.now() - Number(dateFilter) * DAY_MS;
    return invoices.filter((invoice) => {
      if (statusFilter !== 'ALL' && invoice.status !== statusFilter) return false;
      if (cutoff !== null && parseCreatedAt(invoice.created_at).getTime() < cutoff) return false;
      if (!term) return true;
      const vendor = (invoice.vendor?.name || '').toLowerCase();
      const invoiceNumber = (invoice.invoice_number || '').toLowerCase();
      return vendor.includes(term) || invoiceNumber.includes(term);
    });
  }, [invoices, search, statusFilter, dateFilter]);

  // Drop selections that are no longer visible after search/filter changes
  useEffect(() => {
    setSelectedIds((prev) => {
      const visibleIds = new Set(visibleInvoices.map((i) => i.document_id));
      const next = new Set([...prev].filter((id) => visibleIds.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [visibleInvoices]);

  const selectedCount = selectedIds.size;
  const allVisibleSelected = visibleInvoices.length > 0 && visibleInvoices.every((i) => selectedIds.has(i.document_id));
  const someVisibleSelected = selectedCount > 0 && !allVisibleSelected;

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someVisibleSelected;
    }
  }, [someVisibleSelected]);

  useEffect(() => {
    if (selectedCount === 0) setMenuOpen(false);
  }, [selectedCount]);

  useEffect(() => {
    if (!menuOpen) return;
    const handleMouseDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [menuOpen]);

  const toggleOne = (documentId) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(documentId)) {
        next.delete(documentId);
      } else {
        next.add(documentId);
      }
      return next;
    });
  };

  const toggleAll = () => {
    setSelectedIds(allVisibleSelected ? new Set() : new Set(visibleInvoices.map((i) => i.document_id)));
  };

  const chooseAction = (action) => {
    setMenuOpen(false);
    setPendingAction(action);
  };

  const confirmAction = async () => {
    const action = ACTIONS[pendingAction];
    setActionRunning(true);
    setNotice(null);
    try {
      const data = await action.run([...selectedIds]);
      const failed = data.results.filter((r) => !r.success);
      const succeeded = data.results.filter((r) => r.success);
      const details = [
        ...(pendingAction === 'reprocess'
          ? succeeded.map((r) => `${r.document_id}: now ${r.status.replace(/_/g, ' ')}`)
          : []),
        ...failed.map((r) => `${r.document_id}: ${r.message}`),
      ];
      let message = `${action.doneLabel} ${pluralize(data.succeeded)}.`;
      if (data.failed > 0) message += ` ${pluralize(data.failed)} could not be ${action.doneLabel.toLowerCase()}.`;
      setNotice({
        type: data.failed === 0 ? 'success' : data.succeeded === 0 ? 'error' : 'warning',
        message,
        details,
      });
    } catch (error) {
      console.error(`${action.label} failed:`, error);
      setNotice({
        type: 'error',
        message: `${action.label} failed: ${error.response?.data?.detail || error.message}. No changes were confirmed.`,
        details: [],
      });
    } finally {
      setActionRunning(false);
      setPendingAction(null);
      await loadInvoices({ showSpinner: false });
    }
  };

  const clearFilters = () => {
    setSearch('');
    setStatusFilter('ALL');
    setDateFilter('ALL');
  };

  if (loading) {
    return <LoadingState label="Loading documents..." />;
  }

  return (
    <div>
      <PageHeader
        title="Documents"
        description="Manage your uploaded and processed documents."
        actions={
          <Link to="/upload" className="btn-primary">
            <Upload className="h-4 w-4" />
            Upload Document
          </Link>
        }
      />

      {loadError && invoices.length > 0 && (
        <Alert
          type="error"
          title={loadError}
          className="mb-6"
        >
          <button
            type="button"
            onClick={() => loadInvoices()}
            className="btn-secondary text-xs py-1.5 px-3 mt-2 inline-flex items-center gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        </Alert>
      )}

      {/* Controls */}
      <div className="card p-4 mb-6 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex flex-col sm:flex-row gap-3 flex-1">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by vendor or invoice number..."
              aria-label="Search by vendor or invoice number"
              className="input pl-9"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
            className="input sm:w-40"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            aria-label="Filter by date"
            className="input sm:w-40"
          >
            {DATE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center justify-between gap-4 sm:justify-end">
          {selectedCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-primary-50 px-3 py-1 text-sm font-medium text-primary-700">
              {pluralize(selectedCount)} selected
            </span>
          )}
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              disabled={selectedCount === 0 || actionRunning}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              className="btn-secondary"
            >
              Bulk Actions
              <ChevronDown className={`h-4 w-4 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
            </button>
            {menuOpen && (
              <div role="menu" className="absolute right-0 mt-2 w-44 overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg z-20">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => chooseAction('delete')}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => chooseAction('reprocess')}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                >
                  <RefreshCw className="h-4 w-4" />
                  Reprocess
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {notice && (
        <Alert
          type={notice.type}
          title={notice.message}
          details={notice.details}
          onDismiss={() => setNotice(null)}
          className="mb-6"
        />
      )}

      {/* Documents Table */}
      <div className="card overflow-hidden">
        {loadError && invoices.length === 0 ? (
          <EmptyState
            icon={AlertTriangle}
            title="Failed to load documents"
            description={loadError}
            action={
              <button
                type="button"
                onClick={() => loadInvoices()}
                className="btn-secondary inline-flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Retry
              </button>
            }
          />
        ) : invoices.length === 0 ? (
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
                  <th className="table-th w-12">
                    <input
                      ref={selectAllRef}
                      type="checkbox"
                      checked={allVisibleSelected}
                      onChange={toggleAll}
                      disabled={visibleInvoices.length === 0}
                      aria-label="Select all documents"
                      className="checkbox"
                    />
                  </th>
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
                {visibleInvoices.length === 0 ? (
                  <tr>
                    <td colSpan={8}>
                      <EmptyState
                        icon={SearchX}
                        title="No documents found"
                        description="Try changing your search or filters."
                        action={
                          <button type="button" onClick={clearFilters} className="btn-secondary">
                            Clear filters
                          </button>
                        }
                      />
                    </td>
                  </tr>
                ) : (
                  visibleInvoices.map((invoice) => {
                    const isSelected = selectedIds.has(invoice.document_id);
                    return (
                      <tr
                        key={invoice.document_id}
                        className={`transition-colors ${isSelected ? 'bg-primary-50/70' : 'hover:bg-slate-50/70'}`}
                      >
                        <td className="px-6 py-4">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleOne(invoice.document_id)}
                            aria-label={`Select ${invoice.document_id}`}
                            className="checkbox"
                          />
                        </td>
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
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Confirm Dialog */}
      {pendingAction && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div role="dialog" aria-modal="true" className="card w-full max-w-md p-6 shadow-xl">
            <div className="flex items-start gap-4">
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
                pendingAction === 'delete' ? 'bg-red-100' : 'bg-primary-100'
              }`}>
                {pendingAction === 'delete'
                  ? <AlertTriangle className="h-5 w-5 text-red-600" />
                  : <RefreshCw className="h-5 w-5 text-primary-600" />}
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  {ACTIONS[pendingAction].label} {pluralize(selectedCount)}?
                </h3>
                <p className="mt-2 text-sm text-slate-500">{ACTIONS[pendingAction].description}</p>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setPendingAction(null)}
                disabled={actionRunning}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmAction}
                disabled={actionRunning}
                className={pendingAction === 'delete' ? 'btn-danger' : 'btn-primary'}
              >
                {actionRunning ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {ACTIONS[pendingAction].runningLabel}
                  </>
                ) : (
                  ACTIONS[pendingAction].label
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Documents;
