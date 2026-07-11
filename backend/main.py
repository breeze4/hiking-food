from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from starlette.routing import Route

from sqlalchemy import text, inspect

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

FRONTEND_DIR = Path(__file__).parent / ".." / "frontend" / "dist"
MCP_SERVER = build_mcp_server()


def _add_column_if_missing(conn, table: str, column: str, col_type: str = "TEXT"):
    cols = [c["name"] for c in inspect(conn).get_columns(table)]
    if column not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


def _migrate_drink_mix_types(conn):
    """Classify existing drink mix items by type based on ingredient name."""
    try:
        rows = conn.execute(text(
            "SELECT sc.id, i.name FROM snack_catalog sc"
            " JOIN ingredients i ON sc.ingredient_id = i.id"
            " WHERE sc.category = 'drink_mix' AND sc.drink_mix_type IS NULL"
        )).fetchall()
    except Exception:
        return
    for row_id, name in rows:
        lower = name.lower()
        if any(k in lower for k in ("coffee", "carnation", "greens")):
            dmt = "breakfast"
        elif "tea" in lower:
            dmt = "dinner"
        else:
            dmt = "all_day"
        conn.execute(text(
            "UPDATE snack_catalog SET drink_mix_type = :dmt WHERE id = :id"
        ), {"dmt": dmt, "id": row_id})


def _run_migrations(conn):
    _add_column_if_missing(conn, "snack_catalog", "drink_mix_type")
    _migrate_drink_mix_types(conn)
    _add_column_if_missing(conn, "ingredients", "on_hand", "BOOLEAN DEFAULT 0")
    _add_column_if_missing(conn, "ingredients", "essentials", "BOOLEAN DEFAULT 0")
    _add_column_if_missing(conn, "ingredients", "packing_method")
    _add_column_if_missing(conn, "ingredients", "protein_per_oz", "REAL")
    _add_column_if_missing(conn, "ingredients", "fat_per_oz", "REAL")
    _add_column_if_missing(conn, "ingredients", "carb_per_oz", "REAL")
    # Migrate oz_per_day_low/high to single oz_per_day
    cols = [c["name"] for c in inspect(conn).get_columns("trips")]
    if "oz_per_day" not in cols:
        conn.execute(text("ALTER TABLE trips ADD COLUMN oz_per_day REAL DEFAULT 22"))
        conn.execute(text(
            "UPDATE trips SET oz_per_day = ROUND((COALESCE(oz_per_day_low, 19) + COALESCE(oz_per_day_high, 24)) / 2.0, 1)"
        ))
    if "oz_per_day_low" in cols:
        conn.execute(text("ALTER TABLE trips DROP COLUMN oz_per_day_low"))
    if "oz_per_day_high" in cols:
        conn.execute(text("ALTER TABLE trips DROP COLUMN oz_per_day_high"))
    _add_column_if_missing(conn, "trips", "cal_per_oz", "REAL DEFAULT 125")
    _add_column_if_missing(conn, "snack_catalog", "splittable", "BOOLEAN DEFAULT 0")
    # Mark Carnation breakfast essential as splittable
    try:
        conn.execute(text(
            "UPDATE snack_catalog SET splittable = 1"
            " WHERE id IN (SELECT sc.id FROM snack_catalog sc"
            "   JOIN ingredients i ON sc.ingredient_id = i.id"
            "   WHERE LOWER(i.name) LIKE '%carnation%')"
        ))
    except Exception:
        pass


@asynccontextmanager
async def lifespan(inner_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _run_migrations(conn)
        conn.commit()
    async with MCP_SERVER.session_manager.run():
        yield


inner = FastAPI(lifespan=lifespan)

inner.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/hiking-food")
async def redirect_to_trailing_slash():
    return RedirectResponse(url="/hiking-food/")


app.mount("/hiking-food", inner)
