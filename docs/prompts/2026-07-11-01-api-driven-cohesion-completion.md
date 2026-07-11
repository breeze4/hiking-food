/goal The orchestration below has reached a terminal state — EITHER every item in the "Completion criteria" section holds (all `## Tasks` in plans 43, 44, and 45 checked `- [x]`; `cd backend && venv/bin/pytest -q` and `cd frontend && pnpm test && pnpm lint && pnpm build` exit 0; one commit per step in `git log`, each pushed and gated), OR a gate has failed and the failure has been reported with the failing output and no further changes attempted. Execute every step and its sub-goal to get there. Prove the terminal state in your final message: show the passing gate output and `git log --oneline`, or the failing gate output. A reported gate failure ends the run — do not keep retrying past it. +300k

# Orchestration Prompt: API-Driven Cohesion — Completion (plans 43–45)

## Model policy

This session should be running on Opus (`/model opus` before pasting, if it is not). Every implementation agent AND every verifier subagent is launched via the Agent tool with `model: "opus"` explicitly set — do not inherit a different model, do not use Fable for any agent. Use `model: "haiku"` only for trivial git/status lookups if you delegate them at all.

## Project context

- Working directory: `/Users/breeze/dev/hiking-food`
- Spec: `docs/specs/2026-07-11-01-api-driven-cohesion.md`
- Prior-state handoff (background, already reflected in the plans): `docs/handoff/2026-07-11-01-api-driven-cohesion.md`
- MCP playbook (read before exercising MCP trip planning): `docs/agents/hiking-food-mcp.md`
- Backend test: `cd backend && venv/bin/pytest -q`
- Frontend test/lint/build: `cd frontend && pnpm test && pnpm lint && pnpm build`
- Run (for browser verification): backend `cd backend && uvicorn main:app --reload` + frontend `cd frontend && pnpm dev` → `http://localhost:5173/hiking-food/`
- Deployed URL: `http://beebaby:8000/hiking-food/` (commits to `main`, once pushed, are gated and auto-deployed exact-SHA by cicd-router — pushing IS deploying; that is expected)
- Screenshots: `screenshots/` (never staged in commits)
- Handoff directory: `docs/handoff/`
- Progress artifact source: `docs/handoff/progress.html` (published via the Artifact tool; never staged in commits)

Expected starting state: clean `main` worktree at or after commit `f8bb9b8`, with plans `docs/plans/43-*.md`, `44-*.md`, `45-*.md` present and unchecked. Verify with `git status --short` and `git log -3 --oneline` before Step 1; if the tree is dirty, stop and report.

## Orchestrator responsibilities

You are actively managing context between agents. Before launching each step:

1. Read the files listed under "Context sources" and include the relevant sections in the agent's "Context" field.
2. If a previous step completed, read its `docs/handoff/step-{N}-*.md` and use it to fill in what changed.
3. After each step's gates pass, ensure the commit and push land per the **Commit policy** below before launching the next step.
4. **Close the loop on checkboxes.** Each agent must mark its completed tasks `- [x]` in its plan file (part of its "done"). As steps land, you tick this prompt's own boxes below and move the plan between sections in `docs/plans/INDEX.md` (Not Started → Completed) in the same commit as the plan checkoff.
5. **Maintain the progress artifact.** Before Step 1: write `docs/handoff/progress.html` — spec name, the three steps with statuses, gate results — publish it with the Artifact tool, and report the URL to the user. When each step launches, after its gates pass and its commit lands, on any gate failure, and at the terminal state: update the file and republish (same file path = same URL). Inline key screenshots as data: URIs; the page must be self-contained. Never stage this file in a commit.

## Commit policy (applies to every step)

This **overrides** the default "only commit when explicitly asked" behavior. Commits are required, not optional.

- One commit per step, made **only after** that step's gates pass.
- Push each step's commit to `main` after it lands; cicd-router gates and deploys the exact SHA. Do not use any direct deploy script.
- Message format: `step-N: <plan-slug> — <one-line summary>`.
- Stage only files inside the step's `Owns` set, plus the step's handoff file, the step's plan file (with its newly checked `- [x]` boxes), and `docs/plans/INDEX.md`. Never `git add -A`. Never stage `screenshots/` or `docs/handoff/progress.html`.
- **Never** include `Co-Authored-By` trailers, "Generated with Claude Code" footers, or any mention of AI/Claude in commit messages.
- On gate failure: do not commit. Stop and report per the goal's terminal state.

## Execution plan

Three serial steps, all prescriptive: each plan's `## Tasks` are the path, executed in order, test-first.

### Step 1 — OAuth and server boundary hardening

**Plan**: `docs/plans/43-oauth-server-hardening.md`

**Agent briefing** (launch with `model: "opus"`):
- **Goal**: Close the five confirmed security weaknesses (password throttling, honest metadata, CORS removal, MCP host policy, lazy absolute OAuth DB path) without breaking the authorization-code + PKCE flow.
- **Context sources** (orchestrator reads and inlines the relevant parts): `backend/mcp_oauth/app.py`, `backend/mcp_oauth/tokens.py`, `backend/main.py:22-103`, `backend/mcp_server.py:36-49`, `backend/database.py:1-30`, `backend/tests/test_mcp_oauth.py`
- **Read first**: the plan file — its Context section carries exact line references and its Decisions section is settled; implement exactly those decisions.
- **Context**: (orchestrator pastes the inlined code here before launch)
- **Owns**: `backend/mcp_oauth/`, `backend/main.py`, `backend/mcp_server.py` (transport-security block only), `backend/tests/test_mcp_oauth.py`, `backend/tests/test_runtime_config.py`
- **Must not touch**: frontend files, `backend/services/`, `backend/routers/`, other plan files, `docs/` except your own plan file and handoff.
- **MUST follow the pattern in**: `backend/tests/test_mcp_oauth.py` — per-test `tmp_path` DB isolation, `monkeypatch.setenv`, the `_challenge()` PKCE helper; and `backend/database.py:7-11` for the absolute-path-with-env-override shape.
- **Do not**: reimplement client registration, redirect validation, refresh rotation, hashed storage, or the legacy refresh-row migration — those are complete and covered. Do not touch `list_food_options` or router imports — that is Step 3's responsibility.
- **Done when**: the plan's Done-when holds — full backend suite green with new coverage for all five behaviors.
- **Check off**: Mark each completed task `- [x]` in `docs/plans/43-oauth-server-hardening.md` (and any now-satisfied Acceptance criteria). Editing this plan file is the one allowed exception to "Must not touch".
- **Handoff**: Write `docs/handoff/step-1-oauth-hardening.md`: what changed per file, the new env vars and their defaults, and any behavior a reconnecting OAuth client will notice (e.g. removed OIDC discovery).
- Stay within your plan's scope. If you see an improvement that belongs to a later step, leave it.

**Gate**: `cd backend && venv/bin/pytest -q`

**Verify gate** (fresh context, `model: "opus"` — after the Gate passes, before the commit): spawn a verifier subagent whose prompt contains ONLY the plan's `## Acceptance criteria`, the briefing's "Done when", and the step's diff (`git diff`) — never the implementing agent's summary or reasoning. Instruct it to REFUTE completion (find an unmet criterion) and to exercise behavior where possible: run the backend suite itself, start uvicorn locally and curl the discovery endpoints, confirm no CORS header on a cross-origin request, and confirm a disallowed Host is rejected at `/mcp`. On failure: stop and report — do not auto-fix.

**Browser gate**: skipped — no browser surface changed (the authorize page template is untouched; all behaviors are observable at the API level). Live deployed checks happen after the push: curl `http://beebaby:8000/hiking-food/.well-known/oauth-authorization-server` (trimmed metadata), the authorize page (renders), and `/mcp` unauthenticated (401 discovery challenge) once cicd-router reports the SHA deployed.

**Commit** (after gates pass): stage the owned backend paths + `docs/plans/43-oauth-server-hardening.md` + `docs/plans/INDEX.md` + `docs/handoff/step-1-oauth-hardening.md`; message `step-1: oauth-server-hardening — <summary>`; push; confirm the cicd-router exact-SHA gate result and run the live checks above.

### Step 2 — Frontend mutation state, accessible controls, lazy routes

**Plan**: `docs/plans/44-frontend-mutation-ux.md`

**Agent briefing** (launch with `model: "opus"`):
- **Goal**: Every mutation exposes pending/error state and refreshes the right projections; every quantity/half-serving/add/remove control has an accessible name; route pages are lazy-loaded and the bundle warning is gone.
- **Context sources**: `docs/handoff/step-1-oauth-hardening.md`, `frontend/src/App.test.jsx`, `frontend/src/App.jsx`, `frontend/src/context/TripContext.jsx`, `frontend/src/components/MealSelection.jsx`, `frontend/src/components/SnackSelection.jsx`, `frontend/src/pages/DailyPlanPage.jsx`, `frontend/src/pages/PackingScreen.jsx`, `frontend/src/components/TripCalculator.jsx`, `frontend/vite.config.js`
- **Read first**: the plan file — Decisions are settled (one shared hook, no query library, aria-labels with item names, React.lazy + Suspense).
- **Context**: (orchestrator pastes handoff findings + relevant code here)
- **Owns**: `frontend/src/` (components, pages, hooks, context, test files), `frontend/vite.config.js` only if the test setup requires it.
- **Must not touch**: `backend/`, `frontend/package.json` dependencies (no new libraries), other plan files, `docs/` except your own plan file and handoff.
- **MUST follow the pattern in**: `frontend/src/App.test.jsx` — fetch-stub via `vi.stubGlobal`, route seeding via `history.replaceState`, whole-App render, role-based queries; and `DailyPlanPage.jsx`'s `text-destructive` error rendering.
- **Prior step context**: Step 1 changed backend OAuth/CORS/MCP boundaries only; no frontend-visible API contract changed. Trust the step-1 handoff over this description.
- **Done when**: the plan's Done-when holds — `pnpm test && pnpm lint && pnpm build` green, no chunk-size warning, all 17 pre-existing tests still passing alongside the new coverage.
- **Check off**: Mark each completed task `- [x]` in `docs/plans/44-frontend-mutation-ux.md` (and any now-satisfied Acceptance criteria). Editing this plan file is the one allowed exception to "Must not touch".
- **Handoff**: Write `docs/handoff/step-2-frontend-mutation-ux.md`: the hook's API, which call sites adopted it, the accessible-name convention used, and the before/after main-chunk size.
- Stay within your plan's scope. If you see an improvement that belongs to a later step, leave it.

**Gate**: `cd frontend && pnpm test && pnpm lint && pnpm build`

**Verify gate** (fresh context, `model: "opus"` — after the Gate passes, before the commit): verifier sees ONLY the plan's `## Acceptance criteria`, "Done when", and `git diff`. It re-runs the frontend gate itself, greps for remaining fire-and-forget mutation call sites, and runs the Browser gate below. On failure: stop and report — do not auto-fix.

**Browser gate** (run by the Verify-gate subagent, never the implementer): start `cd backend && uvicorn main:app --reload` and `cd frontend && pnpm dev`, open `http://localhost:5173/hiking-food/` with the `agent-browser` skill, `snapshot -i` after every navigation. Drive: navigate planner → daily plan → packing → recipes (lazy chunks load, no blank screens); on the planner, add a snack, change a quantity with the stepper, remove it — each round-trips and re-renders; confirm in snapshots that stepper/remove/add controls expose accessible names identifying their item. Screenshots → `screenshots/`. On failure: stop and report.

**Commit** (after gates pass): stage `frontend/src/` changes + `docs/plans/44-frontend-mutation-ux.md` + `docs/plans/INDEX.md` + `docs/handoff/step-2-frontend-mutation-ux.md`; message `step-2: frontend-mutation-ux — <summary>`; push; confirm the cicd-router gate result.

### Step 3 — Catalog projections, architecture doc, completion audit

**Plan**: `docs/plans/45-catalog-projections-audit.md`

**Agent briefing** (launch with `model: "opus"`):
- **Goal**: `mcp_server.py` imports nothing from `routers.*`; `docs/architecture.md` is accurate; the full audit (gates, deploy verification, spec-behavior accounting) is written down.
- **Context sources**: `docs/handoff/step-1-oauth-hardening.md`, `docs/handoff/step-2-frontend-mutation-ux.md`, `backend/mcp_server.py`, `backend/routers/recipes.py`, `backend/routers/snacks.py`, `backend/services/trip_queries.py`, `backend/tests/test_mcp_tools.py`, `docs/architecture.md`, the spec's four behavior lists
- **Read first**: the plan file — Decisions are settled (module name, function names, byte-identical REST shapes, audit-table-in-handoff).
- **Context**: (orchestrator pastes handoff findings + relevant code here)
- **Owns**: `backend/services/catalog_queries.py` (new), `backend/routers/recipes.py`, `backend/routers/snacks.py`, `backend/mcp_server.py`, `backend/tests/test_mcp_tools.py`, `docs/architecture.md`
- **Must not touch**: `frontend/src/` behavior, `backend/mcp_oauth/`, other plan files, `docs/` except architecture.md, your own plan file, and your handoff.
- **MUST follow the pattern in**: `backend/services/trip_queries.py` — `db: Session` first arg, `<noun>_view`/`<noun>_list_view` naming, plain dicts, no FastAPI imports.
- **Prior step context**: Steps 1 and 2 landed OAuth/CORS/MCP-transport hardening and the frontend mutation/a11y/lazy work; architecture.md must describe the post-step-1 topology. Trust the handoffs over this description.
- **Done when**: the plan's Done-when holds — both gates green, deployed SHA verified on BeeBaby, spec-behavior accounting complete in the handoff.
- **Check off**: Mark each completed task `- [x]` in `docs/plans/45-catalog-projections-audit.md` (and any now-satisfied Acceptance criteria). Editing this plan file is the one allowed exception to "Must not touch".
- **Handoff**: Write `docs/handoff/step-3-catalog-audit.md`: changes per file, plus the full spec-behavior accounting table (every bullet in the spec's Compatibility/Correctness/Security/Operational lists → covering test or commit, or an explicit "uncovered" flag).
- Stay within your plan's scope. This is the final step — do not broaden into visual redesign or new planning features.

**Gate**: `cd backend && venv/bin/pytest -q && cd ../frontend && pnpm test && pnpm lint && pnpm build`

**Verify gate** (fresh context, `model: "opus"` — after the Gate passes, before the commit): verifier sees ONLY the plan's `## Acceptance criteria`, "Done when", and `git diff`. It re-runs the backend suite, confirms `grep -n "routers\." backend/mcp_server.py` finds no imports, spot-checks that a REST snack/recipe list response is shape-identical to the pre-refactor contract (via the existing tests plus a live local request), and checks the audit table covers every spec bullet. On failure: stop and report — do not auto-fix.

**Browser gate** (run by the Verify-gate subagent, after the push and cicd-router deploy of this step's SHA): open `http://beebaby:8000/hiking-food/` with `agent-browser` — planner renders with live data, daily plan and packing pages navigate, a recipes list loads (exercising the refactored catalog projections through the UI). Curl the MCP discovery endpoints and confirm the 401 challenge at `/mcp`. Screenshots → `screenshots/`. On failure: stop and report. The user reviews the deployed app against live data after the run — note that in the final message.

**Commit** (after the local gates pass; the deployed checks then run against the pushed SHA): stage the owned backend paths + `docs/architecture.md` + `docs/plans/45-catalog-projections-audit.md` + `docs/plans/INDEX.md` + `docs/handoff/step-3-catalog-audit.md`; message `step-3: catalog-projections-audit — <summary>`; push; confirm the cicd-router exact-SHA result; then run the deployed browser gate above.

## Interface gates

- [ ] After Step 1: `HIKING_FOOD_MCP_ALLOWED_HOSTS` / `HIKING_FOOD_MCP_ALLOWED_ORIGINS` env vars exist with the documented defaults, and `create_router`'s default DB path is absolute — Step 3's architecture.md rewrite depends on these being real.

## HITL checkpoints

None. The user reviews the deployed BeeBaby app and the three commits after the run (end-of-run review; git makes it reversible).

## UI / Browser testing

Target: `http://localhost:5173/hiking-food/` locally (Step 2) and `http://beebaby:8000/hiking-food/` deployed (Step 3).

- [ ] Step 2, plan-44: drive lazy-loaded navigation, snack add/quantity/remove round-trips, and accessible-name checks via `agent-browser`; screenshots → `screenshots/`
- [ ] Step 3, plan-45: drive the deployed BeeBaby app across planner/daily-plan/packing/recipes plus MCP discovery curls; screenshots → `screenshots/`
- Skipped (no browser surface): Step 1 (API-observable security boundaries; authorize template unchanged — covered by curl-level live checks post-deploy)

## Completion criteria

- All `## Tasks` in plans 43, 44, and 45 are checked `- [x]`, their satisfied Acceptance criteria are checked, and `docs/plans/INDEX.md` lists all three under Completed
- `cd backend && venv/bin/pytest -q` exits 0
- `cd frontend && pnpm test && pnpm lint && pnpm build` exits 0, with no chunk-size warning
- Three commits (`step-1`, `step-2`, `step-3`) exist in `git log`, each pushed, each with a passing cicd-router exact-SHA gate
- No commit message references AI, Claude, or co-authorship
- Steps 2 and 3 passed their live `agent-browser` gates; Step 1's deployed curl checks passed
- Every step's Acceptance criteria were confirmed by a fresh-context Opus verifier, never the implementing agent
- The spec-behavior accounting table in `docs/handoff/step-3-catalog-audit.md` accounts for every bullet in the spec's four behavior lists
- The progress artifact was published before Step 1, updated after every step, and shows the terminal state
