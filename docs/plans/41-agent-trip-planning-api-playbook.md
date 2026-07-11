# Agent Trip Planning API Playbook

## Goal

Make creating a new food plan from a recent, seasonally similar trip a quick agent workflow: select the best prior trip, clone it through the API, update the new trip's identity and duration, regenerate the daily allocation, validate the result, and hand the new plan back to the user for small edits in the app.

The primary use case is: "Create a new 2026 summer trip from my most relevant 2026 summer plan, then let me adjust it."

## Type

Documentation and agent workflow

## Blocked by

None. The current API already supports the required clone, update, auto-fill, summary, daily-plan, packing, and shopping-list operations.

## Deliverables

- [ ] Add `docs/agents/food-planning-api.md` as the canonical agent-facing API playbook.
- [ ] Document the live base URL and local development base URL without embedding credentials or machine-specific secrets.
- [ ] Document the request and response fields for the trip-planning endpoints actually used by agents:
  - `GET /api/trips`
  - `GET /api/trips/{trip_id}`
  - `POST /api/trips/{trip_id}/clone`
  - `PUT /api/trips/{trip_id}`
  - trip meal and snack create/update/delete endpoints
  - `GET /api/trips/{trip_id}/summary`
  - `POST /api/trips/{trip_id}/daily-plan/auto-fill`
  - daily-plan read and assignment endpoints
  - packing and shopping-list reads
- [ ] Include copy-pasteable `curl` examples using shell variables for base URL, source trip ID, and new trip ID.
- [ ] Add a short troubleshooting section for duplicate names, partial-day configuration, unallocated food, calorie/weight drift, and failed API writes.
- [ ] Link the playbook from the root `AGENTS.md` or another checked-in agent entrypoint so future agents discover it before using browser automation.

## Golden path

1. Read all trips with `GET /api/trips`.
2. Identify the requested destination trip if it already exists. Never clone over or delete an existing trip implicitly.
3. Select a source trip using this order:
   1. User explicitly named a source trip.
   2. Same year and same season.
   3. Nearest duration and partial-day shape.
   4. Most recently relevant trip when the API exposes no dates; if the choice remains ambiguous, present the candidates instead of guessing.
4. Read the complete source trip and its summary before writing anything.
5. Clone it with `POST /api/trips/{source_trip_id}/clone`.
6. Immediately rename and configure the clone with `PUT /api/trips/{new_trip_id}`. Set name, first-day fraction, full days, last-day fraction, drink mixes per day, ounces per day, and calories per ounce explicitly.
7. Scale meal and snack quantities to the destination duration while preserving the source trip's compact variety and preference signals.
8. Run `POST /api/trips/{new_trip_id}/daily-plan/auto-fill` after all selection changes.
9. Validate with the detail, summary, and daily-plan endpoints:
   - destination name and trip shape are correct;
   - expected breakfast and dinner counts are present;
   - all food is allocated;
   - each day is reasonably close to its target;
   - total calories and weight are within the documented tolerance;
   - drink-mix servings match the trip configuration.
10. Read packing and shopping-list endpoints as the final completeness check.
11. Report the source trip, changes made, calorie/weight variance, any unallocated items, and the app URL for user review.

## Safety and idempotency rules

- Treat API reads as reconnaissance; do not write until both source and destination identities are confirmed.
- If the destination trip already exists, refine it in place only when the user asked for that. Do not create a second trip with the same intended name.
- Capture the clone response's `id`; do not identify the new trip later by name alone.
- Do not copy packed flags or actual packed weights from a prior trip.
- Re-run auto-fill after meal or snack quantity changes, then verify that the unallocated count is zero.
- On a partial failure, stop further writes, report the new trip ID and completed mutations, and leave the recoverable clone in place unless the user explicitly asks to delete it.
- Prefer one clone plus targeted updates over rebuilding every meal and snack selection from scratch.

## Planning defaults to preserve from existing guidance

- Start from the source trip rather than an empty plan when a relevant same-season/year trip exists.
- Keep breakfast variety low and dinner variety compact; no single dinner should exceed half the dinner count.
- Prefer fewer snack varieties with repeat servings when scaling up, but preserve the source trip's known favorites and notes.
- Balance daily calories after selection totals are correct; do not mistake a complete inventory for a complete daily plan.
- Surface weight or macro tradeoffs rather than silently removing user-selected food to hit a meter exactly.

## Acceptance criteria

- [ ] A new agent can create a destination trip from a named source trip using only the playbook and API responses.
- [ ] The documented happy path takes one source lookup, one clone, one trip update, targeted quantity updates, one auto-fill, and read-only validation.
- [ ] The playbook contains valid examples for both live BeeBaby and local development.
- [ ] Examples match the current FastAPI schemas and are exercised against backend tests or a disposable trip.
- [ ] The workflow handles an already-created destination trip without duplicating or overwriting it.
- [ ] The final validation explicitly checks unallocated food, per-day targets, total calories, total weight, packing detail, and shopping-list generation.
- [ ] Relevant backend tests pass and the live OpenAPI schema is spot-checked before the plan is marked complete.

## Verification

- Run `cd backend && venv/bin/pytest`.
- Compare every documented payload against `backend/schemas.py` and every endpoint against `backend/routers/trips.py` and `backend/routers/daily_plan.py`.
- Exercise the playbook against a disposable clone, verify the summary and daily plan, then delete only that disposable trip.
- Verify the canonical playbook link is visible from the agent entrypoint.
