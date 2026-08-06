# Step 1 — Trip Snack Mode + Schema Foundation — Handoff

Ground truth for plans `2026-08-06-02` through `-06`. It reflects what shipped, not what the plan proposed.

Parent spec: [Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md).
Plan: [Trip Snack Mode + Schema Foundation](../plans/2026-08-06-01-trip-snack-mode-schema.md).

## 1. New columns on `trips`

In `backend/models.py`, appended to `Trip`:

| Column | SQLAlchemy type | Nullable | Model default | Migration DDL default |
|---|---|---|---|---|
| `snack_model` | `Text` | Yes | `"legacy"` | `TEXT DEFAULT 'legacy'` |
| `snacks_per_day` | `Integer` | Yes | `4` | `INTEGER DEFAULT 4` |
| `oz_per_snack` | `Float` | Yes | `2` | `REAL DEFAULT 2` |

Allowed `snack_model` values: `legacy`, `structured`. Validated in application code only
(`SNACK_MODELS` in `backend/services/trip_planning.py`), not at the DB level.

## 2. New tables

All three are created both by `Base.metadata.create_all` (fresh databases) and by
`_migration_3_structured_snacks` (existing databases). The two DDL paths are held in sync by
`test_migration_marks_existing_trips_legacy_and_creates_unit_tables`, which asserts
`collect_database_errors(...) == []` on a database whose tables the *migration* built.

### `snack_unit_types` — model `SnackUnitType`

| Column | Type | Nullable |
|---|---|---|
| `id` | `Integer`, primary key | No |
| `name` | `Text` | No |
| `notes` | `Text` | Yes |

### `snack_unit_ingredients` — model `SnackUnitIngredient`

Mirrors `recipe_ingredients` (plain foreign keys, no cascade).

| Column | Type | Nullable |
|---|---|---|
| `id` | `Integer`, primary key | No |
| `unit_type_id` | `Integer` FK → `snack_unit_types.id` | No |
| `ingredient_id` | `Integer` FK → `ingredients.id` | No |
| `amount_oz` | `Float` | Yes |

### `trip_snack_units` — model `TripSnackUnit`

| Column | Type | Nullable |
|---|---|---|
| `id` | `Integer`, primary key | No |
| `trip_id` | `Integer` FK → `trips.id` **ON DELETE CASCADE** | No |
| `catalog_item_id` | `Integer` FK → `snack_catalog.id` | Yes |
| `unit_type_id` | `Integer` FK → `snack_unit_types.id` | Yes |
| `quantity` | `Integer` (model default 1) | Yes |
| `packed` | `Boolean` (model default false) | Yes |
| `actual_weight_oz` | `Float` | Yes |
| `trip_notes` | `Text` | Yes |

`catalog_item_id` and `unit_type_id` are both nullable because a selection is *either* packaged
(catalog item) *or* a bag (unit type). Nothing enforces the exclusive-or yet — that guard belongs
to plan `-03`, which owns selection CRUD.

All three tables are empty after the migration. No seed data.

## 3. Migration

`_migration_3_structured_snacks` in `backend/migrations.py`, appended to `MIGRATIONS`.
`CURRENT_SCHEMA_VERSION` is now **3**.

Order of operations:
1. `_add_column_if_missing` for the three trip columns, each with its DDL default.
2. Three explicit `UPDATE trips SET <column> = <default> WHERE <column> IS NULL` statements.
   The backfill is written out rather than relying on SQLite's ADD COLUMN default so a database
   that somehow already carries a nullable column still lands on `legacy`.
3. `CREATE TABLE IF NOT EXISTS` for the three tables.

The migration is idempotent and, like its predecessors, is stamped into `PRAGMA user_version`.

Dry-run against a copy of the real dev database (`backend/hiking_food.db`, at version 2): version
went 2 → 3, the one existing trip (`Utah 2026`) became `legacy 4/2.0`, the three tables appeared,
and `collect_database_errors` returned `[]`.

## 4. Where the defaults come from

This is the part later plans must not get wrong:

- **Column default is `legacy`, everywhere** — model, migration DDL, and backfill.
- **`structured` is set only in the create-trip code path**, by `NEW_TRIP_SNACK_DEFAULTS` in
  `backend/services/trip_planning.py`:

  ```python
  NEW_TRIP_SNACK_DEFAULTS = {
      "snack_model": "structured",
      "snacks_per_day": 4,
      "oz_per_snack": 2.0,
  }
  ```

  `TripPlanningService.create_trip` fills in any of the three that arrive `None` or absent, before
  validation. A column default of `structured` would silently apply to any INSERT that omits the
  field, which is exactly what the legacy backfill must never race with.

Because `create_trip` owns the default, **both** consumers get it for free: `POST /api/trips` and
the MCP `create_trip` tool. Neither passes the fields.

`TripCreate` deliberately does **not** expose the three fields — new trips are structured, full
stop; use `PUT` to move one to `legacy`.

## 5. Clone behavior

`TripPlanningService.clone_trip` copies all three fields verbatim from the source trip
(`snack_model`, `snacks_per_day`, `oz_per_snack` added to the existing `fields` dict). A clone of a
legacy trip is legacy; a clone of a structured trip with 5 snacks/day at 1.75 oz keeps 5 and 1.75.
Clone does **not** copy `trip_snack_units` rows yet — plan `-03` owns unit selections and must add
that loop next to the existing `TripSnack` / `TripMeal` loops (packed flags reset, per spec).

## 6. Validation

Added to `TripPlanningService._validate_trip_fields`, so it applies to create, clone, and update:

| Condition | Message |
|---|---|
| `oz_per_snack` present and `<= 0` | `oz_per_snack must be greater than zero` |
| `snacks_per_day` present and `< 0` | `snacks_per_day cannot be negative` |
| `snack_model` present and not in `{legacy, structured}` | `snack_model must be legacy or structured` |

All three surface as HTTP **422** through the router's existing `_http_error` mapping.

## 7. API surface

No new endpoints. Existing trip endpoints carry the three fields:

- `GET /api/trips/{id}` and `POST /api/trips` (both `TripDetailRead`) now include
  `snack_model: str = "legacy"`, `snacks_per_day: int = 4`, `oz_per_snack: float = 2.0`.
- `PUT /api/trips/{id}` (`TripUpdate`) accepts all three as optional fields. `snack_model` is
  accepted here with no dedicated UI affordance, per spec Out of Scope.
- `POST /api/trips/{id}/clone` returns `TripDetailRead`, so the copied values are visible.
- `trip_list_view` (`backend/services/trip_queries.py`) also returns the three fields, for MCP
  consumers that read the projection directly. `TripListRead` was **not** widened — the REST list
  endpoint still returns only `id` and `name`, as before. Widen it if a later plan needs it.

Both `trip_detail_view` and `trip_list_view` coalesce nulls the way the existing target fields do:
`trip.snack_model or "legacy"`, `snacks_per_day` → 4, `oz_per_snack` → 2.

## 8. Frontend

`frontend/src/components/TripCalculator.jsx`:

- Reads `tripDetail.snack_model` directly (never into form state) so a debounced save can never
  carry a stale copy back and flip the mode. The PUT payload therefore never contains `snack_model`.
- Always renders a read-only `Snack model` caption showing `Structured` or `Legacy`.
- Renders `Snacks/day` (id `snacks-per-day`, integer) and `Oz/snack` (id `oz-per-snack`, step 0.25)
  inputs **only** when `snack_model === 'structured'`. They join the same debounced-save form as the
  existing targets.

`frontend/src/test/apiMock.js`: `makeTripDetail()` now defaults to
`snack_model: 'structured', snacks_per_day: 4, oz_per_snack: 2`. Override with
`makeTripDetail({ snack_model: 'legacy' })` to exercise legacy rendering. Later plans building the
structured snacks UI get the structured fixture by default.

## 9. Tests added

`backend/tests/test_migrations.py`
- `test_migration_marks_existing_trips_legacy_and_creates_unit_tables` — two pre-existing trips both
  backfill to `("legacy", 4, 2)`, the three tables exist, and the verifier passes on the
  migration-built schema.
- `test_legacy_trip_summary_is_unchanged_by_the_structured_snack_migration` — the invariant.
- Helpers: `_build_pre_structured_database` (create_all, then drop the three columns and three
  tables and stamp `user_version=2`), `_PreStructuredTrip`, `LEGACY_TRIP_SEED`.
- Updated: the version assertions in `test_migrations_record_current_version_and_are_idempotent`
  (2 → 3) and `test_database_verifier_rejects_unversioned_schema` (`expected 2` → `expected 3`).

How the invariant test gets a genuine "before" snapshot: the pre-migration database has no
`snack_model` column, so the ORM `Trip` mapping cannot read it. The test instead reads the trip row
with raw SQL into `_PreStructuredTrip` — a dataclass holding exactly the pre-feature column set —
and passes that to `trip_summary_view`, which only ever reads attributes off its `trip` argument
and never re-queries `trips`. It then runs the migration and compares the full dict against
`trip_summary_view(db, db.get(Trip, 1))`. If a future change makes the summary read a new `Trip`
column, this test fails with `AttributeError`, which is the correct signal.

`backend/tests/test_trip_workflows.py`
- `test_rest_new_trips_use_the_structured_snack_model`
- `test_rest_can_retune_the_structured_snack_configuration`
- `test_rest_rejects_invalid_snack_configuration` (parametrized over the three validation rules)
- `test_rest_clone_copies_the_snack_model_and_configuration`
- `test_rest_clone_of_a_legacy_trip_stays_legacy`

`frontend/src/components/TripCalculator.test.jsx`
- `a structured trip shows its snack unit configuration`
- `a legacy trip hides the snack unit configuration`
- `editing snacks per day saves the new value` (also asserts the payload omits `snack_model`)

## 10. Deviations from the plan

1. **`backend/verify_database.py` touched** (not listed in the plan's Owns). `trip_snack_units` was
   added to `CASCADE_TABLES` so the new table's trip cascade is covered by the same startup
   invariant that guards `trip_meals` / `trip_snacks` / `trip_day_assignments`. Without it the
   guarantee would have shipped untested.
2. **`frontend/src/test/apiMock.js` touched** (not listed in Owns, not in Must-not-touch). The
   shared `makeTripDetail` fixture needed the three fields for the calculator tests to render a
   structured trip.
3. **`TripListRead` left alone.** The plan allowed widening it "as needed"; nothing needed it, so
   the REST trip-list payload is unchanged.
4. **Validation rules added** beyond the plan's explicit tasks, following the existing
   `oz_per_day` / `cal_per_oz` pattern in `_validate_trip_fields`. See section 6.
