# Step 3 — Trip Unit Selections + Quota + Planner UI — Handoff

Ground truth for plans `2026-08-06-04` through `-06`. It reflects what shipped, not what the
plan proposed.

Parent spec: [Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md).
Plan: [Trip Unit Selections + Quota + Planner UI](../plans/2026-08-06-03-trip-unit-selections.md).
Builds on: [Step 1 handoff](step-1-snack-mode-schema.md), [Step 2 handoff](step-2-snack-unit-library.md).

## 1. The rules that matter for every later plan

- **Quota math lives in `unit_quota`** (`backend/services/snack_units.py`). Never re-derive
  `snacks_per_day × fraction` anywhere else; plan `-04` distributing 2 + 2 per day reads
  `per_day` from it.
- **Unit values live in `snack_units.py`**, which reads bag values from `catalog_queries`
  (step 2's rule still holds: no consumer recomputes composition math). Packaged units take
  catalog *serving* values; bags take the library's derived values.
- **The structured-only guard is `TripPlanningService._structured_trip`.** Any new
  unit-facing operation (MCP tools in `-06`) should route through it so legacy trips answer
  409, not silently accept units.

## 2. `backend/services/snack_units.py` (new module)

### `unit_quota(trip) -> dict`

```python
{"quota": int, "per_day": list[int]}
```

`trip` is anything with `first_day_fraction` / `full_days` / `last_day_fraction` /
`snacks_per_day` (an unsaved `Trip()` works, which is how the quota tests run without a session).

- Day fractions come from `trip_day_fractions(trip)`: `[first_day_fraction]` +
  `[1.0] × full_days` + `[last_day_fraction]`, skipping zero/None ends. Same ordering as
  `autofill.build_day_list`, derived locally — `snack_units.py` imports nothing from `autofill.py`.
- `per_day[i] = floor(snacks_per_day × fraction + 0.5)` — explicit half-up, because Python's
  `round()` is banker's rounding. `snacks_per_day` coalesces None → 4.
- Verified: `0.5 + 2 + 0.5 @ 4/day` → `{"quota": 12, "per_day": [2, 4, 4, 2]}`;
  `0.25 @ 4/day` → `{"quota": 1, "per_day": [1]}`; `0.5 @ 5/day` → `3` (not 2).

### Other exports

| Function | Returns |
|---|---|
| `trip_day_fractions(trip)` | `list[float]`, first day through last |
| `trip_oz_per_snack(trip)` | `trip.oz_per_snack` coalesced to 2.0 |
| `trip_snack_unit_view(db, selection)` | one selection's dict (loads the trip itself) |
| `trip_snack_unit_list_view(db, trip)` | every selection on the trip, ordered by `id` |
| `trip_unit_totals(db, trip)` | what the selections contribute to the summary |

`trip_unit_totals` returns
`{filled, weight, calories, protein_g, fat_g, carb_g, all_calories, macro_covered_calories}` —
all unrounded, all already multiplied by quantity. `filled` is the sum of quantities.

A selection whose reference is missing (or that names neither) is skipped by the list view and
the totals rather than failing the trip; `trip_snack_unit_view` returns an `Unknown unit`
placeholder so a single endpoint call still answers. CRUD makes the case unreachable.

Bag lookups go through one `snack_unit_type_list_view(db)` call keyed by id, so a trip with
twenty bag selections still costs two queries, not forty.

## 3. Selection view fields

Returned by `trip_snack_unit_view` / `trip_snack_unit_list_view`, and by the three endpoints
(schema `TripSnackUnitRead`):

| Key | Type | Meaning |
|---|---|---|
| `id` | int | `trip_snack_units.id` |
| `catalog_item_id` | int \| None | set on packaged units |
| `unit_type_id` | int \| None | set on bag units |
| `kind` | `"packaged"` \| `"bag"` | |
| `name` | str | ingredient name (packaged) or bag name |
| `quantity` | int | |
| `weight_oz` | float | **per unit** |
| `calories` | float | **per unit**; catalog `calories_per_serving` for packaged |
| `cal_per_oz` | float \| None | per unit; None at zero weight |
| `protein_g` / `fat_g` / `carb_g` | float | **per unit**, rounded to 1 |
| `total_weight` | float | `weight_oz × quantity`, rounded 2 |
| `total_calories` | float | `calories × quantity`, rounded 1 |
| `weight_warning` | bool | `snack_unit_weight_warning(weight_oz, trip.oz_per_snack)` |
| `has_full_data` | bool | packaged: all three ingredient macros present; bag: library's flag |
| `packed` | bool | |
| `actual_weight_oz` | float \| None | |
| `trip_notes` | str \| None | |

`weight_warning` is against **this trip's** `oz_per_snack`; the library's own `weight_warning`
stays against the 2 oz default. A 3 oz bag warns on a default trip and does not on an
`oz_per_snack = 3` trip.

Packaged macros are `ingredient.<macro>_per_oz × weight_per_serving`, matching the existing
`TripSnack` loop. Packaged calories are the catalog serving value, **not** per-oz × weight.

## 4. REST surface — `/api/trips/{trip_id}/snack-units`

Router `backend/routers/trips.py`, thin wrappers over `TripPlanningService`, errors mapped by
the existing `_http_error`.

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| POST | `/api/trips/{trip_id}/snack-units` | `TripSnackUnitCreate` | 201 `TripSnackUnitRead` | 404 trip, 409 legacy, 422 XOR/quantity, 400 unknown reference |
| PUT | `/api/trips/{trip_id}/snack-units/{unit_id}` | `TripSnackUnitUpdate` | 200 `TripSnackUnitRead` | 404 trip/selection, 409 legacy, 422 quantity |
| DELETE | `/api/trips/{trip_id}/snack-units/{unit_id}` | — | 204 | 404 trip/selection, 409 legacy |

- `TripSnackUnitCreate`: `catalog_item_id: int | None`, `unit_type_id: int | None`,
  `quantity: int = 1`, `trip_notes: str | None`.
- `TripSnackUnitUpdate`: `quantity`, `packed`, `actual_weight_oz`, `trip_notes`, all optional
  (`exclude_unset`, so a PUT touches only what it names).

Guard messages (exact strings, asserted in tests):

| Condition | Status | Detail |
|---|---|---|
| trip is legacy | 409 | `Trip does not use the structured snack model` |
| both or neither reference | 422 | `Provide exactly one of catalog_item_id or unit_type_id` |
| `quantity <= 0` (create or update) | 422 | `Unit quantity must be greater than zero` |
| unknown catalog item | 400 | `Snack catalog item not found` |
| unknown unit type | 400 | `Snack unit type not found` |
| selection not on this trip | 404 | `Trip snack unit not found` |

The legacy guard runs **before** the selection lookup, so a legacy trip answers 409 even for an
id that does not exist.

All three operations call `_clear_assignments(trip_id)` on create, delete, and quantity change —
the same posture as `add_snack` / `update_snack`. Plan `-04` therefore inherits a daily plan that
already invalidates when the unit inventory changes; `packed` / `actual_weight_oz` / `trip_notes`
edits do not clear it.

`TripDetailRead` now carries `snack_units: list[TripSnackUnitRead] = []`, populated by
`trip_detail_view` for every trip (a legacy trip's list is empty).

`TripPlanningService.clone_trip` copies `trip_snack_units` rows next to the `TripSnack` /
`TripMeal` loops, carrying `catalog_item_id`, `unit_type_id`, `quantity`, and `trip_notes`, and
resetting `packed` / `actual_weight_oz`. `delete_trip` deletes the rows explicitly, like snacks
and meals.

## 5. Summary integration

`trip_summary_view` branches on `_is_structured(trip)` (`trip.snack_model or "legacy"`).

**Legacy path is untouched** — verified two ways: a hard-coded pre-change snapshot in
`tests/test_snack_units_trip.py`, and the step 1 migration invariant.

On a **structured** trip:

- `trip_unit_totals` rolls into `snack_weight`, `snack_calories`, the `snacks` slot subtotal's
  weight/calories, `total_protein_g` / `total_fat_g` / `total_carb_g`, `total_all_calories`, and
  `macro_covered_calories` (so units flow into `combined_weight`, `combined_calories`,
  `weight_per_day`, `cal_per_day`, `macro_actual`, and `macro_coverage_pct` for free).
- `slot_subtotals["snacks"]` is exactly `{"weight": float, "calories": float}` — no `target_cal`,
  `target_cal_low`, `target_cal_high`, or `days_covered`. The 60% band is not computed at all.
- `slot_subtotals["lunch"]` keeps its 40% band, byte for byte.
- A new top-level block:

  ```python
  "snack_units": {"quota": int, "per_day": list[int], "filled": int}
  ```

  Schema `SnackUnitQuota`. **The key is absent entirely on a legacy trip** — later code should
  test `summary.get("snack_units")`, not a None value.

### The one non-obvious bit: `response_model_exclude_unset`

`GET /api/trips/{id}/summary` is declared with `response_model_exclude_unset=True`. Without it,
`TripSummaryRead` would invent `snack_units: null` on legacy responses and
`target_cal: 0` on a structured snacks subtotal, and the REST payload would stop matching the
raw view dict — which `test_mcp_overview_matches_rest_trip_and_summary` asserts. With it, the
response mirrors the view exactly.

**Consequence for plan `-06`**: MCP returns the raw view, so MCP and REST still agree key for
key. If a later plan adds a summary field, set it in the view on every path or accept that REST
will omit it where the view does.

## 6. Frontend

### `frontend/src/components/SnackUnitMeter.jsx` (new)

`SnackUnitMeter({ label, filled, quota, secondary })` — the quota gauge, shared by the planner
and the summary. Not a `ProgressMeter`: there is no band, only short-of-quota (orange) or
complete (green + the word `Complete`). Renders
`role="progressbar" aria-label="{label} filled"` with `aria-valuenow` / `aria-valuemax`, which is
how the tests target it (`Units filled` in the planner, `Snack units filled` in the summary).

### `frontend/src/components/SnackSelection.jsx`

`structured = tripDetail?.snack_model === 'structured'` gates everything. Section order:

1. **Drink Mixes** — unchanged on both models.
2. **Lunch** — unchanged on both models.
3. **Snacks** (legacy slot section) — on a structured trip this renders **only when it still has
   rows**, and with no `+ Add` button (`SlotSection` gained a `canAdd` prop). Rows a user moved
   into the slot with the row's slot dropdown stay visible and removable instead of vanishing.
4. **Snack Units** (`SnackUnitSection`) — structured trips only.

`SlotMeters` returns null when `target_cal_low == null`, so the structured snacks slot never
draws a band it does not have.

`SnackUnitSection` contents: the meter (secondary line = `{weight} oz · {calories} cal · {per_day
joined by +} by day`), an add panel listing library bags first then packaged catalog items
(drink mixes and lunch items excluded, already-selected units excluded), a desktop table
(Unit + kind badge / units stepper / weight + `Off target` badge / calories / packed checkbox /
actual weight / notes / remove), and a mobile card layout (name, `Off target` badge, stepper,
weight·calories, packed checkbox, remove).

Accessible names, all `{unit name}`-scoped: `Increase {name} units`, `Decrease {name} units`,
`{name} units`, `{name} packed`, `{name} actual weight`, `{name} notes`, `Remove {name}`,
`Add {name}` in the picker.

The unit library is fetched with `listSnackUnitTypes()` only on structured trips.

### `frontend/src/components/TripSummary.jsx`

- A `SnackUnitMeter` labeled `Snack units` under the totals block, rendered when
  `summary.snack_units` exists.
- In the category breakdown, the `Snacks` row becomes a plain
  `{filled} of {quota} units · {oz} oz · {cal} cal` line on structured trips; legacy keeps the
  two-bar `CategoryRow`.
- `st.target_cal ?? 0` guards the slot band math against the missing structured band.

### `frontend/src/api.js`

`addTripSnackUnit(tripId, data)`, `updateTripSnackUnit(tripId, unitId, data)`,
`removeTripSnackUnit(tripId, unitId)` — the path is defined once, next to the step 2 library
helpers.

### `frontend/src/test/apiMock.js`

- `makeTripDetail()` now includes `snack_units: []`.
- `makeTripSnackUnit(overrides)` — a selection with every field the planner reads.
- `createApiMock`'s generic mutation fallback already serves the selection endpoints; no new
  route was needed.

## 7. Tests added

`backend/tests/test_snack_units_trip.py` (25 tests)

- `TestUnitQuota`: `test_half_days_at_each_end_round_to_two_units`,
  `test_a_quarter_day_rounds_up_to_one_unit`, `test_a_half_unit_rounds_up_rather_than_to_even`,
  `test_zero_length_days_are_left_out`, `test_an_unconfigured_trip_falls_back_to_four_per_day`
- `TestSelectionCrud`: `test_a_packaged_selection_reports_its_catalog_serving_values`,
  `test_a_bag_selection_reports_the_library_derived_values`,
  `test_the_trip_detail_lists_its_selections`,
  `test_quantity_packed_and_actual_weight_round_trip`,
  `test_removing_a_selection_drops_it_from_the_trip`,
  `test_a_selection_names_exactly_one_kind_of_unit`,
  `test_an_unknown_unit_reference_is_rejected`, `test_quantity_must_be_greater_than_zero`,
  `test_a_selection_from_another_trip_is_not_found`
- `TestToleranceBand`: `test_a_unit_is_measured_against_this_trip_s_target`
- `TestStructuredOnlyGuard`: `test_unit_endpoints_reject_a_legacy_trip`,
  `test_a_missing_trip_is_still_a_404`
- `TestClone`: `test_clone_copies_selections_and_resets_the_packing_record`
- `TestStructuredSummary`: `test_the_summary_reports_units_filled_against_the_quota`,
  `test_the_snacks_slot_trades_its_calorie_band_for_the_meter`,
  `test_unit_weight_and_calories_roll_into_the_trip_totals`,
  `test_unit_macros_roll_into_the_trip_totals`,
  `test_a_unit_without_macro_data_lowers_the_coverage`,
  `test_a_structured_trip_without_selections_reports_an_empty_meter`
- `test_a_legacy_trip_summary_matches_the_pre_change_snapshot` — module-level. The
  `LEGACY_SUMMARY_SNAPSHOT` dict was captured by running the fixture against a git worktree of
  the pre-change tree, not by copying current output.

Test-author note: `TripCreate` still does not expose the snack configuration, so `_trip(...)`
takes a `snack_config=` argument and applies it with a follow-up `PUT`.

`frontend/src/components/SnackSelection.test.jsx` — the five original tests are untouched; a new
`SnackSelection structured units` describe adds nine:
`the units meter reads filled against the trip quota`,
`the units meter reads complete once the quota is filled`,
`the add panel offers library bags and packaged snacks`,
`adding a packaged snack posts a catalog unit selection`,
`the quantity stepper saves the new unit count`,
`a unit outside the trip tolerance is badged`,
`a unit can be marked packed with its actual weight`,
`removing a unit deletes the selection`,
`the trip summary meters units instead of a snack calorie band`,
`a legacy trip keeps the snacks slot and shows no unit section`.

## 8. Deviations from the plan

1. **`backend/routers/trips.py` summary endpoint gained `response_model_exclude_unset=True`**
   (not called out in the plan). Without it the two invariants collide — see §5. This is the
   single most load-bearing decision in the step.
2. **`backend/tests/test_slots.py` touched** (not in Owns, not in Must-not-touch).
   `test_summary_splits_daytime_calorie_target_40_60` created a trip through `POST /api/trips`,
   which now defaults to structured, so the 60% snacks band it asserts no longer exists. The
   test now pins the trip to `legacy` first; it is a legacy-model test.
3. **`backend/tests/test_migrations.py` touched** (same status). `_PreStructuredTrip` gained
   `snack_model: str | None = None`. Step 1's handoff predicted this exact failure mode and
   called the `AttributeError` "the correct signal"; the summary genuinely must read
   `snack_model`. A pre-migration row has no value for the column, so None is the honest
   stand-in, and the test now also proves a NULL `snack_model` reads as legacy.
4. **`backend/tests/test_snack_unit_library.py` touched** — step 2's handoff asked plan `-03` to
   switch `test_a_unit_type_in_use_by_a_trip_cannot_be_deleted` from a direct `TripSnackUnit`
   insert to the real endpoint once it existed. Done; the `test_session` fixture and the
   `TripSnackUnit` import are gone from that file.
5. **`frontend/src/components/SnackUnitMeter.jsx` is a new file** (Owns listed only
   `SnackSelection.jsx` and `TripSummary.jsx`). Both render the same gauge; duplicating it was
   the worse option.
6. **`frontend/src/test/apiMock.js` touched** (same status as steps 1 and 2).
7. **`docs/architecture.md` touched.** Its Services paragraph enumerates the service modules and
   went stale the moment `services/snack_units.py` landed; the frontend test count was also
   updated (8 files / 42 tests → 9 / 60).
8. **Legacy rows in a structured trip's snacks slot stay visible.** The plan did not cover the
   case; the row slot dropdown in the Lunch section can move a `TripSnack` into `snacks` on a
   structured trip, and silently hiding it would have lost data from the user's view.
9. **`docs/plans/INDEX.md` left alone** — the verifier confirms acceptance criteria and the
   orchestrator moves the plan, matching step 2's posture.
