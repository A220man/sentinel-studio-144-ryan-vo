import { NavLink } from 'react-router-dom';

interface LoadingErrorProps {
  title?: string;
  message?: string;
  actionLabel?: string;
  actionHref?: string;
  onClick?: () => void;
}

export function Loading({ title = 'Loading...', message }: LoadingErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] gap-4">
      <div className="spinner" style={{ width: '2rem', height: '2rem', borderWidth: '3px' }} aria-hidden="true" />
      <div>
        <p className="text-lg font-medium text-gray-900">{title}</p>
        {message && <p className="text-gray-500">{message}</p>}
      </div>
    </div>
  );
}

export function ErrorState({ title = 'Something went wrong', message, actionLabel = 'Try again', actionHref, onClick }: LoadingErrorProps & { onClick?: () => void }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon" aria-hidden="true">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{title}</h2>
      {message && <p className="text-gray-500 mb-4 max-w-md">{message}</p>}
      {actionHref && (
        <NavLink to={actionHref} className="btn btn-primary">
          {actionLabel}
        </NavLink>
      )}
      {!actionHref && onClick && (
        <button onClick={onClick} className="btn btn-primary">
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title = 'No data', message, actionLabel, actionHref }: LoadingErrorProps) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon" aria-hidden="true">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M9 9h6v6H9z" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold text-gray-900 mb-1">{title}</h2>
      {message && <p className="text-gray-500 mb-4 max-w-md">{message}</p>}
      {actionHref && (
        <NavLink to={actionHref} className="btn btn-primary">
          {actionLabel}
        </NavLink>
      )}
    </div>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const variants: Record<string, string> = {
    critical: 'badge badge-critical',
    high: 'badge badge-high',
    medium: 'badge badge-medium',
    low: 'badge badge-low',
    info: 'badge badge-info',
  };
  return <span className={variants[severity] || 'badge badge-info'}>{severity}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, string> = {
    pending: 'badge badge-pending',
    in_progress: 'badge badge-in_progress',
    completed: 'badge badge-completed',
    failed: 'badge badge-failed',
  };
  return <span className={variants[status] || 'badge badge-info'}>{status.replace('_', ' ')}</span>;
}

export function FindingCard({ finding }: { finding: any }) {
  return (
    <div className="card mb-4">
      <div className="card-header flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h3 className="font-medium text-gray-900 truncate">{finding.title}</h3>
            <SeverityBadge severity={finding.severity} />
          </div>
          <p className="text-sm text-gray-600 font-mono">{finding.file_path}:{finding.start_line}-{finding.end_line}</p>
        </div>
        <span className="text-xs text-gray-500 whitespace-nowrap">{finding.category}</span>
      </div>
      <div className="card-body">
        <p className="text-gray-700 mb-3">{finding.description}</p>
        {finding.suggestion && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
            <p className="font-medium text-blue-900 mb-1">Suggestion</p>
            <p className="text-blue-800 font-mono">{finding.suggestion}</p>
          </div>
        )}
        {finding.llm_explanation && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm mt-3">
            <p className="font-medium text-amber-900 mb-1 flex items-center gap-1">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4M12 8h.01" />
              </svg>
              AI Advisory (opt-in)
            </p>
            <p className="text-amber-800">{finding.llm_explanation}</p>
          </div>
        )}
        {finding.rule_id && (
          <p className="text-xs text-gray-500 mt-2">Rule: {finding.rule_id}</p>
        )}
      </div>
    </div>
  );
}

export function ReviewCard({ review, onClick }: { review: any; onClick?: () => void }) {

  return (
    <div className="card hover:shadow-md transition-shadow cursor-pointer" onClick={onClick} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onClick?.()}>
      <div className="card-body">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 truncate">{review.title}</h3>
            <p className="text-sm text-gray-500 font-mono mt-1">{review.repository_url || 'Local repository'}</p>
          </div>
          <StatusBadge status={review.status} />
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-600 mb-3 flex-wrap">
          <span className="flex items-center gap-1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            {review.findings_count} findings
          </span>
          <span className="flex items-center gap-1">
            <SeverityBadge severity="critical" />
            {review.critical_count}
          </span>
          <span className="flex items-center gap-1">
            <SeverityBadge severity="high" />
            {review.high_count}
          </span>
          <span className="flex items-center gap-1">
            <SeverityBadge severity="medium" />
            {review.medium_count}
          </span>
          <span className="flex items-center gap-1">
            <SeverityBadge severity="low" />
            {review.low_count}
          </span>
        </div>

        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Updated {new Date(review.updated_at).toLocaleDateString()}</span>
          <span className="font-mono">{review.base_branch} → {review.head_branch}</span>
        </div>
      </div>
    </div>
  );
}