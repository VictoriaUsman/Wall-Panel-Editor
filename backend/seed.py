"""
Seed script: creates an operator account and default canvas sizes with holes.
Run once after `make dev`:  docker compose exec backend python seed.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://wpd:wpd@localhost:5432/wpd")
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

from app.db.base import Base
from app.db.models.user import User
from app.db.models.canvas_size import CanvasSize
from app.db.models.hole import Hole
from app.core.security import hash_password


CATALOG = [
    {
        "name": "20×20 Square",
        "width_mm": 200, "height_mm": 200, "thickness_mm": 18, "price_cents": 2500,
        "holes": [
            {"label": "centre top", "x_mm": 100.0, "y_mm": 30.0},
        ],
    },
    {
        "name": "30×40 Portrait",
        "width_mm": 300, "height_mm": 400, "thickness_mm": 18, "price_cents": 3500,
        "holes": [
            {"label": "left D-ring", "x_mm": 75.0, "y_mm": 30.0},
            {"label": "right D-ring", "x_mm": 225.0, "y_mm": 30.0},
        ],
    },
    {
        "name": "40×30 Landscape",
        "width_mm": 400, "height_mm": 300, "thickness_mm": 18, "price_cents": 3500,
        "holes": [
            {"label": "left D-ring", "x_mm": 80.0, "y_mm": 30.0},
            {"label": "right D-ring", "x_mm": 320.0, "y_mm": 30.0},
        ],
    },
    {
        "name": "60×40 Large",
        "width_mm": 600, "height_mm": 400, "thickness_mm": 18, "price_cents": 5500,
        "holes": [
            {"label": "left D-ring", "x_mm": 100.0, "y_mm": 30.0},
            {"label": "centre top", "x_mm": 300.0, "y_mm": 30.0},
            {"label": "right D-ring", "x_mm": 500.0, "y_mm": 30.0},
        ],
    },
]


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        # Operator account
        existing = await db.execute(select(User).where(User.email == "operator@woodpanel.com"))
        if not existing.scalar_one_or_none():
            op = User(email="operator@woodpanel.com", hashed_password=hash_password("operator123"), is_operator=True)
            db.add(op)
            print("Created operator: operator@woodpanel.com / operator123")

        # Canvas sizes
        for entry in CATALOG:
            existing = await db.execute(select(CanvasSize).where(CanvasSize.name == entry["name"]))
            if not existing.scalar_one_or_none():
                holes = entry.pop("holes")
                cs = CanvasSize(**entry)
                db.add(cs)
                await db.flush()
                for h in holes:
                    db.add(Hole(canvas_size_id=cs.id, **h))
                print(f"Created size: {cs.name} with {len(holes)} holes")

        await db.commit()
    print("Seed complete.")


asyncio.run(main())
