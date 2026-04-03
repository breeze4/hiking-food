from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from sqlalchemy import text, inspect

from database import engine, Base
import models  # noqa: F401 — ensures all models are registered with Base
from routers.ingredients import router as ingredients_router
from routers.snacks import router as snacks_router
from routers.recipes import router as recipes_router
from routers.trips import router as trips_router
from routers.daily_plan import router as daily_plan_router

FRONTEND_DIR = Path(__file__).parent / ".." / "frontend" / "dist"


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


@asynccontextmanager
async def lifespan(inner_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        _run_migrations(conn)
        conn.commit()
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
app = FastAPI()


@app.get("/hiking-food")
async def redirect_to_trailing_slash():
    return RedirectResponse(url="/hiking-food/")


app.mount("/hiking-food", inner)
