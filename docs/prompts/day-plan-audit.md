# Orchestration Prompt: Day Plan Audit (Plans 34-36)

## Project context

- Working directory: `/home/breeze/dev/hiking-food`
- Build: `cd frontend && npm run build`
- Test: `cd backend && venv/bin/pytest`
- Lint: `cd frontend && npm run lint`
- Dev: `cd backend && uvicorn main:app --reload` + `cd frontend && npm run dev`
- Issue: #12
- Handoff directory: `docs/handoff/` (create if needed)

## Orchestrator responsibilities

You are orchestrating three serial plans that all modify `DailyPlanPage.jsx`. Before launching each step's agent:

1. Read the files listed under "Context sources" and include relevant sections in the agent's "Context" field.
2. If a previous step completed, read `docs/handoff/step-{N}.md` and use it to understand what changed.
3. After each step, run the build/test gate and commit.

## Agent granularity rules

**One agent per plan.** Each plan is small (3-5 tasks) and tightly scoped. Do not combine plans — they each need a clean commit.

## Execution plan

All three plans are **serial** because they all modify `frontend/src/pages/DailyPlanPage.jsx`. No parallelization.

Order: 35 → 36 → 34. Rationale:
- Plan 35 (unallocated banner) adds new UI between chart and cards — minimal interaction with existing code
- Plan 36 (mobile UX) changes CSS classes on existing buttons — establishes the button styling foundation
- Plan 34 (fractional allocation) adds new state and modifies button behavior — builds on top of 36's button changes

---

### Step 1 — Unallocated bar chart visibility (Plan 35)

**Plan**: `docs/plans/35-unallocated-bar-chart-visibility.md`

**Agent briefing**: Add unallocated summary banner
- **Context sources** (orchestrator reads these):
  - `backend/routers/daily_plan.py` lines 266-300 (unallocated pool + response assembly)
  - `frontend/src/pages/DailyPlanPage.jsx` lines 300-332 (header, warnings, bar chart area)
  - `backend/tests/test_daily_plan.py` (skim for test patterns — how existing tests call endpoints and assert response shape)
- **Read first**: `docs/plans/35-unallocated-bar-chart-visibility.md`
- **Context**: <orchestrator pastes the above>

- **Owns**:
  - `backend/routers/daily_plan.py` (`_build_daily_plan_response` — add `unallocated_summary` to return dict only)
  - `frontend/src/pages/DailyPlanPage.jsx` (add banner between bar chart and day cards grid)
  - `backend/tests/test_daily_plan.py` (add test for `unallocated_summary` fields)

- **Must not touch**: autofill.py, models.py, any other frontend components, the bar chart SVG itself

- **MUST follow the pattern in**:
  - `backend/routers/daily_plan.py`: the `unallocated_summary` dict should sit alongside `"unallocated"` in the response. Compute it from the same `unallocated` list already built — don't re-query.
  - `backend/tests/test_daily_plan.py`: follow existing test style (fixture setup, endpoint calls via `client`, response shape assertions)

- **Do not**: modify the `StackedBarChart` component, change the unallocated pool section at the bottom, or add fractional serving support — that is Step 3's responsibility.

- **Done when**:
  - API response includes `unallocated_summary` with `count`, `total_calories`, `total_weight`
  - Banner appears between chart and day cards showing "N items unallocated (X cal · Y oz)" in amber text
  - Banner shows "All food allocated" in muted text when count is 0
  - `cd frontend && npm run build` succeeds
  - `cd backend && venv/bin/pytest` passes including new test

- **Handoff**: Write `docs/handoff/step-1.md` listing: response field name, banner component location in JSX, test name.

**Gate**: `cd backend && venv/bin/pytest && cd ../frontend && npm run build`

**Commit** after gate passes.

---

### Step 2 — Day plan mobile UX (Plan 36)

**Plan**: `docs/plans/36-day-plan-mobile-ux.md`

**Lookahead** (while step 1 runs): none needed — all context sources are in DailyPlanPage.jsx which step 1 modifies. Read the fresh version after step 1 completes.

**Agent briefing**: Touch-friendly action buttons and tap targets
- **Context sources** (orchestrator reads these):
  - `frontend/src/pages/DailyPlanPage.jsx` (full file — step 1 modified it, read the current version)
  - `frontend/src/index.css` or equivalent global CSS file (for the `@media (hover: none)` rule)
- **Read first**: `docs/plans/36-day-plan-mobile-ux.md`
- **Context**: <orchestrator pastes DailyPlanPage.jsx button sections — the "+" and "×" buttons around lines 383-394, and the unallocated day-picker buttons around lines 424-435>

- **Owns**:
  - `frontend/src/pages/DailyPlanPage.jsx` (button classes only — the "×", "+", and day-picker `<Button>` elements)
  - `frontend/src/index.css` (or app globals — add `@media (hover: none)` utility rule)

- **Must not touch**: backend code, StackedBarChart, MacroBar, the unallocated banner added in step 1, any component outside DailyPlanPage

- **Implementation approach**:
  - Add a CSS rule: `@media (hover: none) { .touch-visible { opacity: 0.6 !important; } }` and `@media (hover: none) { .touch-visible:active { opacity: 1 !important; } }`
  - Add `touch-visible` class to both the "+" and "×" buttons alongside existing `opacity-0 group-hover:opacity-100`
  - Change unallocated day-picker buttons from `h-6 w-8` to `h-9 w-10 sm:h-6 sm:w-8` (mobile-first, desktop override)
  - Add padding to "+" and "×" buttons: `p-2 sm:px-1 sm:py-0`

- **Do not**: change button onClick behavior, add new buttons, or modify the addToDay/incrementServings functions — that is Step 3's responsibility.

- **Done when**:
  - On `@media (hover: none)` devices, remove and increment buttons are visible without hover at 60% opacity
  - Day-picker buttons are at least 36x40px on mobile viewports
  - Action buttons have adequate tap padding on mobile
  - Desktop hover behavior unchanged
  - `cd frontend && npm run build` succeeds

- **Handoff**: Write `docs/handoff/step-2.md` listing: CSS rule location, class names added, which elements changed.

**Gate**: `cd frontend && npm run build`

**Commit** after gate passes.

---

### Step 3 — Fractional day allocation (Plan 34)

**Plan**: `docs/plans/34-fractional-day-allocation.md`

**Agent briefing**: Half-serving allocation toggle
- **Context sources** (orchestrator reads these):
  - `frontend/src/pages/DailyPlanPage.jsx` (full file — steps 1 and 2 modified it, read the current version)
  - `docs/handoff/step-2.md` (what CSS classes were added for mobile)
- **Read first**: `docs/plans/34-fractional-day-allocation.md`
- **Context**: <orchestrator pastes the `addToDay` function, `incrementServings` function, unallocated pool JSX section, and day item display section>

- **Owns**:
  - `frontend/src/pages/DailyPlanPage.jsx` (new state for allocation amounts, modified `addToDay`, modified `incrementServings`, updated unallocated pool UI, updated serving display)

- **Must not touch**: backend code (API already supports float servings), StackedBarChart, MacroBar, the unallocated banner from step 1, the CSS rules from step 2

- **Implementation approach**:
  - Add state: `const [allocAmounts, setAllocAmounts] = useState({})` — keyed by `${source_type}:${source_id}`, value is the serving amount (default 1)
  - For each unallocated item, add a toggle button before the day buttons: shows "1" or "½". Clicking toggles between 1 and 0.5. Style as a small pill/badge.
  - Auto-detect: when `item.remaining_servings < 1`, initialize that item's allocAmount to `remaining_servings`
  - Update `addToDay(item, dayNumber)` to read `allocAmounts[key] || 1` instead of hardcoded 1
  - For the "+" increment button on day items: add a "½" button next to it. The "+" adds 1, the "½" adds 0.5. Both use `incrementServings` which should accept an increment amount parameter.
  - Update serving display: show "×0.5", "×1.5" etc. Change condition from `item.servings > 1` to `item.servings !== 1` (catches both > 1 and fractional < 1)
  - Ensure new buttons include the `touch-visible` class from step 2 for mobile compatibility

- **Do not**: modify backend endpoints, change the auto-fill algorithm, add arbitrary precision — 0.5 is the only fractional value needed via toggle.

- **Done when**:
  - Unallocated items show a "1/½" toggle that switches allocation amount
  - Day buttons allocate the toggled amount (1 or 0.5)
  - Items with < 1 remaining auto-default to the remaining amount
  - Day items show a "½" button alongside "+" for half-serving increments
  - Fractional serving counts display correctly: "×0.5", "×1.5"
  - `cd frontend && npm run build` succeeds

- **Handoff**: Skip — this is the final step.

**Gate**: `cd backend && venv/bin/pytest && cd ../frontend && npm run build`

**Commit** after gate passes.

---

## Completion criteria

- All three plan files have tasks checked off
- `cd backend && venv/bin/pytest` passes
- `cd frontend && npm run build` succeeds
- `cd frontend && npm run lint` passes
- Three separate commits (one per plan)
- Update `docs/plans/INDEX.md`: move plans 34, 35, 36 to Completed section

## Frontend verification note

All three steps modify frontend with no automated UI test coverage beyond build. After all steps complete, consider launching the dev server and using agent-browser to screenshot the daily plan page on both desktop and mobile viewports to verify:
- Unallocated banner appears with correct totals
- Buttons visible on mobile-width viewport
- Fractional toggle works and displays correctly
