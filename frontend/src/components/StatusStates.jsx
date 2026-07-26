import { AlertTriangle, Inbox, CheckCircle2 } from "lucide-react";

// Reusable states so no page ever quietly falls back to fake numbers.
export function LoadingBlock({ label = "Loading…", lines = 3 }) {
  return (
    <div className="animate-pulse space-y-2" aria-label={label} role="status">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 bg-ink-100 rounded w-full" />
      ))}
    </div>
  );
}

export function ErrorBlock({ error, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-2 py-8 text-ink-500">
      <AlertTriangle size={22} className="text-risk-high" />
      <p className="text-sm font-medium text-ink-700">Couldn't load this from the server.</p>
      <p className="text-xs text-ink-500 max-w-xs">{error?.message || "The backend request failed."}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-1 text-xs font-semibold text-brand-600 hover:text-brand-700">
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyBlock({ label = "Nothing here yet." }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-2 py-8 text-ink-500">
      <Inbox size={22} />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function SuccessBlock({ message = "Success!" }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-2 py-8 text-ink-500">
      <CheckCircle2 size={22} className="text-success-500" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}