# Business Rules — Unit 2: Balance Engine

---

## Split Validation Rules (BR-ENG-VAL)

### BR-ENG-VAL-01: EQUAL split
- `split_details` must contain ≥ 1 member
- `value` field on each SplitDetail is ignored (may be None or any value)
- No sum check required — engine divides `total_amount` equally

### BR-ENG-VAL-02: EXACT split
- Every `value` must be ≥ 0
- `sum(value for all details)` must equal `total_amount` within tolerance `Decimal("0.01")`
- At least one detail must have `value > 0`

### BR-ENG-VAL-03: PERCENTAGE split
- Every `value` must be in range `[0, 100]`
- `sum(value for all details)` must equal `Decimal("100")` within tolerance `Decimal("0.01")`
- At least one detail must have `value > 0`

### BR-ENG-VAL-04: RATIO split
- Every `value` must be ≥ 0
- `sum(value for all details)` must be > 0 (at least one non-zero ratio)
- If all ratios are zero → validation error: "At least one member must have a non-zero ratio"

### BR-ENG-VAL-05: All split types
- `member_ids` list must not be empty
- `len(split_details)` must equal `len(member_ids)` (one detail per included member)
- `total_amount` must be > 0

---

## Share Computation Rules (BR-ENG-COMP)

### BR-ENG-COMP-01: EQUAL — rounding
- Base share = `total_amount / len(members)`, truncated to 2 decimal places
- Remainder = `total_amount - (base_share × len(members))`
- Distribute remainder as 1-cent increments to members in stable order (sorted by `member_id` UUID string)
- **Invariant**: `sum(computed_amount)` == `total_amount` exactly

### BR-ENG-COMP-02: EXACT — pass-through
- `computed_amount` = provided `value` for each member
- **Invariant**: `sum(computed_amount)` == `total_amount` within 1 cent (validated before entry)

### BR-ENG-COMP-03: PERCENTAGE — proportional rounding
- `computed_amount` = `(value / 100) × total_amount`, rounded to 2 decimal places using `ROUND_HALF_UP`
- Adjust last member's share so `sum == total_amount` exactly
- **Invariant**: `sum(computed_amount)` == `total_amount` exactly after adjustment

### BR-ENG-COMP-04: RATIO — proportional rounding
- `total_ratio` = `sum(value for all details)`
- `computed_amount` = `(value / total_ratio) × total_amount`, rounded to 2 decimal places using `ROUND_HALF_UP`
- Adjust last non-zero member's share so `sum == total_amount` exactly
- Members with `value == 0` receive `computed_amount = Decimal("0")`
- **Invariant**: `sum(computed_amount)` == `total_amount` exactly

---

## Balance Aggregation Rules (BR-ENG-BAL)

### BR-ENG-BAL-01: Per-currency isolation
- Expenses and settlements in different currencies are never aggregated together
- Output is keyed by ISO 4217 currency code; each currency produces its own `list[MemberBalance]`

### BR-ENG-BAL-02: Payer credit
- For each expense: the payer receives credit for the total amount (`+total_amount`)
- Then each split member (including payer if in split) is debited their `computed_amount`
- Net effect: payer's balance = `total_amount - payer_computed_amount`

### BR-ENG-BAL-03: Settlement application
- For each settlement: payer's balance increases by `amount` (they paid, reducing their debt)
- Payee's balance decreases by `amount` (they received, reducing what's owed to them)

### BR-ENG-BAL-04: Conservation invariant
- `sum(net_amount for all MemberBalance in a currency)` == `Decimal("0")` for all currencies
- This invariant must hold after processing any combination of expenses and settlements

### BR-ENG-BAL-05: Members not in group
- Engine only processes member IDs provided to it — it does not query the database
- Members not appearing in any expense or settlement will not appear in the output

---

## Debt Simplification Rules (BR-ENG-DEBT)

### BR-ENG-DEBT-01: Algorithm — minimum transfer
- Goal: find the smallest set of directed payments that brings all balances to zero
- Algorithm: greedy min-heap approach
  1. Separate members into creditors (net > 0) and debtors (net < 0)
  2. Sort creditors descending by net_amount; debtors ascending (most negative first)
  3. While both lists non-empty:
     - Take largest creditor (max_credit) and largest debtor (max_debt)
     - Payment = min(max_credit, abs(max_debt))
     - Emit SettlementSuggestion(payer=debtor, payee=creditor, amount=payment)
     - Reduce both by payment; remove if zero, return to heap otherwise
- **Invariant**: applying all suggestions to balances yields all-zero net_amounts

### BR-ENG-DEBT-02: Result size bound
- For n members, at most n-1 suggestions are emitted

### BR-ENG-DEBT-03: Per-currency
- Algorithm runs independently per currency; suggestions are grouped by currency

### BR-ENG-DEBT-04: Already-settled
- If all `net_amount == 0` for a currency, return empty list for that currency

### BR-ENG-DEBT-05: Rounding tolerance
- Members with `abs(net_amount) < Decimal("0.01")` are treated as balanced (avoid floating-point ghost debts)
