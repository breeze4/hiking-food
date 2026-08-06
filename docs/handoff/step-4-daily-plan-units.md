# Step 4 — Daily Plan Integration for Snack Units — Handoff

Ground truth for plans `2026-08-06-05` and `-06`. It reflects what shipped, not what the
plan proposed.

Parent spec: [Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md).
Plan: [Daily Plan Integration for Snack Units](../plans/2026-08-06-04-daily-plan-units.md).
Builds on: [Step 1 handoff](step-1-snack-mode-schema.md), [Step 2 handoff](step-2-snack-unit-library.md),
[Step 3 handoff](step-3-trip-unit-selections.md).

## 1. The rules that matter for every later plan

- **`snack_unit` is now a first-class assignment source type.** `source_id` is a
  `trip_snack_units.id`. It rides the same `TripDayAssignment` table, the same three REST
  endpoints, and the same allocation accounting as `meal` and `snack`. No migration: the
  column is TEXT.
- **On a structured trip, only units fill `morning_snacks` / `afternoon_snacks`.** A
  `TripSnack` row sitting in the `snacks` slot is skipped by auto-fill and waits in the
  unallocated pool. Lunch snacks and drink mixes flow exactly as they always did.
- **Quota math is still `snack_units.unit_quota`.** `autofill.py` imports nothing; the
  per-day quota is handed to it by `daily_plan_queries._autofill_inputs`.
- **The legacy path is byte-identical**, pinned by a snapshot captured against the
  pre-change tree (§6).

## 2. Distribution — `autofill.distribute_snack_units(days, per_day_quota, trip_units, unit_weights)`

`backend/services/autofill.py`. Returns the usual assignment dicts.

### Deal order (variety)

`_unit_deal_order` sorts selections heaviest-first then by id — the same key
`distribute_snacks` uses — then deals **one unit per selection per pass**, round-robin,
rather than a whole selection at a time. Three bags of 4 give `A B C A B C …`, so a full day
draws three types instead of four of one bag.

### Day capacity

`_unit_day_capacity` starts from `per_day_quota` (i.e. `unit_quota(trip)["per_day"]`) and:

- **under quota** — capacities stand; days fill in order and the trailing days stay empty.
  Nothing lands in the unallocated pool, because every selected unit was placed.
- **over quota** — the surplus rides on top, `base = surplus // days` for everyone plus
  evenly-spaced single extras (`stride = days / leftover`), the same shape as a snack's
  leftover servings. Verified: 16 units on a `[2, 4, 4, 2]` quota → `[3, 5, 5, 3]`.

### Morning / afternoon split

Within a day the units alternate `morning_snacks`, `afternoon_snacks`, `morning_snacks`, …
so the split is `ceil/floor` and an odd quota favors the morning:

| Day quota | Morning | Afternoon |
|---|---|---|
| 4 | 2 | 2 |
| 3 | 2 | 1 |
| 2 | 1 | 1 |
| 1 | 1 | 0 |

**`SLOT_RULES` does not gate these two slots for units.** A first-partial day gets morning
units and a last-partial day gets afternoon units, because the day's quota was already
scaled down by the fraction and the spec calls for 1 + 1 on a half day. Legacy `TripSnack`
distribution still honors `SLOT_RULES` untouched.

Same-day, same-slot repeats of one selection are merged into a single assignment with
`servings = count`, matching `distribute_snacks`.

### `auto_fill` signature

```python
auto_fill(trip, trip_meals, trip_snacks, recipe_weights, snack_weights, snack_info,
          trip_units=None, unit_weights=None, per_day_quota=None)
```

The three new arguments are optional and ignored unless
`(trip.snack_model or "legacy") == "structured"`. `_autofill_inputs` now returns a **kwargs
dict**, not a tuple, and `regenerate_daily_plan` calls `auto_fill(trip, **inputs)`.

## 3. The `snack_unit` item shape in `daily_plan_view`

`_snack_unit_info(db, trip)` projects `trip_snack_unit_list_view` into the same per-serving
dict shape `_snack_info` produces, so `_assignment_item` needed only one change: it echoes
`assignment.source_type` instead of hard-coding `"snack"`. A unit's serving **is** the unit,
so the library's per-unit values are already the per-serving values.

A day item:

| Key | Value |
|---|---|
| `id` | `trip_day_assignments.id` |
| `source_type` | `"snack_unit"` |
| `source_id` | `trip_snack_units.id` |
| `name` | the bag name or the packaged ingredient name |
| `category` | the unit's **kind** — `"bag"` or `"packaged"` (not a slot hint) |
| `slot` | `morning_snacks` / `afternoon_snacks` |
| `servings` | units on that day in that slot |
| `weight` | `weight_oz × servings`, rounded 2 |
| `calories` | `calories × servings`, rounded 1 |
| `protein_g` / `fat_g` / `carb_g` | `× servings`, rounded 1, or `None` |

Macros are `None` when the unit has no macro data at all
(`has_full_data` false **and** all three grams zero), so it counts as uncovered in
`_add_day_macros` rather than dragging the day's coverage to a false 100%. A unit with any
real macro number reports its grams — the same posture `_snack_info` takes.

## 4. Unallocated pool

The snack and unit pool loops are now one loop over
`(("snack", snacks), ("snack_unit", units))`; the snack entries are unchanged. A unit entry
carries `source_type: "snack_unit"`, `remaining_servings` (units still unplaced),
`weight_per_serving` = per-unit oz, `calories_per_serving` = per-unit calories, and
`category` = the kind. Removing a unit assignment returns its quantity to the pool with no
extra bookkeeping — `allocated` was always keyed `f"{source_type}:{source_id}"`.

Pool order is meals, then snacks, then units.

## 5. Assignment endpoints

`backend/routers/daily_plan.py` needed **no change** — the source-type validation lives in
`TripPlanningService`. A new module-level table replaces the two-way `if` in both
`add_assignment` and `update_assignment`:

```python
ASSIGNMENT_SOURCES = {
    "meal": (TripMeal, "quantity", "Meal"),
    "snack": (TripSnack, "servings", "Snack"),
    "snack_unit": (TripSnackUnit, "quantity", "Snack unit"),
}
```

- The rejection message changed: **`source_type must be meal, snack, or snack_unit`**.
- `Meal source is not on this trip` and `Snack source is not on this trip` are byte-identical;
  the new one is `Snack unit source is not on this trip`.
- Over-allocation reuses the existing wording, counting against
  `trip_snack_units.quantity`: `Cannot allocate 3 servings; only 2 is available`.
- **There is no separate structured-only guard.** A legacy trip owns no `TripSnackUnit`
  rows, so a `snack_unit` assignment on one already answers 422 "not on this trip".

Step 3's `_clear_assignments` on unit create/delete/quantity-change means the daily plan
already invalidates when the unit inventory moves.

## 6. Legacy parity

`test_a_legacy_trip_auto_fill_matches_the_pre_change_snapshot` pins a legacy trip's whole
auto-fill output — every day's `(slot, name, servings, calories, weight)`, the unallocated
pool, and the drink-mix shortage warning. `LEGACY_AUTOFILL_SNAPSHOT` was captured by running
the fixture against the pre-change tree, not by copying post-change output.

## 7. Frontend — `frontend/src/pages/DailyPlanPage.jsx`

- `defaultSlotForItem` routes `snack_unit` to `afternoon_snacks` **before** reading
  `category`, because a unit's category is its kind, not a slot hint.
- Day items: units read `{weight} oz · {calories} cal` (one text node — the tests match the
  whole string); snacks and meals still read `{calories} cal`.
- Units get the `+` button (`Add unit of {name}`) and **no** `½` — a unit is a whole thing.
  Snacks keep both (`Add half serving of {name}`, `Add serving of {name}`). The `+` gate
  moved from `source_type === 'snack'` to `source_type !== 'meal'`.
- The unallocated pool counts units in "units", not "servings", and hides the ½-allocate
  button for them.
- The "(last day)" marker now covers units as well as snacks.
- `StackedBarChart` needed nothing: `slotToCategory` keys off the slot, so units already
  color as snacks.

## 8. Tests added

`backend/tests/test_daily_plan_units.py` (17 tests). Fixture: three library bags
(Nut Bag 2 oz / Candy Bag 2 oz / Jerky Bag 1.5 oz) plus a packaged M&Ms item, on the
standard `0.5 + 2 + 0.5 @ 4/day` trip.

- `TestUnitDistribution`: `test_a_full_quota_fills_two_units_per_slot_scaled_on_partial_days`,
  `test_each_day_draws_from_a_spread_of_unit_types`,
  `test_an_odd_quota_favors_the_morning_slot`,
  `test_over_quota_units_spill_evenly_across_the_days`,
  `test_under_quota_units_leave_the_later_slots_empty`,
  `test_a_packaged_unit_distributes_like_a_bag`,
  `test_lunch_snacks_and_drink_mixes_still_flow_on_a_structured_trip`,
  `test_a_legacy_snack_row_stays_out_of_the_unit_slots`,
  `test_units_never_reach_a_legacy_trip`
- `TestUnitAssignments`: `test_a_unit_assignment_reports_its_name_weight_and_calories`,
  `test_a_unit_assignment_round_trips_through_the_endpoints`,
  `test_removing_a_unit_assignment_returns_it_to_the_unallocated_pool`,
  `test_a_unit_cannot_be_allocated_past_its_selected_quantity`,
  `test_a_unit_from_another_trip_is_not_on_this_trip`,
  `test_unit_macros_roll_into_the_day_totals`,
  `test_changing_the_unit_inventory_clears_the_plan`
- `test_a_legacy_trip_auto_fill_matches_the_pre_change_snapshot` — module-level.

`frontend/src/pages/DailyPlanPage.test.jsx` — the three original tests are untouched; a new
`DailyPlanPage snack units` describe adds three:
`unit assignments render in both snack slots with their weight and calories`,
`a unit counts up by whole units and offers no half serving`,
`an unallocated unit is measured in units and assigns to a day`.

Suite totals: backend 246 passed; frontend 9 files / 63 tests.

## 9. Deviations from the plan

1. **`backend/services/trip_planning.py` touched** (Owns named `routers/daily_plan.py`).
   Assignment source-type validation lives in the service, not the router; the router is a
   pass-through and needed no edit. The rejection message changed, so
   `backend/tests/test_trip_workflows.py` has a one-line assertion update.
2. **Three legacy-model test modules pinned to `snack_model: "legacy"`** — the trip helpers in
   `tests/test_daily_plan.py`, `tests/test_daily_plan_macros.py`, and
   `_create_trip_with_snack` in `tests/test_trip_workflows.py`. They create trips through
   `POST /api/trips`, which now defaults to structured, so their `snacks`-slot `TripSnack`
   rows stopped landing on days — correct new behavior, wrong model for those assertions.
   Same posture step 3 took with `tests/test_slots.py`. Seven tests were affected.
3. **`SLOT_RULES` deliberately does not gate unit distribution** (§2). The plan said "1 + 1 on
   each half day" and the spec says "a half day with a 2-unit quota gets 1 + 1"; honoring
   `SLOT_RULES` would have put both units in one slot on each partial day.
4. **`_autofill_inputs` returns a kwargs dict instead of a tuple.** Eight positional
   arguments splatted into `auto_fill` was past the point of readability.
5. **`docs/architecture.md` touched.** Its `autofill.py` sentence and the frontend test count
   (60 → 63) both went stale.
6. **`docs/plans/INDEX.md` left alone** — the verifier confirms acceptance criteria and the
   orchestrator moves the plan, matching steps 2 and 3.
