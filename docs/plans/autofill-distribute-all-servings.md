# Improve Auto-Fill: Distribute All Servings

## Context

After running auto-fill on the Utah 2026 trip (7 days: half + 5 full + half), 7 items have unallocated servings totaling ~1,345 calories and ~12 oz of food that should be distributed but isn't. Two algorithmic limitations cause this:

1. **Drink mixes use round-robin instead of independent distribution.** Three breakfast drink items (Tea/coffee 6srv, Athletic greens 6srv, Carnation 3srv) share 6 eligible days via round-robin — each item gets only 2 days. But a hiker wants coffee AND greens AND carnation every morning. Gatorlyte (12srv, 7 eligible days) also leaves 5 unallocated.

2. **Snacks/lunch items capped at 1 serving per item per day.** Babybel has 11 servings but only 5 eligible lunch days, so 6 sit unallocated. Similarly Tortilla (6srv, 1 left) and PB tube (7srv, 2 left). The algorithm should assign 2+/day when servings exceed eligible days.

## Changes

### 1. `distribute_drink_mixes` — independent per-item distribution

**File:** `backend/services/autofill.py` (lines 144-203)

Replace the round-robin loop (lines 180-201) with per-item independent distribution. For each item in a type group:
- Assign to all eligible days: `base = servings // num_days`, `leftover = servings % num_days`
- Every eligible day gets `base` servings; first `leftover` days get `base + 1`
- Result: each drink mix item covers its eligible days independently. Coffee on every breakfast day, greens on every breakfast day, etc.
- Keep the shortage warning (fire when an item has fewer servings than eligible days)

Existing tests unaffected — they all test exact-fit or shortage scenarios where the new behavior produces identical results.

### 2. `distribute_snacks` — multi-pass distribution

**File:** `backend/services/autofill.py` (lines 88-141)

Replace the single-pass cap (`fill_count = min(int(remaining), num_days)`) with multi-pass:
- Calculate `base = int(servings) // num_days`, `leftover = int(servings) % num_days`
- If `base >= 1`: all eligible days get `base`, plus `leftover` days get an extra 1 (using existing offset/stride logic for which days get extras)
- If `base == 0`: same as current behavior — pick `leftover` evenly-spaced days, assign 1 each
- Keep rotating offset so different items' leftovers land on different days

### 3. Update tests

**File:** `backend/tests/test_daily_plan.py`

- [x] **Update `test_unallocated_pool` (line 454):** Currently expects 10 nuts across 3 eligible days = 7 remaining. New behavior: all 10 distributed (3+3+4 across 3 days), 0 remaining. Change assertion to verify Mixed Nuts not in unallocated.
- [x] **Verify `test_unallocated_summary` (line 540):** Crackers 10srv on a 3-day trip (1 eligible lunch day) — now all 10 go to that 1 day. Meals still have unallocated servings, so `count > 0` still holds.
- [x] **Add `test_snack_multi_pass`:** 10 servings across 3 eligible days — all distributed, per-day servings sum to 10.
- [x] **Add `test_drink_mix_independent`:** Two breakfast drink items each cover all eligible days independently.
- [x] **Add `test_drink_mix_excess_servings`:** 10 electrolyte servings across 4 days — all distributed.

### 4. Update spec

**File:** `docs/specs/09-daily-meal-plan.md`

Update the Auto-Fill Algorithm section:
- Snacks: "distribute servings evenly across eligible days; multiple per day when servings exceed days"
- Drink mixes: "each item distributed independently; multiple items of same type all appear on the same day"

## Verification

1. `cd backend && venv/bin/pytest tests/test_daily_plan.py -v` — all tests pass
2. Re-run auto-fill on Utah 2026 via API and verify unallocated pool is empty (or near-empty for fractional remainders)
3. Spot-check that per-day calorie distribution is reasonable
