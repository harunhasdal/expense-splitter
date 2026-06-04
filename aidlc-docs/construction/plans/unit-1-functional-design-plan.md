# Functional Design Plan — Unit 1: Backend API & Data Layer

Please answer each question by filling in the letter choice after the `[Answer]:` tag.

---

## Question 1
How should JWT tokens be stored and transmitted in the browser?

A) HttpOnly cookie (most secure — JavaScript cannot access the token; CSRF mitigation needed)
B) In-memory only (lost on page refresh — very secure but poor UX for a web app)
C) localStorage (convenient but accessible to JavaScript — not recommended for security-sensitive apps)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Question 2
What should happen when an invited member (email placeholder) signs in for the first time?

A) Automatically link their new account to any pending-member entries by email and promote them to full members
B) Show a "You have pending group invitations" screen — they must explicitly accept each invitation
C) Silently link and accept all pending invitations on first sign-in without any prompt
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## Question 3
When a group is archived with non-zero balances blocked (as per US-1-5), should there be an override option for the owner?

A) No override — zero balance is a hard requirement before archiving (as stated in US-1-5)
B) Yes — allow a forced archive with a confirmation prompt, and record a warning in the audit log
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 4
What is the pagination strategy for the expense list endpoint?

A) Cursor-based pagination (stable, performant for large datasets — uses a `cursor` token)
B) Offset/limit pagination (simple — uses `page` and `page_size` query params)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Question 5
Should the API include a soft-delete for members who have already been removed (keeping their name visible on historic expenses), or replace their identity with "Former Member"?

A) Keep the member record with a `removed_at` timestamp — their name remains on historic expenses
B) Replace their display name with "Former Member" on historic expenses once removed
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Generation Checklist

Steps to execute after answers are received.

- [x] Step 1 — Generate `domain-entities.md` — all ORM entities, fields, relationships, constraints
- [x] Step 2 — Generate `business-rules.md` — all validation rules, guards, invariants per domain
- [x] Step 3 — Generate `business-logic-model.md` — detailed workflows for all 9 stories (US-1-1 to US-1-8 + US-2-7)
