import { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams, NavLink } from 'react-router-dom';
import { api } from '../api';
import { Layout } from '../components/Layout';
import { Loading, ErrorState, EmptyState, ReviewCard } from '../components/LoadingError';
import { useAuth } from '../hooks/useAuth';

export function Dashboard() {
  const { loading: authLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({ total: 0, page: 1, page_size: 20, total_pages: 1 });

  const page = parseInt(searchParams.get('page') || '1', 10);
  const status = searchParams.get('status') || undefined;

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchReviews();
  }, [isAuthenticated, page, status, navigate]);

  const fetchReviews = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listReviews({
        page,
        page_size: 20,
        status: status as any,
      });
      setReviews(data.items);
      setPagination(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reviews');
    } finally {
      setLoading(false);
    }
  };
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
      setError('Please select a JSON file');
      return;
    }

    try {
      const text = await file.text();
      // Validate JSON
      JSON.parse(text);

      await api.importReview({ content: text, format: 'json' });
      await fetchReviews();
    } catch (err) {
      if (err instanceof SyntaxError) {
        setError('Invalid JSON file');
      } else {
        setError(err instanceof Error ? err.message : 'Import failed');
      }
    } finally {
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams({ ...Object.fromEntries(searchParams), page: String(newPage) });
  };

  const handleStatusChange = (newStatus: string | undefined) => {
    const params = Object.fromEntries(searchParams);
    if (newStatus) params.status = newStatus;
    else delete params.status;
    params.page = '1';
    setSearchParams(params);
  };

  if (authLoading) return <Loading title="Checking authentication..." />;
  if (!isAuthenticated) return null;

  return (
    <Layout>
      <div className="page-header">
        <div>
          <h1 className="page-title">Code Reviews</h1>
          <p className="page-subtitle">Manage and analyze your code review results</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleImportClick}
            className="btn btn-secondary"
            aria-label="Import review from JSON file"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Import
          </button>
          <NavLink to="/reviews/new" className="btn btn-primary">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Review
          </NavLink>
        </div>
      </div>

      <input
        type="file"
        ref={fileInputRef}
        accept=".json"
        onChange={handleFileChange}
        style={{ display: 'none' }}
        aria-label="Import review JSON file"
      />

      <div className="card mb-6">
        <div className="card-body">
          <div className="flex flex-wrap items-center gap-4">
            <label htmlFor="status-filter" className="label mb-0">Filter by status:</label>
            <select
              id="status-filter"
              value={status || ''}
              onChange={(e) => handleStatusChange(e.target.value || undefined)}
              className="input w-auto"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
            <span className="text-sm text-gray-500 ml-auto">
              Showing {pagination.total} review{pagination.total !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} actionLabel="Retry" actionHref="#" onClick={fetchReviews} />}

      {loading ? (
        <Loading title="Loading reviews..." />
      ) : reviews.length === 0 ? (
        <EmptyState
          title="No reviews yet"
          message="Create your first code review to get started"
          actionLabel="Create Review"
          actionHref="/reviews/new"
        />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {reviews.map((review) => (
              <ReviewCard
                key={review.id}
                review={review}
                onClick={() => navigate(`/reviews/${review.id}`)}
              />
            ))}
          </div>

          {pagination.total_pages > 1 && (
            <nav className="flex items-center justify-center gap-2 mt-6" aria-label="Pagination">
              <button
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={pagination.page === 1}
                className="btn btn-outline btn-sm"
                aria-label="Previous page"
              >
                Previous
              </button>
              <span className="px-3 text-sm text-gray-600">
                Page {pagination.page} of {pagination.total_pages}
              </span>
              <button
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={pagination.page === pagination.total_pages}
                className="btn btn-outline btn-sm"
                aria-label="Next page"
              >
                Next
              </button>
            </nav>
          )}
        </>
      )}
    </Layout>
  );
}