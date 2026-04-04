# App Settings + Macro Targets

## Parent spec

`docs/specs/10-macronutrient-tracking.md`

## What to build

A single-row app settings table storing global macro target percentages (protein/fat/carb, must sum to 100). GET/PUT API endpoints. A settings UI accessible from the app header. Trip summary displays actual macro percentages compared to targets.

## Type

AFK

## Blocked by

- Blocked by `30-trip-summary-macros.md`

## User stories addressed

- User story 5: Set a global macro target ratio
- User story 6: See actual vs target macro percentages

## Acceptance criteria

- [ ] `app_settings` table with `macro_target_protein_pct`, `macro_target_fat_pct`, `macro_target_carb_pct` (defaults: 20, 30, 50)
- [ ] Settings row auto-created on first access if not present
- [ ] `GET /api/settings` returns current settings
- [ ] `PUT /api/settings` updates settings; validates percentages sum to 100
- [ ] Settings UI accessible from app header (modal or simple page)
- [ ] Trip summary shows actual vs target comparison (e.g., side-by-side percentages)
- [ ] Tests for settings CRUD, validation (must sum to 100), and auto-creation

## Pattern exemplar

- Follow the pattern in: `backend/routers/ingredients.py` — simple CRUD router structure
- Follow the pattern in: `backend/models.py` — SQLAlchemy model definition

## Tasks

- [ ] Add `AppSettings` model and migration
- [ ] Create settings router with GET and PUT endpoints
- [ ] Add validation that percentages sum to 100
- [ ] Register settings router in main.py
- [ ] Update trip summary endpoint to include macro targets from settings
- [ ] Update trip summary UI to show actual vs target comparison
- [ ] Add settings UI (modal from header or simple page)
- [ ] Write tests for settings CRUD and validation
