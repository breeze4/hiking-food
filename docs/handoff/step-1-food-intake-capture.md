# Step 1 — Food Intake Capture (Plan 39) — Handoff

This is the ground truth for plan 40 (intake research agent). It reflects what actually shipped.

## 1. Final `FoodIntake` model columns

In `backend/models.py`:

| Column | SQLAlchemy type | Nullable | Default |
|---|---|---|---|
| `id` | `Integer`, primary_key | No | autoincrement |
| `name` | `Text` | No | — |
| `notes` | `Text` | Yes | None |
| `status` | `Text` | No | `"pending"` (Python-side default) |
| `created_at` | `Text` | Yes | None (set server-side on POST to `datetime.utcnow().isoformat()`) |

Table name: `food_intake`. No foreign keys, no check constraints, no indexes. Status is validated in application code only, not at the DB level. Allowed values: `pending`, `researched`, `added`.

## 2. Final Pydantic schemas

In `backend/schemas.py`, under the `# --- Food Intake ---` divider. **Note the naming deviation**: the codebase elsewhere uses the `*Read` suffix (e.g. `IngredientRead`), but per plan 39's interface section the output schema is named `FoodIntakeOut`. Plan 40 should import `FoodIntakeOut`.

```python
class FoodIntakeCreate(BaseModel):
    name: str
    notes: Optional[str] = None


class FoodIntakeUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class FoodIntakeOut(BaseModel):
    id: int
    name: str
    notes: Optional[str] = None
    status: str
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}
```

Field-by-field:

**FoodIntakeCreate**
- `name: str` — required
- `notes: Optional[str]` — optional, defaults to `None`
- Status is **not** an accepted field. The router always forces `status="pending"` on insert.

**FoodIntakeUpdate**
- `name: Optional[str]` — optional
- `notes: Optional[str]` — optional
- `status: Optional[str]` — optional; if present, must be one of `{"pending", "researched", "added"}` or the router returns 422.

**FoodIntakeOut**
- `id: int` — required, assigned by DB
- `name: str` — required
- `notes: Optional[str]` — may be null
- `status: str` — always present, one of the three valid values
- `created_at: Optional[str]` — set by the POST handler, but schema is permissive in case of legacy rows

## 3. Final API surface

All endpoints are under `/hiking-food/api/food-intake` (the app is mounted at `/hiking-food`). Router prefix: `/api/food-intake`. Defined in `backend/routers/food_intake.py`.

### GET `/api/food-intake`

- Query params: optional `status` (one of `pending | researched | added`)
- Invalid `status` value → **422**
- Returns: `list[FoodIntakeOut]`, ordered by `id` ascending
- Status: **200**

```
$ curl -s http://localhost:8765/hiking-food/api/food-intake
[]
```

### POST `/api/food-intake`

- Body: `{"name": str, "notes"?: str}`
- Server sets `status="pending"` and `created_at=datetime.utcnow().isoformat()`
- Returns: the created `FoodIntakeOut` row
- Status: **201**

```
$ curl -sX POST http://localhost:8765/hiking-food/api/food-intake \
    -H 'Content-Type: application/json' -d '{"name":"smoke test"}'
{"id":1,"name":"smoke test","notes":null,"status":"pending","created_at":"2026-04-11T21:16:43.886371"}
```

### PATCH `/api/food-intake/{id}`

- Body: any subset of `{"name"?: str, "notes"?: str, "status"?: str}`
- Uses `exclude_unset=True` — only the fields you pass are touched
- Invalid status value → **422**
- Row not found → **404**
- Returns: the updated `FoodIntakeOut` row
- Status: **200**

```
$ curl -sX PATCH http://localhost:8765/hiking-food/api/food-intake/1 \
    -H 'Content-Type: application/json' -d '{"status":"added"}'
{"id":1,"name":"smoke test","notes":null,"status":"added","created_at":"2026-04-11T21:16:43.886371"}
```

### DELETE `/api/food-intake/{id}`

- Row not found → **404**
- Returns: empty body
- Status: **204**

```
$ curl -sw '\nSTATUS: %{http_code}\n' -X DELETE http://localhost:8765/hiking-food/api/food-intake/1

STATUS: 204
```

### Plan 40 usage notes

- To drain the queue: `GET /api/food-intake?status=pending`, iterate, PATCH each row to `added` after creating the ingredient/snack rows.
- The intake API will not dedupe; duplicate detection lives in the agent per the spec.
- The intake API does not create ingredient or snack rows; the agent must call `POST /api/ingredients` and `POST /api/snacks` explicitly.
- `PATCH` accepts partial updates — you can just send `{"status": "added"}` without re-sending name/notes.

## 4. Deviations from the plan

1. **Schema naming**: kept `FoodIntakeOut` (as plan 39 declares in its "Defines interfaces" section) rather than renaming to `FoodIntakeRead` to match `IngredientRead`/`AppSettingsRead`. Added a comment in `schemas.py` explaining the one-off. Plan 40 can import `FoodIntakeOut` directly.
2. **No `foodIntake` API wrapper in `frontend/src/api.js`**: the existing frontend uses inline `get('/path')` / `post('/path', body)` calls from pages; there are no per-entity wrapper objects anywhere. `IntakePage.jsx` follows that convention. The plan task "Add `foodIntake` client in `frontend/src/api.js`" is satisfied functionally by the page's direct API calls — no new helper object was introduced.
3. **Schema drift test**: `tests/test_schema_match.py::test_fresh_schema_matches_prod` fails because the beebaby prod DB does not yet have the `food_intake` table. This is the intended behavior of that drift test for any new-table plan, not a bug in this work. It will self-resolve on deploy. Not a regression.

## 5. Gate results

### Backend pytest

```
============ 1 failed, 101 passed, 34 warnings in 341.37s (0:05:41) ============
```

- 101 passing (88 existing + 13 new in `test_food_intake.py`)
- 1 failing: `tests/test_schema_match.py::test_fresh_schema_matches_prod` — expected drift vs prod due to the new `food_intake` table, see deviation (3) above

New tests in `backend/tests/test_food_intake.py`:
- `test_list_empty`
- `test_create_sets_pending_and_created_at`
- `test_create_with_notes`
- `test_create_ignores_client_status`
- `test_list_returns_all`
- `test_list_status_filter`
- `test_list_invalid_status_filter`
- `test_patch_name_and_notes`
- `test_patch_status_valid`
- `test_patch_status_invalid`
- `test_patch_nonexistent`
- `test_delete`
- `test_delete_nonexistent`

### Frontend build

```
vite v8.0.3 building client environment for production...
✓ 2016 modules transformed.
dist/index.html                                           0.50 kB │ gzip:   0.31 kB
dist/assets/index-Ce3spoct.css                           80.82 kB │ gzip:  13.53 kB
dist/assets/index-DRD95U7J.js                           537.66 kB │ gzip: 163.58 kB
✓ built in 583ms
```

Build is clean. The 500kB chunk-size warning is pre-existing and unrelated to this change.

## 6. Smoke test results

Ran against `venv/bin/uvicorn main:app --port 8765` (mounted at `/hiking-food`), using the real dev DB (cleaned up after).

| Step | Request | Expected | Actual | Pass |
|---|---|---|---|---|
| 1 | `GET /api/food-intake` | `[]` | `[]` | yes |
| 2 | `POST /api/food-intake` body `{"name":"smoke test"}` | 201, `{id, name, notes=null, status='pending', created_at set}` | `{"id":1,"name":"smoke test","notes":null,"status":"pending","created_at":"2026-04-11T21:16:43.886371"}` | yes |
| 3 | `PATCH /api/food-intake/1` body `{"status":"added"}` | 200, row with `status='added'` | 200, `{"id":1,...,"status":"added",...}` | yes |
| 4 | `GET /api/food-intake?status=added` | list with the row | `[{"id":1,...,"status":"added",...}]` | yes |
| 5 | `DELETE /api/food-intake/1` | 204 | 204 | yes |
| 6 | `GET /api/food-intake` | `[]` | `[]` | yes |

All four curl checks from the prompt behave exactly as expected.
