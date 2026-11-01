import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Search, RefreshCw, ExternalLink, AlertTriangle, BookOpen, SearchX } from 'lucide-react';
import { accountingAPI, ACCOUNTING_APP_URL } from '../services/api';
import PageHeader from '../components/ui/PageHeader';
import LoadingState from '../components/ui/LoadingState';
import EmptyState from '../components/ui/EmptyState';
import Alert from '../components/ui/Alert';

function AccountingRecords() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadRecords();
  }, []);

  const loadRecords = async ({ showSpinner = true } = {}) => {
    if (showSpinner) setLoading(true);
    else setRefreshing(true);
    setLoadError('');
    try {
      const data = await accountingAPI.getRecords();
      setRecords([...data.records].reverse());
    } catch (error) {
      console.error('Failed to load accounting records:', error);
      setLoadError('Failed to load accounting records. Please check that the accounting app is running and try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const visibleRecords = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return records;
    return records.filter((record) =>
      [record.accounting_id, record.vendor, record.invoice_number, record.external_reference]
        .some((value) => (value || '').toLowerCase().includes(term))
    );
  }, [records, search]);

  const retryButton = (
    <button type="button" onClick={() => loadRecords()} className="btn-secondary inline-flex items-center gap-2">
      <RefreshCw className="h-4 w-4" />
      Retry
    </button>
  );

  if (loading) return <LoadingState label="Loading accounting records..." />;

  return (
    <div>
      <PageHeader
        title="Accounting Records"
        description="Invoices the RPA worker has entered into the accounting system."
        actions={
          <>
            <button
              type="button"
              onClick={() => loadRecords({ showSpinner: false })}
              disabled={refreshing}
              className="btn-secondary inline-flex items-center gap-2"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <a href={ACCOUNTING_APP_URL} target="_blank" rel="noopener noreferrer" className="btn-primary">
              <ExternalLink className="h-4 w-4" />
              Open accounting app
            </a>
          </>
        }
      />

      {loadError && records.length > 0 && (
        <Alert type="error" title={loadError} className="mb-6">
          {retryButton}
        </Alert>
      )}

      <div className="card overflow-hidden">
        {loadError && records.length === 0 ? (
          <EmptyState
            icon={AlertTriangle}
            title="Failed to load accounting records"
            description={loadError}
            action={retryButton}
          />
        ) : records.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No accounting records yet"
            description="Approve an invoice and the RPA worker will post it here."
            action={
              <Link to="/documents" className="btn-primary">
                Go to Documents
              </Link>
            }
          />
        ) : (
          <>
            <div className="p-4 border-b border-slate-100">
              <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by ID, vendor or invoice #"
                  aria-label="Search accounting records"
                  className="input pl-9"
                />
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50/80 border-b border-slate-100">
                  <tr>
                    <th className="table-th">Accounting ID</th>
                    <th className="table-th">Vendor</th>
                    <th className="table-th">Invoice #</th>
                    <th className="table-th">Invoice date</th>
                    <th className="table-th text-right">Total</th>
                    <th className="table-th">Source document</th>
                    <th className="table-th">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {visibleRecords.length === 0 ? (
                    <tr>
                      <td colSpan={7}>
                        <EmptyState
                          icon={SearchX}
                          title="No records found"
                          description="Try a different search."
                          action={
                            <button type="button" onClick={() => setSearch('')} className="btn-secondary">
                              Clear search
                            </button>
                          }
                        />
                      </td>
                    </tr>
                  ) : (
                    visibleRecords.map((record) => (
                      <tr key={record.accounting_id} className="hover:bg-slate-50/70 transition-colors">
                        <td className="table-td font-mono text-xs font-medium">
                          <a
                            href={`${ACCOUNTING_APP_URL}record/${record.accounting_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="link"
                          >
                            {record.accounting_id}
                          </a>
                        </td>
                        <td className="table-td font-medium text-slate-700">{record.vendor || '-'}</td>
                        <td className="table-td">{record.invoice_number || '-'}</td>
                        <td className="table-td">{record.invoice_date || '-'}</td>
                        <td className="table-td text-right tabular-nums">
                          {record.total != null ? `${record.currency || ''} ${record.total.toFixed(2)}` : '-'}
                        </td>
                        <td className="table-td font-mono text-xs">
                          {record.external_reference ? (
                            <Link to={`/invoice/${record.external_reference}`} className="link">
                              {record.external_reference}
                            </Link>
                          ) : (
                            '-'
                          )}
                        </td>
                        <td className="table-td text-slate-500">
                          {record.created_at ? record.created_at.slice(0, 19).replace('T', ' ') : '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default AccountingRecords;
