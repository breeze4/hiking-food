# Macro Research Agent

## Parent spec

`docs/specs/11-macro-research-agent.md`

## What to build

A standalone Claude Code agent definition that researches and populates macronutrient data (protein, fat, carb per oz) for ingredients. Uses USDA FoodData Central API as primary source with LLM estimation fallback. Batch-with-review workflow: agent researches all null-macro ingredients, presents a review table, user approves, then agent writes via API.

## Type

AFK

## Blocked by

None — uses existing ingredient API (plans 27-32 already built the macro infrastructure)

## Acceptance criteria

- [ ] Agent definition exists at `.claude/agents/research-macros.md`
- [ ] Agent can scan ingredients and identify those missing macro data
- [ ] Agent queries USDA FoodData Central API for each ingredient
- [ ] Agent falls back to LLM estimation when USDA has no good match
- [ ] Agent presents a review table with values, sources, and calorie impact
- [ ] Agent waits for user approval before writing any data
- [ ] Agent writes approved values via PUT /api/ingredients/:id
- [ ] Agent handles USDA rate limits gracefully
- [ ] Agent is re-runnable (only fills null fields, never overwrites)
- [ ] Lightweight spec exists at `docs/specs/11-macro-research-agent.md`

## Tasks

- [x] Write lightweight spec `docs/specs/11-macro-research-agent.md`
- [x] Create agent definition `.claude/agents/research-macros.md` with:
  - [x] Frontmatter (name, description, tools)
  - [x] App API reference (ingredient endpoints)
  - [x] USDA FoodData Central API reference (search, detail, nutrient IDs, unit conversion)
  - [x] Batch-with-review workflow (scan → research → present → review → write)
  - [x] Ambiguity resolution rules and match preferences
  - [x] Source tracking (USDA with fdcId vs estimated with reasoning)
  - [x] Rate limit handling
- [x] Update `docs/plans/INDEX.md`
- [x] Update `docs/specs/02-app-spec.md` with agent reference
- [ ] Test: run agent against beebaby, verify scan and USDA queries work
- [ ] Test: full cycle on a small batch, verify macros written and rollups compute
