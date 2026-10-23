import React from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import { api } from './api';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { ReviewDetail } from './pages/ReviewDetail';
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="spinner" style={{ width: '3rem', height: '3rem', borderWidth: '4px' }} aria-hidden="true" />
      </div>
    );
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="spinner" style={{ width: '3rem', height: '3rem', borderWidth: '4px' }} aria-hidden="true" />
      </div>
    );
  }

  return isAuthenticated ? <Navigate to="/reviews" replace /> : <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />
      <Route path="/reviews" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
      <Route path="/reviews/new" element={
        <ProtectedRoute>
          <NewReview />
        </ProtectedRoute>
      } />
      <Route path="/reviews/:id" element={
        <ProtectedRoute>
          <ReviewDetail />
        </ProtectedRoute>
      } />
      <Route path="/" element={<Navigate to="/reviews" replace />} />
      <Route path="*" element={<Navigate to="/reviews" replace />} />
    </Routes>
  );
}

function NewReview() {
  const navigate = useNavigate();
  const [formData, setFormData] = React.useState({
    title: '',
    description: '',
    repository_url: '',
    base_branch: 'main',
    head_branch: '',
    diff_content: '',
  });
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.head_branch) {
      setError('Title and head branch are required');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const review = await api.createReview(formData);
      setSuccess(true);
      setTimeout(() => navigate(`/reviews/${review.id}`), 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create review');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="page-header">
        <div>
          <h1 className="page-title">New Review</h1>
          <p className="page-subtitle">Create a new code review</p>
        </div>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="card-body space-y-6">
          {error && <div className="alert alert-error">{error}</div>}
          {success && <div className="alert alert-success">Review created! Redirecting...</div>}

          <div>
            <label htmlFor="title" className="label">Title *</label>
            <input
              type="text"
              id="title"
              className="input"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g., PR #42: Add user authentication"
              required
            />
          </div>

          <div>
            <label htmlFor="description" className="label">Description</label>
            <textarea
              id="description"
              className="input"
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Optional description of the review scope"
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="repository_url" className="label">Repository URL</label>
              <input
                type="url"
                id="repository_url"
                className="input"
                value={formData.repository_url}
                onChange={(e) => setFormData({ ...formData, repository_url: e.target.value })}
                placeholder="https://github.com/owner/repo"
              />
            </div>
            <div>
              <label htmlFor="base_branch" className="label">Base Branch</label>
              <input
                type="text"
                id="base_branch"
                className="input"
                value={formData.base_branch}
                onChange={(e) => setFormData({ ...formData, base_branch: e.target.value })}
                placeholder="main"
              />
            </div>
          </div>

          <div>
            <label htmlFor="head_branch" className="label">Head Branch *</label>
            <input
              type="text"
              id="head_branch"
              className="input"
              value={formData.head_branch}
              onChange={(e) => setFormData({ ...formData, head_branch: e.target.value })}
              placeholder="feature/new-feature"
              required
            />
          </div>

          <div>
            <label htmlFor="diff_content" className="label">Diff Content (Optional)</label>
            <textarea
              id="diff_content"
              className="input font-mono text-sm"
              rows={10}
              value={formData.diff_content}
              onChange={(e) => setFormData({ ...formData, diff_content: e.target.value })}
              placeholder="Paste git diff output here for immediate analysis..."
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
            <button type="button" onClick={() => navigate(-1)} className="btn btn-outline" disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? (
                <>
                  <span className="spinner" /> Creating...
                </>
              ) : (
                'Create Review'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}