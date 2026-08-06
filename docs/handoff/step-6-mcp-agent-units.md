# Step 6 — MCP Tools + Plan-Food Agent for Snack Units — Handoff

Final step of the structured snack units feature. It reflects what shipped, not what the plan
proposed.

Parent spec: [Structured Snack Units](../specs/2026-08-06-01-structured-snack-units.md).
Plan: [MCP Tools + Plan-Food Agent for Snack Units](../plans/2026-08-06-06-mcp-agent-units.md).
Builds on: [Step 2 handoff](step-2-snack-unit-library.md), [Step 3 handoff](step-3-trip-unit-selections.md).

## 1. The rule that matters

MCP owns no domain rules. Every refusal an MCP unit tool can produce — the structured-only
guard, the exactly-one-reference rule, the positive-quantity rule — is raised by
`TripPlanningService`, never re-stated in `mcp_server.py`. `set_trip_snack_unit` routes every
call it cannot satisfy through `add_snack_unit`, whose checks run in that order, so the messages
live in one place. The one exception is the library create path (§3), which has no service.

## 2. New tools

Four tools, added to `backend/mcp_server.py` between `set_trip_snack_servings` and
`auto_fill_daily_plan`. The tool surface is now 14 names; `test_tool_surface_is_small_and_stable`
lists them.

### `list_snack_unit_types()` — READ_ONLY

Returns `{"unit_types": [...]}` — `catalog_queries.snack_unit_type_list_view(db)` verbatim, so
every bag carries its composition rows and the derived `weight_oz`, `calories`, `cal_per_oz`,
`protein_g` / `fat_g` / `carb_g`, `weight_warning`, `has_full_data`. No filter arguments: the
library is small and the surface stays stable.

### `create_snack_unit_type(name, composition=None, notes=None)` — WRITE_NEW

`composition` is `list[SnackUnitIngredientCreate]` (`{"ingredient_id": int, "amount_oz": float}`),
reusing the REST schema so the generated JSON schema names the fields. The function normalizes
with `model_validate`, so it accepts plain dicts too — which is how the tests call `.fn()`
directly, bypassing FastMCP's validation.

Returns `{"unit_type": <snack_unit_type_view>}`.

An unknown ingredient raises `ValueError("Ingredient {id} not found")` — same text as the
router's 400 — and the `_session()` rollback discards the half-built type.

### `set_trip_snack_unit(trip_id, catalog_item_id=None, unit_type_id=None, quantity=1)` — WRITE_UPDATE

The unit analogue of `set_trip_snack_servings`: name exactly one reference, and quantity zero
removes the selection. It reads `TripPlanningService.read_trip` once (the detail view carries
both `snack_model` and the `snack_units` selection list), matches the existing selection by
reference, then dispatches to `add_snack_unit` / `update_snack_unit` / `remove_snack_unit`.

Returns:

```python
{
  "trip_id": int,
  "action": "added" | "updated" | "removed",
  "unit": dict | None,      # the affected selection (trip_snack_unit_view); the
                            # pre-removal view on a remove, None when nothing was selected
  "snack_units": {"quota": int, "per_day": list[int], "filled": int},
  "daily_plan_needs_autofill": True,
}
```

The `snack_units` block is `read_summary(trip_id)["snack_units"]`, so the progress an agent sees
after a write is byte-identical to what `get_trip_plan` reports next.

**The non-obvious bit.** The dispatch condition is

```python
if (not structured) or (not names_one_unit) or (existing is None and quantity > 0):
    planner.add_snack_unit(...)
```

`add_snack_unit` checks the snack model first, the reference second, the quantity third. Sending
every unsatisfiable call there means a legacy trip answers *"Trip does not use the structured
snack model"* even on the remove path, where a naive implementation would find no selection and
silently report success. If that method's checks are ever reordered,
`test_unit_tools_reject_a_legacy_trip` fails — it asserts the message on all three paths.

### `remove_trip_snack_unit(trip_id, unit_id)` — WRITE_UPDATE

Straight delegation to `remove_snack_unit` (structured guard included). Returns
`{trip_id, unit_id, action: "removed", snack_units, daily_plan_needs_autofill}`. `unit_id` is the
selection id from `trip.snack_units[].id`, not a catalog or unit-type id.

## 3. What was replicated rather than reused

`create_snack_unit_type` writes `SnackUnitType` + `SnackUnitIngredient` rows itself, because step
2 put that logic in `routers/snack_units.py::_set_composition` and there is no service function to
call. `mcp_server.py` therefore imports `models` and `schemas` for the first time. Two copies of
"insert a bag" now exist. If a third consumer appears, lift the router's `_set_composition` into
`catalog_queries` and have both call it — that is the only duplication this step introduced.

## 4. Where `snack_units` surfaces in `get_trip_plan`

No re-plumbing was needed, and none was added: the raw views already carry everything, and
duplicating it under a third key would drift.

| Data | Path | Sections |
|---|---|---|
| quota, `per_day`, filled | `result["summary"]["snack_units"]` | `overview`, `all` |
| the selections filling it | `result["trip"]["snack_units"]` | every section (`trip` is always present) |
| packing rows per unit | `result["packing"]["units"]` | `packing`, `all` |

On a legacy trip `summary["snack_units"]` and `packing["units"]` are **absent keys**, not None,
and `trip["snack_units"]` is `[]` (step 3 added that key for every trip).

The `get_trip_plan` docstring now says this, so an MCP client reads it from the tool description.
The server-level `instructions` also gained a sentence pointing structured trips at
`list_snack_unit_types` + `set_trip_snack_unit`.

## 5. `.claude/agents/plan-food.md`

The agent drives REST with `curl`, not MCP, so the new instructions are REST-shaped.

- Endpoint table: `GET`/`POST /snack-unit-types`, and `POST`/`PUT`/`DELETE /trips/:id/snack-units`.
- Workflow step 1 now reads `snack_model` before planning snacks; step 3's snacks line branches.
- "Slot calorie targets" is annotated: on a structured trip only the lunch 40% applies.
- New `## Structured Snack Units` section (before `## Snack Category Assignments`): read the quota
  from `summary.snack_units`; packaged versus bag units; the ±25% band against the trip's
  `oz_per_snack` with `weight_warning` as the server's verdict; building a bag from composition
  ounces; filling the quota exactly; re-running `POST /trips/:id/daily-plan/auto-fill` because
  unit changes clear the day assignments; and that a 409 means the trip is legacy, not that the
  call should be retried.

Legacy trips keep the existing flow verbatim — the 60% band section is untouched.

## 6. Tests

`backend/tests/test_mcp_tools.py`, 12 existing tests unchanged in body (only
`test_tool_surface_is_small_and_stable`'s expected set grew), 10 added, 22 total:

- `test_a_created_bag_lists_with_its_derived_values`
- `test_a_bag_cannot_name_an_unknown_ingredient` (also asserts the library stays empty)
- `test_units_fill_the_quota_of_a_structured_trip`
- `test_the_quota_readout_matches_the_quota_service` (against `snack_units.unit_quota`)
- `test_setting_a_unit_to_zero_removes_it`
- `test_a_unit_selection_can_be_removed_by_its_id`
- `test_a_unit_names_exactly_one_reference` (neither / neither-with-zero / both)
- `test_a_unit_change_clears_stale_assignments`
- `test_unit_tools_reject_a_legacy_trip`
- `test_a_legacy_trip_plan_carries_no_unit_quota`

Fixture notes: the module's autouse `db_setup` trip is **legacy** (the `Trip.snack_model` column
default), which is what the guard tests use; structured trips come from the `create_trip` tool,
which picks up `NEW_TRIP_SNACK_DEFAULTS`. `_structured_trip()` builds a 0.5 + 2 + 0.5 day trip, a
quota of 12 (`per_day == [2, 4, 4, 2]`).

`test_mcp_overview_matches_rest_trip_and_summary` still passes untouched.

## 7. Deviations from the plan

1. **`get_trip_plan` gained no new key.** The plan's task says "extend `get_trip_plan` with the
   `snack_units` block"; the block already flowed through `read_summary`, and the selections
   through `read_trip`. Tests pin both (§4) and the docstring documents them. Adding a merged
   third copy would have been duplicated state.
2. **`mcp_server.py` imports `models` and `schemas`.** Unavoidable for the library create path —
   see §3.
3. **The server `instructions` string was edited**, beyond the plan's "new unit tools" wording.
   It is the only text a client reads before choosing a tool, and it named servings only.
4. **`create_trip` / `update_trip` still do not expose `snacks_per_day`, `oz_per_snack`, or
   `snack_model`.** An MCP client can fill a quota but cannot change it; the quota comes from the
   trip shape and the 4/day, 2 oz defaults. Out of this plan's scope — a follow-up if agent-side
   trip configuration is wanted.
5. **`docs/architecture.md` touched** (not in Owns, not in Must-not-touch — same status as steps
   2 and 3). Its MCP paragraph claimed tools operate through the service layer with no other
   writes; that is now true with one named exception, and the service list gained `snack_units`.
6. **`docs/plans/INDEX.md` left alone**, matching steps 2 and 3: the verifier confirms, the
   orchestrator moves the plan.
