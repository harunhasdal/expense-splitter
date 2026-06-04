# Personas — Expense Splitter

## Persona 1: Group Creator

**Name**: Alex Chen  
**Role**: Group Creator / Group Owner  
**Age**: 28  
**Occupation**: Software engineer, frequent traveller

### Goals
- Quickly set up a shared expense group before or during a trip/event
- Keep the group tidy — archive old groups, remove members who've left
- Get a clear picture of who owes what and be able to trigger settlements

### Frustrations
- Chasing people for money is awkward; wants the app to make settlement suggestions obvious
- Hates re-entering data — wants OAuth2 one-click sign-in, no passwords to remember
- Finds multi-currency trips confusing; wants balances separated by currency, not converted arbitrarily

### Technical Comfort
High — comfortable with web apps, OAuth2 login flows, and reading structured data in tables

### Permissions (vs Group Member)
- Create, rename, and archive groups
- Add and remove members
- Soft-delete (archive) any expense in the group
- All Group Member actions

### Relevant Epics
- Epic 1 — API Endpoints (group management, member management)
- Epic 2 — Business Logic (debt simplification, balance aggregation)
- Epic 3 — Frontend Screens (all screens)

---

## Persona 2: Group Member

**Name**: Jordan Kim  
**Role**: Regular Group Member  
**Age**: 25  
**Occupation**: Graphic designer, shares a flat with 3 others

### Goals
- Log an expense in under 30 seconds after paying for something
- See at a glance exactly what they owe (and to whom), without doing mental arithmetic
- Mark a settlement as done and have their balance update immediately

### Frustrations
- Confused by complex split interfaces — wants split type selection to be clear and forgiving (validation before save)
- Doesn't want to accidentally submit an expense with the wrong split (e.g., percentages not summing to 100%)
- Wants confidence that their past expenses are safe — won't be deleted by someone else

### Technical Comfort
Medium — comfortable with standard web apps but not technical; expects clear error messages

### Permissions (vs Group Creator)
- Log and view expenses in groups they belong to
- Record settlements
- Cannot archive/delete a group or remove other members

### Relevant Epics
- Epic 1 — API Endpoints (expense endpoints, settlement endpoint)
- Epic 2 — Business Logic (split calculation, balance view)
- Epic 3 — Frontend Screens (expense form, dashboard, settlement flow)
