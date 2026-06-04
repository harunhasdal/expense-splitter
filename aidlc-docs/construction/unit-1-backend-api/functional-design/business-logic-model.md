# Business Logic Model — Unit 1: Backend API & Data Layer

Detailed workflows for all 9 stories assigned to Unit 1. Each workflow shows the step-by-step logic inside the service layer (not HTTP routing).

---

## WF-1: OAuth2 Sign-In (US-1-1)

**Trigger**: User completes OAuth2 flow; callback arrives at `GET /auth/{provider}/callback`

```
1. Validate state parameter against signed cookie value
   → FAIL: log event, return 400 (BR-AUTH-03)

2. Exchange authorization code for provider access token (httpx POST to token endpoint)
   → FAIL: return 400 "Sign-in failed"

3. Fetch user profile from provider (email, display_name, avatar_url, provider_id)
   → FAIL: return 400 "Sign-in failed"

4. Normalise email to lowercase

5. UserRepository.upsert_oauth_user(profile):
   a. Look up existing User by (provider, provider_id)
   b. IF found: update display_name, avatar_url, last_sign_in_at → return existing User
   c. IF not found by provider: look up by email
      - IF email match: link new provider to existing account, update fields → return User
      - IF no match: INSERT new User record → return new User

6. IF new User (created_at == last_sign_in_at):
   Pending-member linking (BR-AUTH-04):
   a. SELECT all Member rows WHERE email = user.email AND is_pending = True
   b. FOR each: UPDATE user_id = user.id, is_pending = False, display_name = user.display_name

7. Sign JWT: {sub: user.id, email, exp: now+JWT_EXPIRY_SECONDS, iat: now, iss: APP_ISSUER}

8. Set HttpOnly, Secure, SameSite=Lax cookie with JWT (BR-AUTH-01)

9. Redirect to /dashboard (or originally requested URL stored in state)
```

---

## WF-2: Create Group (US-1-2)

**Trigger**: `POST /groups` — authenticated user

```
1. Validate payload (BR-GRP-01: name 1–100 chars, optional description ≤500)

2. BEGIN transaction:
   a. INSERT Group(name, description, owner_id=current_user.id)
   b. INSERT Member(group_id, user_id=current_user.id, email=current_user.email,
                    display_name=current_user.display_name, is_pending=False)
3. COMMIT

4. Return 201 with Group + initial member list
```

---

## WF-3: Add Member (US-1-3)

**Trigger**: `POST /groups/{id}/members` — must be group owner

```
1. Verify requesting user is group owner (BR-AUTHZ-03) → else 403

2. Validate email (BR-VAL-04: valid email format)

3. Check for duplicate (BR-MBR-01): SELECT Member WHERE group_id=X AND email=Y
   → EXISTS: return 409 "User is already a member of this group"

4. Look up User by email:
   a. IF User found:
      INSERT Member(group_id, user_id=user.id, email, display_name=user.display_name,
                    is_pending=False)
   b. IF no User found:
      INSERT Member(group_id, user_id=NULL, email, display_name=email_local_part,
                    is_pending=True)

5. Return 201 with Member record
```

---

## WF-4: Remove Member (US-1-4)

**Trigger**: `DELETE /groups/{id}/members/{memberId}` — must be group owner

```
1. Verify requesting user is group owner (BR-AUTHZ-03) → else 403

2. Load Member by memberId; verify it belongs to group_id → else 404

3. Sole-owner guard (BR-GRP-05):
   IF member.user_id == group.owner_id → return 409 "Cannot remove sole group owner"

4. Balance guard (BR-MBR-02):
   Call BalanceService.get_balances(group_id)
   IF member has non-zero balance in any currency → return 409 "Member has unsettled balance"

5. BEGIN transaction:
   a. UPDATE Member SET removed_at=now(), removed_by=current_user.id,
                        display_name="Former Member"   (BR-MBR-03)
6. COMMIT

7. Return 200
```

---

## WF-5: Archive Group (US-1-5)

**Trigger**: `PATCH /groups/{id}` with `{"archived": true}` or `{"archived": true, "force": true}`

```
1. Verify requesting user is group owner (BR-AUTHZ-03) → else 403

2. Calculate current balances via BalanceService.get_balances(group_id)

3. IF any member has non-zero balance in any currency:
   a. IF force=false (default): return 409 "Group has unsettled balances" (BR-GRP-03)
   b. IF force=true:
      - Set force_archived=True
      - Write audit log entry with balance snapshot (BR-GRP-04, SECURITY-13)

4. BEGIN transaction:
   UPDATE Group SET archived_at=now(), archived_by=current_user.id,
                    force_archived=<determined above>
5. COMMIT

6. Return 200 with updated Group
```

---

## WF-6: Log Expense (US-1-6)

**Trigger**: `POST /groups/{id}/expenses` — any active group member

```
1. Verify requesting user is active member of group (BR-AUTHZ-02) → else 403

2. Validate payload fields (BR-EXP-01 to BR-EXP-03, BR-EXP-08, BR-EXP-09):
   - expense_date ≤ today UTC
   - amount > 0
   - currency in ISO 4217 allowlist
   - payer_id is active member
   - all split member_ids are active members

3. Call BalanceEngine.validate_split(split_type, amount, member_ids, split_details)
   → FAIL: return 400 with validation errors (BR-EXP-04)

4. Call BalanceEngine.compute_shares(split_type, amount, member_ids, split_details)
   → returns list[MemberShare] with computed_amount per member

5. BEGIN transaction: (BR-EXP-05)
   a. INSERT Expense(group_id, payer_id, description, amount, currency,
                     expense_date, split_type, created_by=current_user.id)
   b. FOR each share: INSERT ExpenseSplit(expense_id, member_id, raw_value, computed_amount)
6. COMMIT

7. Return 201 with Expense + splits
```

---

## WF-7: Record Settlement (US-1-7)

**Trigger**: `POST /groups/{id}/settlements` — any active group member

```
1. Verify requesting user is active member of group (BR-AUTHZ-02) → else 403

2. Validate payload (BR-STL-01 to BR-STL-03):
   - amount > 0
   - payer_id ≠ payee_id
   - both payer_id and payee_id are active members

3. INSERT Settlement(group_id, payer_id, payee_id, amount, currency,
                     recorded_by=current_user.id)

4. Return 201 with Settlement
```

---

## WF-8: List Expenses (US-1-8)

**Trigger**: `GET /groups/{id}/expenses` — any active group member

```
1. Verify requesting user is active member of group (BR-AUTHZ-02) → else 403

2. Parse and validate query parameters (BR-EXP-10):
   - page: int ≥ 1, default 1
   - page_size: int 1–100, default 20
   - payer_id: optional UUID filter
   - include_archived: bool, default False

3. Execute paginated query via ExpenseRepository.list_for_group(
       group_id, filters, pagination
   )
   - WHERE archived_at IS NULL unless include_archived=True (BR-EXP-11)
   - ORDER BY expense_date DESC, created_at DESC

4. Return 200 with Page{items: [Expense+splits], total, page, page_size}
```

---

## WF-9: Expense Immutability Enforcement (US-2-7 — enforced by Unit 1)

**PUT / DELETE on expense endpoint**

```
PUT /groups/{id}/expenses/{expenseId}:
  → Return 405 Method Not Allowed (BR-EXP-06)
  → Log: "Expense update attempt blocked — immutability rule" (SECURITY-13)

DELETE /groups/{id}/expenses/{expenseId}:
  → Return 405 Method Not Allowed (BR-EXP-06)
  → Log: "Expense delete attempt blocked — immutability rule" (SECURITY-13)

PATCH /groups/{id}/expenses/{expenseId} with {archived: true}:
  → Allowed only for group owner (BR-EXP-07) — proceeds to WF-6-archive sub-flow
```

**Archive sub-flow**:
```
1. Verify requesting user is group owner → else 403
2. Load Expense; verify it belongs to group_id → else 404
3. IF already archived: return 409 "Expense already archived"
4. UPDATE Expense SET archived_at=now(), archived_by=current_user.id
5. Write audit log: actor, timestamp, expense_id, action="archived" (SECURITY-13)
6. Return 200 with updated Expense
```

---

## Cross-Workflow Concerns

### Correlation ID
Every request MUST be assigned a unique correlation ID (UUID) at middleware entry. The ID is added to the structured log context for all log entries during that request, and returned in the response header `X-Correlation-Id`. (SECURITY-03)

### Audit Log Writes
All state-changing operations (create, archive, remove) write a structured log entry at INFO level containing: `correlation_id`, `actor_id`, `action`, `resource_type`, `resource_id`, `timestamp`. No PII beyond `actor_id` (a UUID) in log output. (SECURITY-03, SECURITY-13)

### Transaction Failure Handling
On database transaction failure (constraint violation, deadlock, timeout), the service MUST:
1. Roll back the transaction
2. Log the error with correlation ID (full exception server-side)
3. Return a generic 500 or 409 response with no internal details (BR-ERR-01, SECURITY-09)
