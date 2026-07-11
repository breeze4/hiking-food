"""Verify that a database is current and safe to serve."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from database import Base, engine
import models  # noqa: F401 - register all tables with Base
from migrations import CURRENT_SCHEMA_VERSION


CASCADE_TABLES = {"trip_meals", "trip_snacks", "trip_day_assignments"}


def collect_database_errors(db_engine: Engine) -> list[str]:
    errors: list[str] = []
    inspector = inspect(db_engine)
    actual_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables)
    missing_tables = sorted(expected_tables - actual_tables)
    if missing_tables:
        errors.append(f"missing tables: {missing_tables}")

    for table in sorted(expected_tables & actual_tables):
        expected_columns = set(Base.metadata.tables[table].columns.keys())
        actual_columns = {column["name"] for column in inspector.get_columns(table)}
        if expected_columns != actual_columns:
            errors.append(
                f"column mismatch for {table}: expected {sorted(expected_columns)}, "
                f"got {sorted(actual_columns)}"
            )

    with db_engine.connect() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()
        if version != CURRENT_SCHEMA_VERSION:
            errors.append(
                f"schema version is {version}; expected {CURRENT_SCHEMA_VERSION}"
            )
        foreign_keys = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
        if foreign_keys != 1:
            errors.append("SQLite foreign key enforcement is disabled")
        violations = connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall()
        if violations:
            errors.append(f"foreign key violations: {violations}")
        for table in sorted(CASCADE_TABLES & actual_tables):
            rows = connection.exec_driver_sql(
                f"PRAGMA foreign_key_list({table})"
            ).fetchall()
            if not any(
                row[2] == "trips" and row[6].upper() == "CASCADE"
                for row in rows
            ):
                errors.append(f"{table}.trip_id does not cascade on trip deletion")

    return errors


def main() -> None:
    errors = collect_database_errors(engine)
    if errors:
        raise SystemExit("Database verification failed:\n- " + "\n- ".join(errors))
    print(f"Database verification passed at schema version {CURRENT_SCHEMA_VERSION}.")


if __name__ == "__main__":
    main()
