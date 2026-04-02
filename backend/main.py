from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from database import engine, Base
import models  # noqa: F401 — ensures all models are registered with Base
from routers.ingredients import router as ingredients_router
from routers.snacks import router as snacks_router
from routers.recipes import router as recipes_router
from routers.trips import router as trips_router

FRONTEND_DIR = Path(__file__).parent / ".." / "frontend" / "dist"


@asynccontextmanager
async def lifespan(inner_app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
