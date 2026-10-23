# Architecture Documentation

## Overview

Sentinel Studio follows a modular, layered architecture separating concerns between:
- **API Layer**: FastAPI routes, request/response validation
- **Service Layer**: Business logic, orchestration
- **Data Layer**: SQLAlchemy models, database operations
- **Core Layer**: Configuration, security, authentication, database
- **Frontend**: React SPA with typed API client

## Backend Structure

```
backend/app/
├── main.py                 # FastAPI app factory
├── core/
│   ├── config.py           # Pydantic settings from env
│   ├── security.py         # Password hashing, JWT, CSRF, PKCE
│   ├── database.py         # SQLAlchemy async engine/session
│   └── auth.py             # Keycloak OIDC integration
├── models/                 # SQLAlchemy ORM models
│   └── __init__.py         # User, Review, Finding, AuditLog
├── schemas/                # Pydantic request/response models
│   ├── auth.py
│   └── review.py
├── api/
│   ├── deps.py             # FastAPI dependencies (auth, DB, CSRF)
│   └── routes/
│       ├── health.py       # /healthz, /ready
│       ├── auth.py         # /auth/*
│       ├── users.py        # /users/*
│       └── reviews.py      # /reviews/*
└── services/               # Business logic (future)
```

## Database Schema

### Users
- `id` (PK), `keycloak_sub` (unique), `email` (unique), `username` (unique)
- `full_name`, `avatar_url`, `role` (viewer/operator/admin)
- `is_active`, `created_at`, `updated_at`, `last_login_at`

### Reviews
- `id` (PK), `author_id` (FK→Users)
- `title`, `description`, `repository_url`
- `base_branch`, `head_branch`, `diff_content`
- `status` (pending/in_progress/completed/failed)
- Finding counts: `findings_count`, `critical_count`, `high_count`, `medium_count`, `low_count`
- `started_at`, `completed_at`, `created_at`, `updated_at`

### Findings
- `id` (PK), `review_id` (FK→Reviews)
- `file_path`, `start_line`, `end_line`
- `severity` (critical/high/medium/low/info)
- `category` (bug/security/performance/style/documentation/testing/maintainability)
- `title`, `description`, `suggestion`, `rule_id`
- `is_llm_generated`, `llm_explanation`, `created_at`

### Audit Logs
- `id` (PK), `user_id` (FK→Users, nullable), `review_id` (FK→Reviews, nullable)
- `action` (enum), `details`, `ip_address`, `user_agent`, `created_at`

## Authentication Flow

```
1. User clicks "Sign In"
2. Frontend calls GET /auth/login → returns Keycloak auth_url + PKCE challenge
3. Frontend redirects to Keycloak with state + code_challenge (S256)
4. User authenticates at Keycloak
5. Keycloak redirects to /auth/callback?code=...&state=...
6. Frontend sends code + code_verifier + state to POST /auth/callback
7. Backend exchanges code for tokens at Keycloak token endpoint
8. Backend fetches userinfo, verifies ID token
9. Backend creates/updates local User record
10. Backend issues local JWT access + refresh tokens
11. Backend sets HttpOnly SameSite=Lax cookies + CSRF token
12. Frontend receives tokens, stores in memory
```

## Authorization Model

| Role | Permissions |
|------|-------------|
| viewer | Read reviews, export, view findings |
| operator | Create/update/delete own reviews, manage findings |
| admin | All operations, manage users, system settings |

All data endpoints require authentication. CSRF protection on all mutating operations.

## Frontend Structure

```
frontend/src/
├── main.tsx              # Entry point
├── App.tsx               # Routes, protected/public wrappers
├── api/
│   ├── types.ts          # TypeScript interfaces (from backend schemas)
│   ├── client.ts         # Axios instance with interceptors
│   └── index.ts
├── components/
│   ├── Layout.tsx        # Header, navigation, user menu
│   └── LoadingError.tsx  # Loading, Error, Empty states, badges, cards
├── pages/
│   ├── Dashboard.tsx     # Review list with filters, pagination
│   ├── Login.tsx         # OIDC login, callback handling
│   └── ReviewDetail.tsx  # Review findings, export, summary
└── hooks/
    └── useAuth.ts        # Auth state, login, logout, callback
```

## API Client

The typed API client (`api/client.ts`) provides:
- Automatic token attachment via interceptor
- Automatic token refresh on 401
- CSRF token injection for mutating requests
- Full TypeScript types matching backend schemas

## Deployment

### Docker Compose (Development)
```yaml
services:
  backend:    # FastAPI on :8000
  frontend:   # Nginx + React on :5173
  keycloak:   # Keycloak on :8080
volumes:
  backend-data:   # SQLite persistence
  keycloak-data:  # Keycloak persistence
```

### Production Requirements
- PostgreSQL instead of SQLite (`DATABASE_URL=postgresql+asyncpg://...`)
- TLS termination at reverse proxy (nginx/traefik/caddy)
- Secure `SECRET_KEY` (32+ random chars)
- `KEYCLOAK_CLIENT_SECRET` configured
- `DEBUG=false`, `DEMO_MODE=false`
- Keycloak behind same reverse proxy with proper hostname
- Rate limiting, WAF, security headers

## Extensibility

### Adding Rule Packs
1. Create YAML rule file in `backend/app/services/rules/`
2. Register in `system_rules.json` with glob pattern
3. Engine loads rules at startup, caches compiled patterns

### Adding LLM Providers
1. Implement adapter in `backend/app/services/llm/adapters/`
2. Follow `LLMAdapter` protocol: `complete(prompt) -> Response`
3. Register in provider factory with `LLM_PROVIDER` key

### Adding Export Formats
1. Add format to `ReviewExportRequest.format` enum
2. Implement handler in `reviews.py` export endpoint
3. Return appropriate `media_type` and filename