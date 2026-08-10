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
    # The 40/60 split is the legacy snack model; structured trips meter units.
    c.put(f"/api/trips/{trip['id']}", json={"snack_model": "legacy"})

    summary = c.get(f"/api/trips/{trip['id']}/summary").json()

    assert summary["slot_subtotals"]["lunch"]["target_cal"] == 800
    assert summary["slot_subtotals"]["snacks"]["target_cal"] == 1200


def test_summary_defaults_lunches_needed_to_full_days(c):
    trip = c.post(
        "/api/trips",
        json={
            "name": "Lunch count",
            "first_day_fraction": 1,
            "full_days": 5,
            "last_day_fraction": 1,
        },
    ).json()
    # No override on the trip until the planner sets one.
    assert trip["lunches"] is None

    summary = c.get(f"/api/trips/{trip['id']}/summary").json()

    assert summary["slot_subtotals"]["lunch"]["lunches_needed"] == 5
    # The count belongs to lunch alone; other slots never carry it.
    assert "lunches_needed" not in summary["slot_subtotals"]["snacks"]


def test_explicit_lunches_override_the_full_days_default(c):
    trip = c.post(
        "/api/trips",
        json={"name": "Lunch override", "full_days": 5},
    ).json()

    updated = c.put(f"/api/trips/{trip['id']}", json={"lunches": 7}).json()
    assert updated["lunches"] == 7
    summary = c.get(f"/api/trips/{trip['id']}/summary").json()
    assert summary["slot_subtotals"]["lunch"]["lunches_needed"] == 7

    # An explicit null clears the override back to the full-days default.
    cleared = c.put(f"/api/trips/{trip['id']}", json={"lunches": None}).json()
    assert cleared["lunches"] is None
    summary = c.get(f"/api/trips/{trip['id']}/summary").json()
    assert summary["slot_subtotals"]["lunch"]["lunches_needed"] == 5


def test_negative_lunches_are_rejected(c):
    trip = c.post("/api/trips", json={"name": "Bad lunches"}).json()

    response = c.put(f"/api/trips/{trip['id']}", json={"lunches": -1})

    assert response.status_code == 422
    assert response.json()["detail"] == "lunches cannot be negative"
