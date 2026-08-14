# Deployment Design — ECS Express Mode (Revision)

**Status**: Proposed for review — not yet implemented
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
- Replace `REPLACE_ME` placeholders (`appBaseUrl`, `googleClientId`, `googleClientSecretArn`); see §8 open decisions. **`cdk synth` currently fails** because `fromSecretCompleteArn('REPLACE_ME')` rejects the invalid ARN.

### OIDC deploy role — external (not CDK)

The GitHub OIDC provider + deploy role (`GithubActionsRole`) are created **outside CDK**, directly in the account (§6 lists the required permissions). Its ARN is stored as the GitHub repo **secret** `AWS_ROLE_ARN` (a secret, not a variable, so the account ID is masked in Actions logs — it never appears in these docs). CDK does not manage this role.

---

## 6. IAM roles

| Role | Purpose | Policy |
|---|---|---|
| **Execution role** | Pull image from ECR, read secrets, write logs | `AmazonECSTaskExecutionRolePolicy` + `secretsmanager:GetSecretValue` on our secrets |
| **Infrastructure role** | Lets Express Mode manage ALB/target-group/scaling on our behalf | `AmazonECSInfrastructureRoleforExpressGatewayServices` (managed) — **new, required by Express** |
| **Task role** | App runtime AWS calls (minimal; add if needed) | Least-privilege |
| **Deploy role** (CI) — *external, not CDK* — `GithubActionsRole` | GitHub OIDC → ECR push, `run-task`, register task def, update Express service, S3 sync, CloudFront invalidate, read the SSM api-base-url param | Scoped custom policy; created in the account, ARN stored in GitHub repo secret `AWS_ROLE_ARN` |

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

The current `update-service --force-new-deployment` does **not** roll a new image (the task def image tag doesn't change). Revised backend rollout per environment:

1. `build-and-push`: build + push `expense-splitter-api:<sha>` to ECR (unchanged), regenerate `openapi.json` (already fixed to use Cognito env).
2. **Register a new task-def revision** pointing at `:<sha>` (new step).
3. **Migration**: `aws ecs run-task` with the new task def, container `api` command overridden to `alembic upgrade head`; wait for exit 0.
4. **Update the Express service** to the new task-def revision (`update-express-gateway-service` / CFN update), then `aws ecs wait services-stable`.
5. `deploy-frontend`: unchanged (S3 sync + CloudFront invalidation).

### GitHub secrets — what changes

| Secret | Note |
|---|---|
| `AWS_ROLE_ARN`, `AWS_REGION`, `ECR_REGISTRY` | Unchanged. **`AWS_REGION` must be `eu-west-1`** to match the region hardcoded in `bin/expense-splitter.ts`; a mismatch points the pipeline's ECR/ECS calls at the wrong region. Single-region deployment — no us-east-1 dependency (Express Mode ALB cert/domain are in-region; CloudFront uses its default domain). |
| `ECS_CLUSTER_STAGING` / `ECS_CLUSTER_PROD` | Express default cluster is `default` unless we set `Cluster`; set explicitly to `expense-splitter-<env>` and reuse |
| `ECS_SERVICE_STAGING` / `ECS_SERVICE_PROD` | Express service names `expense-splitter-api-<env>` |
| `MIGRATION_TASK_DEFINITION` | Our custom task def family (container `api`) |
| `S3_FRONTEND_BUCKET_PROD`, `CLOUDFRONT_DISTRIBUTION_ID_PROD` | Unchanged (frontend stack) |

---

## 11. Bootstrap / migration order

1. `cdk bootstrap` (first time). Seed `/expense-splitter/<env>/api-base-url` with a placeholder.
2. **Phase 1 (infra)** — deploy `NetworkStack`, `CognitoStack`, `ApplicationStack`, `FrontendStack` per env (§9). This mints the API domain.
3. Push an initial image to ECR (Express service needs a valid image to stabilize).
4. **Seam** — write the Express domain into the SSM parameter.
5. **Phase 2 (app)** — re-deploy `CognitoStack` + `ApplicationStack`; callbacks and `APP_BASE_URL` pick up the real domain (§9).
6. Ensure the **external OIDC deploy role** exists; set its ARN as GitHub `AWS_ROLE_ARN`. Add remaining repo secrets + `staging`/`production` environments.
7. Merge to `main` → pipeline runs (steady-state redeploys are phase-2 only).

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
