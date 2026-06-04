# Code Summary — Unit 1: Backend API & Data Layer

All files created in `backend/` (workspace root). No files in `aidlc-docs/`.

## Project Configuration
- `backend/pyproject.toml` — all pinned dependencies; pytest, mypy, ruff config
- `backend/.python-version` — Python 3.12
- `backend/.env.example` — 14 env vars with documentation
- `backend/Dockerfile` — multi-stage build (builder + python:3.12-slim runtime)
- `backend/.dockerignore`

## Core Infrastructure (`backend/core/`)
- `config.py` — Pydantic Settings; all 14 env vars typed
- `db.py` — async SQLAlchemy engine; `get_db` dependency; pool_size=2, max_overflow=8
- `logging.py` — structlog JSON config; sensitive field filter
- `middleware.py` — CorrelationIDMiddleware, SecurityHeadersMiddleware, CSRFMiddleware (double-submit)
- `errors.py` — global_exception_handler; typed routing for DB/HTTP/unhandled errors
- `main.py` — FastAPI app factory; all routers + middleware registered; health endpoint

## Auth Domain (`backend/auth/`)
- `models.py` — User ORM model (uuid PK, provider enum, unique constraint)
- `schemas.py` — UserResponse Pydantic schema
- `repository.py` — get_by_id, get_by_email, upsert_oauth_user (returns is_new flag)
- `service.py` — OAuth2 flow (Google+GitHub), JWT RS256 issue/validate, state signing, pending-member linking
- `middleware.py` — get_current_user FastAPI dependency; fail-closed JWT validation
- `router.py` — GET /auth/{provider}/login, GET /auth/{provider}/callback, POST /auth/logout

## Groups Domain (`backend/groups/`)
- `models.py` — Group (archived_at, force_archived), Member (is_pending, removed_at, display_name)
- `schemas.py` — GroupCreate, GroupUpdate (archived + force flags), GroupResponse, MemberResponse, AddMemberRequest
- `repository.py` — full GroupRepository + MemberRepository; link_pending_members
- `service.py` — create_group, get_group, list_groups, archive_group (force support), add_member, remove_member
- `router.py` — all group + member endpoints

## Expenses Domain (`backend/expenses/`)
- `models.py` — Expense (immutable after creation), ExpenseSplit (computed_amount)
- `schemas.py` — ExpenseCreate (with split_details), ExpenseResponse, ExpensePage; ISO 4217 currency allowlist
- `repository.py` — create (atomic), list_for_group (paginated), archive, get_all_for_balance
- `service.py` — create_expense (delegates to BalanceEngine), list_expenses, archive_expense (with audit log)
- `router.py` — expense endpoints; PUT/DELETE return 405 (immutability enforcement)

## Settlements Domain (`backend/settlements/`)
- `models.py` — Settlement (check constraints: payer≠payee, amount>0)
- `schemas.py` — SettlementCreate (validates payer≠payee), SettlementResponse
- `repository.py` — create, list_for_group, get_all_for_balance
- `service.py` — create_settlement, list_settlements
- `router.py` — settlement endpoints

## Balance (Stub for Unit 2) (`backend/balance/`)
- `schemas.py` — MemberBalance, SettlementSuggestion, CurrencyBalances, CurrencySettlements
- `service.py` — get_raw_balances (loads data; stub until Unit 2 engine wired)
- `router.py` — GET /groups/{id}/balances, GET /groups/{id}/settlements/suggestions (501 stubs)

## Migrations (`backend/migrations/`)
- `alembic.ini` — DATABASE_URL from env var
- `env.py` — async SQLAlchemy engine; all models imported for autogenerate

## Tests (`backend/tests/`)
- `conftest.py` — in-memory SQLite test DB; auth_client fixture; dependency overrides
- `integration/test_groups.py` — create, list, IDOR, add/remove member, archive
- `integration/test_expenses.py` — EQUAL split, future date, 405 on PUT/DELETE, pagination, non-member blocked
- `integration/test_settlements.py` — create, zero-amount, self-settlement, non-member, list

## Deployment Artifacts
- `docker-compose.yml` — postgres:16-alpine, api (hot-reload), frontend placeholder
- `.env.example` — full 14-var manifest at repo root
- `.github/workflows/ci.yml` — backend-ci (ruff, mypy, pytest, pip-audit) + frontend-ci
- `.github/workflows/deploy.yml` — build→staging migration→staging deploy→prod migration→prod deploy→frontend S3
- `cdk/bin/expense-splitter.ts` — CDK app entry point
- `cdk/lib/network-stack.ts` — VPC, 3 security groups
- `cdk/lib/application-stack.ts` — ECS cluster, RDS, ALB, CloudWatch log group
- `cdk/lib/frontend-stack.ts` — S3 bucket, CloudFront distribution, security headers policy

## Stories Implemented
- US-1-1 OAuth2 Sign-In (auth domain)
- US-1-2 Create Group
- US-1-3 Add Members
- US-1-4 Remove Member
- US-1-5 Archive Group
- US-1-6 Log Expense
- US-1-7 Record Settlement
- US-1-8 View Group Expenses (paginated list)
- US-2-7 Expense Immutability (405 on PUT/DELETE)
