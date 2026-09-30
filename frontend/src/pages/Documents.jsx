import { useState, useEffect, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import { invoiceAPI } from '../services/api';

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

const NOTICE_STYLES = {
  success: { box: 'bg-green-50 border-green-200', text: 'text-green-700', icon: '✅' },
  warning: { box: 'bg-amber-50 border-amber-200', text: 'text-amber-700', icon: '⚠️' },
  error: { box: 'bg-red-50 border-red-200', text: 'text-red-700', icon: '⚠️' },
};

const pluralize = (count) => `${count} document${count === 1 ? '' : 's'}`;

function Documents() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
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

  useEffect(() => {
    loadInvoices();
  }, []);

  const loadInvoices = async ({ showSpinner = true } = {}) => {
    if (showSpinner) setLoading(true);
    setLoadError('');
    setSelectedIds(new Set());
    try {
      const data = await invoiceAPI.getAll();
      setInvoices(data.invoices);
    } catch (error) {
      console.error('Failed to load documents:', error);
      setLoadError('Failed to load documents. Please try again.');
    } finally {
      setLoading(false);
    }
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

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-gray-900 mb-2">Documents</h1>
        <p className="text-gray-600">Manage your uploaded and processed documents.</p>
      </div>

      {loadError && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center">
            <span className="text-red-600 mr-2">⚠️</span>
            <p className="text-sm text-red-700">{loadError}</p>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex flex-col sm:flex-row gap-3 flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by vendor or invoice number..."
            aria-label="Search by vendor or invoice number"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status"
            className="border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            aria-label="Filter by date"
            className="border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            {DATE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4">
          {selectedCount > 0 && (
            <span className="text-sm font-medium text-gray-700">{pluralize(selectedCount)} selected</span>
          )}
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              disabled={selectedCount === 0 || actionRunning}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              Bulk Actions ▾
            </button>
            {menuOpen && (
              <div role="menu" className="absolute right-0 mt-2 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-20 py-1">
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => chooseAction('delete')}
                  className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-gray-50"
                >
                  Delete
                </button>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => chooseAction('reprocess')}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                >
                  Reprocess
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {notice && (
        <div className={`mb-6 p-4 border rounded-lg flex items-start justify-between ${NOTICE_STYLES[notice.type].box}`}>
          <div className="flex items-start">
            <span className="mr-2">{NOTICE_STYLES[notice.type].icon}</span>
            <div className={`text-sm ${NOTICE_STYLES[notice.type].text}`}>
              <p className="font-medium">{notice.message}</p>
              {notice.details.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {notice.details.map((detail) => (
                    <li key={detail} className="flex items-start">
                      <span className="mr-2">•</span>
                      <span>{detail}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            aria-label="Dismiss notice"
            className={`text-sm font-medium ml-4 ${NOTICE_STYLES[notice.type].text}`}
          >
            ✕
          </button>
        </div>
      )}

      {/* Documents Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {invoices.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-4xl mb-4">📄</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No documents yet</h3>
            <p className="text-gray-600 mb-4">Upload your first document to begin extracting structured data.</p>
            <Link
              to="/upload"
              className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Upload Document
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left w-12">
                    <input
                      ref={selectAllRef}
                      type="checkbox"
                      checked={allVisibleSelected}
                      onChange={toggleAll}
                      disabled={visibleInvoices.length === 0}
                      aria-label="Select all documents"
                      className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                    />
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Document ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Vendor</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Invoice #</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {visibleInvoices.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">No documents found</h3>
                      <p className="text-gray-600 mb-4">Try changing your search or filters.</p>
                      <button
                        type="button"
                        onClick={clearFilters}
                        className="text-primary-600 hover:text-primary-800 text-sm font-medium"
                      >
                        Clear filters
                      </button>
                    </td>
                  </tr>
                ) : (
                  visibleInvoices.map((invoice) => {
                    const isSelected = selectedIds.has(invoice.document_id);
                    return (
                      <tr
                        key={invoice.document_id}
                        className={`transition-colors ${isSelected ? 'bg-primary-50' : 'hover:bg-gray-50'}`}
                      >
                        <td className="px-6 py-4">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleOne(invoice.document_id)}
                            aria-label={`Select ${invoice.document_id}`}
                            className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                          />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {invoice.document_id}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {invoice.vendor?.name || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {invoice.invoice_number || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {invoice.total ? `${invoice.currency} ${invoice.total.toFixed(2)}` : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 text-xs font-medium rounded-full border ${getStatusStyle(invoice.status)}`}>
                            {invoice.status.replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                          {new Date(invoice.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <Link
                            to={`/invoice/${invoice.document_id}`}
                            className="text-primary-600 hover:text-primary-800 font-medium"
                          >
                            View
                          </Link>
                          {invoice.status === 'NEEDS_REVIEW' && (
                            <>
                              {' '}
                              <span className="text-gray-300">|</span>{' '}
                              <Link
                                to={`/review/${invoice.document_id}`}
                                className="text-amber-600 hover:text-amber-800 font-medium"
                              >
                                Review
                              </Link>
                            </>
                          )}
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
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div role="dialog" aria-modal="true" className="bg-white rounded-xl border border-gray-200 p-6 w-full max-w-md">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {ACTIONS[pendingAction].label} {pluralize(selectedCount)}?
            </h3>
            <p className="text-sm text-gray-600 mb-6">{ACTIONS[pendingAction].description}</p>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setPendingAction(null)}
                disabled={actionRunning}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmAction}
                disabled={actionRunning}
                className={`px-4 py-2 rounded-lg text-sm font-medium text-white disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors ${
                  pendingAction === 'delete' ? 'bg-red-600 hover:bg-red-700' : 'bg-primary-600 hover:bg-primary-700'
                }`}
              >
                {actionRunning ? (
                  <span className="flex items-center">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    {ACTIONS[pendingAction].runningLabel}
                  </span>
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
