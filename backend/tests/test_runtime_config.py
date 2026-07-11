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

from mcp.server.transport_security import TransportSecurityMiddleware

from database import Base, create_database_engine
from models import Trip, TripDayAssignment
from main import inner, lifespan
from mcp_server import build_mcp_server, build_transport_security


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


def test_api_responses_carry_no_cors_allow_origin_header():
    response = TestClient(inner).get(
        "/api/health", headers={"Origin": "https://evil.example"}
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_mcp_transport_security_defaults_reject_unexpected_host(monkeypatch):
    monkeypatch.delenv("HIKING_FOOD_MCP_ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("HIKING_FOOD_MCP_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv(
        "HIKING_FOOD_OAUTH_ISSUER", "https://food.funnel.ts.net/hiking-food"
    )

    settings = build_transport_security()

    assert settings.enable_dns_rebinding_protection is True
    assert "localhost:8000" in settings.allowed_hosts
    assert "127.0.0.1:8000" in settings.allowed_hosts
    assert "beebaby:8000" in settings.allowed_hosts
    assert "food.funnel.ts.net" in settings.allowed_hosts

    middleware = TransportSecurityMiddleware(settings)
    assert middleware._validate_host("beebaby:8000") is True
    assert middleware._validate_host("food.funnel.ts.net") is True
    assert middleware._validate_host("attacker.example.com") is False


def test_mcp_transport_security_honors_env_overrides(monkeypatch):
    monkeypatch.setenv(
        "HIKING_FOOD_MCP_ALLOWED_HOSTS", "a.example:8000, b.example:9000"
    )
    monkeypatch.setenv(
        "HIKING_FOOD_MCP_ALLOWED_ORIGINS", "https://a.example, https://b.example"
    )

    settings = build_transport_security()

    assert settings.allowed_hosts == ["a.example:8000", "b.example:9000"]
    assert settings.allowed_origins == ["https://a.example", "https://b.example"]


def test_build_mcp_server_enables_dns_rebinding_protection():
    settings = build_mcp_server().settings.transport_security

    assert settings.enable_dns_rebinding_protection is True
    assert "beebaby:8000" in settings.allowed_hosts


def _resolved_auth_db_path(cwd: Path) -> Path:
    env = os.environ.copy()
    env.pop("HIKING_FOOD_AUTH_DB_PATH", None)
    env["PYTHONPATH"] = str(BACKEND)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "from mcp_oauth.app import DEFAULT_AUTH_DB_PATH; "
                "print(Path(DEFAULT_AUTH_DB_PATH).resolve())"
            ),
        ],
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def test_default_auth_db_path_is_independent_of_working_directory():
    from_root = _resolved_auth_db_path(ROOT)
    from_backend = _resolved_auth_db_path(BACKEND)

    assert from_root == from_backend == BACKEND / "hiking_food_auth.db"


def test_importing_main_creates_no_auth_database(tmp_path):
    fresh_db = tmp_path / "fresh_auth.db"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    env["HIKING_FOOD_AUTH_DB_PATH"] = str(fresh_db)

    subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert not fresh_db.exists()


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
