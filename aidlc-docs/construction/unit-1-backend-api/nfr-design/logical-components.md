# Logical Components — Unit 1: Backend API & Data Layer

---

## Middleware Stack (Request Processing Order)

Every incoming HTTP request passes through this stack in order. Responses pass back in reverse order.

```
Incoming HTTPS request (TLS terminated at ALB)
  |
  v
1. CorrelationIDMiddleware
   - Read X-Request-Id or generate UUID4
   - Bind to structlog context vars
   - Add to request.state
  |
  v
2. SecurityHeadersMiddleware
   - Attach CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
   - Applied on ALL responses (including errors)
  |
  v
3. CORSMiddleware (Starlette built-in)
   - Allowed origins: from ALLOWED_ORIGINS env var only
   - Allowed methods: GET, POST, PATCH, DELETE, OPTIONS
   - Allow credentials: True (required for cookie-based auth)
   - No wildcard origins
  |
  v
4. CSRFMiddleware
   - GET/HEAD/OPTIONS: skip
   - POST/PATCH/DELETE: validate X-CSRF-Token header == csrf_token cookie value
   - Fail: 403 Forbidden
  |
  v
5. FastAPI Router dispatch
   |
   v
   [Protected routes only]
   AuthMiddleware (FastAPI Dependency: get_current_user)
   - Extract JWT from session cookie
   - Validate: signature (RS256), exp, iss, aud
   - Load User from DB
   - Inject into request
   - Fail: 401 Unauthorized (fail closed)
  |
  v
6. Route Handler → Service → Repository → DB
  |
  v
7. global_exception_handler
   - Catches all unhandled exceptions
   - Returns safe error response
   - Logs full details server-side with correlation_id
  |
  v
Outgoing response
```

---

## Logical Component Map

```
+------------------------------------------------------------------+
|  FASTAPI APPLICATION (main.py)                                    |
|                                                                    |
|  Middleware Stack (top to bottom):                                 |
|  CorrelationID → SecurityHeaders → CORS → CSRF                    |
|                                                                    |
|  +--------------------+  +------------------+  +---------------+  |
|  |   auth/            |  |   groups/        |  |  expenses/    |  |
|  |   router.py        |  |   router.py      |  |  router.py    |  |
|  |   service.py       |  |   service.py     |  |  service.py   |  |
|  |   repository.py    |  |   repository.py  |  |  repository.py|  |
|  |   middleware.py    |  |   models.py      |  |  models.py    |  |
|  |   (get_current_    |  |   schemas.py     |  |  schemas.py   |  |
|  |    user dep)       |  +------------------+  +---------------+  |
|  +--------------------+                                            |
|                                                                    |
|  +--------------------+  +------------------+                     |
|  |  settlements/      |  |   balance/       |                     |
|  |  router.py         |  |   router.py      |                     |
|  |  service.py        |  |   service.py     |                     |
|  |  repository.py     |  |   [engine.py     |                     |
|  |  models.py         |  |    → Unit 2]     |                     |
|  |  schemas.py        |  |   schemas.py     |                     |
|  +--------------------+  +------------------+                     |
|                                                                    |
|  +------------------------------------------------------+         |
|  |  core/                                               |         |
|  |  config.py (Pydantic Settings)                       |         |
|  |  db.py (AsyncSession factory, connection pool)       |         |
|  |  logging.py (structlog JSON config)                  |         |
|  |  middleware.py (CorrelationID, SecurityHeaders, CSRF)|         |
|  |  errors.py (global_exception_handler)                |         |
|  +------------------------------------------------------+         |
+------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
  [AsyncSession]       [httpx AsyncClient]   [itsdangerous]
  SQLAlchemy pool      (OAuth2 provider       CSRF token
  SQLite / asyncpg      calls)                signing
         |
         v
  [Database]
  SQLite (dev) / PostgreSQL RDS (cloud)
```

---

## Infrastructure Logical View

```
Internet
  |
  v  (HTTPS 443)
[AWS WAF]
  |-- Rate limit: 100 req / 5-min per IP
  |-- Block common attack patterns (AWS managed rules)
  |
  v
[Application Load Balancer]  ← public subnet, 2 AZs
  |-- TLS termination (ACM certificate)
  |-- Access logs → S3 bucket (90-day retention)
  |-- Target group health check: GET /health every 30s
  |-- Listener rule: /openapi.json → only from VPC CIDR
  |
  v  (HTTP 8000, private subnet)
[ECS Fargate Tasks]  ← private subnet, ≥2 AZs
  |-- Auto-scaling: min 1, max 4 tasks; scale at 70% CPU
  |-- Task Role: Secrets Manager read, CloudWatch Logs write
  |-- awslogs driver → CloudWatch Log Group /ecs/expense-splitter-api
  |-- Env vars injected from Secrets Manager at task startup
  |
  +------ [Migration Task] (one-off, pre-deploy)
  |         runs: alembic upgrade head
  |         same image, same Task Role + DB access
  |
  v  (port 5432, private subnet)
[RDS PostgreSQL Multi-AZ]
  |-- Storage encrypted (AES-256, AWS managed key)
  |-- SSL required (force_ssl=1)
  |-- Private subnet only; no public endpoint
  |-- Security group: inbound from ECS SG only
  |
  v
[AWS Secrets Manager]
  |-- JWT_PRIVATE_KEY, DATABASE_URL, GOOGLE_CLIENT_SECRET,
      GITHUB_CLIENT_SECRET, CSRF_SECRET_KEY
  |-- ECS Task Role has GetSecretValue on specific ARNs only

[CloudWatch Logs]
  |-- Log group: /ecs/expense-splitter-api (90-day retention)
  |-- Alarms: auth failures > 10/5min, 403s > 20/5min,
              5xx rate > 1%/5min, CPU > 80%/10min
  |-- SNS topic → email/PagerDuty for alarm notifications

[Amazon ECR]
  |-- Private container registry
  |-- Image scanning on push
  |-- Images tagged with git SHA (no 'latest' in production)
```

---

## Dependency Injection Map

How FastAPI dependencies wire together per request:

```
Request arrives at protected route
  |
  Depends(get_db)                    → yields AsyncSession (request-scoped)
  Depends(get_current_user)
    Depends(oauth2_scheme)           → extracts JWT from session cookie
    Depends(get_db)                  → same AsyncSession (cached by FastAPI)
    → validates JWT, loads User      → returns User
  |
  Route handler receives:
    db: AsyncSession
    current_user: User
    payload: PydanticSchema          (validated by FastAPI automatically)
  |
  Calls service(db, current_user.id, payload)
    Calls repository(db, ...)
    Calls BalanceEngine.*(...)       (pure, no deps)
  |
  Returns response schema            (serialised by Pydantic)
```

---

## No-Cache Decision Record

**Decision**: No response caching for balance/settlement-suggestion endpoints (Q1=A).

**Rationale**:
- Groups are expected to have ≤50 members; balance computation is O(n) — fast enough without caching
- No-cache eliminates cache invalidation complexity and ensures data is always consistent with DB state
- ECS Fargate auto-scaling handles load increases without needing a cache tier
- Can add Redis caching as a future optimisation if load testing reveals a need

**Impact**: Every `GET /groups/{id}/balances` call executes two DB queries (expenses + settlements) and one in-process computation pass. Acceptable for the target scale.
