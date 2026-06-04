# Tech Stack Decisions — Unit 1: Backend API & Data Layer

All decisions are final and carry into code generation. Rationale is included for traceability.

---

## Backend Framework

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| API framework | FastAPI | ≥0.111 | Async-native, Pydantic v2 integration, automatic OpenAPI schema generation for frontend client codegen |
| ASGI server | Uvicorn | ≥0.29 | Production-grade, used with Gunicorn process manager in container |
| Process manager | Gunicorn + UvicornWorker | ≥22.0 | Multi-worker management; graceful shutdown handling |

## Data Layer

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| ORM | SQLAlchemy (async) | ≥2.0 | Async-first API, type-safe query construction, Alembic integration |
| Async driver (dev) | aiosqlite | ≥0.20 | Zero-config SQLite for local development |
| Async driver (cloud) | asyncpg | ≥0.29 | High-performance PostgreSQL async driver |
| Migrations | Alembic | ≥1.13 | Industry standard for SQLAlchemy; auto-generate as starting point, manual review required |
| Connection pool (cloud) | SQLAlchemy async pool: `pool_size=2`, `max_overflow=8`, `pool_pre_ping=True` | — | Small pool per container (Q5=A); pre-ping recycles stale connections |

## Authentication & Security

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| JWT library | python-jose[cryptography] | ≥3.3 | RS256 support, well-maintained |
| OAuth2 HTTP client | httpx | ≥0.27 | Async-native; used for provider token exchange and userinfo calls |
| Password hashing | N/A — OAuth2 only | — | No local passwords; no hashing library needed |
| CSRF protection | Double-submit cookie pattern | — | `itsdangerous` for signing CSRF token cookie (Q3=A) |
| Secrets management | AWS Secrets Manager | — | JWT private key, DB URL, OAuth2 client secrets |

## Validation & Configuration

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| Request/response schemas | Pydantic v2 | ≥2.7 | Native FastAPI integration; 5–50× faster than v1; strict mode |
| App config | Pydantic Settings | ≥2.7 | Env var loading with type validation and `.env` file support for local dev |
| Email validation | `pydantic[email]` (email-validator) | — | RFC 5322 via Pydantic's `EmailStr` |

## Logging & Observability

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| Structured logging | structlog | ≥24.1 | JSON output, context binding, correlation ID propagation (Q4=A → CloudWatch) |
| Log destination | CloudWatch Logs via ECS awslogs driver | — | Zero extra infra; ECS task definition configures log group |
| Log retention | 90 days (CloudWatch log group retention policy) | — | SECURITY-14 minimum |
| Metrics | CloudWatch metrics via ALB + ECS native metrics | — | No custom metrics library in v1 |

## Testing

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| Test runner | pytest | ≥8.2 | Standard; `pytest-asyncio` for async test support |
| Async test support | pytest-asyncio | ≥0.23 | Required for async FastAPI endpoint testing |
| HTTP test client | httpx (async) | ≥0.27 | AsyncClient for FastAPI integration tests |
| Coverage | pytest-cov | ≥5.0 | 80% minimum line coverage enforced in CI |
| Test DB | SQLite in-memory via aiosqlite | — | Same ORM + migrations; no PostgreSQL needed for CI tests |
| Linting | ruff | ≥0.4 | Replaces flake8 + isort + black in one tool |
| Type checking | mypy (strict) | ≥1.10 | Strict mode; all public functions must be annotated |

## Containerisation & Deployment

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| Container runtime | Docker (multi-stage build) | — | Stage 1: build/deps; Stage 2: minimal runtime image |
| Base image | python:3.12-slim | pinned digest | Minimal attack surface (SECURITY-09, SECURITY-10) |
| Orchestration | AWS ECS Fargate | — | Managed container orchestration; no EC2 to patch (Q1=A) |
| Load balancer | AWS ALB | — | TLS termination, WAF integration for rate limiting |
| WAF rate limiting | AWS WAF on ALB — 100 req / 5-min per IP | — | SECURITY-11 (Q2=A) |
| Container registry | Amazon ECR | — | Private registry; image scanning enabled |
| CI/CD | GitHub Actions | — | Build → test → push to ECR → deploy to ECS |

## Infrastructure as Code

| Decision | Choice | Version | Rationale |
|---|---|---|---|
| IaC tool | AWS CDK (TypeScript) | ≥2.140 | Typed constructs; first-class ECS Fargate and RDS patterns; aligns with AWS-native tooling |

## Environment Variable Manifest

All required env vars (none hardcoded):

| Variable | Description | Secret? |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string (`sqlite+aiosqlite:///...` or `postgresql+asyncpg://...`) | Yes |
| `JWT_PRIVATE_KEY` | RS256 private key PEM (from Secrets Manager) | Yes |
| `JWT_PUBLIC_KEY` | RS256 public key PEM | No |
| `JWT_EXPIRY_SECONDS` | Token lifetime in seconds (default 86400) | No |
| `JWT_ISSUER` | Token issuer string (e.g. `https://api.expensesplitter.example.com`) | No |
| `GOOGLE_CLIENT_ID` | Google OAuth2 client ID | No |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret | Yes |
| `GITHUB_CLIENT_ID` | GitHub OAuth2 client ID | No |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth2 client secret | Yes |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowed origins | No |
| `APP_BASE_URL` | Public base URL of this API (used in OAuth2 redirect URIs) | No |
| `CSRF_SECRET_KEY` | Secret for signing CSRF cookie (itsdangerous) | Yes |
| `LOG_LEVEL` | Logging level (default `INFO`) | No |
| `DISABLE_DOCS` | Set `true` in production to disable `/docs` and `/redoc` | No |
