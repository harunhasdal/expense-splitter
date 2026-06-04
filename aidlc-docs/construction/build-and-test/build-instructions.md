# Build Instructions

## Prerequisites

- **Python**: 3.12 (managed by `.python-version`)
- **Node.js**: 20.x
- **pnpm**: 9.4.0
- **uv**: 0.2.33+ (Python package/env manager)
- **Docker + Docker Compose**: For local full-stack environment
- **AWS CDK CLI**: `npm install -g aws-cdk` (for infrastructure only)

### Required Environment Variables (Backend)

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL URL (e.g. `postgresql+asyncpg://...`) or SQLite for local dev |
| `JWT_PRIVATE_KEY` | RS256 private key (PEM) |
| `JWT_PUBLIC_KEY` | RS256 public key (PEM) |
| `JWT_EXPIRY_SECONDS` | Token TTL (e.g. `86400`) |
| `JWT_ISSUER` | Token issuer URL |
| `ALLOWED_ORIGINS` | CORS allowed origins (e.g. `http://localhost:5173`) |
| `GOOGLE_CLIENT_ID` | Google OAuth2 client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 client secret |
| `GITHUB_CLIENT_ID` | GitHub OAuth2 client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth2 client secret |
| `CSRF_SECRET_KEY` | ≥32-char secret for CSRF double-submit |
| `APP_BASE_URL` | Backend base URL (e.g. `http://localhost:8000`) |

---

## Build Steps

### Backend (Unit 1 + Unit 2)

#### 1. Install Python Dependencies

```bash
cd backend
uv sync --frozen
```

> `uv sync` creates a `.venv` and installs all pinned deps from `pyproject.toml`. The `--frozen` flag ensures exact reproducibility.

#### 2. Verify Installation

```bash
uv run python -c "import fastapi, sqlalchemy, hypothesis; print('OK')"
```

#### 3. Run Database Migrations (local PostgreSQL or SQLite)

For SQLite local dev:
```bash
cd backend
DATABASE_URL="sqlite+aiosqlite:///./dev.db" uv run alembic upgrade head
```

For PostgreSQL:
```bash
cd backend
uv run alembic upgrade head
```

#### 4. Start Backend (Development)

```bash
cd backend
uv run uvicorn main:app --reload --port 8000
```

**Expected output**: Uvicorn reports `Application startup complete.` Health check at `http://localhost:8000/health`.

---

### Frontend (Unit 3)

#### 1. Install Node Dependencies

```bash
cd frontend
pnpm install --frozen-lockfile
```

#### 2. TypeScript Check

```bash
cd frontend
pnpm run type-check
```

**Expected output**: No errors. Any TypeScript error is a build blocker.

#### 3. Build for Production

```bash
cd frontend
pnpm run build
```

**Expected output**: `dist/` directory created with bundled assets. Build output reports bundle sizes.

---

### Full Stack (Docker Compose)

```bash
# From workspace root
docker-compose up --build
```

- Backend API: `http://localhost:8000`
- Frontend (dev): `http://localhost:5173`
- PostgreSQL: `localhost:5432`

---

### Infrastructure (CDK — AWS Only)

```bash
cd cdk
npm install
npx cdk synth        # Verify CloudFormation templates
npx cdk diff         # Preview changes vs deployed stack
```

> Do NOT run `cdk deploy` without explicit deployment intent. See `deploy.yml` for the CI/CD deployment pipeline.

---

## Build Artifacts

| Artifact | Location | Description |
|---|---|---|
| Backend venv | `backend/.venv/` | Python virtual environment |
| Frontend bundle | `frontend/dist/` | Production static assets |
| CDK templates | `cdk/cdk.out/` | CloudFormation templates |
| Docker image | Local Docker daemon | `expense-splitter-api` image |

---

## Troubleshooting

### `uv sync` fails — Python version mismatch
**Cause**: System Python is not 3.12.  
**Solution**: Install Python 3.12 (e.g. via `pyenv`) or use `uv python install 3.12`.

### `pnpm install` fails — lockfile mismatch
**Cause**: `pnpm-lock.yaml` is out of sync.  
**Solution**: Run `pnpm install` (without `--frozen-lockfile`) to regenerate, then commit the updated lockfile.

### `alembic upgrade head` fails — no DATABASE_URL
**Cause**: `.env` not created or env var not exported.  
**Solution**: `cp backend/.env.example backend/.env` and fill in required values.

### `pnpm run build` fails — TypeScript errors
**Cause**: Type errors in `src/`.  
**Solution**: Run `pnpm run type-check` for detailed diagnostics.
