import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Dashboard } from '../src/pages/Dashboard';
import { api } from '../src/api';

vi.mock('../src/api', () => ({
  api: {
    listReviews: vi.fn(),
  },
}));

vi.mock('../src/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty state when no reviews', async () => {
    const { useAuth } = await import('../src/hooks/useAuth');
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'viewer', is_active: true },
      loading: false,
      error: null,
      login: vi.fn(),
      handleCallback: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      isAuthenticated: true,
    });

    vi.mocked(api.listReviews).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No reviews yet')).toBeInTheDocument();
    });
  });

  it('displays review cards', async () => {
    const { useAuth } = await import('../src/hooks/useAuth');
    vi.mocked(useAuth).mockReturnValue({
      user: { id: 1, username: 'testuser', email: 'test@example.com', role: 'viewer', is_active: true },
      loading: false,
      error: null,
      login: vi.fn(),
      handleCallback: vi.fn(),
      logout: vi.fn(),
      refresh: vi.fn(),
      isAuthenticated: true,
    });

    vi.mocked(api.listReviews).mockResolvedValue({
      items: [
        {
          id: 1,
          title: 'Test Review',
          author_id: 1,
          status: 'completed',
          findings_count: 5,
          critical_count: 1,
          high_count: 2,
          medium_count: 1,
          low_count: 1,
          repository_url: 'https://github.com/test/repo',
          base_branch: 'main',
          head_branch: 'feature/test',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Test Review')).toBeInTheDocument();
      expect(screen.getByText('5 findings')).toBeInTheDocument();
    });
  });
});