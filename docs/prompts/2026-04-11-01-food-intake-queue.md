# Orchestration Prompt: Food Intake Queue

Implements `docs/specs/15-food-intake-queue.md` via plans 39 and 40. Two serial AFK steps: capture-path vertical slice, then the research agent that consumes it.

## Project context

- Working directory: `/home/breeze/dev/hiking-food`
- Research: none — spec is small enough that no research artifact was produced
- Build: `cd frontend && npm run build`
- Test: `cd backend && venv/bin/pytest`
- Lint: none configured
- Spec: `docs/specs/15-food-intake-queue.md`
- Handoff directory: `docs/handoff/` (exists; add new files)

Dev servers (for manual verification only, not a gate): `cd backend && uvicorn main:app --reload` + `cd frontend && npm run dev`. Vite proxies `/api` to :8000.

## Orchestrator responsibilities

You are actively managing context between agents. Before launching each step:

1. Read the files listed under "Context sources" and paste the relevant sections into the agent's "Context" field so the agent does not waste tokens rediscovering them.
2. If a previous step completed, read its handoff file from `docs/handoff/` and inline the key facts into the next agent's briefing.
3. Do not launch the next step until the gate after the previous step passes.

## Dependency graph

```
Step 1 (plan 39, AFK)  →  Step 2 (plan 40, AFK)
```

Strict serial. Plan 40 consumes the `/api/food-intake` endpoints and `FoodIntakeOut` schema that Step 1 defines. No parallelism possible. No soft-dependency collisions — Step 2 touches only `.claude/agents/` and the INDEX.

## Execution plan

### Step 1 — Food intake capture (DB + API + UI)

**Plan**: `docs/plans/39-food-intake-capture.md`

**Agent briefing**:
- **Context sources** (orchestrator reads these before launch):
  - `docs/specs/15-food-intake-queue.md` — full spec (Data Model, API, Behavior sections are load-bearing)
  - `docs/plans/39-food-intake-capture.md` — the plan
  - `backend/models.py` — to see how existing tables are declared and where the new model goes
  - `backend/schemas.py` — to see request/response schema style
  - `backend/routers/settings.py` — smallest existing router, good structural template
  - `backend/routers/ingredients.py` — has the full GET/POST/PATCH/DELETE set, use for CRUD shape
  - `backend/main.py` lines 1–100 — router registration + `_run_migrations` (DO NOT modify `_run_migrations`; `Base.metadata.create_all` handles brand-new tables)
  - `backend/tests/test_settings.py` — smallest test file, shows TestClient + fixture setup
  - `backend/tests/conftest.py` — shared test fixtures
  - `frontend/src/api.js` — existing API client, append `foodIntake` block in the same style
  - `frontend/src/App.jsx` — routing and nav wiring
  - `frontend/src/pages/SnackCatalogPage.jsx` — closest sibling page (table + inline add + per-row edit/delete)
- **Read first**: `docs/plans/39-food-intake-capture.md`
- **Context**: (orchestrator pastes: the `FoodIntake` row-shape from spec §Data Model, the FastAPI router template from `settings.py`, the SnackCatalogPage's add form + row edit JSX, the nav link pattern from `App.jsx`, and the current `_run_migrations` function so the agent can confirm it does not need to be touched)
- **Owns**:
  - `backend/models.py` — add `FoodIntake` class only
  - `backend/schemas.py` — add `FoodIntakeCreate`, `FoodIntakeUpdate`, `FoodIntakeOut`
  - `backend/routers/food_intake.py` — new file
  - `backend/main.py` — import + `include_router` only (one-line additions)
  - `backend/tests/test_food_intake.py` — new file
  - `frontend/src/pages/IntakePage.jsx` — new file
  - `frontend/src/api.js` — add `foodIntake` client block
  - `frontend/src/App.jsx` — add `/intake` route + nav link
  - `docs/plans/INDEX.md` — move plan 39 to "In Progress" then "Completed" when done
- **Must not touch**:
  - `backend/routers/ingredients.py`, `backend/routers/snacks.py` — Step 2 (plan 40) reads/writes via these endpoints
  - `.claude/agents/` — owned by Step 2
  - Any page under `frontend/src/pages/` other than the new `IntakePage.jsx` and the `App.jsx` nav wiring
  - `backend/models.py` beyond the new `FoodIntake` class
  - `backend/main.py` `_run_migrations` function — new tables are created by `Base.metadata.create_all`
- **MUST follow the pattern in**: `backend/routers/ingredients.py` — CRUD shape (GET with optional filter, POST, PATCH, DELETE), same use of `Depends(get_db)`, same Pydantic schema style. Use `backend/routers/settings.py` as the starting skeleton (smaller, fewer distractions), then extend with the CRUD verbs from `ingredients.py`.
- **Follow the pattern in**: `frontend/src/pages/SnackCatalogPage.jsx` — add form at the top, list below with per-row edit/delete. Match CSS class usage exactly so the Intake page feels native.
- **Follow the pattern in**: `backend/tests/test_settings.py` — TestClient + temp DB fixture setup.
- **Do not**:
  - Do not create a `.claude/agents/research-intake.md` file — that is Step 2's responsibility.
  - Do not add duplicate-name validation to the ingredients API — the spec places that in the agent, not the API.
  - Do not add proposed-value columns (`proposed_calories_per_oz`, etc.) to the `food_intake` table — the spec explicitly rejects this.
  - Do not let the UI mutate `status` — status is read-only in the UI for v1.
- **If unclear, stop**: if the nav in `App.jsx` is not a plain list of links and you are tempted to refactor it to fit the Intake link, stop and ask.
- **Handoff**: Write `docs/handoff/step-1-food-intake-capture.md` listing:
  - Exact `FoodIntake` model columns as shipped (names + types + defaults)
  - Final `FoodIntakeOut` schema shape (fields the agent will see in GET responses)
  - Final API surface (exact paths, methods, query params, body shapes, status codes)
  - Any deviations from the plan and why

**Gate**: `cd backend && venv/bin/pytest && cd ../frontend && npm run build`

Pass = all pytest green, frontend build succeeds with no errors.
Fail = stop and report. Do not launch Step 2.

**Interface gate** (after Step 1, before launching Step 2):
- [ ] `curl -s http://localhost:8000/api/food-intake` returns `[]` or a list (not 404)
- [ ] `curl -sX POST http://localhost:8000/api/food-intake -H 'Content-Type: application/json' -d '{"name":"test"}'` returns a row with `id`, `name`, `status: "pending"`, `created_at`
- [ ] `curl -sX PATCH http://localhost:8000/api/food-intake/1 -H 'Content-Type: application/json' -d '{"status":"added"}'` returns 200
- [ ] `curl -sX DELETE http://localhost:8000/api/food-intake/1` returns 200/204

(Run these against a locally started `uvicorn main:app` — the app's lifespan handler will auto-create the new table via `Base.metadata.create_all`.)

### Step 2 — Intake research agent

**Plan**: `docs/plans/40-intake-research-agent.md`

**Agent briefing**:
- **Context sources** (orchestrator reads these before launch):
  - `docs/handoff/step-1-food-intake-capture.md` — authoritative for the final API + schema shapes
  - `docs/plans/40-intake-research-agent.md` — the plan
  - `docs/specs/15-food-intake-queue.md` — agent §, Behavior §, Judgment Calls §
  - `.claude/agents/research-macros.md` — structural and voice template (this is the hard exemplar)
  - `backend/routers/ingredients.py` — to capture the exact POST payload shape the agent must send
  - `backend/routers/snacks.py` — to capture the exact POST payload shape the agent must send
  - `backend/schemas.py` — to confirm ingredient and snack schemas the agent must satisfy
- **Read first**: `docs/plans/40-intake-research-agent.md`
- **Context**: (orchestrator pastes: the Step 1 handoff file in full, the `research-macros.md` frontmatter + USDA reference block + match-preference rules, the exact `POST /api/ingredients` and `POST /api/snacks` request shapes from the routers, and the spec's Behavior + Judgment Calls sections)
- **Prior step context**: Step 1 added the `food_intake` table and the `/api/food-intake` CRUD endpoints. Trust `docs/handoff/step-1-food-intake-capture.md` over any other description — if the handoff disagrees with this briefing, the handoff wins.
- **Owns**:
  - `.claude/agents/research-intake.md` — new agent definition
  - `docs/plans/INDEX.md` — move plan 40 through In Progress to Completed on finish
- **Must not touch**:
  - Anything under `backend/` — the agent consumes the API, it does not change it
  - Anything under `frontend/` — no UI work in this step
  - `.claude/agents/research-macros.md` — pattern reference only, do not edit
- **MUST follow the pattern in**: `.claude/agents/research-macros.md` — copy the frontmatter format, section headings, API reference block structure, USDA reference block (verbatim — do not paraphrase unit conversion or match preferences), source tracking, and rate limit handling. The new agent is the net-new-items sibling of the missing-macros agent; it must feel like the same hand wrote it.
- **Do not**:
  - Do not add any uniqueness check or validation to the backend — duplicate detection lives inside the agent, via `GET /api/ingredients` + case-insensitive name comparison.
  - Do not propose a schema change (no new columns on `food_intake`, `ingredients`, or `snack_catalog`). If you want to persist something, the schema already has a place for it.
  - Do not make the agent auto-approve — it must present a review table and wait for explicit user approval before writing.
  - Do not let the agent touch `researched` or `added` rows. Scope is strictly `pending`.
- **If unclear, stop**: if the `POST /api/snacks` payload requires a field you cannot infer from the item name + notes + USDA data (e.g. a drink_mix_type for a non-drink-mix item), stop and ask whether to prompt the user per-item or pick a default.
- **Handoff**: Write `docs/handoff/step-2-intake-research-agent.md` listing:
  - Final agent file path and frontmatter
  - Any deviations from `research-macros.md`'s structure and why
  - The POST payload shapes the agent sends (copy-paste examples)
  - Open items the user should manually test with real intake rows

**Gate**: `cd backend && venv/bin/pytest && cd ../frontend && npm run build`

Agent-definition-only changes should not break the build or tests, but run the gate anyway to catch accidental edits outside `.claude/agents/`.

**Manual verification** (post-gate, HITL):
- [ ] Add 3 varied rows via the Intake page: an obvious packaged snack (e.g. "Chomps beef sticks"), a recipe-only ingredient (e.g. "masa harina"), a duplicate of something already in the ingredient catalog (e.g. "Peanut butter" if already there).
- [ ] Run the new agent against the local backend.
- [ ] Confirm the proposal table flags the duplicate, categorizes the snack correctly, and proposes ingredient-only for the recipe item.
- [ ] Approve, confirm new rows exist in `ingredients` / `snack_catalog`, confirm intake rows are `added`.

## HITL checkpoints

- [ ] **After Step 2**: run the manual verification above before marking plan 40 done. The agent's real value is only visible on real data — a green build does not mean it works.

## Completion criteria

- Both plans' acceptance criteria checked off
- `cd backend && venv/bin/pytest && cd ../frontend && npm run build` green
- Interface gate after Step 1 passed (curl smoke test)
- Manual verification after Step 2 passed
- `docs/plans/INDEX.md` reflects both plans as Completed
- Two handoff files written under `docs/handoff/`
- Frontend smoke-tested in a browser on a narrow viewport (Intake is a mobile-first screen — a green `npm run build` is not a UX test)
