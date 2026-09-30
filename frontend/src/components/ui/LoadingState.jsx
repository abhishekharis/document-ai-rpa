import { Loader2 } from 'lucide-react';

function LoadingState({ label = 'Loading...' }) {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-3 text-slate-500">
      <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export default LoadingState;
