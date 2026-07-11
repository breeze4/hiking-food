"""Runtime configuration and process-isolation behavior."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
import subprocess
import sys

from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from database import Base, create_database_engine
from models import Trip, TripDayAssignment
from main import lifespan


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def _resolved_database_path(cwd: Path) -> Path:
    env = os.environ.copy()
    env.pop("HIKING_FOOD_DATABASE_URL", None)
    env["PYTHONPATH"] = str(BACKEND)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "from database import engine; "
                "print(Path(engine.url.database).resolve())"
            ),
        ],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def test_default_database_path_is_independent_of_working_directory():
    from_root = _resolved_database_path(ROOT)
    from_backend = _resolved_database_path(BACKEND)

    assert from_root == from_backend == BACKEND / "hiking_food.db"


def test_sqlite_connections_enforce_foreign_keys(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    env["HIKING_FOOD_DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from sqlalchemy import text; "
                "from database import engine; "
                "c = engine.connect(); "
                "print(c.execute(text('PRAGMA foreign_keys')).scalar_one()); "
                "c.close()"
            ),
        ],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "1"


def test_database_cascades_trip_assignments(tmp_path):
    db_engine = create_database_engine(f"sqlite:///{tmp_path / 'cascade.db'}")
    Base.metadata.create_all(db_engine)
    session_factory = sessionmaker(bind=db_engine)
    with session_factory() as db:
        trip = Trip(name="Cascade", first_day_fraction=0, full_days=1)
        db.add(trip)
        db.flush()
        db.add(TripDayAssignment(
            trip_id=trip.id,
            day_number=1,
            slot="breakfast",
            source_type="meal",
            source_id=1,
            servings=1,
        ))
        db.commit()

        db.delete(trip)
        db.commit()

        assert db.query(TripDayAssignment).count() == 0


def test_shared_test_engine_matches_production_foreign_key_behavior(test_engine):
    with test_engine.connect() as connection:
        enabled = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()

    assert enabled == 1


def test_application_lifespan_uses_injected_engine(tmp_path):
    injected_engine = create_database_engine(
        f"sqlite:///{tmp_path / 'injected.db'}"
    )

    class FakeSessionManager:
        @asynccontextmanager
        async def run(self):
            yield

    class FakeMcpServer:
        session_manager = FakeSessionManager()

    probe = FastAPI(lifespan=lifespan)
    probe.state.database_engine = injected_engine
    probe.state.mcp_server = FakeMcpServer()

    with TestClient(probe):
        pass

    assert inspect(injected_engine).has_table("trips")
