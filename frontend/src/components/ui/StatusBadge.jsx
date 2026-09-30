const STATUS_STYLES = {
  UPLOADED: { pill: 'bg-slate-100 text-slate-700 ring-slate-200', dot: 'bg-slate-400' },
  PROCESSING: { pill: 'bg-blue-50 text-blue-700 ring-blue-200', dot: 'bg-blue-500 animate-pulse' },
  PROCESSED: { pill: 'bg-emerald-50 text-emerald-700 ring-emerald-200', dot: 'bg-emerald-500' },
  NEEDS_REVIEW: { pill: 'bg-amber-50 text-amber-700 ring-amber-200', dot: 'bg-amber-500' },
  APPROVED: { pill: 'bg-emerald-50 text-emerald-700 ring-emerald-200', dot: 'bg-emerald-500' },
  REJECTED: { pill: 'bg-red-50 text-red-700 ring-red-200', dot: 'bg-red-500' },
  RPA_QUEUED: { pill: 'bg-violet-50 text-violet-700 ring-violet-200', dot: 'bg-violet-500' },
  RPA_PROCESSING: { pill: 'bg-blue-50 text-blue-700 ring-blue-200', dot: 'bg-blue-500 animate-pulse' },
  RPA_COMPLETED: { pill: 'bg-emerald-50 text-emerald-700 ring-emerald-200', dot: 'bg-emerald-500' },
  RPA_FAILED: { pill: 'bg-red-50 text-red-700 ring-red-200', dot: 'bg-red-500' },
  ERROR: { pill: 'bg-red-50 text-red-700 ring-red-200', dot: 'bg-red-500' },
};

const FALLBACK = STATUS_STYLES.UPLOADED;

function StatusBadge({ status, size = 'sm' }) {
  const style = STATUS_STYLES[status] || FALLBACK;
  const sizing = size === 'lg' ? 'px-3 py-1.5 text-sm gap-2' : 'px-2.5 py-0.5 text-xs gap-1.5';
  return (
    <span className={`inline-flex items-center rounded-full font-medium ring-1 ring-inset whitespace-nowrap ${sizing} ${style.pill}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {status.replace(/_/g, ' ')}
    </span>
  );
}

export default StatusBadge;
