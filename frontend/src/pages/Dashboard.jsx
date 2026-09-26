import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { invoiceAPI } from '../services/api';

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
        <h1 className="text-3xl font-semibold text-gray-900 mb-2">Document Intelligence</h1>
        <p className="text-gray-600">Upload, process, and extract structured information from your documents.</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500">Total Documents</span>
            <span className="text-2xl">📊</span>
          </div>
          <div className="text-3xl font-semibold text-gray-900">{stats.total}</div>
        </div>
        
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500">Processing</span>
            <span className="text-2xl">⚙️</span>
          </div>
          <div className="text-3xl font-semibold text-blue-600">{stats.processing}</div>
        </div>
        
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500">Needs Review</span>
            <span className="text-2xl">👁️</span>
          </div>
          <div className="text-3xl font-semibold text-amber-600">{stats.needsReview}</div>
        </div>
        
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500">Approved</span>
            <span className="text-2xl">✅</span>
          </div>
          <div className="text-3xl font-semibold text-green-600">{stats.approved}</div>
        </div>
        
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500">RPA Completed</span>
            <span className="text-2xl">🤖</span>
          </div>
          <div className="text-3xl font-semibold text-green-600">{stats.rpaCompleted}</div>
        </div>
        
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm font-medium text-gray-500">RPA Failed</span>
            <span className="text-2xl">❌</span>
          </div>
          <div className="text-3xl font-semibold text-red-600">{stats.rpaFailed}</div>
        </div>
      </div>

      {/* Upload CTA */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-800 rounded-xl p-8 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-white mb-2">Process a New Document</h2>
            <p className="text-primary-100">Upload invoices, receipts, or other documents for AI-powered extraction.</p>
          </div>
          <Link
            to="/upload"
            className="bg-white text-primary-700 px-6 py-3 rounded-lg font-medium hover:bg-primary-50 transition-colors"
          >
            Upload Document
          </Link>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Recent Documents</h3>
        </div>
        
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
                {invoices.map((invoice) => (
                  <tr key={invoice.document_id} className="hover:bg-gray-50 transition-colors">
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
