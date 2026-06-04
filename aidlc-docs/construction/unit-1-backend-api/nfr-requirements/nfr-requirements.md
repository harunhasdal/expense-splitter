# NFR Requirements — Unit 1: Backend API & Data Layer

---

## Scalability

| Requirement | Target | Notes |
|---|---|---|
| Compute scaling | ECS Fargate — horizontal auto-scaling based on CPU/memory | min 1 task, max 4 tasks; scale-out at 70% CPU |
| Stateless API | All session state in JWT cookie; no server-side session store | Enables any task to handle any request |
| DB connection pool | SQLAlchemy async pool: min 2, max 10 per container instance | Suitable for ≤50 concurrent users per task; 4 tasks → max 40 pool connections |
| Database | AWS RDS PostgreSQL (Multi-AZ for HA) in production; single-AZ in staging | |

## Performance

| Requirement | Target | Enforcement |
|---|---|---|
| API p95 response time | < 300 ms for balance calculations on groups up to 50 members | CloudWatch metric alarm on ALB `TargetResponseTime` |
| Debt simplification | O(n log n) — designed in Unit 2 | Verified by Unit 2 NFR Requirements |
| DB query timeout | 5 seconds max per query; abort and return 503 on timeout | SQLAlchemy `pool_timeout=5` |
| Startup time | Container ready within 30 seconds | ECS health check grace period |

## Availability

| Requirement | Target | Notes |
|---|---|---|
| Uptime SLO | 99.5% monthly | ~3.6 hours downtime budget/month |
| Multi-AZ deployment | ECS tasks spread across ≥2 AZs | ECS placement strategy: `spread` across AZs |
| DB failover | RDS Multi-AZ automatic failover | ~60s failover window |
| Health check endpoint | `GET /health` returns 200 with DB ping result; no auth required | ALB target group uses this endpoint |
| Graceful degradation | DB unavailable → 503 with `Retry-After: 30` header | No stale data served |

## Security (SECURITY-01 to SECURITY-15 — full enforcement)

### Encryption (SECURITY-01)
- RDS PostgreSQL: storage encryption enabled (AES-256, AWS managed key)
- All connections via TLS 1.2+ (RDS `force_ssl=1` parameter)
- No plaintext database URLs; URL stored in AWS Secrets Manager

### Access Logging (SECURITY-02)
- ALB access logs → S3 bucket (90-day retention, lifecycle to Glacier after 30 days)
- No API Gateway used (direct ALB → ECS) — ALB logging covers this requirement

### Application Logging (SECURITY-03)
- Structured JSON logging via Python `structlog`
- Log fields: `timestamp`, `level`, `correlation_id`, `message`, `actor_id` (UUID only — no PII)
- Log output → stdout → CloudWatch Logs agent on ECS task
- Log group retention: 90 days (SECURITY-14)
- Sensitive fields (`password`, `token`, `secret`, `authorization`, `cookie`) filtered from all log output

### HTTP Security Headers (SECURITY-04)
Applied by `core/middleware.py` on every response:
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```
No `unsafe-eval`. `unsafe-inline` on `style-src` only — justified by SPA CSS-in-JS requirements; documented exception.

### Input Validation (SECURITY-05)
- Pydantic v2 schemas validate all request bodies at the FastAPI routing layer
- Max request body: 1 MB (`uvicorn --limit-concurrency` + custom middleware)
- All string fields have explicit `max_length` constraints matching ORM columns
- `EmailStr` for email fields (RFC 5322 validation)
- Currency code validated against static ISO 4217 allowlist
- Parameterised SQLAlchemy expressions for all queries — no string concatenation

### IAM / Least Privilege (SECURITY-06)
- ECS Task Role: read from Secrets Manager (specific ARNs only), write to CloudWatch Logs (specific log group ARN)
- No wildcard actions or resources on any policy statement
- RDS access: ECS security group only; no public RDS endpoint
- S3 (ALB logs): ALB service principal write-only; no app read/write to this bucket

### Network (SECURITY-07)
- VPC with public subnets (ALB only) and private subnets (ECS tasks, RDS)
- ALB security group: inbound 443 from `0.0.0.0/0`; outbound to ECS security group on app port only
- ECS security group: inbound from ALB security group only; outbound to RDS security group + internet (via NAT gateway for OAuth2 provider calls)
- RDS security group: inbound from ECS security group on port 5432 only

### Application Authorization (SECURITY-08)
- `get_current_user` FastAPI dependency applied to all routes except `/health` and `/auth/*`
- CORS: `allowed_origins` loaded from env var `ALLOWED_ORIGINS`; no wildcard
- CSRF: double-submit cookie pattern — `X-CSRF-Token` header required on all state-mutating requests (POST/PATCH/DELETE); server validates against `csrf_token` cookie value
- JWT cookie: `HttpOnly=True`, `Secure=True`, `SameSite=Lax`
- JWT validation on every request: signature, expiry, issuer, audience (SECURITY-08, SECURITY-12)

### Hardening (SECURITY-09)
- No default credentials in any config file or environment variable
- Production error responses: generic message + correlation ID only; no stack traces
- No sample/debug routes in production (`/docs` and `/redoc` disabled via env var `DISABLE_DOCS=true`)
- Docker base image: `python:3.12-slim` (minimal footprint)

### Supply Chain (SECURITY-10)
- `uv` lock file (`uv.lock`) committed to version control; all dependencies pinned to exact versions
- GitHub Actions CI step: `uv run pip-audit` (or Dependabot) for vulnerability scanning
- Docker: no `latest` tags — base image pinned to specific digest
- SBOM generated via `cyclonedx-bom` in CI and stored as release artifact

### Secure Design (SECURITY-11)
- Rate limiting: ALB WAF rule — 100 requests per 5-minute window per IP; applied to all paths
- Auth logic isolated in `backend/auth/` — no auth code in other domains
- Design addresses misuse case: non-member attempting to access group data → 404 (no enumeration)

### Authentication (SECURITY-12)
- OAuth2 only — no local password storage; no adaptive hashing needed
- JWT: `python-jose` with RS256 algorithm (asymmetric signing); private key in Secrets Manager
- Session cookies: `HttpOnly`, `Secure`, `SameSite=Lax`
- No brute-force risk on OAuth2 callback (state parameter + provider handles auth attempts)
- Sessions expire after `JWT_EXPIRY_SECONDS` (default 86400 = 24 hours)

### Integrity (SECURITY-13)
- Expense and Settlement immutability enforced at service layer (405 on update/delete attempts)
- Audit log entries (archive events, force-archive events) written via `structlog` to CloudWatch — CloudWatch log groups are append-only (app role has no `DeleteLogGroup`/`DeleteLogStream` permissions)
- External scripts: none loaded from CDN in the API responses — N/A for backend

### Monitoring & Alerting (SECURITY-14)
- CloudWatch Alarms:
  - Auth failures > 10 in 5 minutes → SNS alert
  - HTTP 403 responses > 20 in 5 minutes → SNS alert
  - ALB 5xx error rate > 1% over 5 minutes → SNS alert
  - ECS task CPU > 80% for 10 minutes → scale-out + SNS alert
- Log retention: 90 days minimum on all log groups

### Exception Handling (SECURITY-15)
- Global exception handler in `core/errors.py` catches all unhandled exceptions
- Returns `{"error": "Internal server error", "correlation_id": "..."}` — no internal details
- All external calls (DB, OAuth2 provider HTTP) wrapped in try/except with specific error types
- Fail closed: any auth validation error → 401; any DB error → 503 with Retry-After

## Reliability

| Requirement | Approach |
|---|---|
| Connection errors | SQLAlchemy pool pre-ping enabled; stale connections recycled before use |
| Retry logic | No automatic retries in the API layer — clients retry on 503 |
| Transaction integrity | All multi-row writes in explicit SQLAlchemy transactions with rollback on error |
| Circuit breaker | Not implemented in v1; ALB health check provides basic circuit-breaking at infra level |

## Maintainability

| Requirement | Approach |
|---|---|
| Code quality | `ruff` (linting + formatting), `mypy` (strict type checking) in CI |
| Test coverage | Minimum 80% line coverage required in CI (`pytest-cov`) |
| Environment config | All config via env vars; Pydantic Settings with validation at startup |
| Dependency management | `uv` with lock file; `pyproject.toml` as single source of truth |
| Migration management | Alembic with sequential version numbering; auto-generate disabled (manual review required) |
