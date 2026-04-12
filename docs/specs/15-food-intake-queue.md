# Food Intake Queue

## Problem

Adding a new food item to the app today means opening the Ingredient Database, filling in name/calories/packing method, then (if it's a snack) opening the Snack Catalog and filling in weight per serving, calories per serving, category, etc. Macros are another pass after that. This is friction at the moment of inspiration — at a store, after a trip, browsing a product page — when all you really want to do is jot down "Chomps beef sticks" and move on.

A lightweight capture queue lets the user record raw food names on the fly, then defer the actual research and catalog population to a Claude Code agent that works in bulk (similar to the existing macro research agent, but for net-new items rather than missing macros on existing ones).

## Solution

A new **Intake** screen in the app with a simple CRUD interface over a new `food_intake` table. The table stores a queue of foods the user wants added to the catalog, each with a status tracking its progress through the pipeline.

A new Claude Code agent reads `pending` rows, researches each item (USDA lookup, LLM fallback, same pattern as the macro research agent), creates the appropriate ingredient and/or snack_catalog rows via the existing API, and updates the intake row's status. The user reviews the proposed values in the agent's chat output before approval; the intake table itself does not store proposed values.

## Data Flow

1. User opens the Intake screen, types a food name (and optional notes like "REI, $4" or "tried on Utah '26, liked"), hits add. Row is created with status `pending`.
2. User continues capturing items whenever. The list on the screen shows all rows grouped by status.
3. At some later point, user runs the intake agent from Claude Code.
4. Agent calls `GET /api/food-intake?status=pending`, gets the list of unprocessed items.
5. For each item, agent:
   - Decides whether this is an ingredient only (e.g. flour), a snack only (which still creates an ingredient row because snacks reference ingredients), or both (e.g. peanut butter). Decision is inferred from the item name and any notes.
   - Looks up macros/calories via USDA FoodData Central, falls back to LLM estimation.
   - For snacks, picks a category (drink_mix / lunch / salty / sweet / bars_energy) and a reasonable weight-per-serving + calories-per-serving.
   - Picks a packing method for the ingredient row.
6. Agent presents a proposal table in chat: one row per intake item showing what it will create, with sources and confidence. User reviews.
7. On approval, agent:
   - Calls `POST /api/ingredients` to create the ingredient row (with macros, packing method).
   - Calls `POST /api/snack-catalog` to create the snack row if applicable.
   - Calls `PATCH /api/food-intake/:id` to set status to `added`.
8. Rejected / obsolete intake rows are deleted by the user from the Intake screen (no `rejected` status — delete is rejection).

The `researched` status is used when the agent has investigated an item but the user has not yet approved the creation — e.g. the agent ran, proposed values, user closed chat without approving. Next time the agent runs it can re-pick up `researched` rows without redoing the lookup if it cached its proposal, or just re-research them. For v1, `researched` is optional; the agent may go straight from `pending` to `added` in a single session. The status is in the schema so the workflow has room to grow.

## Behavior

- **Intake screen CRUD**: list view grouped by status (pending, researched, added), inline add form (name + notes), edit and delete per row.
- **Name is the only required field.** Notes is free text and optional.
- **Status transitions**: `pending` → `researched` (optional) → `added`. The UI can show status but does not let the user manually set it — the agent owns status changes beyond the initial `pending` insert. Delete is always available.
- **Duplicates**: the agent checks whether an ingredient with a matching name already exists before creating a new one. If it does, the agent flags it in the proposal and (on approval) just marks the intake row `added` without creating a duplicate. This avoids a common mistake where the user adds "Honey Stinger Waffles" to intake not realizing it's already in the catalog.
- **Scope decision per item**: agent decides ingredient-only vs snack vs both based on the item itself. Notes may override — e.g. a note of "for recipes only" tells the agent to skip the snack_catalog row even for an obvious snack food.
- **Added rows stay in the table** for history. User can delete them manually once they're no longer useful. (We're not building a separate archive; the list is small enough that it doesn't matter.)
- **Mobile-friendly**: the intake screen is the primary capture path, so the add form must work well on a phone.

## Data Model

New table:

### food_intake
| Column | Type |
|--------|------|
| id | INTEGER PRIMARY KEY |
| name | TEXT NOT NULL |
| notes | TEXT |
| status | TEXT NOT NULL DEFAULT 'pending' (`pending` \| `researched` \| `added`) |
| created_at | TEXT (ISO timestamp) |

No foreign keys to created ingredients/snacks — traceability is not worth the schema weight for a single-user app.

## API

- `GET /api/food-intake` — list all, optional `?status=` filter
- `POST /api/food-intake` — body: `{ name, notes? }`, returns created row
- `PATCH /api/food-intake/:id` — body: any of `{ name?, notes?, status? }`
- `DELETE /api/food-intake/:id`

## Agent

New agent definition at `.claude/agents/research-intake.md`, modeled on the existing `research-macros.md`:
- Reads `pending` rows via `GET /api/food-intake?status=pending`
- For each, performs USDA lookup or LLM estimation
- Presents a proposal table in chat (name, decision: ingredient/snack/both, proposed values, source)
- On approval, writes ingredients, snack_catalog entries, and PATCHes intake rows to `added`
- Checks for existing ingredient with matching name before creating — flags duplicates in proposal

## Judgment Calls

- **No proposed-value columns on the intake table.** The agent proposes in chat, not in the schema. Keeps the table to 5 columns and avoids a half-built review workflow the user only exercises occasionally.
- **No intake → created-record links.** Traceability is nice but a join table for a single-user app is overkill. If you want to know "where did this ingredient come from" the answer is the `notes` field on the ingredient, which the agent can optionally populate with "from intake: <notes>".
- **`researched` state is reserved but not strictly required for v1.** The happy path goes `pending` → `added` in one agent session. The middle state exists for the case where the agent does work but the user doesn't approve in the same sitting — the schema can represent that even if v1 doesn't rely on it.
- **Delete = reject.** No separate rejected status, no soft-delete. If you don't want it, remove it.
- **Duplicate detection is name-based and lives in the agent, not the API.** The API will happily create duplicates; it's the agent's job to warn before it does. Rationale: the API should stay dumb and the agent is the one place where natural-language understanding lives, so it's the right place to handle "is 'Clif bar' the same as 'Cliff Bar'".
