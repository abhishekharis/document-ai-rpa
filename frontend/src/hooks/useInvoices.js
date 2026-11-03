import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { invoiceAPI } from '../services/api';

export const invoiceKeys = {
  all: ['invoices'],
  detail: (documentId) => ['invoice', documentId],
};

export function useInvoices() {
  return useQuery({ queryKey: invoiceKeys.all, queryFn: () => invoiceAPI.getAll() });
}

export function useInvoice(documentId) {
  return useQuery({
    queryKey: invoiceKeys.detail(documentId),
    queryFn: () => invoiceAPI.getById(documentId),
  });
}

/**
 * Subscribe to /api/events and refetch whatever changed. EventSource reconnects on
 * its own; queries also refetch on window focus, so a missed event is self-healing.
 */
export function useInvoiceEvents() {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (typeof EventSource === 'undefined') return undefined;
    const source = new EventSource('/api/events');
    source.addEventListener('invoice', (event) => {
      try {
        const { document_id: documentId } = JSON.parse(event.data);
        queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(documentId) });
      } catch {
        // ignore malformed events
      }
      queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
    });
    return () => source.close();
  }, [queryClient]);
}
