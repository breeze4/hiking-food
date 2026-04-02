"""Tests for drink mix manual control behavior."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base
from main import inner as app
from models import Ingredient, SnackCatalogItem

# Override get_db for ALL routers that define their own
from routers import trips, snacks, recipes, ingredients

# In-memory SQLite needs StaticPool to share the same connection across threads
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


for mod in (trips, snacks, recipes, ingredients):
    app.dependency_overrides[mod.get_db] = _override_get_db


@pytest.fixture(autouse=True)
def db_setup():
    Base.metadata.create_all(bind=_engine)
    db = _TestSession()
    ing = Ingredient(name="Lemon Lime Mix", calories_per_oz=100.0)
    db.add(ing)
    db.flush()
    db.add(SnackCatalogItem(
        ingredient_id=ing.id, weight_per_serving=0.5,
        calories_per_serving=25.0, category="drink_mix",
    ))
    ing2 = Ingredient(name="Trail Mix", calories_per_oz=150.0)
    db.add(ing2)
    db.flush()
    db.add(SnackCatalogItem(
        ingredient_id=ing2.id, weight_per_serving=1.0,
        calories_per_serving=150.0, category="salty",
    ))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def c():
    with TestClient(app, raise_server_exceptions=True) as tc:
        yield tc


def _create_trip(c, **overrides):
    payload = {
        "name": "Test Trip",
        "first_day_fraction": 0.5, "full_days": 2,
        "last_day_fraction": 0.5, "drink_mixes_per_day": 3,
    }
    payload.update(overrides)
    resp = c.post("/api/trips", json=payload)
    assert resp.status_code == 201
    return resp.json()


def _get_catalog_id(c, category):
    for item in c.get("/api/snacks").json():
        if item["category"] == category:
            return item["id"]
    raise RuntimeError(f"No {category} catalog item")


def test_updating_trip_days_does_not_recalc_drink_servings(c):
    trip = _create_trip(c)
    cat_id = _get_catalog_id(c, "drink_mix")

    resp = c.post(f"/api/trips/{trip['id']}/snacks", json={
        "catalog_item_id": cat_id, "servings": 5,
    })
    assert resp.status_code == 201
    snack_id = resp.json()["id"]
    assert resp.json()["servings"] == 5

    c.put(f"/api/trips/{trip['id']}", json={"full_days": 5})
    detail = c.get(f"/api/trips/{trip['id']}").json()
    assert next(s for s in detail["snacks"] if s["id"] == snack_id)["servings"] == 5

    c.put(f"/api/trips/{trip['id']}", json={"drink_mixes_per_day": 10})
    detail = c.get(f"/api/trips/{trip['id']}").json()
    assert next(s for s in detail["snacks"] if s["id"] == snack_id)["servings"] == 5


def test_fractional_drink_mix_servings_rounded_up_on_create(c):
    trip = _create_trip(c)
    cat_id = _get_catalog_id(c, "drink_mix")

    resp = c.post(f"/api/trips/{trip['id']}/snacks", json={
        "catalog_item_id": cat_id, "servings": 2.3,
    })
    assert resp.status_code == 201
    assert resp.json()["servings"] == 3


def test_fractional_drink_mix_servings_rounded_up_on_update(c):
    trip = _create_trip(c)
    cat_id = _get_catalog_id(c, "drink_mix")

    resp = c.post(f"/api/trips/{trip['id']}/snacks", json={
        "catalog_item_id": cat_id, "servings": 2,
    })
    snack_id = resp.json()["id"]

    resp = c.put(f"/api/trips/{trip['id']}/snacks/{snack_id}", json={"servings": 3.1})
    assert resp.status_code == 200
    assert resp.json()["servings"] == 4


def test_drink_mix_defaults_to_1_serving(c):
    trip = _create_trip(c)
    cat_id = _get_catalog_id(c, "drink_mix")

    resp = c.post(f"/api/trips/{trip['id']}/snacks", json={
        "catalog_item_id": cat_id, "servings": 0.1,
    })
    assert resp.status_code == 201
    assert resp.json()["servings"] == 1


def test_non_drink_mix_not_rounded(c):
    trip = _create_trip(c)
    salty_id = _get_catalog_id(c, "salty")

    resp = c.post(f"/api/trips/{trip['id']}/snacks", json={
        "catalog_item_id": salty_id, "servings": 2.5,
    })
    assert resp.status_code == 201
    assert resp.json()["servings"] == 2.5
