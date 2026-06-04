# NFR Requirements Plan — Unit 1: Backend API & Data Layer

Most NFR decisions are already locked from requirements.md and the Security Baseline.
The questions below cover the remaining open items that affect concrete implementation choices.

Please fill in the letter choice after each `[Answer]:` tag.

---

## Question 1
What AWS compute target should the backend API use?

A) ECS Fargate — containerised, always-on, predictable latency, simpler horizontal scaling
B) AWS Lambda + API Gateway — serverless, scales to zero, lower cost at low traffic but cold-start latency
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
What rate limiting strategy should protect the public-facing API endpoints? (SECURITY-11)

A) Per-IP rate limiting at the API Gateway / ALB level (e.g. 100 requests/minute per IP)
B) Per-user rate limiting at the FastAPI middleware level (e.g. 60 requests/minute per authenticated user)
C) Both: coarse per-IP limit at the gateway + fine-grained per-user limit in the app
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
What CSRF protection strategy should be used alongside the HttpOnly JWT cookie? (SECURITY-08)

A) Double-submit cookie pattern (a separate non-HttpOnly CSRF token cookie that the SPA reads and sends as a header)
B) SameSite=Lax on the JWT cookie is sufficient for this app's threat model (no cross-origin form submissions)
C) Synchroniser token pattern (server issues a CSRF token per session, stored server-side)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 4
What log aggregation target should structured logs be shipped to? (SECURITY-03, SECURITY-14)

A) AWS CloudWatch Logs (native, zero extra infra, 90-day retention policy)
B) AWS CloudWatch + an OpenSearch (ELK) cluster for searchable log analytics
C) A third-party service (e.g. Datadog, Grafana Cloud) — specify in Other
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 5
What is the target database connection pool size for the cloud (PostgreSQL) deployment?

A) Small pool: min 2, max 10 connections per container instance (suitable for ≤50 concurrent users)
B) Medium pool: min 5, max 20 connections per container instance (suitable for ≤200 concurrent users)
C) Let SQLAlchemy default settings apply and tune after first load test
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Generation Checklist

- [x] Step 1 — Generate `nfr-requirements.md`
- [x] Step 2 — Generate `tech-stack-decisions.md`
