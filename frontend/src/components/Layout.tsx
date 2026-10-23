import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="container">
          <nav className="flex items-center justify-between h-16" aria-label="Main navigation">
            <div className="flex items-center gap-8">
              <NavLink to="/" className="flex items-center gap-2 font-semibold text-lg text-gray-900" aria-label="Sentinel Studio Home">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="M9 12l2 2 4-4" />
                </svg>
                <span>Sentinel Studio</span>
              </NavLink>

              <div className="hidden md:flex items-center gap-1" role="navigation" aria-label="Main">
                <NavLink
                  to="/reviews"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
                    }`}
                >
                  Reviews
                </NavLink>
                <NavLink
                  to="/reviews/new"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100'
                    }`}
                >
                  New Review
                </NavLink>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <UserMenu />
            </div>
          </nav>
        </div>
      </header>

      <main className="container py-6" id="main-content" role="main">
        {children}
      </main>
      <footer className="bg-white border-t border-gray-200 py-4 mt-auto">
        <div className="container text-center text-sm text-gray-500">
          Sentinel Studio &mdash; AI-Powered Code Review &nbsp;|&nbsp; Ryan Vo {'<'}ryandtvo@gmail.com{'>'}
        </div>
      </footer>
    </div>
  );
}

function UserMenu() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="w-8 h-8 rounded-full bg-gray-200 animate-pulse" aria-hidden="true" />
    );
  }

  if (!user) {
    return (
      <NavLink
        to="/login"
        className="btn btn-primary btn-sm"
      >
        Sign In
      </NavLink>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="hidden sm:block text-sm text-gray-600">{user.username}</span>
      <button
        onClick={logout}
        className="btn btn-outline btn-sm"
        aria-label="Sign out"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
        <span className="hidden sm:inline">Sign Out</span>
      </button>
    </div>
  );
}