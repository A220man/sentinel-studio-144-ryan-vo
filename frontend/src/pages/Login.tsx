import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Layout } from '../components/Layout';
import { Loading, ErrorState } from '../components/LoadingError';
import { useAuth } from '../hooks/useAuth';

export function Login() {
  const { loading: authLoading, isAuthenticated } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/reviews');
      return;
    }

    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (code && state) {
      handleCallback(code, state);
    }
  }, [isAuthenticated, navigate, searchParams]);

  const handleCallback = async (code: string, state: string) => {
    try {
      await api.callback({ code, state, code_verifier: '' });
      navigate('/reviews');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    }
  };

  const handleLogin = async () => {
    try {
      const authData = await api.getAuthUrl();
      sessionStorage.setItem('oauth_code_verifier', authData.code_verifier);
      sessionStorage.setItem('oauth_state', authData.state);
      window.location.href = authData.auth_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate login');
    }
  };

  if (authLoading) {
    return (
      <Layout>
        <Loading title="Checking authentication..." />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-[calc(100vh-200px)] flex items-center justify-center">
        <div className="card w-full max-w-md">
          <div className="card-header text-center">
            <h1 className="text-2xl font-bold text-gray-900">Sign in to Sentinel Studio</h1>
            <p className="text-gray-500 mt-1">AI-powered code review platform</p>
          </div>
          <div className="card-body">
            {error && <ErrorState message={error} />}
            <button
              onClick={handleLogin}
              disabled={authLoading}
              className="btn btn-primary w-full py-3 text-lg"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c1.1 0 2-.9 2-2V7c0-.55-.45-1-1-1H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h12c.55 0 1-.45 1-1v-1.5c0-.55-.45-1-1-1H8.5c-.42 0-.74-.33-.9-.74l-1.91-1.91c.67-.95 1.21-2.07 1.21-3.34z"/>
              </svg>
              Continue with Keycloak
            </button>
            <p className="text-center text-sm text-gray-500 mt-4">
              By signing in, you agree to our Terms of Service and Privacy Policy.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}
