# Project Architecture Assessment

Date: 2026-07-11
Status: Working assessment for future planning
Scope: Backend, frontend, persistence, testing, security, deployment, and the live BeeBaby product surface

[BLUF: Hiking Food is a strong, operationally credible personal application whose trip-planning core has outgrown the older architecture around it. The next work should protect production data ownership, deepen the catalog boundary, and give the frontend a coherent server-state model. A rewrite would discard substantial strengths without addressing the actual risks.]

## Context and confidence

This assessment follows the API-driven cohesion work completed through plan 45. It is based on the current source tree, architecture and deployment documentation, recent implementation history, the full local test and build gates, dependency consistency checks, and a read-only inspection of the deployed BeeBaby application at desktop and iPhone-sized viewports.

The repository contains roughly 9,200 lines of first-party backend and frontend source, 173 passing backend tests, and 39 passing frontend tests. Backend tests, frontend tests, lint, production build, the frontend dependency audit, and Python package consistency all passed during the review. The deployed application loaded without browser console or page errors, and sampled API requests returned successfully. These results establish a healthy baseline. They do not substitute for load testing, a Python vulnerability audit, destructive workflow testing, or a backup-and-restore drill.

## Tenets

1. **Production data belongs to the user.** Application code may evolve the shape of stored data through explicit migrations. Deploying code must not silently recreate, overwrite, or reinterpret user-owned records.

2. **A domain rule needs one owner.** REST, MCP, scripts, and future clients should translate into the same application behavior. Validation or transaction policy repeated across adapters will eventually diverge.

3. **Tests belong at durable boundaries.** Tests should describe observable behavior through an application, protocol, or rendered-workflow boundary. Internal decomposition should remain free to change without rewriting the test suite.

4. **Deployment must be deterministic from committed state.** An unchanged commit should not fail because a package index changed, and a successful health check should mean the deployed application can safely serve its owned data.

5. **Complexity should match the product's scale.** This is a single-user application with modest data volume. It benefits from strong invariants, simple deployment, and deep modules. It does not need distributed infrastructure or framework-heavy abstraction introduced for hypothetical scale.

## Current strengths

### The trip-planning application boundary is substantive

`backend/services/trip_planning.py` is the clearest architectural success. `TripPlanningService` owns trip validation, inventory mutation, daily-plan invalidation, assignment constraints, cloning, deletion, and transaction completion. REST and MCP both use this behavior, which sharply reduces the chance that the page and chatbot produce different plans.

The supporting behavior tests are unusually good for an application of this size. They cover partial-day semantics, realistic allocation, over-allocation, deletion cascades, invalid references, REST/MCP parity, migrations, OAuth token rotation, route authority, stale frontend responses, accessible control names, and mutation failures. The test suite reflects product behavior rather than merely exercising functions.

### Persistence and deployment have credible safety mechanisms

The SQLite path is absolute and configurable. Foreign keys are enabled on every connection. Schema changes are ordered and versioned, pre-migration backups are retained, future schema versions are rejected, and database verification checks columns, schema version, foreign-key enforcement, violations, and trip cascades. The cicd-router pipeline gates the exact commit, excludes database files from rsync, runs bootstrap verification, restarts the service, and performs an HTTP smoke check.

This is a sound foundation. The remaining persistence risks arise from data lifecycle policy and missing constraints, not from careless deployment mechanics.

### The exposed security boundary has been treated seriously

The MCP authorization path implements OAuth authorization code with PKCE, exact registered redirects, one-time codes, short-lived JWT access tokens, hashed rotating refresh tokens, issuer and audience validation, password throttling, and DNS-rebinding protection. Browser CORS follows the same-origin deployment model. For a single-owner service published through a controlled ingress, this is a thoughtful security posture.

### The frontend protects important user workflows

Trip URLs are canonical and route-authoritative. Trip switching preserves the current subroute, unknown trips have stable boundaries, and late responses from an old route cannot overwrite the current trip. Mutation failures are visible, pending controls are disabled, route pages are code-split, and the high-frequency trip controls have useful accessible names.

The live surface is fast and usable. Its limitations are maintainability and interaction density rather than fundamental product failure.

## Primary risks and recommendations

### 1. Normal deployment mutates user-owned data

`deploy/remote-bootstrap.sh` runs `backend/seed.py` on every deployment. The seed script recreates missing stock ingredients, recipes, snack items, and the Utah 2026 trip. A record intentionally deleted through the product can therefore return after the next commit. The script also retains an obsolete schema migration and a verification routine that prints failures without failing the process.

This violates the production-data tenet and creates ambiguous ownership. The codebase cannot distinguish a fixture that should be restored from a user record that should remain deleted.

Seeding should become an explicit one-time bootstrap or import operation. Production deploys should run migrations and invariant verification only. Content checks should accept arbitrary user datasets while rejecting structural corruption. This work should include recurring SQLite backups, at least one off-host copy, and a rehearsed restore path. Pre-migration backups are valuable, but they do not protect edits made between migrations.

### 2. The backend contains two architectural eras

Trip planning uses an application service. Ingredients, recipes, snack catalog, settings, and food intake still place validation, persistence, commits, response construction, and domain errors inside HTTP routers. All seven routers define the same database dependency, so tests must override each one independently.

The catalog is the best next deep module. Ingredients, recipes, and snack items jointly own nutrition derivation, serving calculations, category semantics, reference safety, and trip availability. Their current router separation hides this coupling without controlling it. A catalog application boundary should own commands, validation, projections, and transactions; HTTP and agent transports should translate at the edges.

The shared session dependency should move to an application-level dependency module. This is a small refactor with outsized testability value because it removes repeated construction and makes application factories straightforward.

### 3. Data integrity relies too heavily on cooperative callers

Most Pydantic schemas use unconstrained strings and numbers. Most SQLAlchemy columns lack checks, uniqueness rules, or indexes. Blank names, negative nutrition values, negative recipe amounts, invalid category strings, arbitrary ratings, and invalid packing methods can enter through older API paths. Application validation protects the newer trip workflows, but direct database writes and older routers remain able to violate domain assumptions.

Integrity should be layered. Request models provide useful errors, application services enforce cross-record rules, and SQLite preserves invariants when data enters through scripts or future tools. The next migration should consider:

- non-empty normalized names where identity matters;
- non-negative weights, quantities, servings, calories, and macro values;
- bounded ratings and day fractions;
- enumerated categories, slots, statuses, packing methods, and drink-mix types;
- uniqueness for trip names and conceptually singular selections;
- indexes on the foreign keys and status/name columns used by common queries.

Constraints should follow demonstrated product invariants. SQLite remains entirely adequate for the expected scale.

### 4. Trip projections repeat loading and calculation work

`backend/services/trip_queries.py` and `backend/services/daily_plan_queries.py` return large dictionaries assembled through repeated queries. Trip detail, summary, packing, shopping, and daily-plan projections repeatedly load recipes, recipe ingredients, catalog items, and ingredients. The current data volume masks the resulting N+1 query behavior.

The deeper problem is conceptual duplication. Nutrition totals and selected-food identity are recalculated in several projections, so consistency depends on every projection remembering the same rules.

A single normalized trip snapshot should be loaded in a bounded number of queries and become the input to the read projections. Pure calculation can remain separate where it expresses a coherent concept. Transport-shaped dictionaries should be produced at the application boundary rather than passed among internal modules. This improves performance, type clarity, and consistency without changing the public API.

### 5. Frontend server state is distributed across components

`frontend/src/context/TripContext.jsx` owns trips, active-trip identity, detail, and summary. Individual pages and components independently load catalogs and daily plans, create mutation hooks, refresh projections, and handle errors. `SnackSelection.jsx` has grown past 600 lines because it owns data loading, five mutation flows, grouping, filtering, desktop rendering, and mobile rendering.

Several catalog loads discard failures with empty catch handlers. Many mutation callbacks call `refreshTrip()` without awaiting it, which allows pending state to clear before the visible refresh completes. `useMutation` represents overlapping requests with one boolean, so an earlier request can finish and clear pending state while a later request remains active. Repeated writes can also complete out of order.

The frontend needs an owned server-state boundary for the trip workspace and a smaller catalog boundary. It should define cancellation and latest-response behavior, cache invalidation, per-entity mutation state, and common error handling. Whether this is implemented with a small local store or a focused query library matters less than preserving those semantics explicitly. Rendering components should receive stable data and actions rather than orchestrate HTTP behavior.

### 6. Cross-stack compatibility is still manually inferred

Frontend tests use a hand-maintained fetch mock. Backend tests exercise the real FastAPI application. Both suites can pass while disagreeing about a response shape or workflow because no automated test crosses that boundary.

One narrow cross-stack workflow would carry more value than broad browser coverage: start a temporary database and real backend, serve the built frontend, create catalog data, create a trip, add food, generate a daily plan, and inspect the packing result. Keep component tests for interaction details and backend tests for domain edge cases. Use the cross-stack test to protect the owned contract between them.

### 7. Dependency verification is sensitive to upstream releases

The committed Python lock files are pinned and hash-protected, but their input files leave most direct dependencies unpinned. Every gate recompiles those inputs against the current package index and compares the result to the committed lock. An upstream release can therefore break deployment of an unchanged commit.

Dependency resolution should be an explicit maintenance action. The deployment gate should install and validate the committed hash lock. A separate update workflow can re-resolve inputs, run tests, review changelogs, and commit the new lock. This preserves supply-chain integrity while making the build reproducible from repository state.

### 8. Remaining OAuth risks are bounded but persistent

Password throttling is in-process and resets on restart. Dynamic client registrations, expired authorization codes, and unused refresh tokens can accumulate. Client-address behavior depends on the reverse-proxy topology. These are moderate risks for the current single-user service, but custom protocol code becomes a permanent maintenance surface.

Cleanup should remain proportional: prune expired rows, bound or administer client registrations, document trusted proxy behavior, and keep the ASGI protocol tests as the primary compatibility boundary.

## Recommended sequence

1. **Protect production data ownership.** Remove automatic seeding from deployment, separate bootstrap fixtures, and establish recurring backup and restore.
2. **Deepen the food catalog boundary.** Move catalog commands, validation, transactions, and projections out of routers; centralize session injection.
3. **Add durable integrity constraints.** Introduce constrained request values, SQLite checks, uniqueness, and indexes through a versioned migration.
4. **Create a frontend server-state boundary.** Resolve refresh ordering, concurrency, cancellation, and silent-load failures before the main planner grows further.
5. **Add one real cross-stack workflow test.** Protect the contract between the React application and FastAPI.
6. **Normalize trip loading and projections.** Remove repeated queries and shared-calculation drift after the behavior boundary is protected.
7. **Stabilize dependency and readiness gates.** Stop resolving fresh dependencies during ordinary deploys and make health checks assert meaningful readiness.
8. **Archive historical execution artifacts.** `docs/plans/INDEX.md` is a useful authority, but completed plans, handoffs, and prompts now outweigh current design material. Preserve history under an archive boundary so current architecture remains easy to find.

## Deepening candidates

### Candidate 1: Food catalog lifecycle

**Cluster:** ingredient, recipe, snack catalog, catalog projections, schemas, and their routers.

**Coupling:** nutrition derivation, serving calculations, category semantics, deletion safety, and trip references jointly define one catalog.

**Dependency category:** Local-substitutable through temporary SQLite.

**Test impact:** Consolidate ingredient macro, snack macro, recipe calculation, CRUD, and REST/MCP parity behavior at the catalog boundary. Retain small pure-calculation tests only where the calculator remains an independently meaningful module.

### Candidate 2: Trip planning read and write model

**Cluster:** `TripPlanningService`, trip queries, daily-plan queries, autofill, and nutrition calculators.

**Coupling:** These modules co-own trip identity, selected inventory, assignment validity, nutrition totals, allocation warnings, and every trip projection.

**Dependency category:** Local-substitutable with in-process calculation internals.

**Test impact:** Center behavior tests on one trip-planning boundary and retain thin REST/MCP compatibility checks. Projection-specific tests that assert internal assembly can be removed once their outcomes are covered through the boundary.

### Candidate 3: Frontend trip workspace

**Cluster:** trip context, API wrapper, calculator, meal and snack selection, summary, daily plan, and packing.

**Coupling:** Every mutation coordinates trip detail, summary, daily-plan validity, pending state, errors, and route identity.

**Dependency category:** Remote but owned. FastAPI is the production adapter; tests use an in-memory transport or a temporary real backend.

**Test impact:** Replace repeated component-level fetch orchestration tests with workflow tests around the server-state boundary, retain focused rendered interaction tests, and add one cross-stack golden path.

### Candidate 4: Production data lifecycle

**Cluster:** migrations, seeding, verification, deployment bootstrap, backups, and restore.

**Coupling:** Together they determine what data exists after a deployment and whether the service is safe to restart.

**Dependency category:** Local-substitutable with temporary SQLite files.

**Test impact:** Add deploy-lifecycle tests for empty, current, legacy, user-modified, backed-up, and restored databases. Retire fixture-count output as deployment verification.

### Candidate 5: OAuth authorization lifecycle

**Cluster:** OAuth router, token store, bearer middleware, runtime configuration, and proxy assumptions.

**Coupling:** Registration, authorization, rotation, cleanup, throttling, and resource access form one protocol state machine.

**Dependency category:** Local-substitutable with SQLite, an injected clock, and client-address inputs.

**Test impact:** Keep observable ASGI protocol exchanges as the main boundary. Direct storage tests become unnecessary when the complete lifecycle is covered at that boundary.

## Open edges

The first decision should be whether production data lifecycle work remains an operational correction or becomes the first formal implementation plan. The risk is concrete enough to address immediately, while the catalog and frontend candidates require interface design before implementation.

The application does not currently need a database replacement, distributed deployment, a general event system, or a broad visual redesign. Those choices should be revisited only when an observed constraint invalidates the current tenets.
