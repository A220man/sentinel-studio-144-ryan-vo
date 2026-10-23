import { useState, useEffect } from 'react';
import { useParams, useNavigate, NavLink } from 'react-router-dom';
import { api } from '../api';
import { Layout } from '../components/Layout';
import { Loading, ErrorState, EmptyState, FindingCard, SeverityBadge, StatusBadge } from '../components/LoadingError';
import { useAuth } from '../hooks/useAuth';

export function ReviewDetail() {
  const { loading: authLoading, isAuthenticated } = useAuth();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [review, setReview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchReview();
  }, [isAuthenticated, id, navigate]);

  const fetchReview = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getReview(parseInt(id, 10));
      setReview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load review');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format: 'json' | 'markdown' | 'sarif') => {
    if (!review) return;
    setExporting(format);
    try {
      const response = await api.exportReview({ review_id: review.id, format });
      const blob = new Blob([response.content], { type: response.media_type });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(null);
    }
  };

  if (authLoading) return <Loading title="Checking authentication..." />;
  if (!isAuthenticated) return null;
  if (!review && !loading) return null;

  return (
    <Layout>
      {review && (
        <NavLink to="/reviews" className="btn btn-outline btn-sm mb-4 inline-flex">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12" />
            <polyline points="12 19 5 12 12 5" />
          </svg>
          Back to Reviews
        </NavLink>
      )}

      {loading ? (
        <Loading title="Loading review..." />
      ) : error ? (
        <ErrorState message={error} actionLabel="Go Back" actionHref="/reviews" />
      ) : review ? (
        <div>
          <div className="page-header flex-wrap">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="page-title">{review.title}</h1>
                <StatusBadge status={review.status} />
              </div>
              <p className="page-subtitle">{review.repository_url || 'Local repository'} • {review.base_branch} → {review.head_branch}</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleExport('json')}
                disabled={exporting !== null}
                className="btn btn-outline btn-sm"
              >
                {exporting === 'json' ? <span className="spinner" /> : 'Export JSON'}
              </button>
              <button
                onClick={() => handleExport('markdown')}
                disabled={exporting !== null}
                className="btn btn-outline btn-sm"
              >
                {exporting === 'markdown' ? <span className="spinner" /> : 'Export MD'}
              </button>
              <button
                onClick={() => handleExport('sarif')}
                disabled={exporting !== null}
                className="btn btn-outline btn-sm"
              >
                {exporting === 'sarif' ? <span className="spinner" /> : 'Export SARIF'}
              </button>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold">Findings ({review.findings.length})</h2>
                </div>
                <div className="card-body">
                  {review.findings.length === 0 ? (
                    <EmptyState
                      title="No findings"
                      message="This review has no findings yet. Run an analysis or add findings manually."
                    />
                  ) : (
                    review.findings.map((finding: any) => (
                      <FindingCard key={finding.id} finding={finding} />
                    ))
                  )}
                </div>
              </div>
            </div>

            <div>
              <div className="card mb-4">
                <div className="card-header">
                  <h2 className="text-lg font-semibold">Summary</h2>
                </div>
                <div className="card-body space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Total Findings</span>
                    <span className="font-semibold text-lg">{review.findings_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <SeverityBadge severity="critical" />
                      <span>Critical</span>
                    </span>
                    <span className="font-semibold text-red-600">{review.critical_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <SeverityBadge severity="high" />
                      <span>High</span>
                    </span>
                    <span className="font-semibold text-orange-600">{review.high_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <SeverityBadge severity="medium" />
                      <span>Medium</span>
                    </span>
                    <span className="font-semibold text-amber-600">{review.medium_count}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <SeverityBadge severity="low" />
                      <span>Low</span>
                    </span>
                    <span className="font-semibold text-blue-600">{review.low_count}</span>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h2 className="text-lg font-semibold">Details</h2>
                </div>
                <div className="card-body space-y-3 text-sm">
                  <div>
                    <p className="text-gray-500">Status</p>
                    <p className="font-medium">{review.status.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Repository</p>
                    <p className="font-mono text-gray-900 truncate">{review.repository_url || 'Local'}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Branches</p>
                    <p className="font-mono text-gray-900">{review.base_branch} → {review.head_branch}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Created</p>
                    <p className="font-medium">{new Date(review.created_at).toLocaleString()}</p>
                  </div>
                  {review.started_at && (
                    <div>
                      <p className="text-gray-500">Started</p>
                      <p className="font-medium">{new Date(review.started_at).toLocaleString()}</p>
                    </div>
                  )}
                  {review.completed_at && (
                    <div>
                      <p className="text-gray-500">Completed</p>
                      <p className="font-medium">{new Date(review.completed_at).toLocaleString()}</p>
                    </div>
                  )}
                  {review.description && (
                    <div>
                      <p className="text-gray-500">Description</p>
                      <p className="text-gray-700">{review.description}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </Layout>
  );
}