# Business Logic Model — Unit 2: Balance Engine

All functions are pure (no I/O, no side effects). Input/output use only engine dataclasses and Decimal.

---

## Function: validate_split

**Stories**: US-2-1 to US-2-4 (validation gate before any split)

```
validate_split(split_type, total_amount, member_ids, split_details) -> ValidationResult

1. Check member_ids non-empty → error if empty
2. Check len(split_details) == len(member_ids) → error if mismatch
3. Check total_amount > 0 → error if not

4. SWITCH split_type:
   EQUAL:
     → always valid (no sum check)
   
   EXACT:
     → check all values ≥ 0
     → check sum(values) within 0.01 of total_amount
   
   PERCENTAGE:
     → check all values in [0, 100]
     → check sum(values) within 0.01 of 100
   
   RATIO:
     → check all values ≥ 0
     → check sum(values) > 0

5. Return ValidationResult(valid=len(errors)==0, errors=errors)
```

**PBT properties (PBT-03 invariant)**:
- Valid inputs always produce ValidationResult(valid=True)
- Inputs where sum != expected always produce ValidationResult(valid=False)
- Zero-ratio-sum always produces ValidationResult(valid=False)

---

## Function: compute_shares

**Stories**: US-2-1 (EQUAL), US-2-2 (EXACT), US-2-3 (PERCENTAGE), US-2-4 (RATIO)

```
compute_shares(split_type, total_amount, member_ids, split_details) -> list[MemberShare]

Precondition: validate_split() already called and returned valid=True

SWITCH split_type:

  EQUAL:
    1. base = (total_amount / len(members)).quantize(Decimal("0.01"), ROUND_DOWN)
    2. remainder = total_amount - (base * len(members))
    3. cents = int(remainder * 100)  # number of 1-cent increments to distribute
    4. Sort member_ids by str(uuid) for stable ordering
    5. For i, member_id in enumerate(sorted_members):
         extra = Decimal("0.01") if i < cents else Decimal("0")
         share = base + extra
       yield MemberShare(member_id, raw_value=None, computed_amount=share)

  EXACT:
    For each detail:
      yield MemberShare(member_id, raw_value=detail.value, computed_amount=detail.value)

  PERCENTAGE:
    1. For each detail (except last non-zero):
         amount = (detail.value / 100 * total_amount).quantize(Decimal("0.01"), ROUND_HALF_UP)
         yield MemberShare(member_id, raw_value=detail.value, computed_amount=amount)
    2. Last non-zero member gets: total_amount - sum(all others' computed_amount)
       (ensures exact sum)

  RATIO:
    1. total_ratio = sum(detail.value for all details)
    2. For zero-value members: yield MemberShare(member_id, raw_value=Decimal("0"), computed_amount=Decimal("0"))
    3. For non-zero members (except last):
         amount = (detail.value / total_ratio * total_amount).quantize(Decimal("0.01"), ROUND_HALF_UP)
         yield MemberShare(member_id, raw_value=detail.value, computed_amount=amount)
    4. Last non-zero: total_amount - sum(all non-zero others)

POSTCONDITION: sum(share.computed_amount) == total_amount  [checked by test/PBT]
```

**PBT properties**:
- **PBT-03 invariant**: `sum(computed_amount) == total_amount` for all valid inputs
- **PBT-03 invariant**: EQUAL split with equal ratios ≡ RATIO split with all-equal ratios
- **PBT-02 round-trip**: `validate_split(EXACT, total, ids, shares_from_compute_shares(EQUAL,...))` → valid
- **Oracle (PBT-05)**: For small inputs, brute-force exact arithmetic reference implementation

---

## Function: aggregate_balances

**Story**: US-2-5

```
aggregate_balances(expenses, settlements) -> BalanceMap

1. Initialize: balances: dict[str, dict[UUID, Decimal]] = {}

2. For each ExpenseRecord:
   currency = expense.currency
   Ensure balances[currency] exists (defaultdict)
   
   a. Credit payer: balances[currency][payer_id] += total_amount
      (total_amount = sum of all split computed_amounts for this expense)
   
   b. Debit each split member:
      balances[currency][member_id] -= computed_amount

3. For each SettlementRecord:
   currency = settlement.currency
   Ensure balances[currency] exists
   
   a. Payer's debt reduced (balance increases):
      balances[currency][payer_id] += amount
   
   b. Payee's credit reduced (balance decreases):
      balances[currency][payee_id] -= amount

4. Convert to BalanceMap:
   For each currency:
     Return [MemberBalance(member_id, net_amount) for member_id, net_amount in balances[currency].items()]

POSTCONDITION: For each currency, sum(net_amount) == 0  [conservation invariant, PBT-03]
```

**PBT properties**:
- **PBT-03 invariant**: `sum(b.net_amount for b in result[currency]) == 0` for all currencies
- **PBT-03 invariant**: Adding a settlement of amount A between members X and Y changes X by +A and Y by -A, all others unchanged
- **PBT-04 idempotency**: Calling aggregate_balances twice on same data returns same result

---

## Function: simplify_debts

**Story**: US-2-6

```
simplify_debts(balances: BalanceMap) -> SuggestionMap

For each currency in balances:

  1. Filter out members with abs(net_amount) < 0.01 (rounding tolerance, BR-ENG-DEBT-05)
  2. Separate into:
       creditors: [(net_amount, member_id)]  where net_amount > 0
       debtors:   [(abs(net_amount), member_id)]  where net_amount < 0

  3. If both lists empty → suggestions[currency] = []  (already settled)

  4. Convert to max-heaps (negate for Python's min-heap):
       Use sorted lists + greedy matching (equivalent, simpler for small n)

  5. Sort creditors descending by amount
     Sort debtors descending by abs(amount)

  6. While creditors and debtors non-empty:
       max_credit_amount, creditor_id = creditors[0]
       max_debt_amount,   debtor_id   = debtors[0]
       
       payment = min(max_credit_amount, max_debt_amount)
       
       Emit SettlementSuggestion(
           payer_id=debtor_id,
           payee_id=creditor_id,
           amount=payment,
           currency=currency
       )
       
       max_credit_amount -= payment
       max_debt_amount   -= payment
       
       Remove creditor if max_credit_amount < 0.01
       Remove debtor  if max_debt_amount   < 0.01
       Re-sort if amounts changed (or use heap operations)

  7. suggestions[currency] = emitted suggestions

POSTCONDITION: Applying all suggestions to input balances yields all-zero net amounts (PBT-05 oracle)
POSTCONDITION: len(suggestions[currency]) <= len(members_in_currency) - 1  (PBT-03 size bound)
```

**PBT properties**:
- **PBT-05 oracle**: apply all suggestions to original balances → all zeros
- **PBT-03 invariant**: result length ≤ n-1 for n members
- **PBT-03 invariant**: for 2 members (A owes B), exactly 1 suggestion emitted
- **PBT-05 oracle**: compare against brute-force reference (try all permutations for n ≤ 5)

---

## PBT Property Summary (PBT-01 identification)

| Function | Property Category | Rule |
|---|---|---|
| `compute_shares` (all types) | Invariant: sum = total | PBT-03 |
| `compute_shares` (EQUAL ≡ RATIO all-equal) | Commutativity / equivalence | PBT-03 |
| `aggregate_balances` | Invariant: conservation law sum = 0 | PBT-03 |
| `aggregate_balances` | Idempotency: pure function, same output | PBT-04 (advisory) |
| `simplify_debts` | Oracle: applying suggestions zeroes balances | PBT-05 |
| `simplify_debts` | Invariant: result length ≤ n-1 | PBT-03 |
| Split schemas ↔ engine dataclasses | Round-trip serialization | PBT-02 |
| Domain generators: Expense, Group, Member | Generator quality | PBT-07 |
