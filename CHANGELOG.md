# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-10-23

### Added
- FastAPI backend with SQLite/SQLAlchemy persistence
- React + TypeScript + Vite frontend dashboard
- Keycloak OIDC authentication with PKCE, HttpOnly cookies, CSRF protection
- Role-based access control (viewer, operator, admin)
- Review CRUD API with pagination, filtering, search
- Finding management (create, update, severity categories)
- Export reviews to JSON, Markdown, and SARIF 2.1.0
- Docker Compose with backend, frontend, Keycloak, persistent volumes
- GitHub Actions CI workflow (backend tests, frontend build/test, Docker builds)
- Health and readiness endpoints
- Audit logging for all mutations

### Security
- JWT tokens with short expiry and rotating refresh tokens
- CSRF double-submit cookie pattern
- Secure HttpOnly SameSite=Lax cookies
- Input validation via Pydantic schemas

### Infrastructure
- Multi-stage Dockerfiles with non-root users
- Nginx reverse proxy for frontend with API proxying
- SQLite for development, PostgreSQL-ready configuration
- Alembic migrations for schema management

## [Unreleased]

### Added
- Review import from JSON files via API (`POST /reviews/import`)
- Import button with file picker in Dashboard UI
- Validation for imported JSON (required title field, valid JSON format)

### Planned
- Deterministic multi-language rule engine (NPE, SQLi, XSS, thread-safety)
- LLM Agent with OpenAI/Anthropic/Gemini/Ollama adapters
- PR diff parsing and hunk mapping
- CI/CD gate integration with quality thresholds
- Repository scan workflow with baseline comparison
- Real-time review progress via WebSockets
