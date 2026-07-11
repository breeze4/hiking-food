# API-Driven Cohesion and Hardening

## Problem

Hiking Food has two first-class API consumers: the React application over REST and
chatbot clients over MCP. Both operate on the same trip-planning data, but today
they enter the system through different business-logic paths. FastAPI routers own
validation, persistence, projections, and transaction commits; MCP tools import
router handlers and private response helpers while also implementing their own
validation and invalidation rules.

This creates observable inconsistencies:

- REST accepts invalid trip shapes and daily assignments that MCP rejects.
- MCP clears stale daily assignments after inventory changes while REST does not.
- Deleting a trip can leave orphan daily assignments.
- A first-day fraction of `1.0` is treated as a partial day by auto-fill.
- Database selection depends on the process working directory.
- Tests override request sessions but application startup still uses global
  production database and OAuth state.
- A deep-linked trip route can disagree with the trip selected in React context.

The existing product workflows and response shapes should remain stable. Changes
to behavior are limited to enforcing valid inputs, keeping derived daily plans
consistent, fixing demonstrated incorrect semantics, and hardening exposed
security boundaries.

## Solution

Introduce a transaction-scoped trip-planning application module as the sole owner
of trip workflow behavior. REST and MCP become thin adapters that translate their
inputs into application operations and translate domain errors into transport
errors.

The module owns:

- Trip shape and target validation.
- Meal and snack inventory mutations.
- Daily-plan invalidation and regeneration policy.
- Assignment validation and allocation limits.
- Trip cloning and deletion, including dependent data.
- Overview, daily-plan, packing, and shopping projections.
- Transaction commit and rollback boundaries.

Persistence construction moves behind an application factory with injected
configuration and session factories. Database paths are absolute or explicitly
configured, SQLite foreign keys are enabled, and schema changes are versioned.

The frontend treats the route trip ID as the source of truth for trip-specific
screens and uses a cohesive API-backed server-state boundary with observable
loading, saving, and error states.

OAuth client registration and redirects are persisted and validated; refresh
tokens are stored as hashes and rotated; authorization attempts are rate-limited;
browser CORS is restricted to the actual same-origin development and production
contract.

## Dependency Strategy

- **Trip planning:** local-substitutable. Boundary tests use a real in-memory
  SQLite database with foreign keys enabled.
- **Persistence and migrations:** local-substitutable. Tests create temporary
  databases and upgrade them through every supported schema version.
- **Frontend API:** remote but owned. The production adapter uses FastAPI REST;
  frontend tests use an in-memory HTTP adapter or request interception at the API
  boundary.
- **OAuth:** local-substitutable while hosted in-process. Clock, client address,
  secrets, and token storage are explicit dependencies where deterministic tests
  require them.

## Testing Strategy

Testing proceeds in vertical red-green-refactor slices. Tests assert observable
behavior through public REST, MCP, application, or rendered frontend boundaries;
they do not assert private helper calls.

### Compatibility behaviors to preserve

- Existing ingredient, recipe, snack, trip, packing, shopping, macro, and intake
  REST response shapes.
- Deterministic auto-fill and the existing meal/snack/drink distribution rules.
- Trip clone workflows and the compact MCP tool surface.
- OAuth authorization-code plus PKCE access for registered public clients.
- Existing mobile planner, daily-plan, and packing workflows.

### Correctness behaviors to add

- Invalid names, ranges, enum values, references, and negative quantities are
  rejected consistently by REST and MCP.
- Full first/last days receive full-day eligibility and presentation.
- Allocation-affecting trip or inventory changes invalidate daily assignments in
  both transports; display-only and packing-only changes do not.
- Manual assignments must reference inventory on the same trip, use a real day
  and slot, have positive servings, and cannot over-allocate inventory.
- Removing inventory or a trip cannot leave dependent assignments.
- Direct trip URLs and selected trip state remain synchronized.

### Security behaviors to add

- Authorization accepts only persisted clients and exact registered redirects.
- Authorization codes remain one-time and PKCE-bound.
- Refresh tokens rotate, old refresh tokens stop working, and only token hashes
  are persisted.
- Repeated failed password attempts are throttled.
- Browser API responses do not grant arbitrary cross-origin access.

### Operational behaviors to add

- Tests never create or migrate the real application or OAuth database.
- The same configured database is selected regardless of process working
  directory.
- Every supported schema version upgrades to the current schema and preserves
  user data.
- Production schema verification is a post-deploy check, not a skippable unit
  test dependency on live BeeBaby SSH.

## Interface Signature

Illustrative boundary; concrete value types may evolve while implementing the
tests, but transports must depend only on this public surface.

```python
class TripPlanningService:
    def list_trips(self) -> list[TripListView]: ...
    def read_trip(self, trip_id: int, sections: set[TripSection]) -> TripPlanView: ...

    def create_trip(self, spec: TripSpec) -> TripPlanView: ...
    def clone_trip(self, source_trip_id: int, spec: CloneTripSpec) -> TripPlanView: ...
    def update_trip(self, trip_id: int, patch: TripPatch) -> TripPlanView: ...
    def delete_trip(self, trip_id: int) -> None: ...

    def set_meal(self, trip_id: int, selection: MealSelectionChange) -> TripPlanView: ...
    def set_snack(self, trip_id: int, selection: SnackSelectionChange) -> TripPlanView: ...

    def regenerate_daily_plan(self, trip_id: int) -> DailyPlanView: ...
    def change_assignment(
        self, trip_id: int, change: AssignmentChange
    ) -> DailyPlanView: ...
```

REST adapters may retain selection-ID endpoints for compatibility; they translate
those IDs into the same `set_meal` and `set_snack` application operations used by
MCP.

## Usage Example

```python
@router.put("/{trip_id}", response_model=TripDetailRead)
def update_trip(
    trip_id: int,
    data: TripUpdate,
    service: TripPlanningService = Depends(get_trip_planning_service),
):
    return service.update_trip(trip_id, TripPatch.from_api(data))
```

```python
@mcp.tool(annotations=WRITE_UPDATE)
def update_trip(trip_id: int, **changes) -> dict:
    with trip_planning_service() as service:
        trip = service.update_trip(trip_id, TripPatch(**changes))
        return {"trip": trip, "daily_plan_needs_autofill": trip.plan_invalidated}
```

## Complexity Hidden

- SQLAlchemy query construction, eager loading, and response projection.
- Transaction commit/rollback and dependent-row cleanup.
- Validation shared across transport shapes.
- Daily-plan staleness and regeneration rules.
- Recipe, snack, calorie, weight, and macro calculations.
- Translation between catalog identity, trip-selection identity, and assignment
  identity.
- Database engine construction, migration state, and SQLite configuration.

## Migration Notes

1. Add public boundary tests for the demonstrated invalid-input, orphan,
   full-day, invalidation, and deep-link behaviors.
2. Introduce shared domain errors and constrained value models.
3. Move one complete trip workflow behind `TripPlanningService`; migrate REST and
   MCP together, then repeat for the remaining workflows.
4. Replace router-local session dependencies with an injected service/session
   dependency.
5. Introduce absolute configuration and versioned migrations; migrate production
   only after backup and exact-SHA gates pass.
6. Harden OAuth without changing the authorization-code plus PKCE client flow.
7. Add frontend component and browser-level coverage before restructuring trip
   state and mutation handling.
8. Remove superseded private router helpers and shallow tests only after their
   behavior is covered at the new boundary.
