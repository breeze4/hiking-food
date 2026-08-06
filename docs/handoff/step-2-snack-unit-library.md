# Step 2 — Snack Unit Type Library — Handoff

Ground truth for plans `2026-08-06-03` through `-06`. It reflects what shipped, not what the plan
proposed.

Parent spec: [Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md).
Plan: [Snack Unit Type Library](../plans/2026-08-06-02-snack-unit-library.md).
Builds on: [Step 1 handoff](step-1-snack-mode-schema.md).

## 1. The rule that matters for every later plan

All bag composition math lives in `backend/services/catalog_queries.py`. Summary, shopping, packing,
daily plan, and MCP read `snack_unit_type_view` / `snack_unit_type_list_view` and never re-derive
weight, calories, or macros from `snack_unit_ingredients` rows.

## 2. `snack_unit_type_view(unit_type, composition) -> dict`

Pure shaping, like `snack_view(item, ingredient)`. Callers fetch the composition first (see §3).

| Key | Type | Meaning |
|---|---|---|
| `id` | int | `snack_unit_types.id` |
| `name` | str | |
| `notes` | str \| None | |
| `composition` | list[dict] | Rows, insertion order (see §3) |
| `weight_oz` | float | Sum of composition `amount_oz`, rounded to 2 |
| `calories` | float | Σ(`amount_oz` × ingredient `calories_per_oz`), rounded to 1 |
| `cal_per_oz` | float \| None | `calories / weight_oz` rounded to 1; `None` when weight is 0 |
| `protein_g` | float | Σ(`amount_oz` × `protein_per_oz`), rounded to 1 |
| `fat_g` | float | Same, fat |
| `carb_g` | float | Same, carb |
| `weight_warning` | bool | `weight_oz` outside ±25% of the 2 oz default |
| `has_full_data` | bool | False when any composition ingredient is missing any of the four per-oz fields |

Totals come from `services/recipe_calc.compute_recipe_totals`, so bags and recipes round identically.
`cal_per_oz` is not in the plan's field list; it is free from that helper and the library UI shows it.

An ingredient missing per-oz data contributes 0 and flips `has_full_data` to False — the same posture
as macro coverage in `trip_summary_view`. Nothing is blocked.

An empty bag derives `weight_oz = 0`, `calories = 0`, `cal_per_oz = None`, `has_full_data = True`, and
`weight_warning = True` (0 oz is outside the band).

## 3. Composition rows

`snack_unit_composition(db, unit_type_id) -> list[dict]`, ordered by `snack_unit_ingredients.id`
(insertion order), joined to `ingredients`. Mirrors `recipe_ingredients`:

`id`, `unit_type_id`, `ingredient_id`, `ingredient_name`, `amount_oz`, `calories_per_oz`,
`protein_per_oz`, `fat_per_oz`, `carb_per_oz`, `calories` (= `amount_oz × calories_per_oz`, rounded 1).

`amount_oz` is coalesced to 0 when the column is NULL. Plan `-05` (shopping list) has everything it
needs here: `ingredient_id` + `amount_oz` per row.

`snack_unit_type_list_view(db) -> list[dict]` returns every unit type ordered by `name`, with one
composition query for all types (no N+1), each shaped by `snack_unit_type_view`.

## 4. The tolerance band

```
DEFAULT_OZ_PER_SNACK = 2.0
SNACK_UNIT_WEIGHT_TOLERANCE = 0.25
snack_unit_weight_warning(weight_oz, target_oz=DEFAULT_OZ_PER_SNACK) -> bool
```

True when `weight_oz` is outside `target_oz × (1 ± 0.25)`. Inclusive at the edges: at the 2 oz default,
1.4 and 2.6 warn; 1.5, 2.0, and 2.5 do not. A 1e-9 epsilon absorbs binary-float drift, so a bag built
from 1.2 + 0.3 oz reads as exactly 1.5 and does not warn. `target_oz` of 0 never warns.

**Plan `-03` uses this**: call `snack_unit_weight_warning(bag["weight_oz"], trip.oz_per_snack)` on the
planner side. Do not re-implement the band. The `weight_warning` field in the view is always against
the 2 oz default, because a library entry is trip-independent.

## 5. REST surface — `/api/snack-unit-types`

Router `backend/routers/snack_units.py`, prefix `/api/snack-unit-types`, tag `snack-unit-types`,
registered on `inner` in `backend/main.py` next to `snacks_router`. Local `get_db()` like every other
router. Response model `SnackUnitTypeRead` throughout.

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| GET | `/api/snack-unit-types` | — | 200, list | — |
| GET | `/api/snack-unit-types/{id}` | — | 200 | 404 `Snack unit type not found` |
| POST | `/api/snack-unit-types` | `SnackUnitTypeCreate` | 201 | 400 `Ingredient {id} not found` |
| PUT | `/api/snack-unit-types/{id}` | `SnackUnitTypeUpdate` | 200 | 404, 400 as above |
| DELETE | `/api/snack-unit-types/{id}` | — | 204 | 404, 409 (see below) |

Payloads (`backend/schemas.py`, section `--- Snack Unit Types (bags) ---`):

- `SnackUnitTypeCreate`: `name: str`, `notes: str | None`, `composition: list[SnackUnitIngredientCreate] = []`
- `SnackUnitTypeUpdate`: all three optional; **omitting `composition` leaves the existing rows alone**,
  sending it replaces them wholesale (delete-then-insert, exactly like `RecipeUpdate.ingredients`)
- `SnackUnitIngredientCreate`: `ingredient_id: int`, `amount_oz: float`
- `SnackUnitIngredientRead` (what the response carries per row): `id`, `ingredient_id`,
  `ingredient_name`, `amount_oz`, `calories`. The view dict is richer (per-oz fields, `unit_type_id`);
  Pydantic drops the extras for REST, and direct view consumers such as MCP get everything.

Delete protection: a `trip_snack_units` row with `unit_type_id = {id}` yields
**409 `Cannot delete: snack unit type is used in trip snack selections`**. Unreferenced types delete
with 204, and their composition rows are deleted first (no cascade on the FK).

## 6. Frontend

- Page: `frontend/src/pages/SnackUnitLibraryPage.jsx`, route `/snack-units`, lazy-loaded in
  `frontend/src/App.jsx` beside `/snacks`.
- Nav: link labeled **Snack Units**, between "Snack Catalog" and "Ingredients" in `NavLinks`
  (so it appears in both the desktop nav and the mobile sheet).
- Page heading: `Snack Unit Library`. Table columns: Bag, Composition, Weight (oz), Calories, Cal/oz,
  P / F / C (g), Notes, actions. `weight_warning` renders a destructive `Off target` badge next to the
  weight; `has_full_data === false` renders an outline `Partial data` badge next to calories.
- Row action buttons carry per-bag accessible names (`Edit {name}`, `Delete {name}`), because the trip
  selector in the header also renders a plain "Delete" button.
- Builder dialog (create and edit share it): Name, Notes, composition rows (ingredient + oz + Remove),
  an add row (`Ingredient to add` select, `Amount in ounces to add` input, `Add` button), and a live
  `Bag total: {oz} oz · {cal} cal` preview. The preview is client-side, like `RecipeEditPage`'s totals;
  the authoritative derived values are the server's, shown in the table after save. The tolerance rule
  is **not** duplicated client-side — the badge comes from the server's `weight_warning`.
- After any mutation the page refetches the list rather than splicing the response.
- Delete errors (the 409) render inside the delete dialog, so the message is visible while the modal
  holds focus.

API helpers in `frontend/src/api.js` (new, path defined once for plan `-03` to reuse):
`listSnackUnitTypes()`, `createSnackUnitType(data)`, `updateSnackUnitType(id, data)`,
`deleteSnackUnitType(id)`.

Test fixtures in `frontend/src/test/apiMock.js`:
- `makeSnackUnitType(overrides)` — a library row with every derived field.
- `createApiMock({ snackUnitTypes })` serves `GET /hiking-food/api/snack-unit-types`. It accepts an
  array **or a function**, so a test can return a different library on the refetch after a mutation.

## 7. Tests added

`backend/tests/test_snack_unit_library.py` (19 tests)
- `TestSnackUnitTypeCrud`: `test_create_read_update_delete_round_trip`,
  `test_update_without_composition_keeps_the_existing_rows`, `test_unknown_ingredient_is_rejected`,
  `test_missing_unit_type_returns_404`
- `TestDerivedValues`: `test_weight_is_the_sum_of_composition_ounces`,
  `test_calories_come_from_per_oz_ingredient_data`, `test_macros_come_from_per_oz_ingredient_data`,
  `test_ingredients_without_per_oz_data_contribute_zero`,
  `test_full_data_flag_is_true_when_every_ingredient_is_complete`, `test_an_empty_bag_derives_zeros`
- `TestWeightWarning`: `test_warning_marks_bags_outside_25_percent_of_two_ounces` (parametrized over
  1.4 / 1.5 / 2.0 / 2.5 / 2.6), `test_a_band_edge_reached_by_addition_does_not_warn`
- `TestListEndpoint`: `test_list_returns_composition_and_derived_values_in_one_response`
- `TestDeleteProtection`: `test_a_unit_type_in_use_by_a_trip_cannot_be_deleted`,
  `test_an_unreferenced_unit_type_deletes`

Note for test authors: the ingredients router derives `calories_per_oz` from macros (4/9/4) whenever
macros are supplied, so the fixtures state macros only and assert against the derived per-oz calories
(`NUTS_CAL_PER_OZ = 183`, `CANDY_CAL_PER_OZ = 138`). Passing `calories_per_oz` alongside macros is
silently ignored.

The delete-protection test writes a `TripSnackUnit` row through the `test_session` fixture, because
trip unit selections have no endpoint yet — plan `-03` owns them and should switch that test's setup
to the real endpoint once it exists.

`frontend/src/pages/SnackUnitLibraryPage.test.jsx` (5 tests)
- `building a bag from two ingredients shows its derived weight and calories`
- `a bag outside the weight tolerance is badged, an on-target bag is not`
- `a bag missing per-oz ingredient data is badged as partial`
- `deleting a bag that a trip uses surfaces the conflict message`
- `editing a bag sends its whole composition back`

## 8. Deviations from the plan

1. **`backend/tests/conftest.py` touched** (not in Owns, not in Must-not-touch). The new router module
   needs its `get_db` in the `dependency_overrides` loop or its endpoints would hit the real database
   during tests.
2. **`frontend/src/test/apiMock.js` touched** (same status; the orchestrator's brief invited library
   fixtures). Added the `snackUnitTypes` config key, its read route, and `makeSnackUnitType`.
3. **`docs/architecture.md` touched.** It enumerates the routers ("seven routers", the
   `dependency_overrides` list) and the `catalog_queries` view names; both went stale the moment this
   router landed. Updated to eight routers and the new view names.
4. **`cal_per_oz` added to the view** beyond the plan's field list — free from `compute_recipe_totals`,
   and the library table shows it.
5. **Named API helpers in `frontend/src/api.js`** rather than inline `get('/snack-unit-types')` calls.
   Existing pages call the generic helpers with literal paths; the library path is named once here
   because plan `-03` reads the same endpoint from the planner.
6. **`docs/plans/INDEX.md` left alone.** Plan 47 stays under "Not Started" until the verifier confirms
   the acceptance criteria; the orchestrator moves it.
