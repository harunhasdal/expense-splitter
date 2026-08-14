# Deployment Architecture — Unit 1: Backend API & Data Layer

---

## Full Deployment Diagram

```
eu-west-1
==========================================================================

PRODUCTION VPC (10.0.0.0/16)
+------------------------------------------------------------------------+
|                                                                        |
|  Public Subnets (10.0.0.0/24, 10.0.1.0/24)                           |
|  +------------------------------------------------------------------+  |
|  |  [WAF WebACL]                                                    |  |
|  |      |                                                           |  |
|  |  [ALB]  expense-splitter-prod-alb                               |  |
|  |      |  HTTPS:443  Access logs -> S3                            |  |
|  |      |  HTTP:80  -> redirect 443                                |  |
|  +-----|------------------------------------------------------------+  |
|        |                                                               |
|  Private Subnets (10.0.2.0/24, 10.0.3.0/24)                         |
|  +------------------------------------------------------------------+  |
|  |  [ECS Fargate Cluster] expense-splitter-prod                    |  |
|  |                                                                  |  |
|  |  Task: expense-splitter-api (AZ-a)   Task: expense-splitter-api |  |
|  |  +---------------------------+        +----------------------+   |  |
|  |  | FastAPI app               |        | FastAPI app          |   |  |
|  |  | Port 8000                 |        | Port 8000            |   |  |
|  |  | structlog -> CloudWatch   |        |                      |   |  |
|  |  +---------------------------+        +----------------------+   |  |
|  |                                                                  |  |
|  |  Task: expense-splitter-migrate (one-off, pre-deploy)           |  |
|  |  +----------------------------------------------------------+   |  |
|  |  | alembic upgrade head                                     |   |  |
|  |  +----------------------------------------------------------+   |  |
|  |                                                                  |  |
|  +-----|------------------------------------------------------------+  |
|        |                                                               |
|  +-----|------------------------------------------------------------+  |
|  |  [RDS PostgreSQL 16 Multi-AZ]                                   |  |
|  |  Primary (AZ-a)  <-->  Standby (AZ-b)                          |  |
|  |  db.t3.small  Encrypted  force_ssl=1                           |  |
|  +------------------------------------------------------------------+  |
|                                                                        |
|  [NAT Gateway AZ-a]  [NAT Gateway AZ-b]                              |
|     (ECS -> internet for OAuth2 provider calls)                       |
+------------------------------------------------------------------------+

SHARED SERVICES (eu-west-1)
+--------------------------------------------+
| [Secrets Manager]                          |
|   expense-splitter/prod/api                |
|   expense-splitter/staging/api             |
|                                            |
| [ECR] expense-splitter-api                 |
|   :abc123f  :def456a  ...                  |
|                                            |
| [CloudWatch Logs]                          |
|   /ecs/expense-splitter-api-prod (90d)     |
|   /ecs/expense-splitter-api-staging (14d)  |
|                                            |
| [S3] expense-splitter-alb-logs-prod        |
| [S3] expense-splitter-frontend-prod        |
|   ^-- Origin for CloudFront (OAI)          |
+--------------------------------------------+

GLOBAL (us-east-1 for CloudFront cert)
+--------------------------------------------+
| [CloudFront] expense-splitter-prod.cdn     |
|   Origin: S3 frontend bucket (OAI)        |
|   HTTPS only; SPA 404 -> index.html       |
|   Security headers response policy        |
+--------------------------------------------+

STAGING VPC (10.1.0.0/16) — same topology, smaller sizing, no Multi-AZ RDS
```

---

## CDK Stack Structure

### Stack 1: NetworkStack

**Deployed first** — outputs VPC ID and security group IDs consumed by ApplicationStack.

```typescript
// cdk/lib/network-stack.ts
export class NetworkStack extends Stack {
  readonly vpc: ec2.Vpc;
  readonly albSg: ec2.SecurityGroup;
  readonly ecsSg: ec2.SecurityGroup;
  readonly rdsSg: ec2.SecurityGroup;
}
```

Resources:
- `ec2.Vpc` — 2 public + 2 private subnets, 2 NAT gateways
- 3 `ec2.SecurityGroup` instances (alb-sg, ecs-sg, rds-sg) with rules as specified
- Stack exports via `CfnOutput` for cross-stack referencing

---

### Stack 2: ApplicationStack

**Deployed second** — imports VPC/SGs from NetworkStack. Contains all compute, DB, and monitoring.

```typescript
// cdk/lib/application-stack.ts
export class ApplicationStack extends Stack {
  // ECS Cluster + Service
  // ALB + Target Group + WAF
  // RDS Instance
  // Secrets Manager secrets (manual values — not auto-generated)
  // CloudWatch Log Groups + Alarms + SNS Topic
  // IAM Roles (ecsTaskExecutionRole, ecsTaskRole, GithubActionsRole)
  // S3 bucket for ALB logs
}
```

---

### Stack 3: FrontendStack

**Deployed independently** — no dependencies on ApplicationStack (can be deployed in parallel after NetworkStack, or separately).

```typescript
// cdk/lib/frontend-stack.ts
export class FrontendStack extends Stack {
  // S3 Bucket (frontend static files)
  // CloudFront OAI
  // CloudFront Distribution
  // CloudFront Response Headers Policy (security headers)
  // ACM Certificate (us-east-1 cross-region)
}
```

---

### CDK App Entry Point

```typescript
// cdk/bin/expense-splitter.ts
const app = new cdk.App();
const env = { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'eu-west-1' };
const envName = app.node.tryGetContext('env') ?? 'prod';  // cdk deploy -c env=staging

const network = new NetworkStack(app, `NetworkStack-${envName}`, { env, envName });
const application = new ApplicationStack(app, `ApplicationStack-${envName}`, {
  env, envName, vpc: network.vpc, albSg: network.albSg,
  ecsSg: network.ecsSg, rdsSg: network.rdsSg
});
new FrontendStack(app, `FrontendStack-${envName}`, { env, envName });
```

Deploy commands:
```bash
# Bootstrap (first time only)
cdk bootstrap aws://ACCOUNT/eu-west-1

# Deploy all stacks
cdk deploy --all -c env=prod

# Deploy individual stacks
cdk deploy NetworkStack-prod -c env=prod
cdk deploy ApplicationStack-prod -c env=prod
cdk deploy FrontendStack-prod -c env=prod
```

---

## CI/CD Pipeline (GitHub Actions)

### Workflow: `ci.yml` (on every push / PR)

```
Trigger: push to any branch, or PR to main

Jobs (parallel):
  backend-ci:
    1. Checkout code
    2. Setup Python + uv
    3. uv sync --frozen
    4. ruff check backend/
    5. mypy backend/ --strict
    6. pytest backend/tests/ --cov=backend --cov-fail-under=80
    7. pip-audit (vulnerability scan — SECURITY-10)

  frontend-ci:
    1. Checkout code
    2. Setup Node + pnpm
    3. pnpm install --frozen-lockfile
    4. pnpm run lint
    5. pnpm run type-check
    6. pnpm run test
    7. pnpm run build (verifies production build succeeds)
```

### Workflow: `deploy.yml` (on push to main only)

```
Trigger: push to main branch

Steps:
  1. backend-ci + frontend-ci (must pass)

  2. build-and-push:
     - docker build -t expense-splitter-api:${{ github.sha }} backend/
     - docker push ECR expense-splitter-api:${{ github.sha }}
     - Generate and commit openapi.json (for frontend type generation)

  3. deploy-staging:
     a. Run migration task (expense-splitter-migrate) in staging cluster
        → Wait for exit code 0; fail workflow on non-zero
     b. Update ECS service to new task definition revision (staging)
     c. Wait for service stability (aws ecs wait services-stable)
     d. Smoke test: curl https://staging-api.expensesplitter.example.com/health

  4. deploy-production (runs only if deploy-staging succeeds):
     a. Run migration task in production cluster
        → Wait for exit code 0; fail workflow on non-zero
     b. Update ECS service (rolling deploy — min healthy 100%)
     c. Wait for service stability
     d. Health check: curl https://api.expensesplitter.example.com/health

  5. deploy-frontend:
     - pnpm run build (frontend/)
     - aws s3 sync frontend/dist/ s3://expense-splitter-frontend-prod/ --delete
     - aws cloudfront create-invalidation --distribution-id $DIST_ID --paths "/*"
```

---

## Environment Parity

| Aspect | Local Dev | Staging | Production |
|---|---|---|---|
| Runtime | Docker Compose | ECS Fargate | ECS Fargate |
| Database | SQLite (aiosqlite) | RDS PostgreSQL (single-AZ) | RDS PostgreSQL (Multi-AZ) |
| Container image | local build | ECR (git SHA) | ECR (same SHA promoted) |
| Secrets | `.env` file (gitignored) | Secrets Manager | Secrets Manager |
| Migrations | `alembic upgrade head` in compose entrypoint | one-off ECS task | one-off ECS task |
| Frontend | Vite dev server (proxy to API) | S3 + CloudFront | S3 + CloudFront |

**Docker Compose local setup** (`docker-compose.yml`):
```
Services:
  db:       postgres:16-alpine
  api:      backend/ (hot-reload via uvicorn --reload)
  frontend: frontend/ (vite dev server, proxies /api -> api:8000)
```
