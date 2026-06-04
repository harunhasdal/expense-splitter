# Domain Entities — Unit 1: Backend API & Data Layer

All entities are SQLAlchemy async ORM models. Primary keys are UUIDs. Timestamps use UTC. Soft-delete is expressed via nullable `*_at` timestamp columns — no hard deletes anywhere.

---

## Entity: User

Represents an authenticated identity. Created or updated on every OAuth2 sign-in.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `email` | String(254) | NOT NULL, UNIQUE | Normalised to lowercase |
| `display_name` | String(100) | NOT NULL | From OAuth2 profile; user cannot edit |
| `avatar_url` | String(500) | nullable | From OAuth2 profile |
| `provider` | Enum(`google`,`github`) | NOT NULL | OAuth2 provider used at last sign-in |
| `provider_id` | String(100) | NOT NULL | Provider-specific user ID |
| `created_at` | DateTime(tz) | NOT NULL, default utcnow | |
| `last_sign_in_at` | DateTime(tz) | NOT NULL, default utcnow | Updated on every sign-in |

**Unique constraint**: `(provider, provider_id)` — prevents duplicate accounts across providers for the same email.

**Relationships**: one-to-many → `Member` (a user can be a member of many groups)

---

## Entity: Group

Represents an expense-sharing group.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `name` | String(100) | NOT NULL | 1–100 characters |
| `description` | String(500) | nullable | |
| `owner_id` | UUID | FK → User.id, NOT NULL | Creator; immutable after creation |
| `created_at` | DateTime(tz) | NOT NULL, default utcnow | |
| `archived_at` | DateTime(tz) | nullable | Non-null = archived |
| `archived_by` | UUID | FK → User.id, nullable | Must equal owner_id when set |
| `force_archived` | Boolean | NOT NULL, default False | True if archived despite non-zero balances |

**Relationships**:
- many-to-one → `User` (owner)
- one-to-many → `Member`
- one-to-many → `Expense`
- one-to-many → `Settlement`

---

## Entity: Member

Represents a person's participation in a group. Decoupled from `User` to support pending (not-yet-signed-up) invitees.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `group_id` | UUID | FK → Group.id, NOT NULL | |
| `user_id` | UUID | FK → User.id, nullable | Null = pending (not yet signed up) |
| `email` | String(254) | NOT NULL | Used for invite matching; persisted even after linking |
| `display_name` | String(100) | NOT NULL | Copied from User on link; "Former Member" after removal |
| `joined_at` | DateTime(tz) | NOT NULL, default utcnow | |
| `removed_at` | DateTime(tz) | nullable | Non-null = removed from group |
| `removed_by` | UUID | FK → User.id, nullable | |
| `is_pending` | Boolean | NOT NULL, default False | True until linked to a User account |

**Unique constraint**: `(group_id, email)` — one member entry per email per group.

**Relationships**:
- many-to-one → `Group`
- many-to-one → `User` (nullable)
- one-to-many → `ExpenseSplit` (as payer or split participant)
- one-to-many → `Settlement` (as payer or payee)

**Display rule**: once `removed_at` is set, `display_name` is overwritten to `"Former Member"` (FR-09, Q5=B).

---

## Entity: Expense

Represents an immutable expense event. No updates or hard deletes after creation.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `group_id` | UUID | FK → Group.id, NOT NULL | |
| `payer_id` | UUID | FK → Member.id, NOT NULL | Who paid |
| `description` | String(255) | NOT NULL | |
| `amount` | Numeric(12,4) | NOT NULL, > 0 | Stored in original currency |
| `currency` | String(3) | NOT NULL | ISO 4217 (e.g. "GBP", "JPY") |
| `expense_date` | Date | NOT NULL | Must not be in the future |
| `split_type` | Enum(`EQUAL`,`EXACT`,`PERCENTAGE`,`RATIO`) | NOT NULL | |
| `created_at` | DateTime(tz) | NOT NULL, default utcnow | |
| `created_by` | UUID | FK → User.id, NOT NULL | Authenticated user who submitted |
| `archived_at` | DateTime(tz) | nullable | Soft-delete only; group owner only |
| `archived_by` | UUID | FK → User.id, nullable | |

**Relationships**:
- many-to-one → `Group`
- many-to-one → `Member` (payer)
- one-to-many → `ExpenseSplit`

**Immutability rule**: after `INSERT`, no `UPDATE` is permitted on any field except `archived_at`/`archived_by`. Enforced at the service layer (405 returned for any other mutation attempt).

---

## Entity: ExpenseSplit

Stores one row per member per expense. Records both the raw input value and the computed monetary share.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `expense_id` | UUID | FK → Expense.id, NOT NULL | |
| `member_id` | UUID | FK → Member.id, NOT NULL | |
| `raw_value` | Numeric(12,4) | nullable | Null for EQUAL; the input percentage/ratio/exact amount |
| `computed_amount` | Numeric(12,4) | NOT NULL | Always the final monetary share |

**Unique constraint**: `(expense_id, member_id)`

**Invariant**: `SUM(computed_amount) WHERE expense_id = X` = `Expense.amount` (enforced by `BalanceEngine.compute_shares` before insert).

---

## Entity: Settlement

Represents an immutable payment event between two members. No updates or hard deletes.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default uuid4 | |
| `group_id` | UUID | FK → Group.id, NOT NULL | |
| `payer_id` | UUID | FK → Member.id, NOT NULL | Who made the payment |
| `payee_id` | UUID | FK → Member.id, NOT NULL | Who received the payment |
| `amount` | Numeric(12,4) | NOT NULL, > 0 | |
| `currency` | String(3) | NOT NULL | ISO 4217 |
| `recorded_at` | DateTime(tz) | NOT NULL, default utcnow | |
| `recorded_by` | UUID | FK → User.id, NOT NULL | |

**Constraint**: `payer_id != payee_id`

**Immutability rule**: same as Expense — no updates after insert.

---

## Entity Relationship Summary

```
User ──< Member >── Group
                |
                +──< Expense >── ExpenseSplit
                |
                +──< Settlement
```

- `User` 1:N `Member` (a user participates in many groups)
- `Group` 1:N `Member` (a group has many members)
- `Group` 1:N `Expense`
- `Expense` 1:N `ExpenseSplit`
- `Group` 1:N `Settlement`
- `Member` appears as payer in `Expense` and as payer/payee in `Settlement`
