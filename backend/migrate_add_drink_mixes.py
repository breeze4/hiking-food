"""One-shot migration: add drink_mixes_per_day column to trips table."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "hiking_food.db"


def migrate(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(trips)")
    columns = [row[1] for row in cursor.fetchall()]
    if "drink_mixes_per_day" not in columns:
        cursor.execute("ALTER TABLE trips ADD COLUMN drink_mixes_per_day INTEGER DEFAULT 2")
        print("Added drink_mixes_per_day column to trips")
    else:
        print("drink_mixes_per_day column already exists on trips")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
