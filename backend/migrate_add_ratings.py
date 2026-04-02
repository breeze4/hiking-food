"""One-shot migration: add rating column to snack_catalog and recipes tables."""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "hiking_food.db"


def migrate(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for table in ("snack_catalog", "recipes"):
        # Check if column already exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if "rating" not in columns:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN rating INTEGER")
            print(f"Added rating column to {table}")
        else:
            print(f"rating column already exists on {table}")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
