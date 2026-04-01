# Issue #2: Project Scaffolding

## Context
First issue for the hiking-food project. No code exists yet. Need to create the FastAPI backend and React+Vite frontend from scratch, with all 7 SQLite tables defined and a health-check endpoint proving the two can communicate.

## Acceptance Criteria (from issue)
- `cd backend && uvicorn main:app` starts without errors
- `cd frontend && npm run dev` starts without errors
- Frontend can fetch from a health-check endpoint on the backend
- All database tables are created on startup
- No seed data — just empty tables

## Plan

### Step 1: Backend skeleton
Create `backend/` with:
- `requirements.txt`: fastapi, uvicorn, sqlalchemy, pydantic
- `database.py`: SQLAlchemy engine + SessionLocal + Base, SQLite file at `hiking_food.db`, create_all on import
- `models.py`: All 7 SQLAlchemy models matching SPEC.md data model (ingredients, snack_catalog, recipes, recipe_ingredients, trips, trip_meals, trip_snacks)
- `main.py`: FastAPI app with CORS middleware (allow all origins for dev), health-check `GET /api/health`, lifespan event that calls create_all

### Step 2: Install backend deps and verify
- `cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- `uvicorn main:app` — confirm starts clean, hit /api/health

### Step 3: Frontend scaffold
- `npm create vite@latest frontend -- --template react`
- Minimal App.jsx that fetches `/api/health` and displays the result
- `vite.config.js` with proxy to backend at localhost:8000

### Step 4: Verify end-to-end
- Start backend on :8000, frontend on :5173
- Frontend fetches health-check through Vite proxy, displays result

## Files to create
- `backend/requirements.txt`
- `backend/database.py`
- `backend/models.py`
- `backend/main.py`
- `frontend/` (Vite scaffold + modified App.jsx + vite.config.js)

## Verification
1. `cd backend && uvicorn main:app --port 8000` starts without errors
2. `curl http://localhost:8000/api/health` returns 200
3. SQLite DB file created with all 7 tables
4. `cd frontend && npm run dev` starts without errors
5. Frontend displays health-check response
