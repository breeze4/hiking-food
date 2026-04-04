"""Verify that a fresh DB created by create_all + _run_migrations matches prod schema."""
import sqlite3
import subprocess
import tempfile

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# SQLite type aliases that are functionally identical
SQLITE_TYPE_ALIASES = {
    "REAL": "FLOAT",
    "BOOLEAN DEFAULT 0": "BOOLEAN",
}


def _normalize_type(t):
    return SQLITE_TYPE_ALIASES.get(t, t)


def _get_schema(conn):
    """Return {table: sorted list of (name, type)} for all tables."""
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cursor.fetchall()]
    schema = {}
    for table in tables:
        cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
        # pragma returns (cid, name, type, notnull, default, pk)
        schema[table] = sorted((row[1], _normalize_type(row[2])) for row in cols)
    return schema


def _build_fresh_schema():
    """Create a fresh in-memory DB using the app's startup path."""
    from sqlalchemy.pool import StaticPool
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    from database import Base
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    from main import _run_migrations
    with engine.connect() as conn:
        _run_migrations(conn)
        conn.commit()
    raw = sqlite3.connect(":memory:")
    # Dump and load to get a plain sqlite3 connection for schema inspection
    with engine.connect() as conn:
        for line in conn.connection.driver_connection.iterdump():
            raw.execute(line)
    return _get_schema(raw)


def _get_prod_schema():
    """Get schema from beebaby prod DB via SSH + Python."""
    script = "\n".join([
        "import sqlite3, json",
        "conn = sqlite3.connect('dev/hiking-food/backend/hiking_food.db')",
        "tables = [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]",
        "schema = {}",
        "for t in tables:",
        "    cols = conn.execute(f'PRAGMA table_info({t})').fetchall()",
        "    schema[t] = sorted([[r[1], r[2]] for r in cols])",
        "print(json.dumps(schema))",
    ])
    result = subprocess.run(
        ["ssh", "beebaby", "python3"],
        input=script, capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"SSH failed: {result.stderr}")
    import json
    raw = json.loads(result.stdout)
    return {t: sorted((c[0], _normalize_type(c[1])) for c in cols) for t, cols in raw.items()}


def test_fresh_schema_matches_prod():
    fresh = _build_fresh_schema()
    try:
        prod = _get_prod_schema()
    except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        import pytest
        pytest.skip(f"Cannot reach beebaby: {e}")

    # Compare table sets
    fresh_tables = set(fresh.keys())
    prod_tables = set(prod.keys())
    assert fresh_tables == prod_tables, (
        f"Table mismatch.\n  Fresh only: {fresh_tables - prod_tables}\n  Prod only: {prod_tables - fresh_tables}"
    )

    # Compare columns per table
    for table in sorted(fresh_tables):
        assert fresh[table] == prod[table], (
            f"Column mismatch in '{table}'.\n"
            f"  Fresh: {fresh[table]}\n"
            f"  Prod:  {prod[table]}"
        )
