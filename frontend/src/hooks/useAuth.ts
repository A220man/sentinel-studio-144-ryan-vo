import { useState, useEffect, useCallback } from 'react';
import { api, type User } from '../api';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUser = useCallback(async () => {
    try {
      const userData = await api.getMe();
      setUser(userData);
      setError(null);
    } catch (err) {
      setUser(null);
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = useCallback(async () => {
    const authData = await api.getAuthUrl();
    // Store code_verifier and state in sessionStorage for callback
    sessionStorage.setItem('oauth_code_verifier', authData.code_verifier);
    sessionStorage.setItem('oauth_state', authData.state);
    window.location.href = authData.auth_url;
  }, []);

  const handleCallback = useCallback(async (code: string, state: string) => {
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
    const storedState = sessionStorage.getItem('oauth_state');

    if (!codeVerifier || storedState !== state) {
      throw new Error('Invalid OAuth state');
    }

    const token = await api.callback({ code, state, code_verifier: codeVerifier });
    sessionStorage.removeItem('oauth_code_verifier');
    sessionStorage.removeItem('oauth_state');
    await fetchUser();
    return token;
  }, [fetchUser]);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  return {
    user,
    loading,
    error,
    login,
    handleCallback,
    logout,
    refresh,
    isAuthenticated: !!user,
  };
}