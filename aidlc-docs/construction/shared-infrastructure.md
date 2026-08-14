# Shared Infrastructure — Expense Splitter

Resources shared across all units. All units reference these; no unit owns them exclusively.

---

## AWS Account & Region

| Setting | Value |
|---|---|
| Primary region | eu-west-1 (Ireland) |
| Environments | `prod`, `staging` |
| Account | Single AWS account (both environments) |

---

## ECR Repository

- **Name**: `expense-splitter-api`
- **Image tag convention**: git SHA (e.g. `abc123f`) — no `latest` in production
- **Scan on push**: enabled
- **Used by**: Unit 1 (API), Unit 2 (balance engine — same image), CI/CD pipeline

---

## Secrets Manager

| Secret | Used By |
|---|---|
| `expense-splitter/prod/api` | Unit 1 ECS task (all secret env vars) |
| `expense-splitter/staging/api` | Staging ECS task |

---

## Docker Compose (Local Dev)

`docker-compose.yml` at monorepo root. Used by all 3 units for local development.

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: expense_splitter
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    ports: ["5432:5432"]
    volumes: ["postgres_data:/var/lib/postgresql/data"]

  api:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: postgresql+asyncpg://dev:dev@db:5432/expense_splitter
      # ... other vars from .env file
    env_file: .env
    ports: ["8000:8000"]
    depends_on: [db]
    volumes: ["./backend:/app"]

  frontend:
    build: ./frontend
    command: pnpm run dev --host
    ports: ["5173:5173"]
    depends_on: [api]
    volumes: ["./frontend:/app", "/app/node_modules"]
```

A `.env.example` file at repo root documents all required environment variables (mirrors the 14-variable manifest from `tech-stack-decisions.md`).

---

## CDK Project

Location: `cdk/` at monorepo root.

```
cdk/
  bin/
    expense-splitter.ts     # app entry point
  lib/
    network-stack.ts        # VPC, security groups
    application-stack.ts    # ECS, RDS, ALB, WAF, CloudWatch
    frontend-stack.ts       # S3, CloudFront
  cdk.json
  package.json              # CDK v2 TypeScript
  tsconfig.json
```

---

## GitHub Actions Secrets Required

| Secret | Description |
|---|---|
| `AWS_ROLE_ARN` | GitHub Actions OIDC role ARN (role `GithubActionsRole`); the full ARN (incl. account ID) is stored only in the repo secret, never in these docs |
| `AWS_REGION` | `eu-west-1` |
| `ECR_REGISTRY` | ECR registry URL |
| `CLOUDFRONT_DISTRIBUTION_ID_PROD` | CloudFront distribution ID for cache invalidation |
| `CLOUDFRONT_DISTRIBUTION_ID_STAGING` | Staging CloudFront distribution |
| `ECS_CLUSTER_PROD` | `expense-splitter-prod` |
| `ECS_CLUSTER_STAGING` | `expense-splitter-staging` |
| `ECS_SERVICE_PROD` | `api` (production service name) |
| `ECS_SERVICE_STAGING` | `api` (staging service name) |
| `MIGRATION_TASK_DEFINITION` | Task definition family for migration task |
| `S3_FRONTEND_BUCKET_PROD` | `expense-splitter-frontend-prod` |

GitHub Actions uses OIDC (`aws-actions/configure-aws-credentials`) — no long-lived AWS keys stored as secrets.
