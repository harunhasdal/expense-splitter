# Business Rules — Unit 1: Backend API & Data Layer

Rules are grouped by domain. Each rule has an ID for traceability to stories and security rules.

---

## Authentication Rules (BR-AUTH)

### BR-AUTH-01: JWT in HttpOnly Cookie
JWT access tokens MUST be issued as `HttpOnly`, `Secure`, `SameSite=Lax` cookies. JavaScript in the SPA MUST NOT have access to the raw token value. (SECURITY-12)

### BR-AUTH-02: JWT Claims
Every JWT MUST contain: `sub` (User.id), `email`, `exp` (expiry timestamp), `iat` (issued-at), `iss` (app issuer string). Tokens expire after a configurable duration (default 24 hours via `JWT_EXPIRY_SECONDS` env var).

### BR-AUTH-03: OAuth2 State Validation
The `state` parameter in the OAuth2 callback MUST be validated against a short-lived server-side value (stored in a signed cookie). Mismatched or missing state → 400 Bad Request, event logged. (SECURITY-08)

### BR-AUTH-04: Automatic Pending-Member Linking
When a new user signs in for the first time (no existing `User` record for their email), the auth service MUST:
1. Create the `User` record.
2. Find all `Member` rows where `email = user.email AND is_pending = True`.
3. For each: set `user_id = user.id`, `is_pending = False`, `display_name = user.display_name`.
This happens silently with no user prompt required (Q2=C).

### BR-AUTH-05: Session Invalidation on Logout
On logout, the server MUST clear the JWT cookie by issuing a `Set-Cookie` header with `Max-Age=0`. Token blacklisting is not required (short expiry + cookie deletion is sufficient for this app's risk profile).

---

## Group Rules (BR-GRP)

### BR-GRP-01: Group Name Length
Group name MUST be 1–100 characters (non-empty after trim). (SECURITY-05)

### BR-GRP-02: Group Owner Immutability
`Group.owner_id` MUST NOT be changed after creation. There is no ownership transfer feature in v1.

### BR-GRP-03: Archive — Zero Balance Requirement
A group MUST NOT be archived unless all member net balances are zero for ALL currencies, UNLESS `force=true` is passed by the owner (Q3=B).

### BR-GRP-04: Force Archive
When `force=true` is passed and balances are non-zero, the archive proceeds AND:
- `Group.force_archived` is set to `True`
- An audit log entry is written: `"Group force-archived by owner despite non-zero balances"` with the balance snapshot at time of archiving. (SECURITY-13)

### BR-GRP-05: Sole Owner Cannot Self-Remove
If the owner attempts to remove themselves as a member AND they are the only owner, the operation MUST be rejected with 409. There is no ownership transfer in v1.

---

## Member Rules (BR-MBR)

### BR-MBR-01: Member Email Uniqueness per Group
Each email address MUST appear at most once per group (pending or active). Duplicate email → 409 Conflict.

### BR-MBR-02: Remove Guard — Non-Zero Balance
A member MUST NOT be removed if their net balance in the group is non-zero for any currency. Check runs across all active (non-archived) expenses and settlements.

### BR-MBR-03: Remove — Display Name Replacement
On removal (`removed_at` set), `Member.display_name` MUST be overwritten to `"Former Member"`. This affects all historic expense display for that member. (Q5=B)

### BR-MBR-04: Member Authorization Scope
Only group members (active, non-removed) are authorised to read group data. Removed members lose access immediately upon removal.

### BR-MBR-05: Only Owner Can Add/Remove Members
Adding or removing members requires the requesting user to be the group owner. Group Members cannot manage membership. (SECURITY-08)

---

## Expense Rules (BR-EXP)

### BR-EXP-01: Expense Date Constraint
`expense_date` MUST NOT be a future date (greater than today UTC). (SECURITY-05)

### BR-EXP-02: Expense Amount Positive
`amount` MUST be > 0.

### BR-EXP-03: Currency Format
`currency` MUST be a valid ISO 4217 3-letter code (validated against a static allowlist). (SECURITY-05)

### BR-EXP-04: Split Validation Delegation
Before persisting, `BalanceEngine.validate_split()` MUST be called with the split type, total amount, member IDs, and split details. If validation fails, return 400 with the engine's error messages. No partial writes.

### BR-EXP-05: Atomic Expense + Split Insert
`Expense` and all `ExpenseSplit` rows for that expense MUST be inserted in a single database transaction. Partial inserts are not permitted.

### BR-EXP-06: Expense Immutability
After creation, the only permitted mutation on an `Expense` is setting `archived_at` and `archived_by` (soft-archive). Any attempt to update other fields → 405 Method Not Allowed. (FR-09, SECURITY-13)

### BR-EXP-07: Archive — Owner Only
Only the group owner may soft-archive an expense. Group Members → 403 Forbidden. (SECURITY-08)

### BR-EXP-08: Payer Must Be Active Member
The `payer_id` in an expense MUST refer to an active (non-removed) member of the group.

### BR-EXP-09: Split Members Must Be Active Members
All `member_id` values in the split detail MUST refer to active members of the group.

### BR-EXP-10: Pagination
`GET /groups/{id}/expenses` supports `page` (default 1) and `page_size` (default 20, max 100) query parameters. (Q4=B)

### BR-EXP-11: Archived Excluded by Default
Archived expenses are excluded from `GET /groups/{id}/expenses` unless `include_archived=true` is passed.

---

## Settlement Rules (BR-STL)

### BR-STL-01: Settlement Amount Positive
`amount` MUST be > 0. Zero-amount settlements → 400.

### BR-STL-02: Payer ≠ Payee
`payer_id` MUST NOT equal `payee_id`. Self-settlements → 400.

### BR-STL-03: Both Parties Must Be Active Members
Both `payer_id` and `payee_id` MUST be active (non-removed) members of the group.

### BR-STL-04: Settlement Immutability
No updates or deletes after creation. (FR-09, SECURITY-13)

### BR-STL-05: Over-Payment Permitted
A settlement amount may exceed the current outstanding debt. The balance engine accepts any positive amount and computes net balances accordingly.

---

## Authorization Rules (BR-AUTHZ)

### BR-AUTHZ-01: Deny by Default
All routes require authentication via `AuthMiddleware` (`get_current_user` dependency) EXCEPT:
- `GET /health`
- `GET /auth/{provider}/login`
- `GET /auth/{provider}/callback`

### BR-AUTHZ-02: Group Membership Check
For every group-scoped operation, the service layer MUST verify the requesting user is an active member of that group before any data access or mutation. Non-members → 403. (SECURITY-08)

### BR-AUTHZ-03: Owner-Only Operations
Group archive, forced archive, member add/remove, and expense archive require `requesting_user.id == group.owner_id`. Non-owners → 403. (SECURITY-08)

### BR-AUTHZ-04: No Resource Enumeration
`GET /groups` only returns groups the authenticated user is a member of. Requesting a group ID the user does not belong to → 404 (not 403) to prevent group enumeration.

---

## Input Validation Rules (BR-VAL)

### BR-VAL-01: Request Body Size Limit
Maximum request body size: 1 MB. Configured at the FastAPI/uvicorn level. (SECURITY-05)

### BR-VAL-02: String Field Max Lengths
All string fields MUST have explicit max-length validation in Pydantic schemas matching the ORM column constraints.

### BR-VAL-03: No Raw SQL Concatenation
All database queries MUST use SQLAlchemy parameterised expressions. String concatenation into queries is prohibited. (SECURITY-05)

### BR-VAL-04: Email Format Validation
Email fields (in member invite payloads) MUST be validated against RFC 5322 format using Pydantic's `EmailStr`. (SECURITY-05)

---

## Error Handling Rules (BR-ERR)

### BR-ERR-01: Generic Client Error Messages
API error responses to clients MUST contain only a generic message and an error code. Stack traces, SQL errors, file paths, and internal service details MUST NOT appear in responses. (SECURITY-09, SECURITY-15)

### BR-ERR-02: Detailed Server-Side Logging
Full exception details (type, message, stack trace, request ID) MUST be logged server-side at ERROR level with a correlation ID. (SECURITY-03)

### BR-ERR-03: Global Exception Handler
A single `global_exception_handler` MUST catch all unhandled exceptions and return a 500 response with a generic message. No unhandled exceptions may propagate to the ASGI layer. (SECURITY-15)

### BR-ERR-04: Fail Closed on Auth Errors
If JWT validation fails for any reason (malformed, expired, wrong issuer, wrong audience), the handler MUST return 401 and deny access. No fallback to anonymous access. (SECURITY-08, SECURITY-15)

---

## PBT Compliance Note

Unit 1 contains primarily CRUD and orchestration logic. Testable properties are minimal:
- `BR-EXP-05` atomic insert: idempotency under retry (PBT-04 — advisory under partial enforcement)
- Split validation delegation is stateless — covered by Unit 2's PBT suite

**PBT-01 for Unit 1**: N/A — no pure algorithmic functions with identifiable PBT properties. All computation delegated to Unit 2.
