# Requirements Clarification Questions — Expense Splitter

Please answer each question by filling in the letter choice after the `[Answer]:` tag.
If none of the options match your needs, choose the last option (Other) and describe your preference.

---

## Question 1
What tech stack should be used for the backend REST API?

A) Python (FastAPI or Flask)
B) Node.js (Express or Fastify)
C) TypeScript (Node.js + Express/Fastify)
D) Java (Spring Boot)
E) Go
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
What frontend framework should be used for the Single Page Application?

A) React (with TypeScript)
B) Vue.js (with TypeScript)
C) Plain HTML/CSS/JavaScript (no framework)
D) Next.js (React-based, SSR optional)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 3
What database should be used for persistent storage?

A) PostgreSQL (relational)
B) SQLite (relational, file-based — simpler local setup)
C) MongoDB (document store)
D) MySQL / MariaDB
X) Other (please describe after [Answer]: tag below)

[Answer]: X SQLite for local development, Postgres for cloud environments 

---

## Question 4
How should user identity / authentication be handled?

A) No authentication — anyone can create/view any group (anonymous, session-based)
B) Simple user accounts with email + password (JWT-based)
C) OAuth2 / social login (Google, GitHub, etc.)
D) Named members only (no accounts — members are just names within a group)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 5
What is the target deployment environment?

A) Local development only (no deployment needed, just runnable locally)
B) Cloud (AWS, GCP, Azure) — containerized or serverless
C) Docker Compose (multi-container local or server deploy)
D) Any server via a single deployment artifact (e.g. Heroku, Render, Railway)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 6
What currency/locale handling is required?

A) Single currency only (e.g., USD) — no conversion
B) Multi-currency display (store each expense's currency, no conversion)
C) Multi-currency with conversion (pick a base currency, convert on display)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 7
Should the app support real-time updates (e.g., when one group member adds an expense, others see it live)?

A) Yes — real-time updates via WebSockets or SSE
B) No — manual refresh / pull-only is fine
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 8
What split types should be supported at launch?

A) Equal split only
B) Equal split + exact amounts
C) Equal split + exact amounts + percentage-based (all three as stated in PRD)
D) All three plus custom ratios/shares
X) Other (please describe after [Answer]: tag below)

[Answer]: D

---

## Question 9
Should settled expenses/payments be permanently recorded (audit trail), or can they be deleted?

A) Full audit trail — once recorded, expenses and settlements are immutable (soft delete at most)
B) Editable and deletable — users can freely modify or remove past expenses
C) Editable until settled — expenses can be edited/deleted while open, locked after settlement
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 10: Security Extension
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 11: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)
B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)
C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)
X) Other (please describe after [Answer]: tag below)

[Answer]: B
