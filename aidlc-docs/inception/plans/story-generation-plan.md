# Story Generation Plan — Expense Splitter

## Approach Overview
Stories will be organized **Epic-Based** — grouped into epics that map to the three core areas from the PRD, with each epic broken into vertical slices representing independent, deliverable stories. This provides a natural hierarchy (Epic → Story → Acceptance Criteria) while keeping individual stories small and testable.

---

## Questions for User Input

Please fill in the letter choice after each `[Answer]:` tag before I proceed to generation.

---

### Question 1
How detailed should acceptance criteria be per story?

A) Minimal — one or two bullet points per story (quick, enough for developers to work from)
B) Standard — Given/When/Then format with 3–5 scenarios per story
C) Comprehensive — Given/When/Then plus edge cases, error scenarios, and security checks per story
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

### Question 2
Which user personas should be defined?

A) Two: Group Creator and Group Member (creator has extra admin powers; member is everyone else)
B) Three: Group Creator, Group Member, and Guest (unauthenticated visitor who lands on the app)
C) Four: Group Creator, Group Member, Guest, and Invited Pending User (invited by email but not yet signed up)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 3
How should epics be organized?

A) By PRD area: (1) Authentication & Onboarding, (2) Group & Member Management, (3) Expense Recording, (4) Balance & Settlements, (5) Dashboard UI
B) By user journey phase: (1) Getting Started, (2) Managing a Group, (3) Tracking Expenses, (4) Settling Up
C) By technical layer: (1) API Endpoints, (2) Business Logic, (3) Frontend Screens
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

### Question 4
Should stories include UI/UX notes (e.g., suggested component names, screen layout hints)?

A) Yes — include lightweight UI notes to guide frontend implementation
B) No — keep stories purely behavioral (what, not how)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### Question 5
Should the plan include a story map linking personas to stories (showing who benefits from each story)?

A) Yes — include a persona-to-story mapping table
B) No — personas and stories as separate documents is sufficient
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Generation Checklist

The following steps will be executed after answers are received and the plan is approved.

### Phase 1: Personas
- [x] Step 1.1 — Define personas based on Q2 answer; write `aidlc-docs/inception/user-stories/personas.md`
  - Each persona: name, role, goals, frustrations, technical comfort
  - Map persona to relevant epics

### Phase 2: Epics and Stories
- [x] Step 2.1 — Create Epic 1: API Endpoints (auth, groups, members, expenses, settlements)
- [x] Step 2.2 — Create Epic 2: Business Logic (split types, debt simplification, immutability)
- [x] Step 2.3 — Create Epic 3: Frontend Screens (sign-in, dashboard, group detail, expense form, settlement, expense list)
- [x] Step 2.4 — Write all stories into `aidlc-docs/inception/user-stories/stories.md`
  - INVEST compliance check per story
  - Given/When/Then acceptance criteria (3–5 scenarios)
  - UI notes included (Q4=A)
  - Story IDs in format US-[epic#]-[story#]

### Phase 3: Persona-Story Mapping (conditional on Q5)
- [x] Step 3.1 — Q5=B: skipped (no mapping table required)

### Phase 4: Validation
- [x] Step 4.1 — All FR-01 through FR-09 covered (traceability table included in stories.md)
- [x] Step 4.2 — Every story has Given/When/Then acceptance criteria
- [x] Step 4.3 — INVEST criteria verified: stories are independent, behavioral, estimable, and small
- [x] Step 4.4 — Security-relevant stories reference applicable SECURITY rule IDs
