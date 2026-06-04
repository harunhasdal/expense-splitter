# User Stories — Expense Splitter

Stories are organized by technical layer. Each story ID follows the format `US-[epic#]-[story#]`.

Acceptance criteria use Given/When/Then format (3–5 scenarios per story).  
UI/UX notes are included where applicable.  
Security rule references are included where applicable.

---

# Epic 1 — API Endpoints

## US-1-1: OAuth2 Sign-In via Google or GitHub

**As a** Group Creator or Group Member,  
**I want to** sign in using my Google or GitHub account,  
**So that** I don't have to manage a separate password.

**Acceptance Criteria:**

*Scenario 1 — Successful sign-in*  
Given I am on the sign-in page and I click "Sign in with Google"  
When I complete the Google OAuth2 flow and grant the required scopes  
Then I am redirected to my dashboard and a JWT session token is issued

*Scenario 2 — Successful sign-in via GitHub*  
Given I click "Sign in with GitHub"  
When I complete the GitHub OAuth2 flow  
Then I am signed in and my profile is created (or matched to an existing account by email)

*Scenario 3 — User denies OAuth2 consent*  
Given I begin the OAuth2 flow and click "Deny" on the consent screen  
When I am redirected back to the app  
Then I see a clear "Sign-in cancelled" message and remain unauthenticated

*Scenario 4 — Invalid or expired state parameter*  
Given the OAuth2 callback receives an invalid or replayed `state` parameter  
When the API processes the callback  
Then it returns 400 Bad Request and logs the event (SECURITY-08, SECURITY-12)

*Scenario 5 — Session expiry*  
Given my JWT has expired  
When I make any authenticated API request  
Then I receive 401 Unauthorized and am redirected to the sign-in page

**UI/UX Notes:** Sign-in screen shows two buttons ("Continue with Google", "Continue with GitHub") centered on a minimal page with the app logo. No email/password fields.  
**Security:** SECURITY-08 (token validation), SECURITY-12 (session management)

---

## US-1-2: Create a Group

**As a** Group Creator,  
**I want to** create a new expense group with a name and optional description,  
**So that** I can start tracking shared expenses for an event or household.

**Acceptance Criteria:**

*Scenario 1 — Successful creation*  
Given I am authenticated and submit a valid group name (1–100 characters)  
When the API receives `POST /groups`  
Then the group is created, I am automatically added as owner/member, and the API returns 201 with the new group ID

*Scenario 2 — Duplicate group name (same owner)*  
Given I already have a group named "Greece Trip"  
When I create another group also named "Greece Trip"  
Then the API accepts it (names are not unique globally) and returns 201

*Scenario 3 — Missing required field*  
Given I submit a create-group request with an empty name  
When the API validates the input  
Then it returns 400 Bad Request with a field-level error message (SECURITY-05)

*Scenario 4 — Name too long*  
Given I submit a group name of 200 characters  
When the API validates the input  
Then it returns 400 with "Group name must not exceed 100 characters"

**UI/UX Notes:** "New Group" button on dashboard opens a slide-over panel with a name field and optional description textarea. Submit button disabled until name is non-empty.  
**Security:** SECURITY-05 (input validation)

---

## US-1-3: Add Members to a Group

**As a** Group Creator,  
**I want to** invite members to a group by email address,  
**So that** they can contribute expenses and see balances.

**Acceptance Criteria:**

*Scenario 1 — Add a registered user*  
Given a user with email `bob@example.com` exists  
When I submit `POST /groups/{id}/members` with that email  
Then Bob is added as a member and the group member list is updated

*Scenario 2 — Add an unregistered email*  
Given no user exists with email `carol@example.com`  
When I add that email  
Then a placeholder member entry is created (linked to that email) and the group member list shows "Carol (pending)"

*Scenario 3 — Non-owner attempts to add a member*  
Given Jordan is a Group Member (not owner) of group 42  
When Jordan submits `POST /groups/42/members`  
Then the API returns 403 Forbidden (SECURITY-08)

*Scenario 4 — Adding duplicate member*  
Given Bob is already a member of the group  
When I submit his email again  
Then the API returns 409 Conflict with "User is already a member of this group"

**UI/UX Notes:** "Add member" text input in the group settings panel, with an "Add" button. Shows current member list as chips below the input.  
**Security:** SECURITY-08 (function-level authorization)

---

## US-1-4: Remove a Member from a Group

**As a** Group Creator,  
**I want to** remove a member from a group,  
**So that** former participants no longer appear in balance calculations.

**Acceptance Criteria:**

*Scenario 1 — Successful removal with zero balance*  
Given a member has a zero net balance  
When I submit `DELETE /groups/{id}/members/{memberId}`  
Then the member is soft-removed and no longer appears in future expense suggestions

*Scenario 2 — Removal with non-zero balance*  
Given a member has an outstanding balance (owes or is owed money)  
When I attempt removal  
Then the API returns 409 Conflict with "Member has unsettled balance; settle before removing"

*Scenario 3 — Non-owner attempts removal*  
Given Jordan (Group Member) tries to remove another member  
When the request hits the API  
Then it returns 403 Forbidden (SECURITY-08)

*Scenario 4 — Self-removal by owner*  
Given I am the sole owner  
When I attempt to remove myself  
Then the API returns 409 with "Cannot remove sole group owner"

**UI/UX Notes:** Remove icon (×) next to each member chip; confirmation modal before submission.

---

## US-1-5: Archive a Group

**As a** Group Creator,  
**I want to** archive a group when it is no longer active,  
**So that** it is hidden from my main dashboard without deleting historical records.

**Acceptance Criteria:**

*Scenario 1 — Successful archive*  
Given all balances in the group are zero  
When I submit `PATCH /groups/{id}` with `{"archived": true}`  
Then the group is flagged archived, disappears from the active dashboard, but all expenses remain queryable

*Scenario 2 — Archive with non-zero balances*  
Given the group has outstanding debts  
When I attempt to archive it  
Then the API returns 409 Conflict with "Group has unsettled balances"

*Scenario 3 — Non-owner attempts archive*  
When a Group Member submits the archive request  
Then the API returns 403 Forbidden (SECURITY-08)

**UI/UX Notes:** "Archive Group" action in group settings, clearly separated from primary actions. Archived groups accessible via "Show archived" toggle on dashboard.

---

## US-1-6: Log an Expense

**As a** Group Member or Group Creator,  
**I want to** record an expense I paid on behalf of the group,  
**So that** the system tracks what I am owed.

**Acceptance Criteria:**

*Scenario 1 — Successful expense creation (equal split)*  
Given I am a member of group 7 and submit a valid expense payload  
When `POST /groups/7/expenses` is called  
Then the expense is stored, returns 201, and the balance engine recalculates group balances

*Scenario 2 — Non-member tries to log an expense*  
Given Frank is not a member of group 7  
When Frank submits `POST /groups/7/expenses`  
Then the API returns 403 Forbidden (SECURITY-08)

*Scenario 3 — Invalid split (percentages do not sum to 100)*  
Given I submit a percentage split where the values sum to 95%  
When the API validates the request  
Then it returns 400 with "Split percentages must sum to 100"

*Scenario 4 — Invalid split (exact amounts do not match total)*  
Given I submit an exact-amount split where the member shares sum to £50 but the expense amount is £60  
When the API validates  
Then it returns 400 with "Split amounts must equal the total expense amount"

*Scenario 5 — Expense with future date*  
Given I submit an expense with a date 30 days in the future  
When the API validates  
Then it returns 400 with "Expense date cannot be in the future"

**Security:** SECURITY-05 (input validation), SECURITY-08 (object-level authorization)

---

## US-1-7: Record a Settlement

**As a** Group Member or Group Creator,  
**I want to** record that I have paid another member the amount I owe them,  
**So that** the group balances are updated and the debt is cleared.

**Acceptance Criteria:**

*Scenario 1 — Successful settlement*  
Given Alice owes Bob £30 in group 7  
When Alice submits `POST /groups/7/settlements` with `{"payer": Alice, "payee": Bob, "amount": 30, "currency": "GBP"}`  
Then the settlement is recorded immutably, balances update, and the API returns 201

*Scenario 2 — Settlement amount exceeds outstanding debt*  
Given Alice owes Bob £30  
When Alice records a £50 settlement  
Then the API accepts it (over-payment is valid; balances reflect net credit)

*Scenario 3 — Non-member records settlement*  
Given Frank is not in the group  
When Frank submits a settlement for group 7  
Then the API returns 403 Forbidden (SECURITY-08)

*Scenario 4 — Zero-amount settlement rejected*  
When a settlement with `amount: 0` is submitted  
Then the API returns 400 with "Settlement amount must be greater than zero"

**UI/UX Notes:** "Mark as settled" button on dashboard settlement suggestion card pre-fills payer, payee, and amount.

---

## US-1-8: View Group Expenses

**As a** Group Member or Group Creator,  
**I want to** retrieve the list of expenses for a group with optional filters,  
**So that** I can review what has been recorded.

**Acceptance Criteria:**

*Scenario 1 — Successful retrieval*  
Given I am a member of group 7  
When I call `GET /groups/7/expenses`  
Then I receive a paginated list of all non-archived expenses with payer, amount, split, and date

*Scenario 2 — Filter by payer*  
Given I add `?payer_id=alice` to the query  
When the API processes the request  
Then only Alice's expenses are returned

*Scenario 3 — Non-member access blocked*  
Given Frank is not in group 7  
When Frank calls `GET /groups/7/expenses`  
Then the API returns 403 Forbidden (SECURITY-08)

*Scenario 4 — Archived expenses excluded by default*  
Given the group has 10 active and 2 archived expenses  
When I call `GET /groups/7/expenses` without filter  
Then only the 10 active expenses are returned; archived are excluded unless `?include_archived=true`

---

# Epic 2 — Business Logic

## US-2-1: Equal Split Calculation

**As a** Group Member,  
**I want** the system to automatically split an expense equally among selected members,  
**So that** I don't have to manually compute each person's share.

**Acceptance Criteria:**

*Scenario 1 — Even division*  
Given an expense of £60 split equally among 3 members  
When the balance engine processes it  
Then each member's share is exactly £20.00

*Scenario 2 — Remainder distribution*  
Given an expense of £10 split equally among 3 members  
When the engine computes shares  
Then shares are £3.34, £3.33, £3.33 (remainder cent allocated to first member alphabetically)

*Scenario 3 — Single-member group*  
Given a group with only the payer  
When an equal-split expense is logged  
Then the payer's net balance does not change (they owe themselves nothing)

*Scenario 4 — Subset of members selected*  
Given a 5-member group and the expense only applies to 3 members  
When the split is calculated  
Then only the 3 selected members' balances change

**Security:** N/A (pure computation)  
**PBT:** PBT-03 invariant — total of all shares always equals expense amount (Hypothesis)

---

## US-2-2: Exact Amount Split

**As a** Group Member,  
**I want to** specify the exact amount each member owes for an expense,  
**So that** unequal contributions are recorded accurately.

**Acceptance Criteria:**

*Scenario 1 — Valid exact split*  
Given I pay £90 and specify Alice £50, Bob £40  
When the expense is submitted  
Then each member's share is stored as specified and their balances updated accordingly

*Scenario 2 — Amounts don't sum to total (rejected at API layer — covered in US-1-6)*  
Given I specify shares summing to £80 for a £90 expense  
When the API validates  
Then 400 is returned (validation already covered in US-1-6 Scenario 4)

*Scenario 3 — Zero share for a member*  
Given I include a member with a £0 share  
When the expense is saved  
Then that member's balance is unchanged

**PBT:** PBT-03 invariant — sum of exact shares equals expense total

---

## US-2-3: Percentage Split Calculation

**As a** Group Member,  
**I want to** split an expense by percentage,  
**So that** members who consume different proportions pay different amounts.

**Acceptance Criteria:**

*Scenario 1 — Valid percentage split*  
Given an expense of £200 with Alice 50%, Bob 30%, Carol 20%  
When the engine calculates shares  
Then Alice owes £100, Bob £60, Carol £40

*Scenario 2 — Rounding with fractional cents*  
Given an expense of £100 with three members each at 33.33%  
When shares are computed  
Then shares sum to exactly £100 (rounding applied to last member)

*Scenario 3 — Percentages not summing to 100 (rejected at API layer — covered in US-1-6)*  
Already covered in US-1-6 Scenario 3.

**PBT:** PBT-03 invariant — computed shares sum to expense total within £0.01 rounding tolerance

---

## US-2-4: Custom Ratio Split

**As a** Group Member,  
**I want to** split an expense using custom ratios (e.g., 1:2:3),  
**So that** members with proportionally different usage pay accordingly.

**Acceptance Criteria:**

*Scenario 1 — Valid ratio split*  
Given an expense of £120 with Alice ratio 1, Bob ratio 2, Carol ratio 3 (total ratio 6)  
When the engine computes shares  
Then Alice owes £20, Bob £40, Carol £60

*Scenario 2 — All-equal ratios*  
Given all members have ratio 1  
When shares are computed  
Then the result equals an equal split

*Scenario 3 — Zero ratio for a member*  
Given one member has ratio 0  
When shares are computed  
Then that member owes £0 and the full amount is split among non-zero-ratio members

*Scenario 4 — All-zero ratios (invalid)*  
Given all members have ratio 0  
When the API validates  
Then it returns 400 with "At least one member must have a non-zero ratio"

**PBT:** PBT-03 invariant — computed shares sum to expense total; PBT-02 round-trip for ratio serialization/deserialization

---

## US-2-5: Balance Aggregation

**As a** Group Member or Group Creator,  
**I want** the system to compute my net balance across all expenses in a group,  
**So that** I can see at a glance what I owe or am owed.

**Acceptance Criteria:**

*Scenario 1 — Positive balance (owed money)*  
Given Alice paid £90 in a 3-person equal-split group and no settlements exist  
When balances are calculated  
Then Alice's balance is +£60 (owed by others)

*Scenario 2 — Settlement reduces balance*  
Given Alice is owed £60 and Bob records a £30 settlement to Alice  
When balances are recalculated  
Then Alice's balance is +£30, Bob's is reduced by £30

*Scenario 3 — Multi-currency group*  
Given the group has expenses in GBP and JPY  
When balances are returned  
Then the API returns separate balance objects per currency — no aggregation across currencies

*Scenario 4 — Group with no expenses*  
Given a newly created group  
When balances are requested  
Then all member balances are zero

**PBT:** PBT-03 invariant — sum of all member net balances in a group always equals zero (conservation law)

---

## US-2-6: Debt Simplification (Minimum Settlement Suggestions)

**As a** Group Member or Group Creator,  
**I want** the app to suggest the minimum number of payments needed to settle all debts,  
**So that** I don't have to make more transfers than necessary.

**Acceptance Criteria:**

*Scenario 1 — Simple 3-person case*  
Given Alice owes Bob £20 and Bob owes Carol £20  
When the simplification algorithm runs  
Then the suggestion is: Alice pays Carol £20 (1 transfer, not 2)

*Scenario 2 — Maximum simplification*  
Given a 5-person group with 8 individual debts  
When the algorithm runs  
Then at most 4 transfer suggestions are returned (n-1 for n people)

*Scenario 3 — Already-zero balance*  
Given all member balances are zero  
When suggestions are requested  
Then an empty list is returned

*Scenario 4 — Multi-currency*  
Given debts exist in both GBP and EUR  
When simplification runs  
Then suggestions are produced per currency independently; no cross-currency netting

**PBT:** PBT-05 oracle — compare algorithm output against a brute-force reference implementation; PBT-03 invariant — all suggested payments clear all debts when applied

---

## US-2-7: Expense Immutability Enforcement

**As a** Group Member,  
**I want to** be confident that recorded expenses cannot be silently altered or deleted,  
**So that** the audit trail is trustworthy.

**Acceptance Criteria:**

*Scenario 1 — Hard delete rejected*  
Given any authenticated user submits `DELETE /groups/{id}/expenses/{expenseId}`  
When the API processes the request  
Then it returns 405 Method Not Allowed (hard delete not permitted)

*Scenario 2 — Soft archive by owner*  
Given the Group Creator submits `PATCH /expenses/{id}` with `{"archived": true}`  
When the API processes it  
Then the expense is flagged archived but remains in the database and is retrievable with `?include_archived=true`

*Scenario 3 — Update attempt rejected*  
Given any user submits `PUT /expenses/{id}` with modified fields  
When the API processes it  
Then it returns 405 Method Not Allowed (updates not permitted after creation)

*Scenario 4 — Audit log entry present*  
Given an expense is archived by the owner  
When the audit log is checked  
Then an entry exists with actor identity, timestamp, and action "archived" (SECURITY-13)

**Security:** SECURITY-13 (data integrity), SECURITY-08 (authorization)

---

# Epic 3 — Frontend Screens

## US-3-1: Sign-In Screen

**As a** visitor,  
**I want to** see a clear sign-in screen when I am not authenticated,  
**So that** I can sign in with one click using my existing Google or GitHub account.

**Acceptance Criteria:**

*Scenario 1 — Unauthenticated redirect*  
Given I navigate to any protected route while unauthenticated  
When the app checks my session  
Then I am redirected to `/signin`

*Scenario 2 — Successful sign-in redirect*  
Given I click "Continue with Google" and complete OAuth2  
When the session token is issued  
Then I am redirected to my dashboard (or the originally requested URL)

*Scenario 3 — Error state displayed*  
Given the OAuth2 flow fails (e.g., network error)  
When I land back on the sign-in page  
Then a generic "Sign-in failed, please try again" message is shown with no technical details (SECURITY-09)

**UI/UX Notes:** Centered card layout: app logo + tagline, two provider buttons (Google, GitHub), no other form fields. Uses `X-Frame-Options: DENY` — page cannot be embedded in an iframe (SECURITY-04).  
**Security:** SECURITY-04 (security headers), SECURITY-09 (generic error messages)

---

## US-3-2: Group Dashboard

**As a** Group Member or Group Creator,  
**I want to** see all my active groups with current balance summaries,  
**So that** I can immediately identify where I have outstanding debts.

**Acceptance Criteria:**

*Scenario 1 — Groups listed with balance summary*  
Given I have 3 active groups  
When I load `/dashboard`  
Then each group card shows: group name, my net balance (highlighted red if I owe, green if owed), and member count

*Scenario 2 — No groups state*  
Given I have no groups  
When I load the dashboard  
Then I see an empty-state illustration with a "Create your first group" call-to-action button

*Scenario 3 — Archived groups hidden by default*  
Given I have 2 active and 1 archived group  
When the dashboard loads  
Then only the 2 active groups appear; a "Show archived" link reveals the third

*Scenario 4 — Multi-currency balance summary*  
Given a group has balances in both GBP and EUR  
When the group card is rendered  
Then both currency balances are shown stacked (e.g., "+£40 / -€15"), not merged

**UI/UX Notes:** Responsive card grid (2 columns on desktop, 1 on mobile). Balance badge uses semantic colour: red = I owe, green = I'm owed, grey = zero. "New Group" FAB (floating action button) at bottom-right.

---

## US-3-3: Group Detail / Balance View

**As a** Group Member or Group Creator,  
**I want to** see the full balance breakdown for a group and the settlement suggestions,  
**So that** I know exactly who owes whom and how to settle up.

**Acceptance Criteria:**

*Scenario 1 — Balance table shown*  
Given a group has 4 members with non-zero balances  
When I navigate to `/groups/{id}`  
Then a balance table lists each member, their net amount, and direction (owes / is owed)

*Scenario 2 — Settlement suggestions listed*  
Given the debt-simplification algorithm has run  
When the page loads  
Then a "Settle Up" section shows the minimum transfers as action cards (e.g., "You owe Bob £30 → Mark as settled")

*Scenario 3 — All settled state*  
Given all balances are zero  
When the page loads  
Then the Settle Up section shows "All settled up!" with a checkmark

*Scenario 4 — Per-currency display*  
Given debts exist in GBP and JPY  
When the balance view renders  
Then separate sections exist for each currency; no aggregation across currencies

**UI/UX Notes:** Tab bar: "Balances" | "Expenses". Balance table above the fold; settlement cards in a scrollable list below. Each settlement card has a single "Mark settled" button (triggers US-1-7).

---

## US-3-4: Expense Entry Form

**As a** Group Member or Group Creator,  
**I want to** fill in an expense form with a split type selector,  
**So that** I can log a new expense quickly and confidently.

**Acceptance Criteria:**

*Scenario 1 — Form submission success*  
Given I complete all required fields and select "Equal split"  
When I submit the form  
Then the expense is recorded, a success toast is shown, and the balance view updates immediately

*Scenario 2 — Split type selector changes the sub-form*  
Given I select "Percentage" from the split type dropdown  
When the form re-renders  
Then each member row shows a percentage input field with a running sum showing current total

*Scenario 3 — Validation prevents invalid submit*  
Given I enter percentages summing to 95%  
When I attempt to submit  
Then the submit button remains disabled and an inline error "Percentages must sum to 100%" is shown — no API call made

*Scenario 4 — Currency field*  
Given I select "JPY" from the currency picker  
When I enter the amount  
Then the amount field switches to integer-only input (JPY has no minor unit)

*Scenario 5 — Member subset selection*  
Given the group has 5 members and I untick 2  
When I submit an equal split  
Then only the 3 ticked members are included in the split

**UI/UX Notes:** Full-page slide-over on desktop; bottom sheet on mobile. Fields: Description (text), Amount (numeric), Currency (ISO picker), Date (date picker, defaults to today), Payer (dropdown, defaults to me), Split Type (segmented control: Equal | Exact | Percentage | Ratio), member checkboxes with per-member input when not Equal. Submit button is sticky at the bottom.

---

## US-3-5: Settlement Completion Flow

**As a** Group Member,  
**I want to** mark a suggested settlement as complete with one click,  
**So that** the group balances update immediately without any extra data entry.

**Acceptance Criteria:**

*Scenario 1 — One-click mark settled*  
Given I see a settlement card "You owe Bob £30 in GBP"  
When I click "Mark as settled"  
Then a confirmation modal shows the pre-filled details; on confirm, the settlement is recorded and the card disappears

*Scenario 2 — Confirmation modal prevents accidental tap*  
Given I accidentally tap "Mark as settled"  
When the modal appears  
Then I can dismiss it without recording anything

*Scenario 3 — Optimistic UI update*  
Given the settlement API call is in-flight  
When the modal is confirmed  
Then the card immediately enters a "settling…" loading state; on success it is removed; on failure it reverts with an error message

*Scenario 4 — Custom amount settlement*  
Given I want to settle only part of what I owe  
When I click "Settle custom amount" in the modal  
Then an amount field appears pre-filled with the suggested amount, editable before confirmation

**UI/UX Notes:** Settlement card: payer avatar → arrow → payee avatar, amount badge, "Mark as settled" primary button. Modal uses the app's standard confirmation dialog component with "Cancel" (secondary) and "Confirm" (primary, destructive-positive colour).

---

## US-3-6: Expense List and Search

**As a** Group Member or Group Creator,  
**I want to** browse and search the expense history for a group,  
**So that** I can review what was spent and by whom.

**Acceptance Criteria:**

*Scenario 1 — Expense list rendered*  
Given a group has 20 expenses  
When I view the "Expenses" tab  
Then expenses are listed in reverse chronological order, paginated (20 per page)

*Scenario 2 — Search by description*  
Given I type "hotel" in the search field  
When results update  
Then only expenses containing "hotel" in their description are shown

*Scenario 3 — Filter by payer*  
Given I select "Alice" from the payer filter dropdown  
When the list updates  
Then only Alice's expenses appear

*Scenario 4 — Archived expense indicator*  
Given I enable "Show archived" toggle  
When archived expenses appear  
Then each archived expense row has a strikethrough style and an "Archived" badge

**UI/UX Notes:** Search bar at top of Expenses tab with a payer filter pill. List rows: description (truncated), payer avatar, amount + currency, date, split-type chip (Equal/Exact/%). Tapping a row opens a read-only expense detail drawer (no edit capability — immutability).

---

## Requirement Traceability

| Requirement | Covered By |
|---|---|
| FR-01 Group Management | US-1-2, US-1-5, US-3-2, US-3-3 |
| FR-02 Member Management | US-1-3, US-1-4 |
| FR-03 Expense Recording | US-1-6, US-2-7, US-3-4 |
| FR-04 Split Types | US-1-6, US-2-1, US-2-2, US-2-3, US-2-4, US-3-4 |
| FR-05 Balance Calculation | US-2-5, US-2-6, US-3-3 |
| FR-06 Settlement Flow | US-1-7, US-3-5 |
| FR-07 Dashboard & UI | US-3-2, US-3-3, US-3-4, US-3-5, US-3-6 |
| FR-08 Multi-Currency | US-1-6, US-2-5, US-2-6, US-3-3, US-3-4 |
| FR-09 Audit Trail | US-2-7, US-1-7 |
| Auth (NFR-02) | US-1-1, US-3-1 |
