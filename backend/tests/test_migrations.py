"""Versioned SQLite migration behavior."""

import sqlite3
from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy import text as sqlalchemy_text
from sqlalchemy.orm import sessionmaker

from database import Base, create_database_engine
from main import _run_migrations
from models import Trip, TripDayAssignment, TripMeal, TripSnack
from services.trip_queries import trip_summary_view


def test_migrations_record_current_version_and_are_idempotent(tmp_path):
    db_engine = create_database_engine(f"sqlite:///{tmp_path / 'migrations.db'}")
    Base.metadata.create_all(db_engine)

    with db_engine.connect() as connection:
        _run_migrations(connection)
        connection.commit()
        first_version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()

        _run_migrations(connection)
        connection.commit()
        second_version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()

    assert first_version == second_version == 3
    assert len(list((tmp_path / "backups").glob("migrations-v0-*.db"))) == 1


def test_legacy_trip_rows_are_preserved_and_gain_cascades(tmp_path):
    database_path = tmp_path / "legacy.db"
    db_engine = create_database_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(db_engine)
    db_engine.dispose()

    with sqlite3.connect(database_path) as raw:
        raw.executescript(
            """
            PRAGMA foreign_keys=OFF;
            DROP TABLE trip_day_assignments;
            DROP TABLE trip_snacks;
            DROP TABLE trip_meals;
            CREATE TABLE trip_meals (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER NOT NULL REFERENCES trips(id),
                recipe_id INTEGER NOT NULL REFERENCES recipes(id),
                quantity INTEGER,
                packed BOOLEAN,
                actual_weight_oz FLOAT
            );
            CREATE TABLE trip_snacks (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER NOT NULL REFERENCES trips(id),
                catalog_item_id INTEGER NOT NULL REFERENCES snack_catalog(id),
                servings FLOAT,
                slot TEXT,
                packed BOOLEAN,
                actual_weight_oz FLOAT,
                trip_notes TEXT
            );
            CREATE TABLE trip_day_assignments (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER NOT NULL REFERENCES trips(id),
                day_number INTEGER NOT NULL,
                slot TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_id INTEGER NOT NULL,
                servings FLOAT
            );
            INSERT INTO ingredients (id, name) VALUES (1, 'Oats'), (2, 'Nuts');
            INSERT INTO recipes (id, name, category) VALUES (1, 'Oatmeal', 'breakfast');
            INSERT INTO snack_catalog (
                id, ingredient_id, weight_per_serving, calories_per_serving, category
            ) VALUES (1, 2, 1, 100, 'salty');
            INSERT INTO trips (
                id, name, first_day_fraction, full_days, last_day_fraction
            ) VALUES (1, 'Legacy', 0, 1, 0);
            INSERT INTO trip_meals (id, trip_id, recipe_id, quantity)
                VALUES (1, 1, 1, 1);
            INSERT INTO trip_snacks (id, trip_id, catalog_item_id, servings, slot)
                VALUES (1, 1, 1, 1, 'snacks');
            INSERT INTO trip_day_assignments (
                id, trip_id, day_number, slot, source_type, source_id, servings
            ) VALUES
                (1, 1, 1, 'breakfast', 'meal', 1, 1),
                (2, 999, 1, 'breakfast', 'meal', 999, 1);
            PRAGMA user_version=0;
            """
        )

    db_engine = create_database_engine(f"sqlite:///{database_path}")
    with db_engine.connect() as connection:
        _run_migrations(connection)
        connection.commit()

    session_factory = sessionmaker(bind=db_engine)
    with session_factory() as db:
        assert db.query(TripMeal).count() == 1
        assert db.query(TripSnack).count() == 1
        assert db.query(TripDayAssignment).count() == 1

        db.delete(db.get(Trip, 1))
        db.commit()

        assert db.query(TripMeal).count() == 0
        assert db.query(TripSnack).count() == 0
        assert db.query(TripDayAssignment).count() == 0


PRE_STRUCTURED_TRIP_COLUMNS = ("snack_model", "snacks_per_day", "oz_per_snack")
STRUCTURED_TABLES = ("snack_unit_types", "snack_unit_ingredients", "trip_snack_units")


@dataclass
class _PreStructuredTrip:
    """A trips row as it looked before the structured-snack migration.

    Passing this to a read projection proves the projection reads no column
    that migration 3 introduced, which is how the before/after summary
    comparison below can run against the pre-migration database at all.
    """

    id: int
    name: str
    first_day_fraction: float
    full_days: int
    last_day_fraction: float
    drink_mixes_per_day: int
    oz_per_day: float
    cal_per_oz: float


def _build_pre_structured_database(database_path, seed_sql: str):
    """Create a schema-version-2 database seeded with pre-structured data."""
    db_engine = create_database_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(db_engine)
    db_engine.dispose()

    raw = sqlite3.connect(database_path)
    try:
        for table in STRUCTURED_TABLES:
            raw.execute(f"DROP TABLE {table}")
        for column in PRE_STRUCTURED_TRIP_COLUMNS:
            raw.execute(f"ALTER TABLE trips DROP COLUMN {column}")
        raw.executescript(seed_sql)
        raw.execute("PRAGMA user_version=2")
        raw.commit()
    finally:
        raw.close()
    return create_database_engine(f"sqlite:///{database_path}")


LEGACY_TRIP_SEED = """
    INSERT INTO ingredients (
        id, name, calories_per_oz, protein_per_oz, fat_per_oz, carb_per_oz
    ) VALUES
        (1, 'Oats', 110, 4, 2, 19),
        (2, 'Almonds', 165, 6, 14, 6),
        (3, 'Tuna', 35, 8, 0, 0),
        (4, 'Electrolyte Mix', 90, 0, 0, 23);
    INSERT INTO recipes (id, name, category) VALUES (1, 'Oatmeal', 'breakfast');
    INSERT INTO recipe_ingredients (id, recipe_id, ingredient_id, amount_oz)
        VALUES (1, 1, 1, 3.5);
    INSERT INTO snack_catalog (
        id, ingredient_id, weight_per_serving, calories_per_serving, category
    ) VALUES
        (1, 2, 1.5, 248, 'salty'),
        (2, 3, 2.6, 91, 'lunch'),
        (3, 4, 0.7, 63, 'drink_mix');
    INSERT INTO trips (
        id, name, first_day_fraction, full_days, last_day_fraction,
        drink_mixes_per_day, oz_per_day, cal_per_oz
    ) VALUES (1, 'Wonderland', 0.5, 2, 0.5, 2, 21, 120);
    INSERT INTO trip_meals (id, trip_id, recipe_id, quantity) VALUES (1, 1, 1, 3);
    INSERT INTO trip_snacks (id, trip_id, catalog_item_id, servings, slot) VALUES
        (1, 1, 1, 6, 'snacks'),
        (2, 1, 2, 3, 'lunch'),
        (3, 1, 3, 6, 'snacks');
"""


def test_migration_marks_existing_trips_legacy_and_creates_unit_tables(tmp_path):
    db_engine = _build_pre_structured_database(
        tmp_path / "pre-structured.db",
        """
        INSERT INTO trips (
            id, name, first_day_fraction, full_days, last_day_fraction
        ) VALUES (1, 'Wonderland', 0.5, 2, 0.5), (2, 'Goat Rocks', 1, 1, 0);
        """,
    )
    with db_engine.connect() as connection:
        _run_migrations(connection)
        connection.commit()

    assert set(STRUCTURED_TABLES) <= set(inspect(db_engine).get_table_names())
    session_factory = sessionmaker(bind=db_engine)
    with session_factory() as db:
        assert [
            (trip.snack_model, trip.snacks_per_day, trip.oz_per_snack)
            for trip in db.query(Trip).order_by(Trip.id)
        ] == [("legacy", 4, 2), ("legacy", 4, 2)]
    # The tables the migration writes by hand must match the ones the models
    # would create from scratch, columns and trip cascade included.
    from verify_database import collect_database_errors

    assert collect_database_errors(db_engine) == []


def test_legacy_trip_summary_is_unchanged_by_the_structured_snack_migration(tmp_path):
    db_engine = _build_pre_structured_database(
        tmp_path / "legacy-summary.db",
        LEGACY_TRIP_SEED,
    )
    session_factory = sessionmaker(bind=db_engine)
    with session_factory() as db:
        row = db.execute(sqlalchemy_text(
            "SELECT id, name, first_day_fraction, full_days, last_day_fraction,"
            " drink_mixes_per_day, oz_per_day, cal_per_oz FROM trips WHERE id = 1"
        )).one()
        before = trip_summary_view(db, _PreStructuredTrip(*row))

    with db_engine.connect() as connection:
        _run_migrations(connection)
        connection.commit()

    session_factory = sessionmaker(bind=db_engine)
    with session_factory() as db:
        trip = db.get(Trip, 1)
        assert trip.snack_model == "legacy"
        after = trip_summary_view(db, trip)

    assert after == before
    # A summary with nothing in it would pass the comparison vacuously.
    assert before["slot_subtotals"]["snacks"]["calories"] > 0
    assert before["slot_subtotals"]["lunch"]["calories"] > 0
    assert before["macro_actual"]["protein_g"] > 0


def test_database_verifier_accepts_current_migrated_schema(tmp_path):
    from verify_database import collect_database_errors

    db_engine = create_database_engine(f"sqlite:///{tmp_path / 'verified.db'}")
    Base.metadata.create_all(db_engine)
    with db_engine.connect() as connection:
        _run_migrations(connection)
        connection.commit()

    assert collect_database_errors(db_engine) == []


def test_database_verifier_rejects_unversioned_schema(tmp_path):
    from verify_database import collect_database_errors

    db_engine = create_database_engine(f"sqlite:///{tmp_path / 'outdated.db'}")
    Base.metadata.create_all(db_engine)

    assert "schema version is 0; expected 3" in collect_database_errors(db_engine)
