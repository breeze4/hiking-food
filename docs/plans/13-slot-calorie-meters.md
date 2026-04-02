# Per-Slot Calorie Meters

## Parent PRD

`docs/specs/03-prd-meal-slots-and-planning-agent.md` — User stories 6, 8-9

## What to build

Replace the single summary panel with a slot-aware dashboard. Show per-slot calorie meters (target vs actual) for morning snack, lunch, and afternoon snack. Include a heatmap row showing which days are "covered" by each slot (based on total slot calories / daily slot target). Calorie targets per slot are derived from: (total daily target - breakfast cal - dinner cal) * slot percentage (25/40/35).

## Type

AFK

## Blocked by

- Blocked by `11-meal-slots.md` (needs slot assignments on trip_snacks and per-slot subtotals from API)

## User stories addressed

- As a user, I can see at a glance whether each meal slot is under/over its calorie target
- As a user, I can see a heatmap showing how many days each slot covers
- As a user, I can see how adding/removing a snack changes the slot meters in real time

## Acceptance criteria

- [x] Summary API returns per-slot calorie targets (based on 25/40/35 split of remaining calories)
- [x] Summary API returns per-slot actuals (calories and weight)
- [x] Summary API returns days_covered per slot (slot calories / daily slot target)
- [x] TripSummary component shows a meter per slot with target vs actual
- [x] Meters use green (in range), amber (under/over) status colors
- [x] Days covered shown as N/total_days text per slot
- [x] Overall trip totals still shown below slot breakdown

## Tasks

- [x] Update summary endpoint: compute per-slot calorie targets from (remaining_cal * 0.25/0.40/0.35)
- [x] Update summary endpoint: compute per-slot actuals by grouping trip_snacks by slot
- [x] Update summary endpoint: compute days_covered = slot_actual_cal / (daily_remaining_cal * slot_pct)
- [x] Redesign TripSummary: add slot meter section above the existing totals
- [x] Each slot meter: label, progress bar (actual/target), status badge, days covered indicator
- [x] Days covered shown as text (N/total_days) — visual heatmap grid deferred
- [x] Keep existing combined totals section below the slot breakdown
- [x] Mobile: slot meters stack vertically naturally (already responsive)
