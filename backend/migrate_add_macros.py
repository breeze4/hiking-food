"""One-shot migration: add protein_per_oz, fat_per_oz, carb_per_oz to ingredients."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "hiking_food.db"


def migrate(db_path: str = str(DB_PATH)):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(ingredients)")
    columns = [row[1] for row in cursor.fetchall()]
    for col in ("protein_per_oz", "fat_per_oz", "carb_per_oz"):
        if col not in columns:
            cursor.execute(f"ALTER TABLE ingredients ADD COLUMN {col} REAL")
            print(f"Added {col} column to ingredients")
        else:
            print(f"{col} column already exists on ingredients")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
