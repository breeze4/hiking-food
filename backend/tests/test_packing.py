"""Packing view: recipe assembly reports per-serving amounts, not combined totals."""

import pytest

from database import Base


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _trip_with_meal(c, amount_oz, quantity):
    ingredient = c.post(
        "/api/ingredients",
        json={"name": "Granola", "calories_per_oz": 130},
    ).json()
    recipe = c.post(
        "/api/recipes",
        json={
            "name": "Breakfast",
            "category": "breakfast",
            "ingredients": [{"ingredient_id": ingredient["id"], "amount_oz": amount_oz}],
        },
    ).json()
    trip = c.post(
        "/api/trips",
        json={"name": "Plan", "first_day_fraction": 0, "full_days": 4},
    ).json()
    c.post(
        f"/api/trips/{trip['id']}/meals",
        json={"recipe_id": recipe["id"], "quantity": quantity},
    )
    return trip


def test_packing_reports_per_serving_and_total(c):
    """4 servings of a 4oz-granola breakfast -> 4oz per serving, 16oz total."""
    trip = _trip_with_meal(c, amount_oz=4, quantity=4)

    packing = c.get(f"/api/trips/{trip['id']}/packing").json()

    meal = packing["meals"][0]
    assert meal["quantity"] == 4
    ingredient = meal["ingredients"][0]
    assert ingredient["amount_oz"] == 4  # per single baggie, not 16
    assert ingredient["total_oz"] == 16  # combined across all servings


def test_packing_single_serving_amount_equals_total(c):
    """With quantity 1 the per-serving amount and total coincide."""
    trip = _trip_with_meal(c, amount_oz=3, quantity=1)

    packing = c.get(f"/api/trips/{trip['id']}/packing").json()

    ingredient = packing["meals"][0]["ingredients"][0]
    assert ingredient["amount_oz"] == 3
    assert ingredient["total_oz"] == 3
