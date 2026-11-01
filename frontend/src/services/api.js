import axios from 'axios';

const API_BASE_URL = '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const invoiceAPI = {
  upload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/invoices/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getAll: async (status = null, limit = 100) => {
    const params = {};
    if (status) params.status_filter = status;
    params.limit = limit;
    const response = await api.get('/invoices', { params });
    return response.data;
  },

  getById: async (documentId) => {
    const response = await api.get(`/invoices/${documentId}`);
    return response.data;
  },

  update: async (documentId, data) => {
    const response = await api.put(`/invoices/${documentId}`, data);
    return response.data;
  },

  approve: async (documentId, reviewedBy, notes = '') => {
    const response = await api.post(`/invoices/${documentId}/approve`, {
      document_id: documentId,
      reviewed_by: reviewedBy,
      notes,
    });
    return response.data;
  },

  reject: async (documentId, reviewedBy, reason) => {
    const response = await api.post(`/invoices/${documentId}/reject`, {
      document_id: documentId,
      reviewed_by: reviewedBy,
      reason,
    });
    return response.data;
  },

  bulkDelete: async (documentIds) => {
    const response = await api.post('/invoices/bulk-delete', { document_ids: documentIds });
    return response.data;
  },

  bulkReprocess: async (documentIds) => {
    const response = await api.post('/invoices/bulk-reprocess', { document_ids: documentIds });
    return response.data;
  },

  getDocument: async (documentId) => {
    const response = await api.get(`/invoices/${documentId}/document`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

export const rpaAPI = {
  getQueue: async () => {
    const response = await api.get('/rpa/queue');
    return response.data;
  },

  start: async (documentId, apiKey) => {
    const response = await api.post(`/rpa/${documentId}/start`, {
      document_id: documentId,
      api_key: apiKey,
    });
    return response.data;
  },

  result: async (documentId, apiKey, success, accountingRecordId = null, message = null) => {
    const response = await api.post(`/rpa/${documentId}/result`, {
      document_id: documentId,
      api_key: apiKey,
      success,
      accounting_record_id: accountingRecordId,
      message,
    });
    return response.data;
  },
};

export const healthAPI = {
  check: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

// The accounting app is a separate service, reverse-proxied at /accounting/
export const ACCOUNTING_APP_URL = '/accounting/';

export const accountingAPI = {
  getRecords: async () => {
    const response = await axios.get('/accounting/api/records');
    return response.data;
  },
};
