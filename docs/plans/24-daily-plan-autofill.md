# Daily Plan — Auto-Fill Engine

## Parent spec

[docs/specs/09-daily-meal-plan.md](../specs/09-daily-meal-plan.md)

## What to build

The core daily meal plan feature: a new table for day assignments, the auto-fill algorithm that distributes meals/snacks/drink mixes across trip days, GET and POST auto-fill API endpoints, a comprehensive test suite, and a basic read-only UI showing how food distributes across days. This slice delivers the demoable "here's how your food distributes" experience without manual editing.

## Type

AFK

## Blocked by

- Blocked by `23-drink-mix-subcategories.md` (drink_mix_type needed for correct distribution)

## User stories addressed

- User story 1 — see food distributed across days
- User story 2 — auto-fill with sensible defaults
- User story 5 — partial days with proportional targets
- User story 9 — meals appear once per day only
- User story 12 — breakfast drinks excluded from first partial day
- User story 13 — dinner drinks excluded from last partial day
- User story 14 — flag insufficient drink mixes

## Acceptance criteria

- [x] trip_day_assignments table created with columns per spec (trip_id, day_number, slot, source_type, source_id, servings)
- [x] Auto-fill algorithm distributes meals heaviest-first, earliest-day-first, respecting slot rules
- [x] Auto-fill distributes snacks 1 serving per item per eligible day, heaviest-first
- [x] Auto-fill distributes drink mixes by subcategory to correct slots, with shortage warnings
- [x] Partial day slot rules enforced (first partial: no breakfast/morning; last partial: no dinner/afternoon)
- [x] GET endpoint returns day assignments grouped by day, plus unallocated items and warnings
- [x] POST auto-fill endpoint runs algorithm and replaces existing assignments
- [x] Comprehensive test suite covering meal/snack/drink distribution, partial days, edge cases
- [x] Basic read-only UI: navigate to daily plan, see day-by-day food assignments
- [x] Algorithm is deterministic (same inputs → same output)

## Tasks

- [x] Create trip_day_assignments table schema
- [x] Implement auto-fill algorithm: meal distribution (breakfast/dinner, heaviest-first, quantity handling)
- [x] Implement auto-fill algorithm: snack distribution (lunch/snacks slots, 1 per day per item)
- [x] Implement auto-fill algorithm: drink mix distribution (by subcategory, even spread, shortage warnings)
- [x] Implement GET /api/trips/{trip_id}/daily-plan endpoint
- [x] Implement POST /api/trips/{trip_id}/daily-plan/auto-fill endpoint
- [x] Write tests: meal distribution (correct days, heaviest-first, multi-quantity)
- [x] Write tests: partial day slot rules
- [x] Write tests: snack distribution (1/day, slot assignment, heaviest-first)
- [x] Write tests: drink mix distribution (subcategory mapping, even distribution, shortage warnings)
- [x] Write tests: edge cases (more meals than days, single-day trip, all-partial trip, zero servings)
- [x] Add daily plan route and basic read-only page showing day assignments
- [x] Add navigation link to daily plan from trip planner
