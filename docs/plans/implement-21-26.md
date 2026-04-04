# Implement Plans 21–26

You are implementing 6 plans for the hiking food trip planner app. Read each plan file carefully before starting work on it. Follow CLAUDE.md instructions.

## Project context

- **Dev**: `cd backend && uvicorn main:app --reload` + `cd frontend && npm run dev`
- **Test**: `cd backend && venv/bin/pytest`
- **App spec**: `docs/specs/02-app-spec.md`
- **Stack**: FastAPI + SQLAlchemy + SQLite backend, React + Vite + Tailwind + shadcn frontend

## Plans to implement

### Phase 1 — Parallel (no dependencies)

These three plans have no blockers. Implement them in any order.

1. **Plan 21 — Collapsible Category Grid** (`docs/plans/21-collapsible-category-grid.md`)
   - Pure frontend. Wrap the category grid in TripSummary in a collapsible section, collapsed by default.
   - No backend changes. No tests needed.

2. **Plan 22 — Shopping List Enhancements** (`docs/plans/22-shopping-list-enhancements.md`)
   - Add 3 new columns to ingredients table (on_hand, essentials, packing_method).
   - Update ingredient CRUD, shopping list endpoint, and packing screen.
   - Add frontend UI for all new fields.
   - Write backend tests for shopping list sorting and on_hand toggle.

3. **Plan 23 — Drink Mix Subcategories** (`docs/plans/23-drink-mix-subcategories.md`)
   - Add drink_mix_type column to snack_catalog table.
   - Migrate existing drink mix items to correct types.
   - Show conditional selector in snack catalog edit UI.

### Phase 2 — Sequential (dependency chain)

These must be done in order. Phase 2 starts only after Plan 23 is complete.

4. **Plan 24 — Daily Plan Auto-Fill** (`docs/plans/24-daily-plan-autofill.md`)
   - New trip_day_assignments table.
   - Auto-fill algorithm for meals, snacks, and drink mixes.
   - GET and POST auto-fill endpoints.
   - Comprehensive test suite (this is the most test-heavy plan).
   - Basic read-only daily plan page + nav link.

5. **Plan 25 — Daily Plan Manual Editing** (`docs/plans/25-daily-plan-manual-editing.md`)
   - CRUD endpoints for individual assignments.
   - Remove/add buttons on day details, increment for snacks only.
   - Unallocated pool UI with day picker.
   - Reset-to-auto-fill with confirmation.

6. **Plan 26 — Daily Plan Bar Chart & Layout** (`docs/plans/26-daily-plan-bar-chart.md`)
   - Stacked bar chart (calories per day by category) with target lines.
   - Responsive grid layout for day detail sections.
   - Shortage warnings display.
   - Chart updates reactively on assignment changes.

## Rules

1. **Read the plan file** before starting each plan. The plan has acceptance criteria and task lists — use them.
2. **Read existing code** before modifying it. Understand what's there before writing.
3. **Run tests** after each plan: `cd /home/breeze/dev/hiking-food/backend && venv/bin/pytest`. Fix failures before moving on.
4. **Git commit** after completing each plan. Use a descriptive commit message. Do not batch multiple plans into one commit.
5. **Mark tasks complete** in the plan file as you finish them.
6. **Update the plan index** (`docs/plans/INDEX.md`): move completed plans from "Not Started" to "Completed".
7. **Do not deploy.** Do not run deploy.sh.
8. **Consult the app spec** (`docs/specs/02-app-spec.md`) if you need broader context about how the app works.
9. **Match existing patterns.** Look at how existing routers, models, components, and tests are structured and follow the same patterns.
10. **Keep it simple.** Don't add features or abstractions beyond what the plan specifies.
11. **Schema changes**: add new columns with ALTER TABLE in the app startup (follow the existing pattern in main.py or models.py for adding columns to existing tables).
12. **Frontend routing**: follows the pattern in the existing router setup. The daily plan page should be at `/trips/:tripId/daily-plan`.
