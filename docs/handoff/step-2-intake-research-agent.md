# Step 2 — Intake Research Agent (plan 40)

## Deliverable

`.claude/agents/research-intake.md`

### Frontmatter (verbatim)

```yaml
---
name: research-intake
description: Turn pending food_intake rows into ingredients and snack catalog entries via USDA lookup, with user review before write.
tools: Bash, Read, Write, WebFetch
---
```

## Structural diff vs `research-macros.md`

| Section | research-macros | research-intake | Treatment |
|---|---|---|---|
| Frontmatter | name/description/tools | same shape | Intake-specific rewrite (new name/description, same tools) |
| Title + intro | "Macro Research Agent" | "Intake Research Agent" | Rewrite — explicitly positions this agent as the sibling to research-macros |
| App API block | GET/PUT ingredients | GET/PATCH food-intake + GET/POST ingredients + POST snacks | Rewrite — intake-specific endpoint table, plus inline JSON payload examples for the two POST routes and the PATCH |
| USDA FoodData Central block | API key, search, food detail, nutrient IDs, per-oz conversion, match preferences, rate-limit paragraph | Same | **Verbatim copy**, including the conversion math (`* 0.283495`), rounding rule (1 decimal), match preferences list, and rate-limit graceful-handling language. This is the shared block the plan explicitly called out as copy-don't-paraphrase |
| Workflow / 1. Scan | Filter ingredients with null macros | GET /food-intake?status=pending + cached GET /ingredients for dup detection | Rewrite |
| Workflow / 2. Research | USDA search + estimate fallback | Same + categorization + duplicate check + snack field defaults + packing method inference | Rewrite, additive — the USDA good-match / ambiguous / no-match trichotomy is preserved, bullet-for-bullet |
| Workflow / 3. Present | Review table | Review table with intake-specific columns (# / Item / Decision / Category / Wt/srv / Cal/srv / P-F-C per oz / Packing / Source / Flags) + summary counts | Rewrite |
| Workflow / 4. Review | Approve / flag / re-research | Same + "override a duplicate flag" | Rewrite, additive |
| Workflow / 5. Write | PUT /ingredients/:id | POST /ingredients → capture id → POST /snacks if applicable → PATCH /food-intake/:id | Rewrite with worked curl example |
| Rules | Never overwrite / never guess / show calorie impact / conservative estimates / rate-limit | Never auto-approve / never write without approval / never touch researched-or-added / no backend duplicate validation / source required / every snack entails an ingredient / let backend derive calories / rate-limit / conservative estimates / fail loud on partial failure | Rewrite — the macro agent's "only fill null fields" rule doesn't map (net-new items), replaced with the spec's "scope is strictly pending" and "every snack creates an ingredient" rules |

## POST/PATCH payload examples (copy-paste-ready)

### Create ingredient

```bash
curl -s -X POST http://beebaby:8000/hiking-food/api/ingredients \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chomps beef sticks",
    "protein_per_oz": 3.4,
    "fat_per_oz": 1.7,
    "carb_per_oz": 0.0,
    "packing_method": "original",
    "notes": "USDA 174832"
  }'
```

Response is 201 with an `IngredientRead` including `id`. Capture it for the snack POST. Backend auto-derives `calories_per_oz = round(p*4 + f*9 + c*4, 2)` when all three macros are sent.

### Create snack (requires the ingredient_id returned above)

```bash
curl -s -X POST http://beebaby:8000/hiking-food/api/snacks \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": $ING_ID,
    \"weight_per_serving\": 1.0,
    \"calories_per_serving\": 100,
    \"category\": \"salty\",
    \"drink_mix_type\": null,
    \"splittable\": false,
    \"notes\": \"estimated serving weight\"
  }"
```

`category` must be one of `drink_mix` / `lunch` / `salty` / `sweet` / `bars_energy`. `drink_mix_type` is only set when `category == "drink_mix"`.

### Mark intake row added

```bash
curl -s -X PATCH http://beebaby:8000/hiking-food/api/food-intake/7 \
  -H "Content-Type: application/json" \
  -d '{"status": "added"}'
```

Valid statuses: `pending` / `researched` / `added`.

## Manual test plan (three-item smoke test)

Add three varied rows via the Intake page, then run the agent:

1. **Obvious packaged snack** — e.g. "Chomps beef sticks" with notes "REI". Expected: decision = snack, category = salty (or lunch — the item blurs the line and the agent may flag for confirmation), packing_method = original, both an ingredient and a snack row created, intake → added.
2. **Recipe-only ingredient** — e.g. "Organic rolled oats" with notes "for breakfast recipes". Expected: decision = ingredient-only (no snack POST), packing_method = bag, intake → added.
3. **Duplicate** — pick an item whose name already exists in `/api/ingredients`, e.g. "Olive oil". Expected: review table flags `Duplicate of #{id}: {name}`, user accepts the flag, agent skips both POSTs and PATCHes the intake row to `added`.

Verify after the run:
- `GET /api/ingredients` shows the two new rows (items 1 and 2)
- `GET /api/snacks` shows the one new snack row (item 1) with the correct `ingredient_id`
- `GET /api/food-intake?status=pending` returns an empty list
- `GET /api/food-intake` shows all three rows with `status = "added"`

Partial-failure test (optional): point the agent at an intake item whose name triggers a backend validation failure (e.g. pass an invalid `packing_method` by hand-editing the proposal) — verify the intake row stays `pending` / `researched` and the snack POST is skipped.

## Gate results

- `cd backend && venv/bin/pytest` → `1 failed, 101 passed, 34 warnings in 2.90s`. The single failure is the expected `tests/test_schema_match.py::test_fresh_schema_matches_prod` (known drift from plan 39 — will self-resolve on next deploy).
- `cd frontend && npm run build` → green, `built in 1.00s`. Only the pre-existing chunk-size warning.

Agent-definition-only changes did not affect either gate, as expected; they were run to catch accidental edits outside `.claude/agents/`.

## Files touched

- `.claude/agents/research-intake.md` (new)
- `docs/plans/40-intake-research-agent.md` (acceptance criteria checked, tasks marked, review section added)
- `docs/plans/INDEX.md` (plan 40 moved Not Started → Completed)
- `docs/handoff/step-2-intake-research-agent.md` (this file)

No files touched under `backend/`, `frontend/`, or `.claude/agents/research-macros.md`.
