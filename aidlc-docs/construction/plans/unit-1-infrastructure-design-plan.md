# Infrastructure Design Plan — Unit 1: Backend API & Data Layer

Most infrastructure decisions are locked from the NFR Requirements and NFR Design stages.
This plan covers the remaining open items plus the Unit 3 frontend infrastructure
(which has no separate Infrastructure Design stage).

Please fill in the letter choice after each `[Answer]:` tag.

---

## Question 1
What AWS region should the production deployment target?

A) us-east-1 (US East — most AWS services available, lowest cost)
B) eu-west-1 (Ireland — EU data residency, good for European users)
C) ap-southeast-1 (Singapore — good for Asia-Pacific users)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 2
Should there be a staging environment in addition to production?

A) Yes — identical infrastructure to production (separate VPC, RDS, ECS cluster) but smaller sizing
B) Yes — lightweight staging using the same VPC as production but separate ECS service and RDS instance
C) No — only production; developers test locally with Docker Compose
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
How should the frontend SPA (Unit 3) be served? (Unit 3 has no separate Infrastructure Design stage — specifying it here.)

A) S3 static website + CloudFront CDN (standard SPA pattern — zero server cost, global CDN, HTTPS via ACM)
B) Serve the frontend static build directly from the FastAPI backend (single origin, simpler CORS)
C) Separate container on ECS Fargate serving the static files via nginx
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
What AWS CDK stack organisation should be used?

A) Single CDK stack for all resources (VPC, ECS, RDS, S3, CloudFront, IAM) — simpler for a small app
B) Separate CDK stacks: Network stack + Application stack + Frontend stack (cleaner separation, independent deploy)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 5
Should an RDS read replica be provisioned for read-heavy balance queries?

A) No read replica — single RDS instance is sufficient at this scale (primary handles all reads + writes)
B) Yes — one read replica; balance/expense list queries routed to replica
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Generation Checklist

- [x] Step 1 — Generate `infrastructure-design.md` — service-by-service specification
- [x] Step 2 — Generate `deployment-architecture.md` — full deployment diagram, CDK stack structure, CI/CD pipeline
- [x] Step 3 — Generate `aidlc-docs/construction/shared-infrastructure.md` — shared resources referenced by all units
