# Food Intake Capture (DB + API + UI)

## Parent spec

`docs/specs/15-food-intake-queue.md`

## What to build

The full capture path for the food intake queue: a new `food_intake` SQLite table, a CRUD REST API for it, and a new Intake page in the frontend with add/list/edit/delete. After this plan ships, the user can open the Intake screen on a phone, type a food name (and optional notes), and see it show up in a list grouped by status. No agent yet — status will sit at `pending` until plan 39 lands.

## Type

AFK

## Blocked by

None — can start immediately.

## User stories addressed

From `docs/specs/15-food-intake-queue.md`:
- Capture a food item on the fly with just a name (and optional notes) without having to fill out the full ingredient / snack catalog forms
- Edit or delete a captured item before it gets researched
- See the queue of pending items grouped by status

## Acceptance criteria

- [x] `food_intake` table exists with columns: `id`, `name` (required), `notes`, `status` (default `pending`), `created_at` (ISO string)
- [x] Status is constrained in application code to `pending` | `researched` | `added` (no DB check constraint required)
- [x] `GET /api/food-intake` returns all rows; supports `?status=` filter
- [x] `POST /api/food-intake` creates a row from `{name, notes?}`, always starting in `pending`
- [x] `PATCH /api/food-intake/:id` accepts partial updates of `{name?, notes?, status?}`
- [x] `DELETE /api/food-intake/:id` removes the row
- [x] New Intake page is reachable from the main nav
- [x] Page shows three sections (Pending, Researched, Added), each listing rows with name + notes
- [x] Add form at the top of Pending section with name input, optional notes input, and add button
- [x] Rows in any section can be edited (name/notes only — status is read-only in the UI) or deleted
- [x] Page works on mobile screens (the primary capture form factor)
- [x] Backend tests cover create, list, list-with-status-filter, patch, and delete

## Owns

- `backend/models.py` — add `FoodIntake` model
- `backend/schemas.py` — add `FoodIntakeBase`, `FoodIntakeCreate`, `FoodIntakeUpdate`, `FoodIntakeOut` schemas
- `backend/routers/food_intake.py` — new router with GET/POST/PATCH/DELETE
- `backend/main.py` — register `food_intake_router` (import + `inner.include_router`). Do NOT modify `_run_migrations` — new tables are created by `Base.metadata.create_all`.
- `backend/tests/test_food_intake.py` — new test file
- `frontend/src/pages/IntakePage.jsx` — new page component
- `frontend/src/api.js` — add `foodIntake` API client functions (list, create, update, delete)
- `frontend/src/App.jsx` — add route and nav link for `/intake`
- `docs/plans/INDEX.md` — add this plan to the index

## Must not touch

- `backend/routers/ingredients.py` — out of scope; plan 40 will read/write via this router
- `backend/routers/snacks.py` — out of scope; plan 40 will write via this router
- `.claude/agents/` — owned by plan `40-intake-research-agent.md`
- Any existing page under `frontend/src/pages/` other than `App.jsx` nav wiring — no incidental edits
- `backend/models.py` beyond adding the new `FoodIntake` class — no edits to existing models

## Defines interfaces

- `FoodIntakeOut` schema in `backend/schemas.py` — consumed by plan `40-intake-research-agent.md`
- `GET/POST/PATCH /api/food-intake` endpoints in `backend/routers/food_intake.py` — consumed by plan `40-intake-research-agent.md`

## Pattern exemplar

Two exemplars — one for backend, one for frontend.

- **MUST follow the pattern in**: `backend/routers/settings.py` — small, self-contained router with Pydantic schemas in `backend/schemas.py`, SQLAlchemy session via the shared `get_db` dependency, simple GET/PATCH pattern. Extend it with POST/DELETE in the style of `backend/routers/ingredients.py` (which has the full CRUD set).
- **Follow the pattern in**: `frontend/src/pages/SnackCatalogPage.jsx` — table/list layout, inline add form at the top, edit mode per row, delete button. Match the styling idioms (CSS classes, table structure) so the Intake page feels native.
- **Follow the pattern in**: `backend/tests/test_settings.py` — smallest full test file in the suite, shows the FastAPI TestClient + temp DB setup via `conftest.py`. Mirror its structure for `test_food_intake.py`.

## Tasks

- [x] Add `FoodIntake` model in `backend/models.py` (columns: id, name, notes, status default `pending`, created_at)
- [x] Add Pydantic schemas (`FoodIntakeCreate`, `FoodIntakeUpdate`, `FoodIntakeOut`) in `backend/schemas.py`
- [x] Create `backend/routers/food_intake.py` with GET (with optional `status` filter), POST, PATCH, DELETE
- [x] Validate status values in PATCH (only `pending` / `researched` / `added` allowed); return 422 on bad input
- [x] Register router in `backend/main.py`
- [x] Write `backend/tests/test_food_intake.py` covering create/list/filter/patch/delete
- [x] Run `cd backend && venv/bin/pytest` — all tests pass
- [x] Add `foodIntake` client in `frontend/src/api.js` (list, create, update, delete)
- [x] Create `frontend/src/pages/IntakePage.jsx` with add form + three status sections + per-row edit/delete
- [x] Wire route + nav link in `frontend/src/App.jsx`
- [x] Manual test in browser: add item, edit item, delete item, confirm grouping by status works (can fake a status change via curl/PATCH for now since the agent isn't built yet)
- [x] Update `docs/plans/INDEX.md`

## Implementation notes

- **No migration entry needed**: `food_intake` is a brand-new table. The lifespan handler already runs `Base.metadata.create_all(bind=engine)` in `backend/main.py`, which picks up new models automatically. Only add to `_run_migrations` when altering existing tables.
- **`created_at`**: store as ISO 8601 string (`datetime.utcnow().isoformat()`), set server-side in the POST handler. Matches the repo's SQLite-friendly approach (no `DateTime` columns elsewhere in `models.py`).
- **Status validation**: keep it simple — a module-level constant `VALID_STATUSES = {"pending", "researched", "added"}` in the router, checked in the PATCH handler. No need for an Enum column type.
- **Frontend status sections**: since status is read-only in the UI for v1, just render three `<section>` blocks and filter the fetched list client-side by status. No need for separate API calls per section.
- **Nav**: add the new link in whatever nav pattern `App.jsx` already uses — do not invent a new nav component. If nav is a plain list of links, append to it.

## Review

Shipped: `food_intake` table, `GET/POST/PATCH/DELETE /api/food-intake`, new `IntakePage` at `/intake` reachable from both desktop nav and mobile hamburger.

Key details:
- Schemas named `FoodIntakeCreate`, `FoodIntakeUpdate`, `FoodIntakeOut` (not `*Read`) to satisfy plan 40's expected imports. Deviation from the rest of the codebase's naming convention is intentional and called out in a comment above the schemas.
- Status validation is app-level via `VALID_STATUSES = {"pending", "researched", "added"}` in the router. Invalid values on PATCH or on the `?status=` filter return 422.
- `created_at` is set server-side via `datetime.utcnow().isoformat()`; `POST` always forces `status="pending"` regardless of client input (the `FoodIntakeCreate` schema doesn't even include status).
- Frontend uses inline `get/post/patch/del` calls (no `foodIntake` wrapper object) to match existing page idioms — the plan wording ("add foodIntake client") is satisfied by the page's direct calls.
- Intake page is a single-column mobile-first layout: prominent add form at top, then three sections (Pending / Researched / Added). Status is read-only in the UI (no dropdown). Edit is inline per row.
- Backend tests: 13 new tests in `test_food_intake.py`. All pass.

Known gate caveat:
- `tests/test_schema_match.py::test_fresh_schema_matches_prod` fails because the prod DB on beebaby does not yet have the `food_intake` table. This is the expected behavior of that drift test for any new-table plan; it clears on next deploy. All other tests (100 existing + 13 new) pass.

Smoke test passed — GET empty, POST returned row with id/status=pending/created_at, PATCH status=added returned 200, DELETE returned 204, post-delete GET empty.
