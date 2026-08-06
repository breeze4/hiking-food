# MCP Tools + Plan-Food Agent for Snack Units

## Parent spec

[Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md)

## What to build

Agent-driven planning works on structured trips (spec: Data Flow — MCP; user story 15). MCP tools for the unit-type library (list/create) and trip unit selections (list with quota readout, set quantity, remove), mirroring the existing snack-serving tools. `get_trip_plan` includes the `snack_units` block for structured trips. The plan-food agent instructions gain the structured flow: check `snack_model`, fill the unit quota from packaged items and library bags, respect the tolerance band. Legacy-trip tool behavior unchanged.

## Goal

The plan-food agent (and any MCP client) can plan a structured trip end-to-end — read the quota, browse the library, create a bag type, and fill units to quota — without touching the web UI.

## Type

AFK

## Blocked by

- Blocked by `2026-08-06-03-trip-unit-selections.md`

## User stories addressed

- User story 15

## Acceptance criteria

- [ ] `venv/bin/pytest` passes with new MCP tool tests (prior art `test_mcp_tools.py`): list unit types returns derived values; create a bag type; set/remove trip units; quota readout matches `unit_quota`; unit tools against a legacy trip return the structured-only error; existing tool tests unchanged.
- [ ] `get_trip_plan` on a structured trip includes `snack_units` (quota, filled, selections); on a legacy trip its output is unchanged.
- [ ] `.claude/agents/plan-food.md` documents the structured flow (mode check, quota fill, bag creation, tolerance) and keeps the legacy flow for legacy trips.

## Owns

- `backend/mcp_server.py` — new unit tools; `get_trip_plan` (add `snack_units` block)
- `backend/tests/test_mcp_tools.py` — added cases
- `.claude/agents/plan-food.md` — structured flow instructions

## Must not touch

- `backend/services/snack_units.py`, `backend/services/trip_queries.py`, `backend/routers/trips.py` — owned by plan `2026-08-06-03` (consume, don't modify)
- `backend/services/catalog_queries.py`, `backend/routers/snack_units.py` — owned by plan `2026-08-06-02`
- `backend/services/autofill.py`, `backend/services/daily_plan_queries.py` — owned by plan `2026-08-06-04`
- `backend/models.py`, `backend/migrations.py`, `backend/schemas.py` — schema frozen
- `frontend/` — no frontend changes in this slice

## Defines interfaces

None — consumes the service layer defined by plans 02 and 03.

## Pattern exemplar

- **MUST follow the pattern in**: `backend/mcp_server.py` — `set_trip_snack_servings` for the unit mutation tools and `get_trip_plan` for the readout extension
- Follow the pattern in: `backend/tests/test_mcp_tools.py` — tool invocation + assertion style; `.claude/agents/plan-food.md` — existing instruction structure

## Tasks

- [ ] Tools: `list_snack_unit_types`, `create_snack_unit_type`, `set_trip_snack_unit` (add/update quantity by catalog item or unit type), `remove_trip_snack_unit` — all delegating to the plan-02/03 service layer.
- [ ] Extend `get_trip_plan` with the `snack_units` block on structured trips.
- [ ] MCP tests per criteria, including the legacy-unchanged assertion.
- [ ] Update the plan-food agent instructions with the structured flow.
