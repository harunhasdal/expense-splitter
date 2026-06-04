# NFR Design Patterns — Unit 1: Backend API & Data Layer

---

## Pattern 1: Authentication — JWT HttpOnly Cookie + CSRF Double-Submit

**Addresses**: SECURITY-08, SECURITY-12, BR-AUTH-01, BR-AUTH-03

### Design
```
Client                          FastAPI
  |                               |
  |  GET /auth/google/login       |
  |------------------------------>|
  |                               |-- generate state = sign(random_bytes, CSRF_SECRET_KEY)
  |                               |-- Set-Cookie: oauth_state=<state>; HttpOnly; SameSite=Lax
  |  302 → Google (state param)   |
  |<------------------------------|
  |
  | [OAuth2 flow at Google]
  |
  |  GET /auth/google/callback?code=...&state=...
  |------------------------------>|
  |                               |-- validate state == cookie value (BR-AUTH-03)
  |                               |-- exchange code → access token → user profile
  |                               |-- upsert User; link pending members
  |                               |-- sign JWT (RS256, 24h expiry)
  |  Set-Cookie: session=<jwt>;   |
  |    HttpOnly; Secure;          |
  |    SameSite=Lax               |
  |  Set-Cookie: csrf_token=<t>;  |-- non-HttpOnly; SPA reads this
  |    Secure; SameSite=Lax       |
  |  302 → /dashboard             |
  |<------------------------------|
```

**CSRF double-submit on every state-mutating request**:
```
Client                          FastAPI AuthMiddleware
  |                               |
  |  POST /groups                 |
  |  Cookie: session=<jwt>        |
  |  X-CSRF-Token: <t>            |
  |------------------------------>|
  |                               |-- validate JWT (signature, exp, iss, aud)
  |                               |-- validate X-CSRF-Token == Cookie csrf_token
  |                               |-- extract User from JWT sub claim
  |                               |-- inject User into request state
  |  200 / 4xx                    |
  |<------------------------------|
```

**Implementation notes**:
- `csrf_token` cookie: `itsdangerous.URLSafeTimedSerializer` signs a random value; expires in 24h matching JWT
- Middleware skips CSRF check for GET/HEAD/OPTIONS (safe methods)
- CSRF check runs before any business logic in the dependency chain

---

## Pattern 2: Request Lifecycle — Correlation ID Propagation

**Addresses**: SECURITY-03, BR-ERR-02, cross-workflow concern

### Design
```
Incoming request
  |
  v
[CorrelationIDMiddleware]
  |-- read X-Request-Id header (if provided by ALB or client)
  |-- OR generate new UUID4
  |-- bind correlation_id to structlog context
  |-- add to request.state.correlation_id
  |
  v
[All middleware and handlers]
  |-- structlog auto-includes correlation_id in every log line
  |
  v
[Response]
  |-- X-Correlation-Id: <id> header added to all responses
```

**structlog configuration**:
```python
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,   # includes correlation_id
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
```

---

## Pattern 3: Global Error Handler — Fail Closed

**Addresses**: SECURITY-15, BR-ERR-01, BR-ERR-03, BR-ERR-04

### Design
```
Exception raised anywhere in handler chain
  |
  v
[global_exception_handler] in core/errors.py
  |
  |-- IS ValidationError (Pydantic)?
  |     → 422 with field-level errors (safe to expose — no internals)
  |
  |-- IS HTTPException?
  |     → pass through status + generic detail
  |
  |-- IS SQLAlchemy OperationalError (DB unavailable)?
  |     → log ERROR with full traceback + correlation_id
  |     → return 503 {"error": "Service temporarily unavailable",
  |                    "correlation_id": "...", "retry_after": 30}
  |
  |-- IS any other Exception?
  |     → log ERROR with full traceback + correlation_id (SECURITY-03)
  |     → return 500 {"error": "Internal server error",
  |                    "correlation_id": "..."}
  |                    (NO stack trace, NO internal details — SECURITY-09)
```

**Auth failure path (fail closed)**:
```
JWT missing / expired / invalid signature / wrong issuer
  |
  v
[get_current_user dependency]
  |-- raises HTTPException(status_code=401, detail="Authentication required")
  |-- NO fallback to anonymous — always denied (BR-ERR-04)
```

---

## Pattern 4: Security Headers Middleware

**Addresses**: SECURITY-04

Applied as a Starlette middleware on every response — no per-route decoration needed.

```python
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "   # documented exception: SPA CSS-in-JS
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
```

---

## Pattern 5: Input Validation — Defence in Depth

**Addresses**: SECURITY-05, BR-VAL-01 to BR-VAL-04

Three validation layers applied in sequence:

```
Layer 1 — Network/ALB:
  AWS WAF: max body size 1 MB; rate limit 100 req/5-min per IP

Layer 2 — FastAPI/Pydantic (schema boundary):
  - Type coercion and validation via Pydantic v2 model_validator
  - Field-level: max_length, gt=0, EmailStr, pattern matching
  - Request body size double-checked in middleware (defence in depth)
  - Returns 422 with structured field errors on failure

Layer 3 — Service layer:
  - Business rule validation (date not in future, payer is active member, etc.)
  - BalanceEngine.validate_split() for financial split rules
  - Returns 400 with domain error messages on failure
  - NEVER reaches Layer 3 with structurally invalid data (Layer 2 catches it first)
```

---

## Pattern 6: Repository — Unit of Work via SQLAlchemy Session

**Addresses**: NFR-Reliability, BR-EXP-05 (atomic insert)

```python
# Service layer pattern — session as unit of work
async def create_expense(db: AsyncSession, ...):
    async with db.begin():           # begins transaction; auto-commits or rolls back
        expense = await expense_repo.create(db, ...)
        for share in shares:
            await split_repo.create(db, expense.id, share)
    # commit happens here; rollback on any exception inside the block
```

- `AsyncSession` is request-scoped (created per request via `get_db` dependency)
- `db.begin()` context manager ensures atomic multi-row writes
- `pool_pre_ping=True` recycles stale connections before use

---

## Pattern 7: Migration as a One-Off ECS Task

**Addresses**: NFR deployment Q2=A

```
GitHub Actions CI/CD pipeline:
  1. Build and push Docker image to ECR (tagged with git SHA)
  2. Register new ECS task definition revision
  3. Run migration task:
       aws ecs run-task \
         --cluster <cluster> \
         --task-definition expense-splitter-migrate \
         --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}'
  4. Wait for migration task to complete (exit code 0)
  5. IF migration succeeds: update ECS service to new task definition (rolling deploy)
  6. IF migration fails: stop deployment; do NOT update service
```

- Migration task uses the same Docker image as the API (no separate migration image)
- Migration task has DB access but no inbound network; no ALB target
- Rolling deployment with minimum healthy percent 100% ensures no downtime during service update

---

## Pattern 8: OpenAPI Schema — Internal Access Only

**Addresses**: NFR design Q3=A

```
Production:
  DISABLE_DOCS=false (docs disabled via FastAPI app config)
  /docs    → 404
  /redoc   → 404
  /openapi.json → accessible ONLY from within VPC
              (ALB listener rule: forward /openapi.json only from VPC CIDR)

CI/CD:
  Step in GitHub Actions:
    docker run ... python -c "
      from main import app
      import json
      print(json.dumps(app.openapi()))
    " > openapi.json
  openapi.json committed to repo and used by frontend codegen
  (openapi-typescript generates TypeScript types from this file)
```

---

## Pattern 9: Health Check

**Addresses**: ECS ALB target group health check; availability NFR

```
GET /health  (no auth required)
  |
  v
  SELECT 1 FROM pg_catalog.pg_stat_activity LIMIT 1
  |-- SUCCESS → 200 {"status": "ok", "db": "ok"}
  |-- DB ERROR → 503 {"status": "degraded", "db": "unavailable"}
```

- ALB health check: path `/health`, port `8000`, interval 30s, threshold 2
- ECS will replace unhealthy tasks automatically
- No sensitive info in health response
