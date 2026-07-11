from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from starlette.routing import Route

from database import engine, Base
import models  # noqa: F401 — ensures all models are registered with Base
from routers.ingredients import router as ingredients_router
from routers.snacks import router as snacks_router
from routers.recipes import router as recipes_router
from routers.trips import router as trips_router
from routers.daily_plan import router as daily_plan_router
from routers.settings import router as settings_router
from routers.food_intake import router as food_intake_router
from mcp_oauth.app import create_router as create_oauth_router
from mcp_oauth.auth import BearerAuthMiddleware
from mcp_server import build_mcp_server
from migrations import run_migrations as _run_migrations

FRONTEND_DIR = Path(__file__).parent / ".." / "frontend" / "dist"
MCP_SERVER = build_mcp_server()


@asynccontextmanager
async def lifespan(inner_app: FastAPI):
    database_engine = inner_app.state.database_engine
    mcp_server = inner_app.state.mcp_server
    Base.metadata.create_all(bind=database_engine)
    with database_engine.connect() as conn:
        _run_migrations(conn)
        conn.commit()
    async with mcp_server.session_manager.run():
        yield


inner = FastAPI(lifespan=lifespan)
inner.state.database_engine = engine
inner.state.mcp_server = MCP_SERVER

inner.include_router(ingredients_router)
inner.include_router(snacks_router)
inner.include_router(recipes_router)
inner.include_router(trips_router)
inner.include_router(daily_plan_router)
inner.include_router(settings_router)
inner.include_router(food_intake_router)
inner.include_router(create_oauth_router())

# Mount streamable HTTP at the exact /mcp path. The outer app contributes the
# public /hiking-food prefix; an exact Route avoids redirecting OAuth clients.
MCP_SERVER.streamable_http_app()
inner.router.routes.append(Route(
    "/mcp",
    endpoint=BearerAuthMiddleware(StreamableHTTPASGIApp(MCP_SERVER.session_manager)),
    methods=["GET", "POST", "DELETE"],
))


@inner.get("/api/health")
def health_check():
    return {"status": "ok"}


# Serve frontend static files in production (when dist/ exists)
if FRONTEND_DIR.is_dir():
    inner.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @inner.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA client-side routing)."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


# Mount the app under /hiking-food and redirect bare path
# Uvicorn runs the outer app. Mounted sub-app lifespans are not entered by
# Starlette, so the outer app must own database setup and the MCP task group.
app = FastAPI(lifespan=lifespan)
app.state.database_engine = engine
app.state.mcp_server = MCP_SERVER


@app.get("/hiking-food")
async def redirect_to_trailing_slash():
    return RedirectResponse(url="/hiking-food/")


app.mount("/hiking-food", inner)
