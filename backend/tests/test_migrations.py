"""Versioned SQLite migration behavior."""

import sqlite3

from sqlalchemy.orm import sessionmaker

from database import Base, create_database_engine
from main import _run_migrations
from models import Trip, TripDayAssignment, TripMeal, TripSnack


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

    assert first_version == second_version == 2
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

    assert "schema version is 0; expected 2" in collect_database_errors(db_engine)
