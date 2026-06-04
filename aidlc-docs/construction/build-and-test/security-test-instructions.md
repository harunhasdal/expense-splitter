# Security Test Instructions

Security Baseline extension is enabled (SECURITY-01 to SECURITY-15).

---

## 1. Dependency Vulnerability Scanning

### Backend (pip-audit)

```bash
cd backend
uv run pip-audit
```

**Expected**: No known CVEs. If vulnerabilities are found, update the affected package in `pyproject.toml` and re-lock.

### Frontend (pnpm audit)

```bash
cd frontend
pnpm audit --audit-level=moderate
```

**Expected**: 0 moderate/high/critical vulnerabilities.

---

## 2. Static Application Security Testing (SAST)

### Backend — ruff security rules (S-prefix)

Bandit-equivalent rules are enforced via ruff's `S` ruleset:

```bash
cd backend
uv run ruff check . --select S
```

**Expected**: No S-prefixed violations. Common checks include:
- `S105/S106` — hardcoded passwords
- `S108` — insecure temp file
- `S301/S302` — pickle/marshal usage
- `S501` — `ssl_verify=False`

---

## 3. Authentication and Authorization Tests

Run these manually against the running local stack (`docker-compose up`):

### 3.1 JWT Validation

```bash
# Invalid token → 401
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/groups \
  -H "Authorization: Bearer invalid.token.here"
# Expected: 401

# No token → 401
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/groups
# Expected: 401

# Expired token → 401 (create a token with exp in the past, if you have key material)
```

### 3.2 IDOR (Insecure Direct Object Reference)

```bash
# User B tries to access User A's group — expects 403
# (See integration-test-instructions.md Scenario 4 for full steps)
```

### 3.3 CSRF (Double-Submit Cookie)

```bash
# POST without X-CSRF-Token → 403
# (See integration-test-instructions.md Scenario 5 for full steps)
```

---

## 4. Security Headers Verification

```bash
curl -s -I http://localhost:8000/health | grep -i \
  -e "x-content-type" \
  -e "x-frame-options" \
  -e "strict-transport" \
  -e "content-security-policy" \
  -e "x-correlation-id"
```

**Expected headers** (from `SecurityHeadersMiddleware`):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-Correlation-ID: <uuid>` (every response)

HSTS (`Strict-Transport-Security`) will only appear in production (HTTPS). Verify via CloudFront headers in staging.

---

## 5. Input Validation Tests

### SQL Injection (parameterized queries)

All queries use SQLAlchemy ORM with parameterized statements. Verify via:

```bash
# Attempt SQL injection in group name
curl -s -X POST http://localhost:8000/groups \
  -H "Cookie: <jwt_cookie>" \
  -H "X-CSRF-Token: <csrf_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "\"; DROP TABLE groups; --"}' | jq .name
# Expected: name stored as literal string, no SQL error
```

### Currency Code Allowlist

```bash
# Invalid currency → 422
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8000/groups/$GROUP_ID/expenses \
  -H "Cookie: <jwt_cookie>" \
  -H "X-CSRF-Token: <csrf_token>" \
  -H "Content-Type: application/json" \
  -d '{"description":"X","total_amount":"10","currency":"XYZ","paid_by":"...","split_type":"EQUAL","split_details":[]}'
# Expected: 422
```

---

## 6. Error Response Sanitization

```bash
# Trigger a 404 — verify no stack trace in response
curl -s http://localhost:8000/groups/00000000-0000-0000-0000-000000000000 \
  -H "Cookie: <jwt_cookie>" | jq .
# Expected: {"detail": "Not found"} — no internal paths, no stack trace
```

---

## 7. CloudFront Security Headers (Staging/Prod)

After CDK deployment, verify the CloudFront security headers policy is applied:

```bash
curl -s -I https://<cloudfront-domain>/ | grep -i \
  -e "strict-transport-security" \
  -e "x-content-type" \
  -e "x-frame-options" \
  -e "content-security-policy"
```

The CDK `frontend-stack.ts` configures a managed security headers policy on the CloudFront distribution.
