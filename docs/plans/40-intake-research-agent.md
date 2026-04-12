# Intake Research Agent

## Parent spec

`docs/specs/15-food-intake-queue.md`

## What to build

A Claude Code agent definition at `.claude/agents/research-intake.md` that reads pending rows from the food intake queue, researches each food (USDA FoodData Central primary, LLM estimation fallback), decides per item whether it should be created as an ingredient only, a snack only (which still needs an ingredient), or both, presents a review table in chat, and on user approval writes the new records via the existing ingredient and snack_catalog POST endpoints and PATCHes the intake row to `added`. Includes name-based duplicate detection against the existing ingredient table.

## Type

AFK

## Blocked by

- Blocked by `39-food-intake-capture.md` — consumes `GET /api/food-intake?status=pending` and `PATCH /api/food-intake/:id`.

## User stories addressed

From `docs/specs/15-food-intake-queue.md`:
- Run an agent that turns raw intake rows into fully populated ingredients and snack catalog entries without manual data entry
- See the agent's proposal before anything is written, and approve / correct / skip per item
- Avoid accidentally creating duplicate ingredients when a captured item already exists in the catalog

## Acceptance criteria

- [x] Agent definition exists at `.claude/agents/research-intake.md` with frontmatter (name, description, tools)
- [x] Agent reads pending intake rows via `GET /api/food-intake?status=pending`
- [x] For each item, agent decides: ingredient-only, snack-only (creates ingredient too), or both
- [x] Decision rationale uses the item name and the `notes` field (notes may override the default categorization)
- [x] Agent checks for existing ingredients with matching name before creating — flags duplicates in the proposal
- [x] Agent queries USDA FoodData Central for macros/calories; falls back to LLM estimation with a flagged source
- [x] For snack items, agent proposes: category (drink_mix/lunch/salty/sweet/bars_energy), weight_per_serving, calories_per_serving, and drink_mix_type when applicable
- [x] For ingredient rows, agent proposes: calories_per_oz, macros (protein/fat/carb per oz), and packing_method
- [x] Agent presents a single review table per run with one row per intake item showing proposed records, sources, and duplicate flags
- [x] Agent waits for explicit user approval before writing anything
- [x] On approval, agent writes ingredients via `POST /api/ingredients`, snacks via `POST /api/snacks`, and PATCHes intake rows to status `added`
- [x] Agent handles the "duplicate of existing ingredient" case by skipping the ingredient create and still marking the intake row `added`
- [x] Agent is re-runnable: only looks at `pending` rows, never touches `researched` or `added` rows unless asked

## Owns

- `.claude/agents/research-intake.md` — new agent definition
- `docs/plans/INDEX.md` — add this plan to the index

## Must not touch

- `backend/` — no code changes; the agent uses the API only
- `frontend/` — no code changes
- `.claude/agents/research-macros.md` — pattern reference only, do not edit
- `backend/models.py`, `backend/schemas.py`, `backend/routers/*` — all interfaces this agent consumes are built by plan 38 and existing code; do not modify

## Defines interfaces

None — this plan only consumes existing interfaces (`/api/food-intake` from plan 38, `/api/ingredients` and `/api/snacks` from existing code).

## Pattern exemplar

- **MUST follow the pattern in**: `.claude/agents/research-macros.md` — sibling agent for the closest analogous workflow (scan → research via USDA → present review table → write on approval). Match its structure: frontmatter format, section headings, API reference block, USDA API reference block, ambiguity rules, source tracking, rate limit handling. The new agent is "what research-macros is to missing macros, but for net-new items."

## Tasks

- [x] Read `.claude/agents/research-macros.md` end-to-end to internalize structure and voice
- [x] Read `backend/routers/ingredients.py` and `backend/routers/snacks.py` to list the exact POST payload shapes the agent will send (payload shapes sourced from handoff/prior step context)
- [x] Draft `.claude/agents/research-intake.md`:
  - [x] Frontmatter (name, description, tools — match research-macros)
  - [x] Purpose + when-to-run section
  - [x] App API reference: food_intake GET/PATCH, ingredients POST, snacks POST
  - [x] USDA FoodData Central reference (reuse the block from research-macros; do not paraphrase — it's already correct)
  - [x] Categorization rules: ingredient-only vs snack vs both, how notes override
  - [x] Snack field inference rules: category selection from name, reasonable weight_per_serving defaults by category, calories_per_serving derivation, drink_mix_type rules (breakfast/dinner/all_day)
  - [x] Packing method inference rules for ingredients
  - [x] Duplicate detection: fuzzy name match against `GET /api/ingredients`, report matches in the proposal, do not auto-merge
  - [x] Review table format (one row per intake item, showing decision + proposed values + source + duplicate flag)
  - [x] Write-phase sequence: for each approved item, POST ingredient (capture id), POST snack if applicable, PATCH intake to `added`
  - [x] Error handling: if ingredient POST fails, skip snack and leave intake as `pending` or flip to `researched` so the user can retry
  - [x] Re-runnability note: only scans `pending`
- [ ] Test: add a few varied intake rows via the Intake page (one obvious snack, one recipe-only ingredient, one duplicate of an existing ingredient), run agent end-to-end, verify correct records created and intake rows advanced to `added` — DEFERRED TO USER (manual test plan in handoff)
- [x] Update `docs/plans/INDEX.md`

## Review

Agent file written at `.claude/agents/research-intake.md` following the research-macros structure. The USDA FoodData Central block (API key, search, food detail, nutrient ID list, per-oz conversion, match preferences, rate-limit language) is copied verbatim from research-macros so the two agents stay in sync when corrections land. Intake-specific content: five-state workflow (Scan / Research / Present / Review / Write), categorization rules (ingredient vs snack vs both with notes override), snack field defaults by category, drink_mix_type inference, packing method inference, duplicate detection via cached `GET /ingredients`, explicit write sequence with ingredient POST → capture id → snack POST → intake PATCH, and a failure rule that keeps the intake row off `added` when writes fail. Manual end-to-end test is deferred to the user (three-item test plan in the handoff file).

## Implementation notes

- **Reuse, don't rewrite, the USDA reference block.** The macro agent already nails unit conversion (per-100g → per-oz via × 0.283495), match preferences, and rate-limit handling. Copy those sections verbatim into the new agent so both agents stay consistent and any future correction can be applied once per agent file.
- **Duplicate detection is name-based and lives in the agent.** Do not add a uniqueness check to the ingredients API. The agent fetches `GET /api/ingredients`, compares intake names against existing names (case-insensitive, trimmed, ignoring common noise like "bar" / "bars"), and surfaces matches in the review table with a `Duplicate of #id` flag. The user decides whether to still create or skip.
- **Snack field defaults.** For common packaged snacks, the agent should propose reasonable defaults (e.g. bars ~1.4 oz, drink mix packets 0.5–0.7 oz) and flag them as "estimated, please verify" in the review table. The user can correct before approving.
- **No new schema columns.** Everything the agent needs to persist already has a home: macros on ingredients, category + weight/cal per serving on snack_catalog, status on food_intake. If you find yourself wanting to add a column, stop — the spec explicitly says no proposed-value columns on the intake table.
