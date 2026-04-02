# Slot Simplification

## Parent spec

`docs/specs/04-utility-audit.md`

## What to build

Collapse the three-slot snack model (morning_snack, lunch, afternoon_snack) to two slots (lunch, snacks) with a 40/60 calorie split. Migrate existing data, update backend mappings, frontend constants, summary meters, and packing screen — so the entire app reflects the simpler model end-to-end.

## Type

AFK

## Blocked by

None - can start immediately

## User stories addressed

- User story 1: Single "snacks" slot instead of morning/afternoon
- User story 2: Lunch/Snacks with 40/60 calorie split
- User story 3: Migrate existing morning_snack/afternoon_snack data to snacks
- User story 4: Human-readable slot names everywhere

## Acceptance criteria

- [x] No rows in trip_snacks have slot = morning_snack or afternoon_snack after migration
- [x] Backend CATEGORY_TO_SLOT maps bars_energy, salty, sweet → snacks; lunch → lunch
- [x] Frontend SLOTS array has two entries: lunch, snacks
- [x] SLOT_DEFAULT_CATEGORIES for snacks includes bars_energy, salty, sweet
- [x] TripSummary shows two slot meters with 40/60 split targets
- [x] Packing screen groups snacks under two slots
- [x] Slot dropdowns show "Lunch" and "Snacks" labels, no raw DB values
- [x] Backend tests verify migration and new slot values
- [x] Summary endpoint returns two slot subtotals with correct 40/60 split targets

## Tasks

- [x] Write DB migration `migrate_simplify_slots.py`: update trip_snacks rows where slot is morning_snack or afternoon_snack to snacks
- [x] Update CATEGORY_TO_SLOT in `backend/routers/trips.py` to new two-slot mapping
- [x] Update slot calorie split constants in backend (40/60 replacing 25/40/35)
- [x] Update SLOTS, SLOT_LABELS, SLOT_DEFAULT_CATEGORIES in `frontend/src/components/SnackSelection.jsx`
- [x] Update SNACK_SLOTS in `frontend/src/pages/PackingScreen.jsx`
- [x] Update TripSummary slot meters to render two slots with new split
- [x] Add backend tests: migration leaves no old slot values, summary returns correct split
- [x] Run migration on dev DB and verify
