# Issue #4: Snack Catalog CRUD API + Management UI

## Context
The snack catalog wraps ingredients with serving-size info for trip planning. It's the second CRUD vertical slice, building on the ingredient database from issue #3. Snack catalog items reference ingredients via FK and add weight_per_serving, calories_per_serving, and optional notes. A computed field (calories_per_oz) is derived at display time.

This is a dependency for trip snack selection (issue #5+), so it needs to be solid.

## Assumptions
- Issue #2 (scaffolding) is done: backend/frontend running, all DB tables exist including `snack_catalog`
- Issue #3 (ingredients CRUD) is done: `backend/routers/ingredients.py` exists with full CRUD, frontend has an Ingredients page with inline editing and sortable columns
- The `snack_catalog` table already exists in `backend/models.py` from scaffolding
- We follow the same patterns established in issue #3 (router structure, Pydantic schemas, frontend component patterns)

## Plan

### Step 1: Backend — Pydantic schemas for snack catalog
Create `backend/schemas/snack.py` with:
- `SnackBase`: weight_per_serving (float), calories_per_serving (float), notes (optional str)
- `SnackCreate(SnackBase)`: adds ingredient_id (int)
- `SnackUpdate(SnackBase)`: all fields optional
- `SnackResponse(SnackBase)`: adds id, ingredient_id, ingredient_name (str), calories_per_oz (float, computed)

**Files**: `backend/schemas/snack.py`
**Verify**: Backend still starts without errors

### Step 2: Backend — CRUD router for snack catalog
Create `backend/routers/snacks.py` with:
- `GET /api/snacks` — list all, join with ingredients table to include ingredient name, compute calories_per_oz in response
- `POST /api/snacks` — create, validate ingredient_id exists
- `PUT /api/snacks/{id}` — update weight/calories/notes
- `DELETE /api/snacks/{id}` — delete, warn if referenced by trip_snacks

Register router in `backend/main.py`.

**Files**: `backend/routers/snacks.py`, `backend/main.py`
**Verify**: `curl` all four endpoints, confirm ingredient name included in GET response, confirm calories_per_oz computed correctly

### Step 3: Frontend — Add Snack Catalog page route and nav link
Add a `/snacks` route and navigation link, rendering a placeholder component. Follow the same pattern as the Ingredients page.

**Files**: `frontend/src/App.jsx` (or router config), nav component, `frontend/src/pages/SnackCatalog.jsx` (placeholder)
**Verify**: Click nav link, see placeholder page, other pages still work

### Step 4: Frontend — Snack catalog table with data fetching
Build out `SnackCatalog.jsx`:
- Fetch `GET /api/snacks` on mount
- Display table with columns: Ingredient Name, Weight/Serving (oz), Cal/Serving, Cal/Oz (computed), Notes
- Sortable columns (reuse pattern from Ingredients page)

**Files**: `frontend/src/pages/SnackCatalog.jsx`
**Verify**: Page loads, displays snack data (empty table if no data), columns sort correctly

### Step 5: Frontend — Add snack form with ingredient dropdown
Add inline form (or modal) for creating a new snack catalog item:
- Dropdown to select ingredient (fetch `GET /api/ingredients` for options)
- Inputs for weight_per_serving, calories_per_serving
- Optional notes field
- Submit calls `POST /api/snacks`, refreshes table

**Files**: `frontend/src/pages/SnackCatalog.jsx` (or extract a component)
**Verify**: Can add a snack item linked to an existing ingredient, it appears in the table with correct cal/oz

### Step 6: Frontend — Inline edit for snack catalog items
Add edit capability to table rows:
- Click to edit weight_per_serving, calories_per_serving, notes
- Save calls `PUT /api/snacks/{id}`, refreshes table
- Follow same inline edit pattern as Ingredients page

**Files**: `frontend/src/pages/SnackCatalog.jsx`
**Verify**: Can edit a snack item's serving size and calories, cal/oz updates correctly

### Step 7: Frontend — Delete snack catalog items
Add delete button per row:
- Calls `DELETE /api/snacks/{id}`
- Backend returns warning if item is referenced by active trips
- Confirm dialog before delete

**Files**: `frontend/src/pages/SnackCatalog.jsx`
**Verify**: Can delete a snack item, warning shown if referenced by trips, table refreshes after delete

## Verification
1. Backend: all four CRUD endpoints work via curl/httpie
2. GET response includes ingredient_name from joined ingredient record
3. calories_per_oz = calories_per_serving / weight_per_serving computes correctly
4. Frontend: table displays all snack items with correct data
5. Frontend: can add new snack item with ingredient dropdown
6. Frontend: can inline edit weight, calories, notes
7. Frontend: can delete with confirmation
8. Frontend: columns are sortable
9. Existing Ingredients page still works
10. Data persists across page reloads
