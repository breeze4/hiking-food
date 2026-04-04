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

- [x] `app_settings` table with `macro_target_protein_pct`, `macro_target_fat_pct`, `macro_target_carb_pct` (defaults: 20, 30, 50)
- [x] Settings row auto-created on first access if not present
- [x] `GET /api/settings` returns current settings
- [x] `PUT /api/settings` updates settings; validates percentages sum to 100
- [x] Settings UI accessible from app header (modal or simple page)
- [x] Trip summary shows actual vs target comparison (e.g., side-by-side percentages)
- [x] Tests for settings CRUD, validation (must sum to 100), and auto-creation

## Pattern exemplar

- Follow the pattern in: `backend/routers/ingredients.py` — simple CRUD router structure
- Follow the pattern in: `backend/models.py` — SQLAlchemy model definition

## Tasks

- [x] Add `AppSettings` model and migration
- [x] Create settings router with GET and PUT endpoints
- [x] Add validation that percentages sum to 100
- [x] Register settings router in main.py
- [x] Update trip summary endpoint to include macro targets from settings
- [x] Update trip summary UI to show actual vs target comparison
- [x] Add settings UI (modal from header or simple page)
- [x] Write tests for settings CRUD and validation
