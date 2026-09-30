import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

function PageHeader({ title, description, backTo, backLabel, actions }) {
  return (
    <div className="mb-8">
      {backTo && (
        <Link
          to={backTo}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900 mb-3 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {backLabel}
        </Link>
      )}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">{title}</h1>
          {description && <div className="mt-1.5 text-sm sm:text-base text-slate-500">{description}</div>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}

export default PageHeader;
