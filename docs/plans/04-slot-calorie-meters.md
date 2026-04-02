# Per-Slot Calorie Meters

## Parent PRD

`docs/SPEC.md` — Meal Slots section (L210, "per-slot calorie meters and heatmap"), Future Feature Request #3

## What to build

Replace the single summary panel with a slot-aware dashboard. Show per-slot calorie meters (target vs actual) for morning snack, lunch, and afternoon snack. Include a heatmap row showing which days are "covered" by each slot (based on total slot calories / daily slot target). Calorie targets per slot are derived from: (total daily target - breakfast cal - dinner cal) * slot percentage (25/40/35).

## Type

AFK

## Blocked by

- Blocked by `02-meal-slots.md` (needs slot assignments on trip_snacks and per-slot subtotals from API)

## User stories addressed

- As a user, I can see at a glance whether each meal slot is under/over its calorie target
- As a user, I can see a heatmap showing how many days each slot covers
- As a user, I can see how adding/removing a snack changes the slot meters in real time

## Acceptance criteria

- [ ] Summary API returns per-slot calorie targets (based on 25/40/35 split of remaining calories)
- [ ] Summary API returns per-slot actuals (calories and weight)
- [ ] Summary API returns days_covered per slot (slot calories / daily slot target)
- [ ] TripSummary component shows a meter per slot with target vs actual
- [ ] Meters use green (in range), amber (under/over) status colors
- [ ] Heatmap row shows N/total_days coverage per slot
- [ ] Overall trip totals still shown below slot breakdown

## Tasks

- [ ] Update summary endpoint: compute per-slot calorie targets from (remaining_cal * 0.25/0.40/0.35)
- [ ] Update summary endpoint: compute per-slot actuals by grouping trip_snacks by slot
- [ ] Update summary endpoint: compute days_covered = slot_actual_cal / (daily_remaining_cal * slot_pct)
- [ ] Redesign TripSummary: add slot meter section above the existing totals
- [ ] Each slot meter: label, progress bar (actual/target), status badge, days covered indicator
- [ ] Heatmap row: visual grid showing coverage per slot (filled/empty cells per day)
- [ ] Keep existing combined totals section below the slot breakdown
- [ ] Mobile: slot meters stack vertically, heatmap simplifies to text ("5/7 days")
