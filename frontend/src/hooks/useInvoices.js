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

const PROCESSING_STATUSES = new Set(['PROCESSING', 'RPA_PROCESSING', 'RPA_QUEUED']);

export function useInvoice(documentId) {
  const { data: invoice, ...rest } = useQuery({
    queryKey: invoiceKeys.detail(documentId),
    queryFn: () => invoiceAPI.getById(documentId),
  });
  // Poll while the invoice is mid-pipeline in case an SSE event is missed
  const refetchInterval = invoice && PROCESSING_STATUSES.has(invoice.status) ? 10000 : false;
  return useQuery({
    queryKey: invoiceKeys.detail(documentId),
    queryFn: () => invoiceAPI.getById(documentId),
    refetchInterval,
  });
}

/**
 * Subscribe to /api/events and refetch whatever changed. EventSource reconnects on
 * its own; queries also refetch on window focus, so a missed event is self-healing.
 * On (re)connect we invalidate all invoices to catch anything we missed while disconnected.
 */
export function useInvoiceEvents() {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (typeof EventSource === 'undefined') return undefined;
    const source = new EventSource('/api/events');
    source.addEventListener('open', () => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
    });
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
