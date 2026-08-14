# Infrastructure Design — Unit 1: Backend API & Data Layer

**Region**: eu-west-1 (Ireland)  
**Environments**: Production + Staging (separate VPCs, same account)  
**CDK organisation**: 3 stacks — NetworkStack, ApplicationStack, FrontendStack

---

## Service Specifications

### VPC (NetworkStack)

| Attribute | Production | Staging |
|---|---|---|
| CIDR | 10.0.0.0/16 | 10.1.0.0/16 |
| Public subnets | 2 × /24 (AZ-a, AZ-b) — ALB only | 2 × /24 |
| Private subnets | 2 × /24 (AZ-a, AZ-b) — ECS + RDS | 2 × /24 |
| NAT Gateway | 1 per AZ (2 total) — ECS outbound | 1 shared |
| DNS | `enableDnsHostnames: true`, `enableDnsSupport: true` | same |

**Security Groups** (created in NetworkStack, referenced by ApplicationStack):

| SG Name | Inbound | Outbound |
|---|---|---|
| `alb-sg` | 443 from `0.0.0.0/0` | 8000 to `ecs-sg` |
| `ecs-sg` | 8000 from `alb-sg` | 5432 to `rds-sg`; 443 to `0.0.0.0/0` (OAuth2 calls via NAT) |
| `rds-sg` | 5432 from `ecs-sg` | none |

---

### Application Load Balancer (ApplicationStack)

| Attribute | Value |
|---|---|
| Scheme | internet-facing |
| Subnets | Public subnets |
| Security group | `alb-sg` |
| Listener | HTTPS 443; ACM certificate (eu-west-1) |
| HTTP → HTTPS redirect | 80 → 443 permanent redirect |
| Access logs | Enabled → S3 bucket `expense-splitter-alb-logs-{env}` |
| WAF | AWS WAFv2 WebACL attached — rate rule 100 req/5-min per IP + AWSManagedRulesCommonRuleSet |
| Target group | `ecs-tg`: HTTP, port 8000, health check `GET /health` interval 30s, threshold 2 |
| Listener rules | `/openapi.json` → forward only from VPC CIDR (`10.0.0.0/8`); all others forward to `ecs-tg` |

---

### ECS Fargate (ApplicationStack)

| Attribute | Production | Staging |
|---|---|---|
| Cluster | `expense-splitter-prod` | `expense-splitter-staging` |
| Service name | `api` | `api` |
| Task CPU | 512 vCPU units | 256 |
| Task memory | 1024 MB | 512 MB |
| Container image | ECR: `expense-splitter-api:{git-sha}` | same |
| Container port | 8000 | 8000 |
| Desired count | 2 (multi-AZ spread) | 1 |
| Min capacity | 1 | 1 |
| Max capacity | 4 | 2 |
| Auto-scaling metric | CPU utilisation > 70% for 2 consecutive 60s periods | same |
| Scale-in cooldown | 300s | 300s |
| Platform version | LATEST (Fargate 1.4+) | same |
| Assign public IP | false (private subnet) | false |

**Task Definition**:
- `executionRoleArn`: `ecsTaskExecutionRole` — ECR pull + CloudWatch Logs
- `taskRoleArn`: `ecsTaskRole` — Secrets Manager `GetSecretValue` on specific ARNs; CloudWatch Logs `CreateLogStream`/`PutLogEvents` on `/ecs/expense-splitter-api-{env}`
- `logConfiguration`: awslogs driver → `/ecs/expense-splitter-api-{env}`, region `eu-west-1`
- Environment variables: injected from Secrets Manager via `secrets:` block in task definition

**Migration Task Definition** (separate, re-uses same image):
- Command override: `["alembic", "upgrade", "head"]`
- No load balancer target, no auto-scaling
- Same Task Role + network config as API task
- Runs as one-off task in CI/CD before service update

---

### RDS PostgreSQL (ApplicationStack)

| Attribute | Production | Staging |
|---|---|---|
| Engine | PostgreSQL 16.x | PostgreSQL 16.x |
| Instance class | `db.t3.small` | `db.t3.micro` |
| Multi-AZ | Yes | No |
| Storage | 20 GB gp3, auto-scaling to 100 GB | 20 GB gp3 |
| Encryption | `storageEncrypted: true`, AWS managed key | same |
| Parameter group | `force_ssl=1`, `log_connections=1` | same |
| Backup retention | 7 days | 1 day |
| Deletion protection | Enabled | Disabled |
| Public accessibility | false | false |
| Security group | `rds-sg` | `rds-sg` |
| Credentials | Stored in Secrets Manager (`DATABASE_URL`) | separate secret |

---

### AWS Secrets Manager

One secret per environment. Secrets referenced by ARN in ECS task definition.

| Secret name | Contents |
|---|---|
| `expense-splitter/prod/api` | `DATABASE_URL`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_SECRET`, `CSRF_SECRET_KEY` |
| `expense-splitter/staging/api` | same keys, staging values |

Secret rotation: manual (no automated rotation in v1 — documented as future enhancement).

---

### Amazon ECR

| Attribute | Value |
|---|---|
| Repository name | `expense-splitter-api` |
| Image scanning | Scan on push enabled |
| Lifecycle policy | Keep last 10 tagged images; expire untagged after 7 days |
| Image tag | git SHA (no `latest` tag in production) |

---

### CloudWatch (Monitoring)

| Resource | Production | Staging |
|---|---|---|
| Log group (API) | `/ecs/expense-splitter-api-prod` (90-day retention) | `/ecs/expense-splitter-api-staging` (14-day) |
| Alarm: auth failures | `AUTH_FAILURES > 10` / 5 min → SNS | advisory only |
| Alarm: 403s | `HTTP_403 > 20` / 5 min → SNS | — |
| Alarm: 5xx rate | ALB `HTTPCode_Target_5XX_Count > 1%` / 5 min → SNS | — |
| Alarm: CPU high | ECS CPU > 80% / 10 min → SNS + scale-out trigger | — |
| SNS topic | `expense-splitter-alerts-prod` | — |

---

### S3 (ALB Access Logs)

| Attribute | Value |
|---|---|
| Bucket | `expense-splitter-alb-logs-{env}` |
| Public access | Blocked (all 4 block public access settings enabled) |
| Encryption | SSE-S3 |
| Lifecycle | Move to Glacier after 30 days; delete after 90 days |
| Bucket policy | ALB service principal write-only (`elasticloadbalancing.amazonaws.com`) |

---

## Frontend Infrastructure (Unit 3 — covered here per execution plan)

### S3 (Frontend Static Files)

| Attribute | Value |
|---|---|
| Bucket | `expense-splitter-frontend-{env}` |
| Static website hosting | Disabled (served exclusively via CloudFront OAI) |
| Public access | Blocked |
| Versioning | Enabled |
| Encryption | SSE-S3 |

### CloudFront Distribution

| Attribute | Production | Staging |
|---|---|---|
| Origin | S3 bucket (OAI — no public S3 URL) | same |
| Default root object | `index.html` | same |
| Custom error pages | 403/404 → `/index.html` (SPA client-side routing) | same |
| Viewer protocol | Redirect HTTP → HTTPS | same |
| TLS certificate | ACM (eu-west-1 us-east-1 global cert) | same |
| Price class | `PriceClass_100` (NA + Europe) | same |
| Cache policy | `CachingOptimized` for assets; `CachingDisabled` for `index.html` | same |
| Security headers | Response headers policy: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy | same |

**SRI notes (SECURITY-13)**: No third-party scripts loaded from CDN in the SPA build. All dependencies bundled by Vite. N/A for external SRI hashes.

---

## IAM Roles Summary (ApplicationStack)

| Role | Permissions |
|---|---|
| `ecsTaskExecutionRole` | `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` |
| `ecsTaskRole` | `secretsmanager:GetSecretValue` on `expense-splitter/{env}/api` ARN; `logs:CreateLogStream`, `logs:PutLogEvents` on `/ecs/expense-splitter-api-{env}` ARN — no wildcards (SECURITY-06) |
| `GithubActionsRole` | `ecr:*` on repository ARN; `ecs:RegisterTaskDefinition`, `ecs:UpdateService`, `ecs:RunTask`, `ecs:DescribeTasks`; `iam:PassRole` on Task roles — scoped to specific ARNs |
