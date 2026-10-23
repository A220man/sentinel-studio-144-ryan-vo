import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from '../src/App';

// Mock the useAuth hook
vi.mock('../src/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

// Mock the API
vi.mock('../src/api', () => ({
  api: {
    getMe: vi.fn(),
    getAuthUrl: vi.fn(),
    callback: vi.fn(),
    listReviews: vi.fn(),
    createReview: vi.fn(),
  },
}));

import { useAuth } from '../src/hooks/useAuth';
import { api } from '../src/api';

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('redirects to login when not authenticated', async () => {
    (useAuth as any).mockReturnValue({
      user: null,
      loading: false,
      error: null,
      login: vi.fn(),
      handleCallback: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      isAuthenticated: false,
    });

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Sign in to Sentinel Studio')).toBeInTheDocument();
    });
  });

  it('shows dashboard when authenticated', async () => {
    (useAuth as any).mockReturnValue({
      user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'viewer', is_active: true },
      loading: false,
      error: null,
      login: vi.fn(),
      handleCallback: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      isAuthenticated: true,
    });

    (api.listReviews as any).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Code Reviews')).toBeInTheDocument();
    });
  });
});