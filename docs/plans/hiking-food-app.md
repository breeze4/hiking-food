# Hiking Food Planner - Implementation Plan

## Context
Replacing a Google Sheets backpacking food planner with a self-hosted web app. User plans multi-day hiking trips, needs to manage ingredients, recipes (from Skurka's book + custom), snack selections, calorie/weight budgets, and a packing-day workflow. Hosted on "beebaby" (Linux mini PC) accessible via Tailscale.

## Architecture
```
hiking-food/
  backend/
    main.py              # FastAPI app entry point
    database.py          # SQLite setup, connection
    models.py            # SQLAlchemy models
    schemas.py           # Pydantic request/response schemas
    routers/
      ingredients.py     # CRUD for ingredients
      snacks.py          # CRUD for snack catalog
      recipes.py         # CRUD for recipes + ingredients
      trips.py           # CRUD for trips + snacks + meals
    seed.py              # Seed DB with Skurka recipes + Utah 2026 data
    requirements.txt
  frontend/
    (Vite + React scaffolding)
    src/
      api.js             # Fetch wrapper for backend calls
      App.jsx            # Router + layout
      components/
        TripPlanner/     # Trip calculator, snack table, meal selection, summary
        PackingScreen/   # Recipe assembly, snack checklist, actual weights, shopping list
        RecipeLibrary/   # Browse/create/edit recipes
        Ingredients/     # Ingredient database management
        TripManager/     # Create/switch/delete/clone trips
      hooks/             # Shared data-fetching hooks
  docs/
    SPEC.md
    plans/
```

## Implementation Checklist

### Phase 1: Project scaffolding
- [ ] 1. Init git repo, create .gitignore (Python venv, node_modules, *.db, dist/)
- [ ] 2. Set up backend: `requirements.txt` (fastapi, uvicorn, sqlalchemy, pydantic), `main.py` with CORS + static file serving
- [ ] 3. Set up frontend: `npm create vite@latest` with React template, verify dev server runs
- [ ] 4. Set up SQLite database with SQLAlchemy models matching the spec's data model
- [ ] 5. Verify: backend starts, frontend starts, they can talk to each other (proxy or CORS)

### Phase 2: Ingredient database
- [ ] 6. Backend: ingredients CRUD endpoints (GET list, POST, PUT, DELETE)
- [ ] 7. Frontend: Ingredients page — table with add/edit/delete inline
- [ ] 8. Verify: can add, edit, delete ingredients through the UI

### Phase 3: Snack catalog
- [ ] 9. Backend: snack catalog CRUD endpoints (references ingredients)
- [ ] 10. Frontend: Snack catalog management — table showing ingredient name, weight/serving, cal/serving, cal/oz
- [ ] 11. Verify: can create snack items linked to ingredients, computed cal/oz is correct

### Phase 4: Recipe library
- [ ] 12. Backend: recipe CRUD endpoints including nested recipe_ingredients
- [ ] 13. Frontend: Recipe list page — browse recipes by category (breakfast/dinner)
- [ ] 14. Frontend: Recipe editor — name, category, ingredient list with amounts, at-home prep text, computed totals
- [ ] 15. Verify: can create/edit a recipe, totals (weight, calories, cal/oz) compute correctly

### Phase 5: Seed data
- [ ] 16. Extract all 12 Skurka recipes from PDF into seed data (ingredients + amounts)
- [ ] 17. Extract Utah 2026 snack items + servings into seed data
- [ ] 18. Write seed.py that populates the database with all ingredients, snack catalog items, recipes, and the Utah 2026 trip
- [ ] 19. Verify: seed data loads, Utah 2026 totals match spreadsheet (~103 oz snacks, ~11,745 cal)

### Phase 6: Trip planner (core)
- [ ] 20. Backend: trip CRUD endpoints (create, read, update, delete, clone)
- [ ] 21. Frontend: Trip selector in header (dropdown + new/clone/delete)
- [ ] 22. Frontend: Trip calculator config (first day fraction, full days, last day fraction) with computed recommendations (low/high ranges)
- [ ] 23. Frontend: Snack selection table — add from catalog, set servings (0.5 step), packed checkbox, computed columns
- [ ] 24. Frontend: Meal selection — pick breakfast/dinner recipes with quantities
- [ ] 25. Frontend: Summary dashboard — snack totals, meal totals, combined totals, per-day, actual vs target ranges
- [ ] 26. Verify: Utah 2026 trip shows correct totals, calculator recommendations match the spreadsheet

### Phase 7: Packing screen
- [ ] 27. Frontend: Recipe assembly view — for each trip meal, show ingredient list with target amounts, prep instructions, checkbox, actual weight input
- [ ] 28. Frontend: Snack packing view — snack list with target amounts, checkbox, actual weight input
- [ ] 29. Frontend: Combined shopping list — aggregate all ingredients across recipes + snacks
- [ ] 30. Backend: endpoints to update packed status and actual weights on trip_meals and trip_snacks
- [ ] 31. Verify: packing a recipe updates its status, actual weights flow into summary

### Phase 8: Polish
- [ ] 32. Mobile-responsive layout across all screens
- [ ] 33. Sorting on table columns (snack table, ingredient table, recipe list)
- [ ] 34. Trip-level notes on snack items
- [ ] 35. Navigation between screens (React Router)
- [ ] 36. Error handling and loading states

## Verification
- Run backend: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`
- Run frontend: `cd frontend && npm run dev`
- Seed database: `cd backend && python seed.py`
- Check Utah 2026 snack totals: ~103 oz, ~11,745 cal, ~114 cal/oz
- Check trip calculator: 7-day trip should recommend 123.5-156 oz total, subtract meals for daytime target
- Test on mobile viewport
- Test full packing workflow: shopping list → recipe assembly → snack packing → actual weights
