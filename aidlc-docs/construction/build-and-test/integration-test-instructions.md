# Integration Test Instructions

## Purpose

Verify that Unit 1 (Backend API), Unit 2 (Balance Engine), and Unit 3 (Frontend SPA) work correctly together as a system. These tests target cross-unit interactions that cannot be validated by per-unit tests alone.

---

## Prerequisites

Start the full stack:

```bash
# From workspace root
cp .env.example .env   # fill in OAuth2 credentials + JWT keys
docker-compose up --build -d
```

Wait for services to be ready:

```bash
# Backend health check
curl -s http://localhost:8000/health | jq .status
# Expected: "ok"

# Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
# Expected: 200
```

---

## Integration Test Scenarios

### Scenario 1: Auth → Group → Expense → Balance (Full Happy Path)

**Description**: End-to-end user journey covering all three units in sequence.

**Actors**: User A (group creator), User B (group member)

**Steps**:

1. **Auth (Unit 1 → Unit 3 integration)**
   - Navigate to `http://localhost:5173`
   - Click "Sign in with Google" or "Sign in with GitHub"
   - Complete OAuth2 flow — expect redirect back to `/dashboard`
   - Verify JWT cookie is set (`httpOnly`, `sameSite=Lax`, `secure` in prod)

2. **Create Group**
   ```bash
   curl -s -X POST http://localhost:8000/groups \
     -H "Cookie: <jwt_cookie>" \
     -H "X-CSRF-Token: <csrf_token>" \
     -H "Content-Type: application/json" \
     -d '{"name": "Integration Test Group"}' | jq .id
   # Record GROUP_ID
   ```

3. **Add Member**
   ```bash
   curl -s -X POST http://localhost:8000/groups/$GROUP_ID/members \
     -H "Cookie: <jwt_cookie>" \
     -H "X-CSRF-Token: <csrf_token>" \
     -H "Content-Type: application/json" \
     -d '{"email": "member@example.com"}'
   ```

4. **Create Expense (Equal Split)**
   ```bash
   curl -s -X POST http://localhost:8000/groups/$GROUP_ID/expenses \
     -H "Cookie: <jwt_cookie>" \
     -H "X-CSRF-Token: <csrf_token>" \
     -H "Content-Type: application/json" \
     -d '{
       "description": "Dinner",
       "total_amount": "60.00",
       "currency": "USD",
       "paid_by": "<user_a_id>",
       "split_type": "EQUAL",
       "split_details": []
     }' | jq .id
   ```

5. **Verify Balance Calculation (Unit 1 + Unit 2)**
   ```bash
   curl -s http://localhost:8000/groups/$GROUP_ID/balances \
     -H "Cookie: <jwt_cookie>" | jq .
   # Expected: USD balances showing user_a_id = +30.00, member_id = -30.00
   ```

6. **Verify Settlement Suggestions (Unit 2)**
   ```bash
   curl -s http://localhost:8000/groups/$GROUP_ID/settlements/suggestions \
     -H "Cookie: <jwt_cookie>" | jq .
   # Expected: 1 suggestion: member_id pays user_a_id USD 30.00
   ```

7. **Record Settlement**
   ```bash
   curl -s -X POST http://localhost:8000/groups/$GROUP_ID/settlements \
     -H "Cookie: <jwt_cookie>" \
     -H "X-CSRF-Token: <csrf_token>" \
     -H "Content-Type: application/json" \
     -d '{"payer_id": "<member_id>", "payee_id": "<user_a_id>", "amount": "30.00", "currency": "USD"}'
   ```

8. **Verify Balances Clear After Settlement**
   ```bash
   curl -s http://localhost:8000/groups/$GROUP_ID/balances \
     -H "Cookie: <jwt_cookie>" | jq .
   # Expected: all balances = 0.00
   ```

**Expected Result**: All 8 steps complete without errors. Final balance is zero.

---

### Scenario 2: Balance Engine — Multi-Currency Isolation

**Description**: Verifies that expenses in different currencies produce separate balance buckets and do not cross-contaminate.

**Steps**:
1. Create group with 3 members
2. Add expense of USD 90.00 (equal split, 3 members)
3. Add expense of EUR 60.00 (equal split, 3 members)
4. GET `/groups/{id}/balances`

**Expected Result**:
```json
{
  "USD": [
    {"member_id": "...", "net_balance": "60.00"},
    {"member_id": "...", "net_balance": "-30.00"},
    {"member_id": "...", "net_balance": "-30.00"}
  ],
  "EUR": [
    {"member_id": "...", "net_balance": "40.00"},
    {"member_id": "...", "net_balance": "-20.00"},
    {"member_id": "...", "net_balance": "-20.00"}
  ]
}
```
USD and EUR balances are completely independent.

---

### Scenario 3: Expense Immutability (Units 1 + 3)

**Description**: Verifies that the frontend never presents edit/delete for expenses, and the backend enforces 405 on those methods.

**Steps**:
1. Create an expense
2. Attempt PUT:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" -X PUT \
     http://localhost:8000/groups/$GROUP_ID/expenses/$EXPENSE_ID \
     -H "Cookie: <jwt_cookie>"
   # Expected: 405
   ```
3. Attempt DELETE:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" -X DELETE \
     http://localhost:8000/groups/$GROUP_ID/expenses/$EXPENSE_ID \
     -H "Cookie: <jwt_cookie>"
   # Expected: 405
   ```
4. In the frontend expense list, verify no "Edit" or "Delete" buttons appear — only "Archive".

**Expected Result**: 405 from API; no mutation buttons in UI.

---

### Scenario 4: IDOR Prevention (Unit 1 Security)

**Description**: Verifies that a user cannot access another user's groups.

**Steps**:
1. User A creates group — record `GROUP_ID`
2. Authenticate as User B (different account)
3. Attempt GET `/groups/{GROUP_ID}` as User B

**Expected Result**: 403 Forbidden. User B cannot read User A's group.

---

### Scenario 5: Frontend → Backend CSRF Protection

**Description**: Verifies that state-mutating requests without a CSRF token are rejected.

**Steps**:
```bash
# Attempt POST without X-CSRF-Token header
curl -s -o /dev/null -w "%{http_code}" -X POST \
  http://localhost:8000/groups \
  -H "Cookie: <jwt_cookie>" \
  -H "Content-Type: application/json" \
  -d '{"name": "No CSRF"}'
# Expected: 403
```

**Expected Result**: 403 Forbidden. The double-submit CSRF middleware blocks the request.

---

## Cleanup

```bash
docker-compose down -v   # Stop services and remove volumes (clears test data)
```

---

## CI Integration Test (GitHub Actions)

The existing `ci.yml` runs backend unit+integration tests in-memory (no Docker required for the per-unit test suites). Full-stack integration scenarios above are designed for local validation or a dedicated staging pipeline.

To run the backend tests as CI does:
```bash
cd backend
DATABASE_URL="sqlite+aiosqlite:///:memory:" \
JWT_PRIVATE_KEY="test" JWT_PUBLIC_KEY="test" \
JWT_EXPIRY_SECONDS=86400 JWT_ISSUER="http://localhost" \
ALLOWED_ORIGINS="http://localhost:5173" \
GOOGLE_CLIENT_ID=test GOOGLE_CLIENT_SECRET=test \
GITHUB_CLIENT_ID=test GITHUB_CLIENT_SECRET=test \
CSRF_SECRET_KEY="test-secret-key-minimum-32-chars!!" \
APP_BASE_URL="http://localhost:8000" \
uv run pytest tests/ --cov=. --cov-fail-under=80
```
