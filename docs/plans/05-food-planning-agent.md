# Food Planning Agent v1

## Parent PRD

`docs/prd-meal-slots-and-planning-agent.md` — User stories 15-26

## What to build

A custom agent definition for use in the hiking-food project that plans trip food by reading and writing to the beebaby API. The agent reads the trip config, recipe library, snack catalog, and user preferences (catalog notes + conversation memory), then refines the current trip plan by making API calls to add/remove/adjust meals and snacks. The user reviews in the app and provides feedback; the agent iterates until the user is satisfied.

V1 works with the existing API — no app changes required. The agent carries snack category and meal slot knowledge in its system prompt rather than reading it from the API.

## Type

AFK

## Blocked by

None - can start immediately (v1 uses existing API)

## User stories addressed

- As a user, I can ask the agent to plan food for a specific trip
- As a user, the agent starts from my current selections and refines them
- As a user, I can give feedback and the agent adjusts the plan
- As a user, the agent remembers my preferences across sessions

## Acceptance criteria

- [ ] Agent definition file exists at `.claude/agents/plan-food.md` (or similar)
- [ ] Agent can read trip config, recipes, snack catalog via beebaby API
- [ ] Agent selects breakfasts (1-2 recipes, repeated) and dinners (2-3, no one > half the trip)
- [ ] Agent balances dinner variety by type (noodle, rice/bean, rice/meat, etc.)
- [ ] Agent fills snack slots using 25/40/35 split of remaining calories
- [ ] Agent prefers fewer unique items with more servings (enough multiples to prevent hoarding instinct)
- [ ] Agent front-loads good food — doesn't save treats for later days
- [ ] Agent prefers recipes sharing ingredients (tiebreaker)
- [ ] Agent flags anomalies in existing plan before making changes (missing meals, over/under slots, mismatches)
- [ ] Agent reads catalog notes as preference signals
- [ ] Agent reads conversation memory for accumulated preferences
- [ ] Agent writes plan via API (add/remove/update meals and snacks)
- [ ] Agent explains what it picked and why
- [ ] Agent saves new preference learnings to memory after session

## Tasks

- [ ] Create agent definition file with system prompt covering:
  - API base URL and available endpoints
  - Meal selection rules (breakfast minimal variety, dinner 2-3 unique, max half rule)
  - Snack slot logic (category-to-slot mapping, 25/40/35 calorie split)
  - Snack philosophy (fewer items, more servings — scarcity causes hoarding so give multiples; eat the good stuff early)
  - Anomaly detection (flag problems in existing plan before changing it)
  - Preference reading (catalog notes, memory)
  - Shopping list minimization (ingredient overlap as tiebreaker)
- [ ] Include hardcoded category assignments for all current catalog items in prompt
- [ ] Include the full category-to-slot mapping in prompt
- [ ] Define the agent's workflow: read state → propose changes → write via API → summarize
- [ ] Test: agent can plan a fresh trip end-to-end
- [ ] Test: agent can refine an existing trip with feedback
- [ ] Test: agent saves preference learnings to memory
