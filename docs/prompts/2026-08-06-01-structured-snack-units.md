/goal The structured-snack-units orchestration below has reached a terminal state — EITHER every item in the "Completion criteria" section holds (all six plans' `## Tasks` checked `- [x]`, backend pytest + frontend test/build/lint all exit 0, one commit per step in `git log`, run report committed), OR a gate has failed and the failure has been reported with the failing output and no further changes attempted. Execute every step and its sub-goal to get there. Prove the terminal state in your final message: show the passing gate output and `git log --oneline`, or the failing gate output. A reported gate failure ends the run — do not keep retrying past it. +500k

# Orchestration Prompt: Structured Snack Units (4 × 2 oz per day)

Six goal-directed steps, strictly serial, one commit per step. Every implementing agent and every verifier subagent is launched with `model: "opus"`.

## Project context

- Working directory: `/Users/breeze/dev/hiking-food`
- Spec: `docs/specs/2026-08-06-01-structured-snack-units.md` (read fully before Step 1)
- Build: `cd frontend && pnpm build`
- Test: `cd backend && venv/bin/pytest` then `cd frontend && pnpm test`
- Lint: `cd frontend && pnpm lint` (final gate; not per-step)
- Run (for browser verification): `cd backend && uvicorn main:app --reload` (port 8000) + `cd frontend && pnpm dev` → `http://localhost:5173/hiking-food/`
- Screenshots: `screenshots/`
- Handoff directory: `docs/handoff/`
- Progress artifact data: `docs/handoff/progress.json` (schema: `~/.claude/skills/plans-to-prompt/progress/SCHEMA.md`) — rendered via `progress/build.sh` to `docs/handoff/progress.html`, published with the Artifact tool; transient during the run (never in step commits), renamed at the terminal state to `docs/handoff/2026-08-06-01-structured-snack-units-run.{json,html}` and committed as the run report.
- Note: commits to `main` are enqueued for gated deploy by cicd-router automatically. This is expected — not an error, not a reason to pause.

## Orchestrator responsibilities

You actively manage context between agents:

1. Before each step, read its "Context sources" and the prior step's handoff file; paste the relevant excerpts into the agent's Context.
2. After each step's gates pass, ensure the commit lands per the Commit policy before launching the next step.
3. Close the loop on checkboxes: each agent ticks its own plan's `- [x]` boxes; you tick this prompt's boxes and the spec's `## Acceptance criteria` as steps satisfy them (criteria can span plans — that's your job, not the workers').
4. Maintain the progress artifact. Before Step 1: create `docs/handoff/progress.json` per the schema (six steps, all `"queued"`), build with `sh ~/.claude/skills/plans-to-prompt/progress/build.sh docs/handoff/progress.json docs/handoff/progress.html`, publish `progress.html` via the Artifact tool, report the URL to the user. Re-run that loop (edit JSON → build → republish, same path = same URL) on every step launch, gate result, commit, failure, and the terminal state — stamping `updated` and prepending an `events` row each time. Every gate carries evidence, never a bare checkmark: test `cmd` + output `tail` (`full` verbatim on failure); the verifier's per-criterion table; for browser gates 1–3 `shots` (downscale via `sips -Z 900 -s format jpeg`, then data-URI) captioned with flow + assertion; `commit` hash + diffstat. If `build.sh` fails, fix the JSON, never the HTML. At the terminal state (pass OR fail): final republish, rename the pair to `docs/handoff/2026-08-06-01-structured-snack-units-run.{json,html}`, commit both alone as `run: structured-snack-units — report (pass|fail)`. Then capture any run friction as entries in `docs/lessons.md` (ingest-lessons format; skip if frictionless — ride in the run-report commit) and tag that commit `run/2026-08-06-01-structured-snack-units`.

## Commit policy (applies to every step)

This **overrides** the default "only commit when explicitly asked" behavior. Commits are required.

- One commit per step, made **only after** that step's gates pass (backend pytest + frontend test + build).
- Message format: `step-N: <plan-slug> — <one-line summary>`.
- Stage only the step's `Owns` paths, plus the step's handoff file and the step's plan file (with newly checked `- [x]` boxes) — the plan file is the one exception to Owns-only staging. Never `git add -A`. Never stage `docs/handoff/progress.*` or `screenshots/` in a step commit.
- **Never** mention AI or Claude or add co-author trailers in commit messages.
- On gate failure: do not commit; stop and report. Fixes (if the run resumes later) go in new commits, never amends.

## Execution plan

All six steps are **goal-directed**: lead with the Goal and Done-when; the agent reads its plan and chooses tactics. Every briefing includes: "Stay within your plan's scope. If you see an improvement that belongs to a later step, leave it. If a plan instruction contradicts what you find in the code, stop and report — do not guess."

### Step 1 — Trip snack mode + schema foundation

**Plan**: `docs/plans/2026-08-06-01-trip-snack-mode-schema.md`

**Agent briefing** (`model: "opus"`):
- **Goal**: Every trip carries an explicit snack model with configurable snacks-per-day and oz-per-snack, existing trips are frozen as legacy, and the three unit tables exist — so later steps can gate on `snack_model` and build on the tables.
- **Context sources** (orchestrator reads these): `backend/models.py`, `backend/migrations.py` (migration pattern + `MIGRATIONS` tuple), the trip create/clone code in `backend/services/trip_planning.py` and `backend/routers/trips.py`.
- **Read first**: the plan file, then the spec's Data Flow and Behavior sections.
- **Owns**: per the plan's `## Owns` list.
- **Must not touch**: per the plan's `## Must not touch` list.
- **MUST follow the pattern in**: `backend/migrations.py` — `_migration_2_trip_cascades` + `_add_column_if_missing`.
- **Do not**: build any library/selection/planner behavior — Steps 2 and 3 own those. Heed the plan's implementation note: column default stays `legacy`; `structured` is set in the create path.
- **Done when**: the plan's `## Acceptance criteria` all hold, including the legacy-summary-unchanged invariant test.
- **Check off**: mark completed tasks `- [x]` in the plan file (the one allowed exception to Must-not-touch).
- **Handoff**: `docs/handoff/step-1-snack-mode-schema.md` — new columns/tables, where defaults are set, clone behavior, test names added.

**Gate**: `cd backend && venv/bin/pytest` then `cd frontend && pnpm test && pnpm build`.

**Interface gate** (orchestrator, after Gate): confirm `Trip.snack_model`/`snacks_per_day`/`oz_per_snack` and models `SnackUnitType`, `SnackUnitIngredient`, `TripSnackUnit` exist in `backend/models.py`, and the trip API returns the three fields — Steps 2–6 depend on these exact names.

**Verify gate** (fresh context, `model: "opus"` — after the Gate, before the commit): spawn a verifier whose prompt contains ONLY the plan's `## Acceptance criteria`, the Done-when, and the step's diff — never the implementer's summary. Instruct it to REFUTE completion and exercise behavior (run targeted pytest cases, hit the API). It returns a structured per-criterion report (text, PASS/FAIL, how exercised) which you render into the progress artifact. On failure: stop and report — do not auto-fix.

**Browser gate** (run by the verifier, never the implementer): with backend + frontend dev servers running, drive `http://localhost:5173/hiking-food/` via the `agent-browser` skill — create a new trip, assert the calculator shows "Snacks/day" 4 and "Oz/snack" 2; open a pre-existing trip, assert those inputs are absent. Screenshots → `screenshots/`.

**Commit**: `step-1: trip-snack-mode-schema — <summary>`.

### Step 2 — Snack unit type library

**Plan**: `docs/plans/2026-08-06-02-snack-unit-library.md`

**Agent briefing** (`model: "opus"`):
- **Goal**: The user can define a bag composition once in a library UI, see derived weight/calories/macros and a drift warning, and no other module recomputes that math.
- **Context sources**: `docs/handoff/step-1-snack-mode-schema.md`, `backend/routers/snacks.py`, `backend/services/catalog_queries.py`, `frontend/src/pages/SnackCatalogPage.jsx`, `frontend/src/pages/RecipeEditPage.jsx`.
- **Read first**: the plan file.
- **Owns** / **Must not touch**: per the plan.
- **MUST follow the pattern in**: `backend/routers/snacks.py` — router structure, response models, status codes.
- **Do not**: wire units into trips, summaries, or planner UI — Step 3 owns that.
- **Prior step context**: Step 1 created the tables and models; trust the handoff file.
- **Done when**: the plan's `## Acceptance criteria` all hold (CRUD, derived math, ±25% warning bounds, 409 delete protection, library UI with component test).
- **Check off**: tick the plan file.
- **Handoff**: `docs/handoff/step-2-snack-unit-library.md` — endpoint shapes, `snack_unit_type_view` fields, page route/nav location.

**Gate**: same as Step 1.

**Interface gate** (orchestrator): `GET /api/snack-unit-types` returns `composition[]`, `weight_oz`, `calories`, macro grams, `weight_warning` — Steps 3/5/6 consume this shape.

**Verify gate**: same protocol as Step 1 (criteria + diff only, refute, structured report, opus).

**Browser gate** (verifier): drive the library page — create a two-ingredient bag, assert derived weight/calories render and update; create an off-weight bag, assert the warning badge. Screenshots → `screenshots/`.

**Commit**: `step-2: snack-unit-library — <summary>`.

### Step 3 — Trip unit selections + quota + planner UI

**Plan**: `docs/plans/2026-08-06-03-trip-unit-selections.md`

**Agent briefing** (`model: "opus"`):
- **Goal**: On a structured trip the user fills a visible unit quota from packaged snacks and library bags, sees drifty units flagged against the trip's `oz_per_snack`, and packs against it — while every legacy trip's planner and summary remain byte-identical.
- **Context sources**: handoffs from Steps 1–2, `backend/routers/trips.py` (snack endpoints + clone), `backend/services/trip_queries.py` (`trip_snack_view`, `trip_summary_view`), `frontend/src/components/SnackSelection.jsx`.
- **Read first**: the plan file, then the spec's Behavior section.
- **Owns** / **Must not touch**: per the plan.
- **MUST follow the pattern in**: `backend/routers/trips.py` — `add_trip_snack`/`update_trip_snack`/`remove_trip_snack` for the selection endpoints.
- **Do not**: touch autofill/daily-plan (Step 4), `packing_view`/`shopping_view` (Step 5), or MCP (Step 6). Heed the plan's note: derive day fractions locally in `snack_units.py`, do not import from `autofill.py`.
- **Prior step context**: trust the Step 1–2 handoffs for table/model and view shapes.
- **Done when**: the plan's `## Acceptance criteria` all hold, including quota math (0.5+2+0.5 @ 4/day = 12), 409 on legacy trips, clone copying, and the legacy-summary snapshot.
- **Check off**: tick the plan file.
- **Handoff**: `docs/handoff/step-3-trip-unit-selections.md` — `unit_quota` signature, selection REST shapes, summary `snack_units` block fields, UI component structure.

**Gate**: same as Step 1.

**Interface gate** (orchestrator): `services/snack_units.py` exposes `unit_quota(trip)` (total + per-day list); structured trip summary contains `snack_units {quota, filled, per_day}`; `/api/trips/{id}/snack-units` CRUD works — Steps 4–6 consume these.

**Verify gate**: same protocol (opus, refute, structured report).

**Browser gate** (verifier): on a structured trip, add a packaged unit and a bag unit, set quantities, assert the meter reads filled/quota and completes at quota, assert a tolerance badge on an off-weight unit; open a legacy trip and assert the snacks section renders the old calorie-band UI unchanged. Screenshots → `screenshots/`.

**Commit**: `step-3: trip-unit-selections — <summary>`.

### Step 4 — Daily plan integration

**Plan**: `docs/plans/2026-08-06-04-daily-plan-units.md`

**Agent briefing** (`model: "opus"`):
- **Goal**: Auto-fill on a structured trip lands every unit on a day — two morning, two afternoon, scaled by per-day quota on partial days — and the day view shows them, while legacy trips' daily plans are untouched.
- **Context sources**: Step 3 handoff, `backend/services/autofill.py` (`distribute_snacks`, `auto_fill`), `backend/services/daily_plan_queries.py` (`_snack_info`, `_assignment_item`), `backend/routers/daily_plan.py`, `frontend/src/pages/DailyPlanPage.jsx`.
- **Read first**: the plan file.
- **Owns** / **Must not touch**: per the plan.
- **MUST follow the pattern in**: `backend/services/autofill.py` — `distribute_snacks`.
- **Do not**: modify `snack_units.py` or `trip_queries.py` (Step 3's, consume only); no schema changes (`source_type` is TEXT — the new `snack_unit` value needs no migration).
- **Prior step context**: `unit_quota` and selection views exist per the Step 3 handoff.
- **Done when**: the plan's `## Acceptance criteria` all hold, including 1+1 half-day distribution and the legacy auto-fill snapshot.
- **Check off**: tick the plan file.
- **Handoff**: `docs/handoff/step-4-daily-plan-units.md` — distribution behavior, `snack_unit` assignment shape.

**Gate**: same as Step 1.

**Verify gate**: same protocol (opus, refute, structured report).

**Browser gate** (verifier): on the structured trip from Step 3's data, run daily-plan auto-fill and assert units appear 2+2 in morning/afternoon snack slots on full days and scaled on partial days; remove one and assert it returns to the unallocated pool. Screenshots → `screenshots/`.

**Commit**: `step-4: daily-plan-units — <summary>`.

### Step 5 — Shopping list + packing screen

**Plan**: `docs/plans/2026-08-06-05-shopping-packing-units.md`

**Agent briefing** (`model: "opus"`):
- **Goal**: The shopping list tells the user exactly how many ounces of each bulk ingredient to buy (bags expanded) and the packing screen reads as a bag-assembly checklist with counts and target weights — legacy outputs untouched.
- **Context sources**: Step 3 handoff, `backend/services/trip_queries.py` (`shopping_view`, `packing_view`), `frontend/src/pages/PackingScreen.jsx`, `backend/tests/test_shopping_list.py`.
- **Read first**: the plan file.
- **Owns** / **Must not touch**: per the plan — only `shopping_view`/`packing_view` in `trip_queries.py`; packed checkoff reuses Step 3's selection update endpoint, no new mutations.
- **MUST follow the pattern in**: `backend/services/trip_queries.py` — the existing `shopping_view` aggregation loop.
- **Do not**: touch summary/selection code (Step 3) or MCP (Step 6).
- **Done when**: the plan's `## Acceptance criteria` all hold, including the 6-bag expansion math and legacy snapshots.
- **Check off**: tick the plan file.
- **Handoff**: `docs/handoff/step-5-shopping-packing-units.md` — response shape additions.

**Gate**: same as Step 1.

**Verify gate**: same protocol (opus, refute, structured report).

**Browser gate** (verifier): on the structured trip, open the shopping list and assert expanded ingredient ounces from bags; open the packing screen and assert "make N × <type> @ <target> oz" rows with working checkoff and actual-weight entry. Screenshots → `screenshots/`.

**Commit**: `step-5: shopping-packing-units — <summary>`.

### Step 6 — MCP tools + plan-food agent

**Plan**: `docs/plans/2026-08-06-06-mcp-agent-units.md`

**Agent briefing** (`model: "opus"`):
- **Goal**: Any MCP client can plan a structured trip end-to-end — read the quota, browse the library, create a bag type, fill units to quota — without the web UI.
- **Context sources**: Step 3 handoff, `backend/mcp_server.py` (`get_trip_plan`, `set_trip_snack_servings`), `backend/tests/test_mcp_tools.py`, `.claude/agents/plan-food.md`.
- **Read first**: the plan file.
- **Owns** / **Must not touch**: per the plan; consume the Step 2/3 service layer, never modify it. No frontend changes.
- **MUST follow the pattern in**: `backend/mcp_server.py` — `set_trip_snack_servings` and `get_trip_plan`.
- **Done when**: the plan's `## Acceptance criteria` all hold, including legacy-unchanged `get_trip_plan` output.
- **Check off**: tick the plan file.
- **Handoff**: `docs/handoff/step-6-mcp-agent-units.md` — new tool names and shapes.

**Gate**: same as Step 1, plus the final lint gate: `cd frontend && pnpm lint`.

**Verify gate**: same protocol (opus, refute, structured report). No browser gate — no user-facing surface; MCP behavior is exercised via the pytest tool tests.

**Commit**: `step-6: mcp-agent-units — <summary>`.

## Interface gates

- [x] After Step 1: trip fields + three models exist under the exact names Steps 2–6 use
- [x] After Step 2: `snack_unit_type_view` shape (composition, derived values, `weight_warning`) present in list endpoint
- [x] After Step 3: `unit_quota(trip)`, summary `snack_units` block, and selection REST shape present

## HITL checkpoints

None — end-of-run review of the commits instead.

## UI / Browser testing

Target: `http://localhost:5173/hiking-food/` (start `uvicorn main:app --reload` in `backend/` and `pnpm dev` in `frontend/`).

- [x] Step 1: calculator fields on new vs legacy trip
- [x] Step 2: bag builder, derived values, warning badge
- [x] Step 3: unit picker + quota meter + tolerance badge; legacy planner unchanged
- [x] Step 4: auto-fill 2+2 distribution, unallocated return
- [x] Step 5: shopping expansion, bag-assembly packing rows
- Skipped (no browser surface): Step 6 (MCP tools; exercised via pytest)

## Completion criteria

- All six plans' `## Acceptance criteria` met and all `## Tasks` checked `- [x]`; the spec's satisfied `## Acceptance criteria` checked `- [x]`
- `cd backend && venv/bin/pytest` passes; `cd frontend && pnpm test && pnpm build && pnpm lint` passes
- One commit per step in `git log` (steps 1–6, no squashes), no AI/co-author mentions
- Every user-facing step passed its live `agent-browser` gate with screenshots in `screenshots/`
- Every step's acceptance criteria confirmed by a fresh-context verifier (opus), never the implementing agent
- Progress artifact published before Step 1 (URL reported), republished at every transition, evidence-backed throughout; finalized as `docs/handoff/2026-08-06-01-structured-snack-units-run.{json,html}` in its own `run:` commit (pass or fail), tagged `run/2026-08-06-01-structured-snack-units`, no untracked progress files left
