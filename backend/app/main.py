from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.session import engine
from app.db.base import Base
# Import all models so Base.metadata is populated
import app.db.models  # noqa: F401

from app.api import auth, jobs, photos, panels, catalog, pdfs


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist (dev convenience; use alembic in prod)
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
