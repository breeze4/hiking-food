import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "hiking_food.db"
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "HIKING_FOOD_DATABASE_URL",
    f"sqlite:///{DEFAULT_DATABASE_PATH}",
)



def create_database_engine(url: str = SQLALCHEMY_DATABASE_URL, **kwargs):
    if url.startswith("sqlite:"):
        connect_args = dict(kwargs.pop("connect_args", {}))
        connect_args.setdefault("check_same_thread", False)
        kwargs["connect_args"] = connect_args
    db_engine = create_engine(url, **kwargs)
    if url.startswith("sqlite:"):
        @event.listens_for(db_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return db_engine


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
