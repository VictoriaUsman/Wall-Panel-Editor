import pathlib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.db.session import engine
from app.db.base import Base
# Import all models so Base.metadata is populated
import app.db.models  # noqa: F401

from app.api import auth, jobs, photos, panels, catalog, pdfs

FRONTEND_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import get_settings
    import logging
    db_url = get_settings().DATABASE_URL
    # Log host only (never log credentials)
    try:
        host = db_url.split("@")[1].split("/")[0]
    except Exception:
        host = "unknown"
    logging.getLogger("uvicorn").info(f"Connecting to DB host: {host}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Wood Panel Wall Designer", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(photos.router, prefix="/api")
app.include_router(panels.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(pdfs.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve built React frontend in production (must come after all API routes)
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="spa")
