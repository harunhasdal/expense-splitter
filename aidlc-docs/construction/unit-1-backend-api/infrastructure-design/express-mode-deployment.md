# Deployment Design — ECS Express Mode (Revision)

**Status**: Implemented (2026-08-14) — CDK stacks synth clean; `deploy.yml` reworked to the cdk-deploy-driven rollout (§10). The external OIDC deploy role and the phase-1/phase-2 bootstrap (§11) remain operational steps.
**Supersedes**: The ECS/ALB portions of `deployment-architecture.md` (backend compute only; the CloudFront/S3 frontend design there is unchanged and already implemented in `frontend-stack.ts`).
**Date**: 2026-08-14

---

## 1. Why revise

Two problems with the current state:

1. **The CDK doesn't build the documented backend stack.** `application-stack.ts` stops at a VPC + RDS + empty ECS cluster + a bare ALB (no listener, no target group, no service, no task definition, no ECR). `deployment-architecture.md` describes a full ALB + WAF + ACM + private-subnet Fargate design that was never implemented. `deploy.yml` targets ECS services/task-definitions that don't exist.
2. **The documented design carries pre-Cognito assumptions** (NAT egress "for OAuth2 provider calls", manual ACM certs, custom domains) and still requires us to solve HTTPS + domain + certificate management by hand.

**ECS Express Mode** (GA Nov 2025) removes the hardest part: it provisions an ALB with an HTTPS listener, target group, an **AWS-managed ACM certificate, and an AWS-provided domain name** automatically, plus the ECS service, auto-scaling, log group, and deployment alarms. It is available as a first-class CloudFormation/CDK resource (`AWS::ECS::ExpressGatewayService` / L1 `CfnExpressGatewayService`), so it fits the existing CDK app.

---

## 2. Decision

**Adopt ECS Express Mode for the backend API (both `staging` and `prod`).**

Keep: VPC (NetworkStack), RDS PostgreSQL, ECR, Secrets Manager, the custom Fargate task definition, and the CloudFront/S3 frontend stack.
Replace: the hand-rolled ALB + listener + target group + ECS service + auto-scaling stub in `application-stack.ts` with a single `CfnExpressGatewayService`.

---

## 3. What Express Mode provides vs. what we still own

| Concern | Express Mode (auto) | We own |
|---|---|---|
| ALB + HTTPS listener (443) + target group | Yes | — |
| ACM certificate | Yes | — |
| Public domain name | Yes (AWS-provided) | — |
| ECS service (Fargate) + canary deploy | Yes | — |
| Target-tracking auto-scaling + scalable target | Yes (tunable) | — |
| CloudWatch log group + failed-deploy alarms | Yes | — |
| Security groups | Yes (or we pass our own) | Optionally our `ecsSg` |
| Task definition (image, env, secrets, port, health) | Uses ours as-is | **Yes — custom task def** |
| ECR repository | No | **Yes** |
| RDS + `DATABASE_URL` assembly | No | **Yes** |
| Secrets (`COGNITO_CLIENT_SECRET`, `CSRF_SECRET_KEY`) | No | **Yes** |
| IAM: execution role, infrastructure role, task role | No | **Yes** |
| Cognito callback / `APP_BASE_URL` wiring | No | **Yes (two-phase)** |

---

## 4. Revised architecture

```
eu-west-1  (per environment: prod = 10.0.0.0/16, staging = 10.1.0.0/16)
============================================================================

  +--------------------------------------------------------------------+
  |  ECS Express Mode service  (AWS::ECS::ExpressGatewayService)        |
  |                                                                    |
  |   [AWS-provided domain]  https://<generated>.<region>.amazonaws...  |
  |          |  ACM cert (auto)                                        |
  |          v                                                         |
  |   [ALB : 443 HTTPS]  (auto)  --- target group --->  ECS service    |
  |                                                                    |
  |   Fargate task (custom task def):                                  |
  |     container "api"  port 8000                                     |
  |       env:     COGNITO_REGION, COGNITO_USER_POOL_ID,               |
  |                COGNITO_CLIENT_ID, COGNITO_DOMAIN,                   |
  |                ALLOWED_ORIGINS, APP_BASE_URL, LOG_LEVEL            |
  |       secrets: DATABASE_URL, COGNITO_CLIENT_SECRET,                |
  |                CSRF_SECRET_KEY   (from Secrets Manager)            |
  |     health check: GET /health                                      |
  +-------------------------------|------------------------------------+
                                  |  port 5432 (rdsSg <- ecsSg)
                                  v
  +--------------------------------------------------------------------+
  |  [RDS PostgreSQL 16]   (ApplicationStack, private subnets)         |
  |   prod: Multi-AZ, deletion protection | staging: single-AZ         |
  +--------------------------------------------------------------------+

  SHARED (per env)
  +---------------------------------------------+
  | [ECR] expense-splitter-api  (scan on push)  |
  | [Secrets Manager] expense-splitter/<env>/api|
  | [CloudWatch Logs] (created by Express Mode) |
  +---------------------------------------------+

  FRONTEND (unchanged — already implemented)
  +---------------------------------------------+
  | [S3] expense-splitter-frontend-<env>        |
  | [CloudFront]  OAI, security headers, SPA    |
  +---------------------------------------------+

  Migration: one-off `aws ecs run-task` against the same custom task def,
             overriding container "api" command -> `alembic upgrade head`
```

---

## 5. CDK stack changes

### `application-stack.ts` (rewritten backend)

Remove: `elbv2.ApplicationLoadBalancer` and the placeholder ECS cluster/ALB wiring.
Keep: `logs.LogGroup` (optional — Express creates its own), RDS instance.
Add:

```typescript
// ECR repository
const repo = new ecr.Repository(this, 'ApiRepo', {
  repositoryName: 'expense-splitter-api',
  imageScanOnPush: true,
  lifecycleRules: [{ maxImageCount: 20 }],
});

// DATABASE_URL assembled from the RDS-generated secret into its own secret
// (app expects a single `postgresql+asyncpg://...` string, not discrete fields)
const dbUrlSecret = new secretsmanager.Secret(this, 'DbUrlSecret', { /* ... */ });

// Custom Fargate task definition — container "api", port 8000
const taskDef = new ecs.FargateTaskDefinition(this, 'ApiTaskDef', {
  cpu: 1024, memoryLimitMiB: 2048,
  executionRole, taskRole,
});
taskDef.addContainer('api', {
  image: ecs.ContainerImage.fromEcrRepository(repo, imageTag),
  portMappings: [{ containerPort: 8000 }],
  logging: ecs.LogDrivers.awsLogs({ streamPrefix: 'api' }),
  // APP_BASE_URL resolves from SSM /expense-splitter/<env>/api-base-url (phase seam, §9)
  environment: { /* COGNITO_REGION, ..., APP_BASE_URL, ALLOWED_ORIGINS, LOG_LEVEL */ },
  secrets: {
    DATABASE_URL: ecs.Secret.fromSecretsManager(dbUrlSecret),
    COGNITO_CLIENT_SECRET: ecs.Secret.fromSecretsManager(apiSecret, 'cognito_client_secret'),
    CSRF_SECRET_KEY: ecs.Secret.fromSecretsManager(apiSecret, 'csrf_secret_key'),
  },
});

// Express Mode service (L1 — no L2 construct yet)
new ecs.CfnExpressGatewayService(this, 'ApiExpress', {
  serviceName: `expense-splitter-api-${props.envName}`,
  taskDefinitionArn: taskDef.taskDefinitionArn,
  executionRoleArn: executionRole.roleArn,
  infrastructureRoleArn: infraRole.roleArn,
  taskRoleArn: taskRole.roleArn,
  healthCheckPath: '/health',
  networkConfiguration: {
    subnets: props.vpc.publicSubnets.map(s => s.subnetId),  // see §7
    securityGroups: [props.ecsSg.securityGroupId],
  },
  scalingTarget: { minTaskCount: props.envName === 'prod' ? 2 : 1 },
});
```

> `CfnExpressGatewayService` properties (confirmed against the CFN reference): `Cluster`, `Cpu`, `Memory`, `ExecutionRoleArn`, `InfrastructureRoleArn`, `TaskRoleArn`, `TaskDefinitionArn`, `HealthCheckPath`, `NetworkConfiguration {Subnets, SecurityGroups}`, `PrimaryContainer`, `ScalingTarget`, `ServiceName`, `Tags`. Supplying `TaskDefinitionArn` makes Express use our task def as-is (image, cpu/mem, container defs).

### `bin/expense-splitter.ts`

- Instantiate **both** `staging` and `prod` (currently only one env, defaulting to `prod`) — `deploy.yml` has separate staging + prod jobs.
- The old `REPLACE_ME` placeholders (`appBaseUrl`, `googleClientId`, `googleClientSecretArn`) that made `cdk synth` fail via `fromSecretCompleteArn('REPLACE_ME')` are **removed** — config now resolves from SSM / Secrets Manager at deploy time (§8), so synth is clean.

### OIDC deploy role — external (not CDK)

The GitHub OIDC provider + deploy role (`GithubActionsRole`) are created **outside CDK**, directly in the account (§6 lists the required permissions). Its ARN is stored as the GitHub repo **secret** `AWS_ROLE_ARN` (a secret, not a variable, so the account ID is masked in Actions logs — it never appears in these docs). CDK does not manage this role.

---

## 6. IAM roles

| Role | Purpose | Policy |
|---|---|---|
| **Execution role** | Pull image from ECR, read secrets, write logs | `AmazonECSTaskExecutionRolePolicy` + `secretsmanager:GetSecretValue` on our secrets |
| **Infrastructure role** | Lets Express Mode manage ALB/target-group/scaling on our behalf | `AmazonECSInfrastructureRoleforExpressGatewayServices` (managed) — **new, required by Express** |
| **Task role** | App runtime AWS calls (minimal; add if needed) | Least-privilege |
| **Deploy role** (CI) — *external, not CDK* — `GithubActionsRole` | GitHub OIDC → ECR push; `sts:AssumeRole` on the CDK bootstrap roles (`cdk-hnb659fds-*`) so `cdk deploy` can register the task-def revision + update the Express service via CFN; `ecs:RunTask`/`DescribeTasks` + `iam:PassRole` (execution + task roles) for the migration; S3 sync + CloudFront invalidate for the frontend | Scoped custom policy; created in the account, ARN stored in GitHub repo secret `AWS_ROLE_ARN` |

---

## 7. Networking trade-off — ACCEPTED (2026-08-14)

**Decision**: Accept public-subnet Fargate tasks with public IPs, locked down by the service security group. The SG restrictions (only the ALB SG reaches port 8000; RDS reachable only from `ecsSg`) are sufficient for this application. This intentionally diverges from the original private-subnet design in `deployment-architecture.md`.

Express Mode couples the **ALB scheme to the subnet type** of the service:

- **Public subnets → internet-facing ALB, and tasks get public IPs** (`assignPublicIp` on).
- **Private subnets → internal ALB** (not reachable from the internet).

Because the API must be publicly reachable, Express Mode places the Fargate tasks in **public subnets with public IPs**, locked down by the service security group. This **diverges from the original `deployment-architecture.md`** design (tasks in private subnets behind NAT).

- **Security**: tasks are still protected by SGs (only the ALB SG can reach port 8000); the RDS SG already restricts DB access to `ecsSg`. Public IPs on tasks are a wider surface than private-subnet tasks, but a standard Express Mode posture.
- **Alternative if unacceptable**: keep a classic self-managed ALB + private-subnet Fargate (the original design) and forgo Express Mode. This reinstates manual ACM/domain/listener work — i.e. the effort Express Mode was chosen to avoid.

**Recommendation**: accept public-subnet tasks for this app; the SG restrictions are sufficient. Flagged for explicit approval.

---

## 8. Decisions

**Resolved (2026-08-14):**
- ✅ **Networking trade-off** (§7): public-subnet tasks accepted.
- ✅ **Two-phase deploy** (§9): split into an **infrastructure phase** and an **application phase** so the generated API domain can be wired into Cognito callbacks and `APP_BASE_URL` between phases. A stable custom domain (single-phase) is explicitly *not* pursued.
- ✅ **OIDC deploy role**: created **externally in the account** (out of CDK scope); its ARN is supplied to GitHub Actions as the repo **secret** `AWS_ROLE_ARN`. See §6 for the permissions the external role must carry.
- ✅ **Config source** for `appBaseUrl`, Google client id/secret ARN (replacing the `REPLACE_ME` placeholders): **SSM Parameter Store** for non-secrets + **Secrets Manager** for the Google client secret. The API base URL SSM parameter (`/expense-splitter/<env>/api-base-url`) is written in the app phase (§9).

**All design decisions resolved.**

---

## 9. Two-phase deployment (infra → app)

Express Mode generates the API domain at create time, but `cognito-stack.ts` callback URLs (`${appBaseUrl}/auth/callback`) and the app's `APP_BASE_URL` depend on that hostname. We split deployment into two phases with a stable seam between them: **an SSM parameter `/expense-splitter/<env>/api-base-url`** that phase 1 seeds with a placeholder and phase 2 overwrites with the real domain. Cognito and the task def read this parameter, so domain-dependent config lives entirely in phase 2.

### Phase 1 — Infrastructure (`cdk deploy` infra stacks)

Provisions everything that does **not** depend on the API domain, and produces it:

- `NetworkStack` — VPC, subnets, security groups.
- `CognitoStack` — user pool, Google IdP, app client. Callback/logout URLs seeded from the placeholder SSM value (plus `http://localhost:8000` for local dev, which stays valid).
- `ApplicationStack` — ECR, RDS, Secrets Manager, custom task def, and the **`CfnExpressGatewayService`** (this is what mints the AWS-provided domain). `APP_BASE_URL` reads the placeholder SSM value.
- `FrontendStack` — S3 + CloudFront (domain-independent).
- Push an initial image to ECR so the Express service can reach a stable state.

**Output of phase 1**: the Express service's generated domain (via `CfnOutput`).

### Seam — capture the domain

Write the Express domain into `/expense-splitter/<env>/api-base-url` (manually, or a small script reading the stack output). This is the only handoff between phases.

### Phase 2 — Application wiring (`cdk deploy` again, domain now known)

Re-deploys the two domain-dependent pieces, now reading the real SSM value:

- `CognitoStack` — callback/logout URLs updated to `https://<express-domain>/auth/callback` (+ logout).
- `ApplicationStack` task def — `APP_BASE_URL` updated to the real domain; rolls a new task-def revision and updates the Express service.

`NetworkStack`, `FrontendStack`, RDS, and ECR are unchanged in phase 2 (no-op).

> Steady-state redeploys (new app image) only touch phase 2. Phase 1 re-runs only when infra changes. The SSM seam means neither phase hard-codes the domain, so this is repeatable, not a one-time bootstrap hack.

---

## 10. CI/CD (`deploy.yml`) revisions

The old `update-service --force-new-deployment` was doubly wrong: it doesn't roll a new image (the task-def image tag doesn't change) and `update-service` isn't the API for an Express Gateway Service. **Rollout model: `cdk deploy`-driven** (chosen 2026-08-14 over the raw-API alternative) — the task def is CDK-managed, so a single `cdk deploy` re-registers the revision at the new image tag *and* updates the Express service via CloudFormation. This keeps CDK the single source of truth (no task-def JSON duplicated in CI, no drift on the next deploy) and matches §9's "steady-state redeploys only touch phase 2 (ApplicationStack)".

Revised backend rollout per environment (implemented as the `deploy-backend` composite action, called by the `staging` and `production` jobs):

1. `build-and-push`: build + push `expense-splitter-api:<sha>` to ECR (unchanged), regenerate `openapi.json` (already fixed to use Cognito env).
2. **`cdk deploy ApplicationStack-<env> --exclusively --context imageTag=<sha> --outputs-file cdk-outputs.json`**. This registers a new task-def revision at `:<sha>` and rolls the Express service (canary) via CFN. `--exclusively` avoids touching Network/Cognito/Frontend stacks. Outputs (`TaskDefinitionArn`, `ClusterName`, `MigrationSubnetIds`, `EcsSecurityGroupId`) are captured for the next step.
3. **Migration**: `aws ecs run-task` against the exact `TaskDefinitionArn` just deployed, launch-type FARGATE, `networkConfiguration` = the private subnets + ECS SG from the outputs (`assignPublicIp=DISABLED`; NAT egress for ECR/Secrets, RDS reachable via the SG), container **`Main`** command overridden to `alembic upgrade head`; wait for `tasks-stopped` and assert exit 0. (Container name is `Main`, not `api` — an Express BYO-task-def requirement.) Migrations must be expand/contract-safe since the canary rollout runs old and new tasks concurrently.
4. `deploy-frontend`: unchanged (S3 sync + CloudFront invalidation).

### GitHub config — secrets vs. variables

Only the role ARN is a **secret** (it embeds the account ID, kept masked). Everything else is a non-sensitive **repo variable** (referenced as `${{ vars.* }}`).

| Name | Kind | Value / note |
|---|---|---|
| `AWS_ROLE_ARN` | **secret** | ARN of the external OIDC deploy role (`GithubActionsRole`). Masked in logs. |
| `AWS_REGION` | variable | `eu-west-1` — **must** match the region hardcoded in `bin/expense-splitter.ts`; a mismatch points ECR/ECS calls at the wrong region. Single-region — no us-east-1 dependency (Express ALB cert/domain are in-region; CloudFront uses its default domain). |
| `ECR_REGISTRY` | variable | `<account>.dkr.ecr.eu-west-1.amazonaws.com`. |
| `S3_FRONTEND_BUCKET_PROD` | variable | Deterministic: `expense-splitter-frontend-prod`. |
| `CLOUDFRONT_DISTRIBUTION_ID_PROD` | variable | **Not known until `FrontendStack-prod` is deployed** — set it after the first frontend deploy (read from the stack's `DistributionId` output). Leave unset rather than placeholder, or the invalidation step targets a nonexistent distribution. |
| `ENABLE_PROD` | variable | **Gate for the `deploy-production` + `deploy-frontend` jobs.** Leave unset while only staging is bootstrapped — both jobs skip, so a push to `main` rolls out staging alone. Set to `true` after the prod phase-1/phase-2 local runbook has run once (image pushed, api secret populated, `ApplicationStack-prod` deployed), which lets CI take over prod steady-state. |
| ~~`ECS_CLUSTER_*` / `ECS_SERVICE_*` / `MIGRATION_TASK_DEFINITION`~~ | — | **No longer needed.** Cluster (`expense-splitter-<env>`), service, and task-def family (`expense-splitter-api-<env>`) are deterministic and read from the `cdk deploy` outputs file instead. |

---

## 11. Bootstrap / migration order

> **Why Express can't come up in one pass (found during first deploy, 2026-08-14).**
> The Express service's health check is `GET /health`, which executes `SELECT 1`
> against the DB, and its task reads three JSON keys (`database_url`,
> `cognito_client_secret`, `csrf_secret_key`) from the `expense-splitter/<env>/api`
> secret. On a first deploy that secret is an empty shell (not valid JSON) and the
> only `database_url` that could point at RDS belongs to an instance created in the
> *same* stack — which the Express resource does not depend on, so Express would try
> to start tasks before RDS is reachable. Either way `/health` returns 503, the
> canary rollback fires, and the deploy fails. The fix is the **`deployExpress`
> context flag** (default `true`): bootstrap deploys `ApplicationStack` once with
> `-c deployExpress=false` to create RDS + secret + task def, populates the secret,
> then redeploys with the flag defaulting on so the service stabilizes on first try.
> This only affects bootstrap; steady-state CI deploys always run with the default.

1. `cdk bootstrap` (first time). Seed the SSM params `/expense-splitter/<env>/api-base-url` (placeholder `http://localhost:8000`) and `/expense-splitter/<env>/allowed-origins` (JSON array) — both are read at deploy time via `{{resolve:ssm}}` and must exist first.
2. Deploy `EcrStack`, then build + push an initial image (`:bootstrap`) so the task def resolves and (later) Express can stabilize.
3. **Phase 1a (infra, no service)** — deploy `NetworkStack`, `CognitoStack`, `FrontendStack`, and `ApplicationStack` **with `-c deployExpress=false`** (creates RDS, the secret shell, task def, cluster, roles, log group — but not the Express service).
4. **Populate the secret** `expense-splitter/<env>/api` with valid JSON: `database_url` (assembled from the RDS-generated master secret + endpoint, `postgresql+asyncpg://…`), `cognito_client_secret` (from `describe-user-pool-client`), and a generated `csrf_secret_key` (≥32 chars).
5. **Phase 1b (add service)** — redeploy `ApplicationStack` (flag defaults to `true`). Express now stabilizes (valid secret + reachable RDS → `/health` 200) and mints the AWS-provided domain (`ApiEndpoint` output).
6. **Seam** — write the Express domain into `/expense-splitter/<env>/api-base-url`; update `/expense-splitter/<env>/allowed-origins` if the frontend origin changed.
7. **Phase 2 (app wiring)** — re-deploy `CognitoStack` + `ApplicationStack`; callbacks and `APP_BASE_URL` pick up the real domain (§9).
8. **Migration** — one-off `aws ecs run-task` against the deployed task-def revision, container `Main` command `alembic upgrade head` (private subnets + `ecsSg`); wait for stop, assert exit 0.
9. Ensure the **external OIDC deploy role** exists; set its ARN as GitHub `AWS_ROLE_ARN`. Add remaining repo variables + `staging`/`production` environments.
10. Merge to `main` → pipeline runs (steady-state redeploys are phase-2 only, always `deployExpress=true`).

---

## 12. Effort estimate

| Work | Rough size |
|---|---|
| Rewrite `application-stack.ts` (ECR, task def, secrets, Express service) | ~half–1 session |
| `bin` two-env + config source | small |
| OIDC deploy role | **external (not CDK)** — provide required policy (§6) |
| `deploy.yml` rollout rework | small–medium |
| Cognito two-phase runbook | doc + small script |

Non-blocking cleanups noticed: deprecated `vpc.cidr` (→ `ipAddresses`) and CloudFront `OriginAccessIdentity`/`S3Origin` (→ OAC).

---

## 13. References

- Announcing Amazon ECS Express Mode — https://aws.amazon.com/about-aws/whats-new/2025/11/announcing-amazon-ecs-express-mode/
- Resources created by Express Mode services — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-work.html
- Extending Express Mode (custom task defs, ECS Exec) — https://aws.amazon.com/blogs/containers/extending-amazon-ecs-express-mode-to-build-an-optimal-container-environment/
- `AWS::ECS::ExpressGatewayService` (CFN) — https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-expressgatewayservice.html
- Custom task definition support — https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-ecs-express-mode-custom-task-def/
```
