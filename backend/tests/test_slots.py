"""Slot behavior tests through the public trip-planning API."""

import pytest

from database import Base


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.mark.parametrize(
    ("category", "expected_slot"),
    [
        ("bars_energy", "snacks"),
        ("salty", "snacks"),
        ("sweet", "snacks"),
        ("drink_mix", "snacks"),
        ("lunch", "lunch"),
    ],
)
def test_catalog_category_selects_default_trip_slot(c, category, expected_slot):
    ingredient = c.post(
        "/api/ingredients",
        json={"name": f"Food {category}", "calories_per_oz": 100},
    ).json()
    catalog_item = c.post(
        "/api/snacks",
        json={
            "ingredient_id": ingredient["id"],
            "weight_per_serving": 1,
            "calories_per_serving": 100,
            "category": category,
        },
    ).json()
    trip = c.post("/api/trips", json={"name": f"Trip {category}"}).json()

    selected = c.post(
        f"/api/trips/{trip['id']}/snacks",
        json={"catalog_item_id": catalog_item["id"], "servings": 1},
    ).json()

    assert selected["slot"] == expected_slot


def test_summary_splits_daytime_calorie_target_40_60(c):
    trip = c.post(
        "/api/trips",
        json={
            "name": "Slot targets",
            "first_day_fraction": 0,
            "full_days": 1,
            "last_day_fraction": 0,
            "oz_per_day": 20,
            "cal_per_oz": 100,
        },
    ).json()

    summary = c.get(f"/api/trips/{trip['id']}/summary").json()

    assert summary["slot_subtotals"]["lunch"]["target_cal"] == 800
    assert summary["slot_subtotals"]["snacks"]["target_cal"] == 1200
