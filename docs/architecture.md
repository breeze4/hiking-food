# Architecture

## Project Structure

The project is two independent sibling directories (`backend/`, `frontend/`) with no shared root build tooling, monorepo manager, or container config.

Seed data lives in `data/` as JSON files (`skurka-recipes.json`, `utah-2026-snacks.json`) and is loaded by `backend/seed.py` on every deploy.

Specs, plans, and session logs live in `docs/`; `docs/plans/INDEX.md` is the authoritative status tracker for all implementation plans.

## Backend

**Framework**: FastAPI with a nested ASGI mount — an outer `app` mounts the real application at `/hiking-food`, so all routes are served under that prefix.

**Database**: SQLite via SQLAlchemy ORM, stored as `backend/hiking_food.db` (gitignored, excluded from rsync, never overwritten by deploy). Tables are created by `Base.metadata.create_all()` at startup.

**Migrations**: Run inline in `main.py:_run_migrations()` at every startup using an idempotent `_add_column_if_missing()` helper that inspects columns and issues `ALTER TABLE ADD COLUMN` if missing. No Alembic — schema evolution is fully manual.

**Routing**: Each domain has its own router module in `routers/` under the `/api/` prefix (`ingredients`, `snacks`, `recipes`, `trips`, `daily_plan`, `settings`). `daily_plan` shares the `/api/trips` prefix with `trips`.

**Session management**: Each router defines its own identical `get_db()` generator (no shared utility). Tests override all six independently via `app.dependency_overrides`.

**Schemas**: Pydantic v2 models with a `Create`/`Update`/`Read` pattern per resource. Some computed fields (e.g. macro per-serving on snacks) are derived at response time in the router, not stored in the DB.

**Services**: Thin service layer — `recipe_calc.py` computes recipe totals, `autofill.py` distributes meals/snacks across trip days, `calculator.py` implements Skurka method calorie/weight targets. Business logic also lives directly in routers (e.g. macro derivation from protein/fat/carb on ingredient create/update).

**Configuration**: All config is hardcoded — DB path, calorie constants, target ranges, default macro splits. No env vars, no config files.

**Dependencies**: Four unpinned packages: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`.

**CORS/Auth**: The browser API retains wide-open CORS and relies on Tailscale network access. The separate `/mcp` transport is protected by OAuth 2.0 authorization code + PKCE, dynamically registered public clients, short-lived JWT access tokens, and persistent refresh tokens.

**MCP**: `mcp_server.py` exposes a compact domain-level FastMCP tool surface over exact-path Streamable HTTP. It operates directly against the same SQLAlchemy models and transaction boundary as the REST API. OAuth discovery, registration, authorization, and token endpoints live in `mcp_oauth/`; the outer `/hiking-food` ASGI mount becomes the public issuer prefix.

**Static serving**: In production, FastAPI serves the built frontend from `frontend/dist/` with a catch-all route that falls back to `index.html` for SPA routing.

## Frontend

**Stack**: React 19 + Vite 8, plain JavaScript (`.jsx`/`.js` only, no TypeScript anywhere).

**Routing**: React Router v7 with `basename="/hiking-food"`. Routes are declared inline in `App.jsx`. There are 8 routes covering trip planning, daily plan, packing, ingredients, snacks, and recipes.

**State management**: A single `TripContext` holds global state (`trips`, `activeTripId`, `tripDetail`, `summary`). Mutations call the API then update local state; `refreshTrip()` re-fetches detail and summary. Pages manage their own local state via `useState`/`useEffect` for page-specific data.

**API layer**: A single `src/api.js` file wraps `fetch` with five named exports (`get`, `post`, `put`, `patch`, `del`). Base URL is hardcoded to `/hiking-food/api`. No interceptors, auth, retries, or cancellation.

**UI components**: shadcn/ui (base-nova style) built on `@base-ui/react` primitives, with `lucide-react` icons. UI components live in `src/components/ui/` and use `data-slot` attributes for CSS targeting.

**Styling**: Tailwind CSS v4 configured entirely in CSS (`src/index.css`) using `@theme inline` with `oklch` colors. Class-based dark mode. Geist variable font. No CSS modules or styled-components.

**Dev proxy**: Vite proxies `/hiking-food/api` to `http://localhost:8000`, stripping the `/hiking-food` prefix, so the frontend and backend share the same URL structure in dev and prod.

**Patterns**: Trip calculator uses debounced save (500ms `setTimeout`). Daily plan page renders a hand-built SVG stacked bar chart with no charting library. Some form controls use native `<select>` rather than shadcn equivalents.

## Testing

**Framework**: pytest with `fastapi.testclient.TestClient` against an in-memory SQLite database using `StaticPool`.

**Approach**: Mix of unit tests (calculator, recipe calc) and HTTP integration tests (daily plan, shopping list, slots, drink mixes, macros, settings). Each integration test fixture creates and drops all tables around each test. Tests run against the inner app directly (not the `/hiking-food` mounted wrapper).

**No frontend tests** — no test runner, no component tests, no E2E tests.

## Deployment

**Method**: `cicd-router` watches verified commits to `main`, runs the exact-SHA project gates from `scripts/cicd-router-gates.sh`, rsyncs the approved source to `beebaby`, runs `deploy/remote-bootstrap.sh`, restarts the user systemd service, and performs the configured health check.

**Service**: Runs as a user-level systemd unit (`hiking-food.service`) on port 8000. `loginctl enable-linger` keeps it alive after logout. BeeBaby's Tailscale Funnel publishes the OAuth-protected `/hiking-food` MCP path through a recognized-certificate HTTPS hostname for remote chatbot clients.

**Database persistence**: The SQLite file on the server is never overwritten — rsync excludes `*.db`, and schema changes are applied by the idempotent startup migrations.

**CI/CD**: cicd-router provides the project gate, exact-SHA deployment, service restart, smoke check, and result publication for commits pushed to `main`.
