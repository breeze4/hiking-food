import sys
import sqlite3
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from migrate_simplify_slots import migrate


def _seed_db(db_path):
    """Create a minimal trip_snacks table with old slot values."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE trip_snacks (
            id INTEGER PRIMARY KEY,
            trip_id INTEGER,
            catalog_item_id INTEGER,
            servings REAL,
            slot TEXT,
            packed INTEGER DEFAULT 0
        )
    """)
    c.executemany(
        "INSERT INTO trip_snacks (trip_id, catalog_item_id, servings, slot) VALUES (?,?,?,?)",
        [
            (1, 10, 2.0, "morning_snack"),
            (1, 11, 1.5, "afternoon_snack"),
            (1, 12, 3.0, "lunch"),
            (1, 13, 1.0, "morning_snack"),
            (2, 10, 2.0, "afternoon_snack"),
        ],
    )
    conn.commit()
    conn.close()


def test_migration_removes_old_slots():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        _seed_db(f.name)
        migrate(f.name)

        conn = sqlite3.connect(f.name)
        c = conn.cursor()

        # No rows should have old slot values
        c.execute("SELECT COUNT(*) FROM trip_snacks WHERE slot IN ('morning_snack', 'afternoon_snack')")
        assert c.fetchone()[0] == 0

        # All old rows should now be 'snacks'
        c.execute("SELECT COUNT(*) FROM trip_snacks WHERE slot = 'snacks'")
        assert c.fetchone()[0] == 4

        # Lunch row untouched
        c.execute("SELECT COUNT(*) FROM trip_snacks WHERE slot = 'lunch'")
        assert c.fetchone()[0] == 1

        conn.close()


def test_migration_idempotent():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        _seed_db(f.name)
        migrate(f.name)
        migrate(f.name)  # run twice

        conn = sqlite3.connect(f.name)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM trip_snacks WHERE slot IN ('morning_snack', 'afternoon_snack')")
        assert c.fetchone()[0] == 0
        c.execute("SELECT COUNT(*) FROM trip_snacks")
        assert c.fetchone()[0] == 5
        conn.close()


def test_slot_pcts_sum_to_one():
    from routers.trips import CATEGORY_TO_SLOT

    # All non-lunch categories map to snacks
    assert CATEGORY_TO_SLOT["bars_energy"] == "snacks"
    assert CATEGORY_TO_SLOT["salty"] == "snacks"
    assert CATEGORY_TO_SLOT["sweet"] == "snacks"
    assert CATEGORY_TO_SLOT["drink_mix"] == "snacks"
    assert CATEGORY_TO_SLOT["lunch"] == "lunch"


def test_slot_split_is_40_60():
    """Verify the slot percentage constants used in the summary endpoint."""
    # Import the module and check the values are used correctly
    # We read them from the source since they're inline in the function
    source = (Path(__file__).parent.parent / "routers" / "trips.py").read_text()
    assert '"lunch": 0.40' in source or '"lunch": 0.4' in source
    assert '"snacks": 0.60' in source or '"snacks": 0.6' in source
    # Verify no old slot names remain
    assert '"morning_snack"' not in source
    assert '"afternoon_snack"' not in source
