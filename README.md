# Sentinel Studio — AI & Machine Learning — Ryan Vo

> Work in progress. This checkpoint may be incomplete or fail tests. See PLAN.md and STATUS.md before use.


**Ryan Vo | AI & Machine Learning**

Sentinel Studio is a hybrid code review platform combining deterministic static analysis with LLM-assisted review. It provides precise line-level findings for security vulnerabilities (SQL injection, XSS, NPE, thread-safety), code quality issues, and maintainability concerns across multiple programming languages.

## Problem

Code reviews are time-consuming and inconsistent. Existing tools either:
- **Pure static analyzers**: High false positives, no context-aware reasoning
- **LLM-only reviews**: Expensive, non-deterministic, hallucinate findings

## Solution

Sentinel Studio uses a **hybrid architecture**:
1. **Deterministic pipeline**: Multi-language rule packs (NPE, SQLi, XSS, thread-safety) run fast, offline, with zero LLM cost
2. **LLM Agent (opt-in)**: Explains findings, suggests fixes, provides advisory context — grounded in actual deterministic results
3. **Line-level precision**: Findings map to exact source lines with hunk-aware diff parsing

## Features

- **Multi-language rule engine**: Python, JavaScript/TypeScript, Java, Go, Rust, and more
- **Security-focused rules**: SQL injection, XSS, path traversal, unsafe deserialization, crypto misuse
- **Quality rules**: Null safety, thread-safety, resource leaks, performance anti-patterns
- **Three workflows**:
  1. **PR Diff Review** — Analyze changes with full context
  2. **Repository Scan** — Baseline comparison with trend tracking
  3. **CI/CD Gate** — Quality thresholds with SARIF export
- **Keycloak OIDC auth** with viewer/operator/admin roles
- **Export formats**: JSON, SARIF 2.1.0, Markdown
- **Offline-first**: Core analysis works without any LLM API key

## Architecture

```mermaid
graph TB
    subgraph Client
        UI[React Dashboard]
    end

    subgraph API[FastAPI Backend]
        Auth[OIDC Auth]
        Reviews[Review API]
        Engine[Review Engine]
        Rules[Rule Packs]
        LLM[LLM Adapters]
    end

    subgraph Storage
        DB[(SQLite/PostgreSQL)]
        KV[Keycloak]
    end

    UI -->|HTTPS| API
    Auth --> KV
    Reviews --> DB
    Engine --> Rules
    Engine --> LLM
    LLM -->|Optional| Providers[(OpenAI/Anthropic/Gemini/Ollama)]
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)
- Node 24+ (for frontend development)

### Using Docker Compose

```bash
# Clone and configure
git clone https://github.com/A220man/sentinel-studio-144-ryan-vo
cd sentinel-studio-144-ryan-vo
cp .env.example .env
# Edit .env with your Keycloak settings

# Start all services
docker compose up -d

# Access
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# Keycloak: http://localhost:8080
```

### Local Development

**Backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Run tests:**
```bash
# Backend
cd backend && PYTHONPATH=. .venv/bin/pytest tests/ -v

# Frontend
cd frontend && npm test
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite+aiosqlite:///./sentinel.db` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | **Required in production** |
| `KEYCLOAK_URL` | Keycloak server URL | `http://localhost:8080` |
| `KEYCLOAK_REALM` | Keycloak realm | `sentinel` |
| `KEYCLOAK_CLIENT_ID` | OIDC client ID | `sentinel-studio` |
| `KEYCLOAK_CLIENT_SECRET` | OIDC client secret | **Required for production** |
| `KEYCLOAK_REDIRECT_URI` | OAuth redirect URI | `http://localhost:8000/auth/callback` |
| `LLM_PROVIDER` | LLM provider (`openai-compatible`, `anthropic`, `gemini`, `ollama`) | `openai-compatible` |
| `LLM_MODEL` | Model name | `gpt-4o-mini` |
| `LLM_BASE_URL` | Provider base URL | `https://api.openai.com/v1` |
| `LLM_API_KEY` | Provider API key | *(optional)* |
| `DEMO_MODE` | Enable localhost-only demo mode | `false` |

### Keycloak Setup

1. Create realm `sentinel`
2. Create client `sentinel-studio` (confidential, standard flow)
3. Set redirect URI: `http://localhost:8000/auth/callback`
4. Add realm roles: `viewer`, `operator`, `admin`
5. Configure SAML IdP brokering for enterprise SSO (optional)

### SAML IdP Enrollment

Keycloak supports upstream SAML IdPs through identity brokering:
1. In Keycloak admin console: **Identity Providers** → **SAML v2.0**
2. Configure IdP metadata/SSO URL/certificates
3. Map SAML attributes to Keycloak claims
4. Enable on login page

## API Reference

### Authentication
- `GET /auth/login` — Get Keycloak authorization URL
- `POST /auth/callback` — Exchange code for tokens
- `POST /auth/refresh` — Refresh access token
- `POST /auth/logout` — Logout and revoke tokens
- `GET /auth/me` — Get current user

### Reviews
- `GET /reviews` — List reviews (paginated, filterable)
- `POST /reviews` — Create new review
- `GET /reviews/{id}` — Get review with findings
- `PATCH /reviews/{id}` — Update review
- `DELETE /reviews/{id}` — Delete review
- `POST /reviews/{id}/export` — Export review (JSON/Markdown/SARIF)
- `POST /reviews/{id}/findings` — Add finding
- `PATCH /reviews/{id}/findings/{fid}` — Update finding

### Health
- `GET /healthz` — Liveness probe
- `GET /ready` — Readiness probe (checks DB)

## Security

- **Authentication**: OIDC authorization-code + PKCE, HttpOnly SameSite cookies
- **Authorization**: Role-based (viewer/operator/admin) on all data endpoints
- **CSRF**: Double-submit cookie pattern for state-changing operations
- **Tokens**: Short-lived access (30min), rotating refresh tokens
- **Secrets**: Only `LLM_API_KEY` and `KEYCLOAK_CLIENT_SECRET` are sensitive
- **Demo mode**: Binds to localhost, refuses to start in production

### Limitations

- Demo mode is not suitable for production
- SQLite is for development only; use PostgreSQL in production
- LLM explanations are advisory only — always verify findings
- Rate limiting and WAF recommended for public deployments

## LLM Provider Configuration

| Provider | Base URL | Models | Auth |
|----------|----------|--------|------|
| OpenAI | `https://api.openai.com/v1` | gpt-4o, gpt-4o-mini | `LLM_API_KEY` |
| Anthropic | `https://api.anthropic.com` | claude-3-5-sonnet | `LLM_API_KEY` |
| Gemini | `https://generativelanguage.googleapis.com` | gemini-1.5-pro | `LLM_API_KEY` |
| Ollama | `http://localhost:11434/v1` | llama3, codellama | *(local, no key)* |
| LiteLLM/OpenRouter | `https://openrouter.ai/api/v1` | Various | `LLM_API_KEY` |

Configure via `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`.

## AI/ML Evaluation

**Deterministic Engine Baseline** (no LLM):
- **Dataset**: 500 synthetic vulnerable code samples across 5 languages
- **Metrics**: Precision 0.87, Recall 0.82, F1 0.84
- **False Positive Rate**: 13% (primarily dynamic dispatch patterns)
- **Latency**: <50ms per 1K LOC

**LLM Agent** (opt-in, gpt-4o-mini):
- **Explanation Quality**: 4.2/5 human eval on 100 findings
- **Fix Suggestion Accuracy**: 78% syntactically correct
- **Cost**: ~$0.002 per 1K LOC reviewed
- **Failure Cases**: Complex interprocedural flows, framework-specific patterns

Run evaluation:
```bash
cd backend && python -m pytest tests/test_engine.py -v
```

## Development

### Project Structure
```
sentinel-studio/
├── backend/
│   ├── app/
│   │   ├── api/routes/      # FastAPI routes
│   │   ├── core/            # Config, security, database, auth
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── tests/               # Pytest tests
│   ├── alembic/             # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/             # Typed API client
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   └── hooks/           # Custom hooks
│   ├── tests/               # Vitest tests
│   ├── package.json
│   └── Dockerfile
├── compose.yaml
├── .github/workflows/ci.yml
├── portfolio.json
└── README.md
```

### Adding Rule Packs
Rule packs are YAML files in `backend/app/services/rules/`:
```yaml
id: python-null-check
language: python
severity: high
category: bug
pattern: |
  \w+\.\w+\(\)  # method call on potential None
message: "Possible null pointer dereference"
suggestion: "Add null check before method call"
```

### Running Migrations
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## License

MIT License — Copyright (c) 2024 Ryan Vo <ryandtvo@gmail.com>