# Issue #3: Ingredient Database — CRUD API + Management UI

## Context
The ingredient table is the shared foundation for recipes and snack catalog items. This is the first vertical slice with real data flow: backend CRUD endpoints, frontend table UI with inline editing, and column sorting. The scaffolding from issue #2 provides `models.py` (with the `Ingredient` SQLAlchemy model), `database.py`, and `main.py` with CORS and health-check already working.

## Acceptance Criteria
- Add ingredient with name and calories_per_oz
- Edit ingredient name, calories_per_oz, or notes
- Delete ingredient (warn/block if referenced by recipes or snack catalog)
- Table sorts by clicking column headers
- Data persists across page reloads (SQLite)

## Plan

### ✅ Step 1: Backend — Pydantic schemas for ingredients
Create `backend/schemas.py` with IngredientCreate, IngredientUpdate, and IngredientRead pydantic models. IngredientRead includes `id`. IngredientUpdate has all fields optional.

**Files**: `backend/schemas.py`
**Verify**: Backend still starts cleanly.

### ✅ Step 2: Backend — CRUD router for ingredients
Create `backend/routers/ingredients.py` with:
- `GET /api/ingredients` — list all, returns list of IngredientRead
- `POST /api/ingredients` — create, returns IngredientRead
- `PUT /api/ingredients/{id}` — update, returns IngredientRead, 404 if missing
- `DELETE /api/ingredients/{id}` — delete, 404 if missing, 409 if referenced by recipe_ingredients or snack_catalog

Register the router in `main.py`.

**Files**: `backend/routers/__init__.py`, `backend/routers/ingredients.py`, `backend/main.py` (add router include)
**Verify**: `curl` against all 4 endpoints — create, list, update, delete. Confirm 409 on delete when referenced (manually insert a referencing row to test).

### ✅ Step 3: Frontend — API client helper
Create a thin fetch wrapper (`frontend/src/api.js`) that handles base URL, JSON headers, and error responses. All API calls go through this.

**Files**: `frontend/src/api.js`
**Verify**: Frontend still builds and runs.

### ✅ Step 4: Frontend — Ingredients page with read-only table
Create `frontend/src/pages/IngredientsPage.jsx`. On mount, fetch `GET /api/ingredients` and render a table with columns: Name, Cal/oz, Notes. Add a route for `/ingredients` in the app router and a nav link.

**Files**: `frontend/src/pages/IngredientsPage.jsx`, `frontend/src/App.jsx` (add route + nav)
**Verify**: Navigate to /ingredients, see empty table. Manually POST an ingredient via curl, refresh, see it in the table.

### ✅ Step 5: Frontend — Add ingredient (inline form)
Add an "Add Ingredient" row or button at the bottom/top of the table. On submit, POST to the API and append to the local list. Name is required, cal/oz is required, notes is optional.

**Files**: `frontend/src/pages/IngredientsPage.jsx`
**Verify**: Add an ingredient through the UI, confirm it appears in the table and persists on reload.

### ✅ Step 6: Frontend — Edit ingredient (inline)
Click a row to enter edit mode (fields become inputs). Save sends PUT request, updates local state. Cancel reverts. Only one row editable at a time.

**Files**: `frontend/src/pages/IngredientsPage.jsx`
**Verify**: Edit an ingredient, confirm changes persist on reload.

### ✅ Step 7: Frontend — Delete ingredient
Add delete button per row. On click, confirm dialog, then DELETE request. If 409 (referenced), show a message explaining the ingredient is in use. On success, remove from local list.

**Files**: `frontend/src/pages/IngredientsPage.jsx`
**Verify**: Delete an unreferenced ingredient — gone on reload. Attempt delete of a referenced ingredient (seed one via curl with a recipe_ingredient FK) — see blocking message.

### ✅ Step 8: Frontend — Column sorting
Click column header to sort ascending; click again for descending. Client-side sort on the already-fetched list. Visual indicator (arrow) on the active sort column.

**Files**: `frontend/src/pages/IngredientsPage.jsx`
**Verify**: Click Name header — rows sort A-Z. Click again — Z-A. Same for Cal/oz (numeric sort).

## Files Summary

| Action | Path |
|--------|------|
| Create | `backend/schemas.py` |
| Create | `backend/routers/__init__.py` |
| Create | `backend/routers/ingredients.py` |
| Modify | `backend/main.py` |
| Create | `frontend/src/api.js` |
| Create | `frontend/src/pages/IngredientsPage.jsx` |
| Modify | `frontend/src/App.jsx` |

## Verification
1. Backend starts, all 4 ingredient endpoints return correct responses
2. Create 3+ ingredients via UI, confirm table displays them
3. Edit one ingredient, reload, confirm change persisted
4. Delete an unreferenced ingredient, confirm removed
5. Attempt delete of a referenced ingredient, confirm 409 with user-facing message
6. Sort by Name (asc/desc) and Cal/oz (asc/desc) via column headers
7. Full page reload retains all data
