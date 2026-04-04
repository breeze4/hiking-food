import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from main import inner as test_app
from routers import trips, snacks, recipes, ingredients, daily_plan, settings

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


for mod in (trips, snacks, recipes, ingredients, daily_plan, settings):
    test_app.dependency_overrides[mod.get_db] = _override_get_db


@pytest.fixture()
def test_engine():
    return _engine


@pytest.fixture()
def test_session():
    return _TestSession


@pytest.fixture()
def c():
    with TestClient(test_app, raise_server_exceptions=True) as tc:
        yield tc
