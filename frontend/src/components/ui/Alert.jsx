import { AlertCircle, AlertTriangle, CheckCircle2, X } from 'lucide-react';

const VARIANTS = {
  error: { box: 'bg-red-50 border-red-200', title: 'text-red-800', body: 'text-red-700', icon: AlertCircle, iconColor: 'text-red-500' },
  warning: { box: 'bg-amber-50 border-amber-200', title: 'text-amber-800', body: 'text-amber-700', icon: AlertTriangle, iconColor: 'text-amber-500' },
  success: { box: 'bg-emerald-50 border-emerald-200', title: 'text-emerald-800', body: 'text-emerald-700', icon: CheckCircle2, iconColor: 'text-emerald-500' },
};

function Alert({ type = 'error', title, children, details = [], onDismiss, className = '' }) {
  const v = VARIANTS[type];
  const Icon = v.icon;
  return (
    <div className={`flex items-start gap-3 rounded-lg border p-4 ${v.box} ${className}`}>
      <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${v.iconColor}`} />
      <div className="min-w-0 flex-1 text-sm">
        {title && <p className={`font-medium ${v.title}`}>{title}</p>}
        {children && <div className={`${title ? 'mt-1' : ''} ${v.body}`}>{children}</div>}
        {details.length > 0 && (
          <ul className={`mt-2 list-disc space-y-1 pl-5 ${v.body}`}>
            {details.map((detail) => (
              <li key={detail}>{detail}</li>
            ))}
          </ul>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss notice"
          className={`shrink-0 rounded p-0.5 opacity-70 transition-opacity hover:opacity-100 ${v.title}`}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

export default Alert;
