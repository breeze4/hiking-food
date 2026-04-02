"""One-shot migration: collapse morning_snack and afternoon_snack slots into snacks."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "hiking_food.db"


def migrate(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE trip_snacks SET slot = 'snacks' WHERE slot IN ('morning_snack', 'afternoon_snack')"
    )
    updated = cursor.rowcount
    print(f"Migrated {updated} trip_snacks rows from morning_snack/afternoon_snack to snacks")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
