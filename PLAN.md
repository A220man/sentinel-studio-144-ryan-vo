# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

review-import-export

## Roadmap

### core-skeleton — Core FastAPI/React skeleton with auth and DB

Status: done

Acceptance:
- FastAPI app starts and serves health endpoint
- React app builds and serves frontend
- SQLite database with migrations
- OIDC Keycloak auth configured (backend sessions + HttpOnly cookies)
- Docker compose with backend, frontend, Keycloak, postgres
- CI workflow runs backend/frontend tests and builds

Implementation: `backend/app/main.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/core/security.py`, `backend/app/core/auth.py`, `backend/app/models/__init__.py`, `backend/app/api/deps.py`, `backend/app/api/routes/health.py`, `backend/app/api/routes/auth.py`, `backend/app/api/routes/users.py`, `backend/app/api/routes/reviews.py`, `backend/app/schemas/auth.py`, `backend/app/schemas/review.py`, `backend/requirements.txt`, `backend/Dockerfile`, `backend/.dockerignore`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/api/types.ts`, `frontend/src/hooks/useAuth.ts`, `frontend/src/components/Layout.tsx`, `frontend/src/components/LoadingError.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/ReviewDetail.tsx`, `frontend/src/styles/globals.css`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/Dockerfile`, `frontend/.dockerignore`, `compose.yaml`, `.github/workflows/ci.yml`

Tests: `backend/tests/test_health.py`, `backend/tests/test_auth.py`, `backend/tests/test_reviews.py`, `backend/tests/conftest.py`, `frontend/tests/App.test.tsx`, `frontend/tests/Dashboard.test.tsx`, `frontend/tests/setup.ts`, `frontend/vitest.config.ts`

### review-import-export — Review import/export functionality

Status: done

Acceptance:
- Export review as JSON, Markdown, or SARIF
- Import review from JSON file via API
- Import review from JSON file via Dashboard UI
- Validation for imported JSON (required fields, valid format)

Implementation: `backend/app/schemas/review.py`, `backend/app/api/routes/reviews.py`, `frontend/src/api/types.ts`, `frontend/src/api/client.ts`, `frontend/src/pages/Dashboard.tsx`

Tests: `backend/tests/test_reviews.py::test_import_review`, `backend/tests/test_reviews.py::test_import_review_invalid_json`, `backend/tests/test_reviews.py::test_import_review_missing_title`

### code-review-engine — Deterministic code review engine with rule packs

Status: planned

Acceptance:
- Rule pack loader for multi-language rules
- AST-based deterministic analyzers (NPE, SQLi, XSS, thread-safety)
- Line-level comment generation
- Diff parsing and hunk mapping

### llm-agent-review — LLM Agent review with opt-in advisory explanations

Status: planned

Acceptance:
- OpenAI-compatible, Anthropic, Gemini, Ollama adapters
- Provider errors surfaced clearly
- Explanations labeled advisory, grounded in findings
- Configurable provider/model/endpoint

### review-workflows — Three complete review workflows

Status: planned

Acceptance:
- PR diff review (create/import/search/detail/export)
- Repository scan with baseline comparison
- CI/CD gate integration with quality thresholds

### frontend-dashboard — React dashboard with review management UI

Status: planned

Acceptance:
- Domain dashboard with loading/error/empty states
- Review list, detail, create, import, search, export
- Typed API client from backend routes
- Responsive professional UI

