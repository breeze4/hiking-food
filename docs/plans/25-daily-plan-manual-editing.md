# Daily Plan — Manual Editing

## Parent spec

[docs/specs/09-daily-meal-plan.md](../specs/09-daily-meal-plan.md)

## What to build

Add manual editing capabilities to the daily plan screen. Users can remove items from days (returning servings to the unallocated pool), add snack servings to existing day assignments, and assign unallocated items to specific days via a day picker. A reset button re-runs auto-fill after confirmation. The unallocated pool shows remaining servings with add-to-day controls.

## Type

AFK

## Blocked by

- Blocked by `24-daily-plan-autofill.md`

## User stories addressed

- User story 6 — remove item from day, returns to pool
- User story 7 — add snack serving to a day
- User story 8 — add from unallocated pool to specific day via day picker
- User story 10 — reset button re-runs auto-fill
- User story 11 — see when items run out across trip

## Acceptance criteria

- [x] Remove button on each day assignment returns servings to unallocated pool
- [x] Add button on snack assignments increments servings on that day
- [x] Meals cannot be doubled up on a day (no add button for meals)
- [x] Unallocated pool shows items with remaining servings and day picker to assign them
- [x] Reset button with confirmation dialog re-runs auto-fill
- [x] UI reflects changes immediately after each action
- [x] DELETE, POST, and PATCH assignment endpoints working

## Tasks

- [x] Implement POST /api/trips/{trip_id}/daily-plan/assignments endpoint (add item to day)
- [x] Implement DELETE /api/trips/{trip_id}/daily-plan/assignments/{id} endpoint
- [x] Implement PATCH /api/trips/{trip_id}/daily-plan/assignments/{id} endpoint (update servings)
- [x] Add remove button to each item in day detail sections
- [x] Add increment button for snack items (not meals)
- [x] Build unallocated pool UI with remaining servings and day picker buttons
- [x] Add reset-to-auto-fill button with confirmation dialog
- [x] Show "runs out after day X" indicator for items that don't cover all days
