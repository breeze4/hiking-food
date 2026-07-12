# Architecture

## Project Structure

The project is two independent sibling directories (`backend/`, `frontend/`) with no shared root build tooling, monorepo manager, or container config.

Seed data lives in `data/` as JSON files (`skurka-recipes.json`, `utah-2026-snacks.json`) and is loaded by `backend/seed.py` on every deploy.

Specs, plans, and session logs live in `docs/`; `docs/plans/INDEX.md` is the authoritative status tracker for all implementation plans.

## Backend

**Framework**: FastAPI with a nested ASGI mount — an outer `app` mounts the real application at `/hiking-food`, so all routes are served under that prefix.

**Database**: SQLite via SQLAlchemy ORM. The URL comes from `HIKING_FOOD_DATABASE_URL`; when unset it defaults to an absolute path anchored to `database.py` itself (`Path(__file__).resolve().parent / "hiking_food.db"`), so the selected database no longer depends on the process working directory. The file is gitignored, excluded from rsync, and never overwritten by deploy. `create_database_engine()` registers a SQLite `connect` event listener that issues `PRAGMA foreign_keys=ON` on every connection so ON DELETE CASCADE and reference constraints are enforced. Tables are created by `Base.metadata.create_all()` at startup.

**Migrations**: Ordered, versioned, idempotent migrations live in `backend/migrations.py` and run from the application lifespan (not inline in `main.py`). `run_migrations()` reads the SQLite `PRAGMA user_version`, refuses to run against a schema newer than it understands, takes a pre-migration backup of the live database (into `HIKING_FOOD_BACKUP_DIR` or `<db_dir>/backups/`, retaining the 10 most recent) before applying anything, then runs each pending migration in order and stamps `user_version`. Migrations cover both `ADD COLUMN` evolutions and table rebuilds that introduce trip foreign-key cascades. No Alembic, but schema evolution is versioned and backed up rather than manual.

**Routing**: Each domain has its own router module in `routers/` under the `/api/` prefix (`ingredients`, `snacks`, `recipes`, `trips`, `daily_plan`, `settings`, `food_intake`) — seven routers. `daily_plan` shares the `/api/trips` prefix with `trips`.

**Session management**: Each router defines its own identical `get_db()` generator (no shared utility). Tests override all seven independently via `app.dependency_overrides` (`trips`, `snacks`, `recipes`, `ingredients`, `daily_plan`, `settings`, `food_intake`).

**Schemas**: Pydantic v2 models with a `Create`/`Update`/`Read` pattern per resource. Some computed fields (e.g. macro per-serving on snacks) are derived at response time in the service projection layer, not stored in the DB.

**Services**: A service layer owns workflow and read projections; routers and MCP tools are thin adapters over it. `services/trip_planning.py` (`TripPlanningService`) is the transaction-scoped owner of trip validation, inventory mutation, daily-plan invalidation/regeneration, cloning, and deletion. `services/trip_queries.py` and `services/daily_plan_queries.py` produce the trip overview, summary, packing, shopping, and daily-plan read projections; `services/catalog_queries.py` produces the shared recipe and snack catalog projections (`recipe_list_view`, `snack_view`, `snack_list_view`) that both `/api/recipes` + `/api/snacks` and the MCP `list_food_options` tool return, so `mcp_server.py` imports nothing from `routers.*`. Supporting calculators remain small and pure: `recipe_calc.py` computes recipe totals, `autofill.py` distributes meals/snacks across trip days, `calculator.py` implements Skurka method calorie/weight targets.

**Configuration**: Runtime configuration is supplied through environment variables (no config files); sensible defaults keep local development zero-config. `HIKING_FOOD_DATABASE_URL` selects the database; `HIKING_FOOD_OAUTH_ISSUER` sets the public issuer/prefix; `HIKING_FOOD_JWT_KEY` (min 32 bytes) signs access tokens; `HIKING_FOOD_AUTH_PASSWORD` is the authorization password; `HIKING_FOOD_AUTH_DB_PATH` locates the OAuth token store; `HIKING_FOOD_MCP_ALLOWED_HOSTS` / `HIKING_FOOD_MCP_ALLOWED_ORIGINS` (comma-separated) override the MCP transport host/origin allow-lists; `HIKING_FOOD_BACKUP_DIR` overrides the pre-migration backup location. Domain constants (calorie constants, target ranges, default macro splits) remain in code.

**Dependencies**: Pinned and hash-locked. `requirements.txt` (runtime) and `requirements-dev.txt` (adds the test toolchain) list every transitive dependency with `==` versions and `--hash` entries, so installs are reproducible and integrity-checked rather than resolving unpinned latest.

**CORS/Auth**: The browser SPA is served same-origin under the same `/hiking-food` mount as the API, so the previous wide-open `CORSMiddleware` has been removed entirely — API responses grant no cross-origin access. The separate `/mcp` transport is protected by OAuth 2.0 authorization code + PKCE, persisted dynamically registered public clients with exact redirect matching, short-lived JWT access tokens, and hashed refresh tokens that rotate on use. Repeated failed authorization-password attempts are throttled per client address (5 failures → HTTP 429 for a 5-minute window, reset on success). Discovery is trimmed to supported authorization-server metadata: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource`, and an OpenID compatibility alias that returns the same authorization-server metadata without OIDC-only claims or JWKS. The outer app also serves metadata-only Codex aliases at `/.well-known/oauth-authorization-server/hiking-food` and `/.well-known/openid-configuration/hiking-food` so path-mounted issuer discovery cannot fall through to another service on the shared BeeBaby host.

**MCP**: `mcp_server.py` exposes a compact domain-level FastMCP tool surface over exact-path Streamable HTTP. Tools operate through the service layer (`TripPlanningService` and `catalog_queries`) against the same transaction boundary as the REST API — no imports from REST router modules. DNS-rebinding protection is enabled with an env-driven allowed host/origin policy: defaults cover `localhost:8000`, `127.0.0.1:8000`, `beebaby:8000`, and the host/origin of `HIKING_FOOD_OAUTH_ISSUER`, and are replaced wholesale when `HIKING_FOOD_MCP_ALLOWED_HOSTS` / `HIKING_FOOD_MCP_ALLOWED_ORIGINS` are set. OAuth discovery, registration, authorization, and token endpoints live in `mcp_oauth/`; the outer `/hiking-food` ASGI mount becomes the public issuer prefix.

**Static serving**: In production, FastAPI serves the built frontend from `frontend/dist/` with a catch-all route that falls back to `index.html` for SPA routing.

## Frontend

**Stack**: React 19 + Vite 8, plain JavaScript (`.jsx`/`.js` only, no TypeScript anywhere).

**Routing**: React Router v7 with `basename="/hiking-food"`. The canonical trip routes are `/trips/:tripId`, `/trips/:tripId/daily-plan`, and `/trips/:tripId/packing`; `/` and `/packing` remain compatibility redirects. Recipe, snack, ingredient, and intake routes remain global. Unknown trips and unknown trip subroutes render stable not-found boundaries. Route page components are code-split via `React.lazy`, and the whole `<Routes>` element is wrapped in a single `<Suspense>` fallback, so each page ships as its own async chunk (the entry chunk dropped from ~529 kB to ~306 kB); `TripSelector`, `SettingsModal`, and nav components stay eagerly imported.

**State management**: A single `TripContext` holds global state (`trips`, `activeTripId`, `tripDetail`, `summary`). On trip-scoped pages, the route trip ID is authoritative; selecting another trip preserves the current planner/daily-plan/packing subroute. Global pages retain the selection without navigating away. Late detail or summary responses are ignored after the active route changes. Mutations call the API then update local state; `refreshTrip()` re-fetches detail and summary. A shared `useMutation(mutationFn)` hook standardizes mutation state — it returns `{ run, pending, error }`, captures failures without rethrowing, and is adopted at every mutation call site (meal/snack selection, calculator save, packing, trip create/clone/delete, daily-plan edits) so each control exposes pending and error state; interactive controls carry accessible names (`aria-label`s that include the item name) for targetable, screen-reader-friendly interaction.

**API layer**: A single `src/api.js` file wraps `fetch` with five named exports (`get`, `post`, `put`, `patch`, `del`). Base URL is hardcoded to `/hiking-food/api`. No interceptors, auth, retries, or cancellation.

**UI components**: shadcn/ui (base-nova style) built on `@base-ui/react` primitives, with `lucide-react` icons. UI components live in `src/components/ui/` and use `data-slot` attributes for CSS targeting.

**Styling**: Tailwind CSS v4 configured entirely in CSS (`src/index.css`) using `@theme inline` with `oklch` colors. Class-based dark mode. Geist variable font. No CSS modules or styled-components.

**Dev proxy**: Vite proxies `/hiking-food/api` to `http://localhost:8000`, stripping the `/hiking-food` prefix, so the frontend and backend share the same URL structure in dev and prod.

**Patterns**: Trip calculator uses debounced save (500ms `setTimeout`). Daily plan page renders a hand-built SVG stacked bar chart with no charting library. Some form controls use native `<select>` rather than shadcn equivalents.

## Testing

**Framework**: pytest with `fastapi.testclient.TestClient` against an in-memory SQLite database using `StaticPool`.

**Frontend**: Vitest, Testing Library, jest-dom, and jsdom exercise the rendered application through `BrowserRouter` with mocked HTTP responses at the owned API boundary (`src/test/apiMock.js`). The suite is 8 files / 39 tests and covers routing (direct links, redirects, trip switching, deletion, global pages, not-found states, stale-response races), the `useMutation` hook, per-control pending/error state, and accessible control names across meal/snack selection, the calculator, packing, trip create/clone/delete, and the daily plan.

**Approach**: Mix of unit tests (calculator, recipe calc) and HTTP integration tests (daily plan, shopping list, slots, drink mixes, macros, settings). Backend catalog projections and MCP tools are covered at their public boundaries, including a REST-vs-MCP parity check that asserts `list_food_options` returns byte-identical recipe/snack payloads to `/api/recipes` and `/api/snacks`. Each integration test fixture creates and drops all tables around each test. Tests run against the inner app directly (not the `/hiking-food` mounted wrapper). Backend tests never create or migrate the real application or OAuth database.

## Deployment

**Method**: `cicd-router` watches verified commits to `main`, runs the exact-SHA project gates from `scripts/cicd-router-gates.sh`, rsyncs the approved source to `beebaby`, runs `deploy/remote-bootstrap.sh`, restarts the user systemd service, and performs the configured health check.

**Service**: Runs as a user-level systemd unit (`hiking-food.service`) on port 8000. `loginctl enable-linger` keeps it alive after logout. BeeBaby's Tailscale Funnel publishes the OAuth-protected `/hiking-food` MCP path through a recognized-certificate HTTPS hostname for remote chatbot clients.

**Database persistence**: The SQLite file on the server is never overwritten — rsync excludes `*.db`, and schema changes are applied by the idempotent startup migrations.

**CI/CD**: cicd-router provides the project gate, exact-SHA deployment, service restart, smoke check, and result publication for commits pushed to `main`.
