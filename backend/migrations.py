"""Ordered, idempotent SQLite schema migrations."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


def _add_column_if_missing(
    conn: Connection,
    table: str,
    column: str,
    col_type: str = "TEXT",
) -> None:
    columns = [item["name"] for item in inspect(conn).get_columns(table)]
    if column not in columns:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


def _migrate_drink_mix_types(conn: Connection) -> None:
    rows = conn.execute(text(
        "SELECT sc.id, i.name FROM snack_catalog sc"
        " JOIN ingredients i ON sc.ingredient_id = i.id"
        " WHERE sc.category = 'drink_mix' AND sc.drink_mix_type IS NULL"
    )).fetchall()
    for row_id, name in rows:
        lower = name.lower()
        if any(keyword in lower for keyword in ("coffee", "carnation", "greens")):
            drink_mix_type = "breakfast"
        elif "tea" in lower:
            drink_mix_type = "dinner"
        else:
            drink_mix_type = "all_day"
        conn.execute(
            text("UPDATE snack_catalog SET drink_mix_type = :value WHERE id = :id"),
            {"value": drink_mix_type, "id": row_id},
        )


def _migration_1_existing_columns(conn: Connection) -> None:
    _add_column_if_missing(conn, "snack_catalog", "drink_mix_type")
    _migrate_drink_mix_types(conn)
    _add_column_if_missing(conn, "ingredients", "on_hand", "BOOLEAN DEFAULT 0")
    _add_column_if_missing(conn, "ingredients", "essentials", "BOOLEAN DEFAULT 0")
    _add_column_if_missing(conn, "ingredients", "packing_method")
    _add_column_if_missing(conn, "ingredients", "protein_per_oz", "REAL")
    _add_column_if_missing(conn, "ingredients", "fat_per_oz", "REAL")
    _add_column_if_missing(conn, "ingredients", "carb_per_oz", "REAL")

    trip_columns = [item["name"] for item in inspect(conn).get_columns("trips")]
    if "oz_per_day" not in trip_columns:
        conn.execute(text("ALTER TABLE trips ADD COLUMN oz_per_day REAL DEFAULT 22"))
        conn.execute(text(
            "UPDATE trips SET oz_per_day = ROUND("
            "(COALESCE(oz_per_day_low, 19) + COALESCE(oz_per_day_high, 24)) / 2.0, 1)"
        ))
    if "oz_per_day_low" in trip_columns:
        conn.execute(text("ALTER TABLE trips DROP COLUMN oz_per_day_low"))
    if "oz_per_day_high" in trip_columns:
        conn.execute(text("ALTER TABLE trips DROP COLUMN oz_per_day_high"))
    _add_column_if_missing(conn, "trips", "cal_per_oz", "REAL DEFAULT 125")
    _add_column_if_missing(conn, "snack_catalog", "splittable", "BOOLEAN DEFAULT 0")
    conn.execute(text(
        "UPDATE snack_catalog SET splittable = 1"
        " WHERE id IN (SELECT sc.id FROM snack_catalog sc"
        "   JOIN ingredients i ON sc.ingredient_id = i.id"
        "   WHERE LOWER(i.name) LIKE '%carnation%')"
    ))


def _trip_fk_cascades(conn: Connection, table: str) -> bool:
    rows = conn.exec_driver_sql(f"PRAGMA foreign_key_list({table})").fetchall()
    return any(row[2] == "trips" and row[6].upper() == "CASCADE" for row in rows)


def _rebuild_with_trip_cascade(
    conn: Connection,
    *,
    table: str,
    create_sql: str,
    columns: str,
    orphan_predicate: str,
) -> None:
    if _trip_fk_cascades(conn, table):
        return
    conn.execute(text(f"DELETE FROM {table} WHERE {orphan_predicate}"))
    replacement = f"{table}__migration_2"
    conn.exec_driver_sql(f"DROP TABLE IF EXISTS {replacement}")
    conn.exec_driver_sql(create_sql.format(table=replacement))
    conn.exec_driver_sql(
        f"INSERT INTO {replacement} ({columns}) SELECT {columns} FROM {table}"
    )
    conn.exec_driver_sql(f"DROP TABLE {table}")
    conn.exec_driver_sql(f"ALTER TABLE {replacement} RENAME TO {table}")


def _migration_2_trip_cascades(conn: Connection) -> None:
    _rebuild_with_trip_cascade(
        conn,
        table="trip_meals",
        columns="id, trip_id, recipe_id, quantity, packed, actual_weight_oz",
        orphan_predicate=(
            "trip_id NOT IN (SELECT id FROM trips) OR "
            "recipe_id NOT IN (SELECT id FROM recipes)"
        ),
        create_sql="""
            CREATE TABLE {table} (
                id INTEGER NOT NULL PRIMARY KEY,
                trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                recipe_id INTEGER NOT NULL REFERENCES recipes(id),
                quantity INTEGER,
                packed BOOLEAN,
                actual_weight_oz FLOAT
            )
        """,
    )
    _rebuild_with_trip_cascade(
        conn,
        table="trip_snacks",
        columns=(
            "id, trip_id, catalog_item_id, servings, slot, packed, "
            "actual_weight_oz, trip_notes"
        ),
        orphan_predicate=(
            "trip_id NOT IN (SELECT id FROM trips) OR "
            "catalog_item_id NOT IN (SELECT id FROM snack_catalog)"
        ),
        create_sql="""
            CREATE TABLE {table} (
                id INTEGER NOT NULL PRIMARY KEY,
                trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                catalog_item_id INTEGER NOT NULL REFERENCES snack_catalog(id),
                servings FLOAT,
                slot TEXT,
                packed BOOLEAN,
                actual_weight_oz FLOAT,
                trip_notes TEXT
            )
        """,
    )
    conn.execute(text(
        "DELETE FROM trip_day_assignments WHERE "
        "trip_id NOT IN (SELECT id FROM trips) OR "
        "(source_type = 'meal' AND source_id NOT IN (SELECT id FROM trip_meals)) OR "
        "(source_type = 'snack' AND source_id NOT IN (SELECT id FROM trip_snacks)) OR "
        "source_type NOT IN ('meal', 'snack')"
    ))
    _rebuild_with_trip_cascade(
        conn,
        table="trip_day_assignments",
        columns="id, trip_id, day_number, slot, source_type, source_id, servings",
        orphan_predicate="trip_id NOT IN (SELECT id FROM trips)",
        create_sql="""
            CREATE TABLE {table} (
                id INTEGER NOT NULL PRIMARY KEY,
                trip_id INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
                day_number INTEGER NOT NULL,
                slot TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                servings FLOAT
            )
        """,
    )


MIGRATIONS: tuple[Callable[[Connection], None], ...] = (
    _migration_1_existing_columns,
    _migration_2_trip_cascades,
)
CURRENT_SCHEMA_VERSION = len(MIGRATIONS)


def _backup_database(conn: Connection, current_version: int) -> Path | None:
    database = conn.engine.url.database
    if conn.engine.dialect.name != "sqlite" or not database or database == ":memory:":
        return None
    database_path = Path(database).resolve()
    if not database_path.exists():
        return None
    backup_dir = Path(os.environ.get(
        "HIKING_FOOD_BACKUP_DIR",
        database_path.parent / "backups",
    ))
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = backup_dir / (
        f"{database_path.stem}-v{current_version}-{timestamp}.db"
    )
    with sqlite3.connect(backup_path) as destination:
        conn.connection.driver_connection.backup(destination)

    backups = sorted(
        backup_dir.glob(f"{database_path.stem}-v*-*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for expired in backups[10:]:
        expired.unlink()
    return backup_path


def run_migrations(conn: Connection) -> None:
    current_version = conn.exec_driver_sql("PRAGMA user_version").scalar_one()
    if current_version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema version {current_version} is newer than supported "
            f"version {CURRENT_SCHEMA_VERSION}"
        )
    if current_version < CURRENT_SCHEMA_VERSION:
        _backup_database(conn, current_version)
    for version, migration in enumerate(MIGRATIONS, start=1):
        if version <= current_version:
            continue
        migration(conn)
        conn.exec_driver_sql(f"PRAGMA user_version={version}")
