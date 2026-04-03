"""Run startup migrations (same ones that run in app lifespan)."""
from database import engine, Base
import models  # noqa: F401
from main import _run_migrations

Base.metadata.create_all(bind=engine)
with engine.connect() as conn:
    _run_migrations(conn)
    conn.commit()
print("Migrations complete.")
