# Step 5 — Shopping List + Packing Screen for Snack Units — Handoff

Ground truth for plan `2026-08-06-06` (MCP). It reflects what shipped, not what the plan proposed.

Parent spec: [Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md).
Plan: [Shopping List + Packing Screen for Snack Units](../plans/2026-08-06-05-shopping-packing-units.md).
Builds on: [Step 2 handoff](step-2-snack-unit-library.md), [Step 3 handoff](step-3-trip-unit-selections.md).

## 1. The rules that matter for plan `-06`

- **Both projections gate on `_is_structured(trip)`.** A legacy trip's `shopping_view` and
  `packing_view` output is byte-for-byte what it was before this step: shopping does not expand
  stray unit rows, and `packing_view` does **not** grow a `units` key at all (absent, not empty —
  the same posture as `snack_units` in `trip_summary_view`). MCP should test
  `packing.get("units")`, not a None value.
- **Nothing recomputes composition math.** Bag ounces come from
  `catalog_queries.snack_unit_type_list_view(db)`'s `composition` rows; selection values come from
  `snack_units.trip_snack_unit_list_view(db, trip)`; the per-unit target comes from
  `snack_units.trip_oz_per_snack(trip)`.
- **No new backend mutations.** Packed checkoff and actual weight on the packing screen reuse
  step 3's `PUT /api/trips/{id}/snack-units/{unit_id}`.
- Neither endpoint declares a `response_model` (`routers/trips.py:243` and `:251` return the raw
  dict), so no schema widening was needed and MCP sees exactly these keys.

## 2. `shopping_view` — what changed

Response shape is unchanged: `{"items": [...], "essentials": [...]}` with the same per-line keys.
What changed is what feeds the aggregation.

- New private `_shopping_line(totals, ingredient)` replaces the three copies of the
  `totals.setdefault(...)` block, keyed on `ingredient.id`. Every source merges into the same line,
  so `on_hand` / `essentials` / `packing_method` apply to an expanded bag ingredient exactly as they
  do to a recipe ingredient, and the essentials split plus the
  `(on_hand, ingredient_name)` sort are inherited for free.
- New private `_unit_ingredient_ounces(db, trip) -> list[tuple[int, float]]`, run only on a
  structured trip, after the meal and TripSnack loops:
  - **bag selection** → one entry per composition row: `(row["ingredient_id"], row["amount_oz"] × quantity)`.
    Six bags of 1 oz nuts + 1 oz M&Ms buy 6 oz of each.
  - **packaged selection** → `(catalog_item.ingredient_id, weight_per_serving × quantity)` — the
    same line a `TripSnack` row of that item produces, so the two merge.
- New private `_bags_by_id(db, selections)` — one `snack_unit_type_list_view(db)` call, keyed by id,
  and skipped entirely when the trip has no bag selections. Shared with `_packing_units`.

On a structured trip the legacy TripSnack path still runs: lunch items and drink mixes are still
`TripSnack` rows and still contribute their servings.

## 3. `packing_view` — the new `units` key

`{"trip_name", "meals": [...], "snacks": [...]}` gains `"units": [...]` **on structured trips only**.
Each entry is one group — one thing to make N of:

| Key | Type | Meaning |
|---|---|---|
| `kind` | `"bag"` \| `"packaged"` | |
| `unit_type_id` | int \| None | set on bags |
| `catalog_item_id` | int \| None | set on packaged units |
| `name` | str | bag name, or the packaged item's ingredient name |
| `count` | int | units to make — the summed `quantity` of the group's selections |
| `target_weight` | float | **per unit**, the trip's `oz_per_snack` |
| `unit_weight` | float | **per unit**, what the composition/serving derives |
| `unit_calories` | float | **per unit** |
| `total_weight` | float | `Σ selection.total_weight`, rounded 2 |
| `total_calories` | float | `Σ selection.total_calories`, rounded 1 |
| `weight_warning` | bool | from the selection view — against **this trip's** target |
| `packed` | bool | true when **every** selection in the group is packed |
| `actual_weight_oz` | float \| None | the first recorded per-unit weight in the group |
| `composition` | list[dict] | `{ingredient_name, amount_oz}` per row; `[]` for packaged units |
| `selections` | list[dict] | `{id, quantity, packed, actual_weight_oz}` per selection |

Grouping rules:

- Key is `(kind, unit_type_id)` for bags and `(kind, catalog_item_id)` for packaged units, so two
  selections of the same bag pack as one group with the counts summed. The API permits duplicate
  selections of the same reference (no uniqueness guard in step 3); the planner UI hides
  already-selected units, so in practice a group holds exactly one selection.
- Order is **selection order** (`trip_snack_unit_list_view` orders by `id`), not name order, so the
  checklist reads in the same order as the planner table.
- A structured trip with no selections reports `"units": []`.
- `packed` and `actual_weight_oz` are per-selection fields in the schema; the group repeats them so
  a single-selection group reads as one row, and `selections` keeps the detail for anyone who needs
  the individual ids (that is what the frontend writes back to).

`composition` is **an addition beyond the plan's field list** — see Deviations.

## 4. Frontend

`frontend/src/pages/PackingScreen.jsx` gains a **Snack Unit Assembly** section, rendered between
Recipe Assembly and Snack Packing whenever `packing.units` is present (structured trips); a legacy
trip's payload has no `units` key, so the section does not render at all. An empty array renders
"No snack units selected for this trip.", matching the other two sections' empty states.

- Header badge: `{packed}/{groups} packed`.
- Row: checkbox | `Make {count} × {name} @ {target_weight} oz` (with the bag recipe
  `1 oz Almonds + 1 oz M&Ms` beneath it) | derived `unit_weight` plus a destructive `Off target`
  badge when `weight_warning` | actual-weight input.
- Accessible names are deliberately distinct from the legacy snack rows, because a packaged unit
  and a lunch `TripSnack` can carry the same ingredient name: **`{name} units packed`** and
  **`{name} unit actual weight`** (the legacy snack rows keep `{name} packed` /
  `{name} actual weight`).
- Both controls go through `updateUnitGroup(group, fields)`, which writes the same field to every
  selection id in the group via `updateTripSnackUnit(tripId, selectionId, fields)` from
  `frontend/src/api.js` (step 3's helper) and then refetches through the page's existing
  `useMutation` wrapper. A group is one unit type, so "this bag weighs 2.1 oz" applies to all of it.

`frontend/src/test/apiMock.js` gains `makePackingUnit(overrides)` — a group with every field the
section reads. The default packing response is unchanged (no `units` key), so existing tests keep
exercising the legacy shape.

## 5. Tests added

`backend/tests/test_shopping_list.py` (+8, 5 → 13)

- `TestSnackUnitExpansion`: `test_a_bag_buys_its_composition_ounces_per_unit`,
  `test_bag_ounces_merge_with_the_same_ingredient_from_other_sources`,
  `test_a_packaged_unit_buys_its_catalog_serving_weight`,
  `test_a_packaged_unit_merges_with_the_same_catalog_item_in_a_slot`,
  `test_an_essential_inside_a_bag_lands_in_the_essentials_list`,
  `test_bag_ingredients_carry_on_hand_and_packing_method`,
  `test_a_legacy_trip_ignores_stray_unit_rows`
- `test_a_legacy_trip_shopping_list_matches_the_pre_change_snapshot` — module level.

`backend/tests/test_packing.py` (+8, 2 → 10)

- `TestUnitAssembly`: `test_a_bag_reports_its_count_target_and_derived_weight`,
  `test_a_bag_lists_what_goes_into_it`, `test_selections_of_the_same_type_pack_as_one_group`,
  `test_a_packaged_unit_packs_under_its_catalog_item`,
  `test_a_bag_off_the_trip_target_is_flagged`, `test_packing_a_unit_records_its_actual_weight`,
  `test_a_structured_trip_without_selections_has_an_empty_checklist`
- `test_a_legacy_trip_packing_matches_the_pre_change_snapshot` — module level; also asserts
  `"units" not in packing`.

Both `LEGACY_*_SNAPSHOT` dicts were captured by running the exact fixture against a **git worktree
of the pre-change tree** (the step-4 commit), not by copying current output — the same method
steps 3 and 4 used. The shopping snapshot hard-codes ingredient ids, which is safe because each
test module's fixture drops and recreates every table, resetting SQLite rowids.

`frontend/src/pages/PackingScreen.test.jsx` — the three original tests are untouched; a new
`PackingScreen snack unit assembly` describe adds five:
`a unit group reads as make N of a type at the trip target`,
`checking off a group packs every selection behind it`,
`an actual unit weight saves against the selection`,
`a unit off the trip target is badged`,
`a legacy trip has no unit assembly section`.

Suites: backend 246 → 262, frontend 63 → 68.

## 6. Deviations from the plan

1. **`composition` added to each packing group** (beyond the plan's count / target / derived weight
   / packed / actual weights). The spec calls for packing day to be an assembly checklist, and a
   bag cannot be assembled without knowing what goes in it — the meal rows carry their ingredient
   table for the same reason. Packaged groups carry `[]`.
2. **`selections` added to each packing group.** The checkoff had to write somewhere, and packed /
   actual weight are per-selection columns; exposing the ids is what lets the screen reuse step 3's
   update endpoint with no new backend mutation.
3. **`_shopping_line` extracted** from the three identical `totals.setdefault(...)` blocks. It is a
   pure extraction (the key was already `ingredient.id` under two other names) and it is what makes
   the on_hand / essentials / packing_method criterion hold for bag ingredients by construction
   rather than by a fourth copy. The legacy snapshot pins that nothing moved.
4. **`frontend/src/test/apiMock.js` touched** (not in Owns) — `makePackingUnit`, the same status as
   steps 1–3.
5. **`docs/architecture.md` touched** (not in Owns). Its Services paragraph describes the packing
   and shopping projections explicitly and went stale; the frontend test count (9 files / 63 tests)
   was also updated to 68.
6. **No schema change.** The brief flagged that widening `TripPackingRead` / `TripShoppingRead`
   would be within remit if needed — those schemas do not exist. Both endpoints return plain dicts
   with no `response_model`, so the new keys pass through untouched.
7. **`docs/lessons.md` appended** — two entries (snapshot provenance, and extracting the shared
   aggregation line before adding a third source), per the project's end-of-work convention.
8. **`docs/plans/INDEX.md` left alone** — the verifier confirms the acceptance criteria and the
   orchestrator moves the plan, matching steps 2–4.
