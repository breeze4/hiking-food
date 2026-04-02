"""One-shot migration: add slot column to trip_snacks and backfill from snack category."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "hiking_food.db"

CATEGORY_TO_SLOT = {
    "drink_mix": "morning_snack",
    "bars_energy": "morning_snack",
    "lunch": "lunch",
    "salty": "afternoon_snack",
    "sweet": "afternoon_snack",
}


def migrate(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add column if missing
    cursor.execute("PRAGMA table_info(trip_snacks)")
    columns = [row[1] for row in cursor.fetchall()]
    if "slot" not in columns:
        cursor.execute("ALTER TABLE trip_snacks ADD COLUMN slot TEXT")
        print("Added slot column to trip_snacks")
    else:
        print("slot column already exists on trip_snacks")

    # Backfill from snack_catalog category (if category column exists)
    cursor.execute("PRAGMA table_info(snack_catalog)")
    sc_columns = [row[1] for row in cursor.fetchall()]
    if "category" in sc_columns:
        cursor.execute("""
            SELECT ts.id, sc.category
            FROM trip_snacks ts
            JOIN snack_catalog sc ON ts.catalog_item_id = sc.id
            WHERE ts.slot IS NULL
        """)
        rows = cursor.fetchall()
        for ts_id, category in rows:
            slot = CATEGORY_TO_SLOT.get(category, "afternoon_snack")
            cursor.execute("UPDATE trip_snacks SET slot = ? WHERE id = ?", (slot, ts_id))
        if rows:
            print(f"Backfilled slot for {len(rows)} trip_snacks rows")
        else:
            print("No rows needed backfill")
    else:
        print("snack_catalog has no category column yet, skipping backfill")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
