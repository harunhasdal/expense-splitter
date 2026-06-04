# NFR Design Plan — Unit 1: Backend API & Data Layer

Most patterns follow directly from the NFR requirements. Three open decisions remain.
Please fill in the letter choice after each `[Answer]:` tag.

---

## Question 1
Should the API use a response cache for the balance/settlement-suggestions endpoints
(the most expensive reads)?

A) No caching — always recompute from the database on every request (simplest; data always fresh)
B) Short-lived in-process cache per request only (memoize within a single request lifecycle, no cross-request caching)
C) Redis-backed cache with short TTL (e.g. 5 seconds) — reduces DB load under concurrent reads of the same group
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
How should database migration (Alembic) be run in the ECS Fargate deployment?

A) As a one-off ECS task that runs before the main service starts (migration-as-a-job pattern)
B) On application startup inside the container (`alembic upgrade head` in the entrypoint script)
C) Manually via a developer running `alembic upgrade head` from their local machine against the cloud DB
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
Should the API expose an OpenAPI schema endpoint (`/openapi.json`) in production for the frontend to use for client code generation?

A) Yes — expose `/openapi.json` but restrict access to internal network / VPC only (not public)
B) Yes — expose publicly (the schema contains no secrets; enables third-party integrations)
C) No — generate the OpenAPI schema once at build time in CI and commit it to the repo; disable the endpoint in production
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Generation Checklist

- [x] Step 1 — Generate `nfr-design-patterns.md` — all design patterns with implementation guidance
- [x] Step 2 — Generate `logical-components.md` — middleware stack, component interactions, infrastructure logical view
