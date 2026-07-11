"""Public workflow tests shared by browser REST and chatbot MCP consumers."""

import pytest

from database import Base


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_trip_with_breakfast(c):
    ingredient = c.post(
        "/api/ingredients",
        json={"name": "Oats", "calories_per_oz": 110},
    ).json()
    recipe = c.post(
        "/api/recipes",
        json={
            "name": "Oatmeal",
            "category": "breakfast",
            "ingredients": [{"ingredient_id": ingredient["id"], "amount_oz": 3}],
        },
    ).json()
    trip = c.post(
        "/api/trips",
        json={"name": "Plan", "first_day_fraction": 0, "full_days": 1},
    ).json()
    meal = c.post(
        f"/api/trips/{trip['id']}/meals",
        json={"recipe_id": recipe["id"], "quantity": 1},
    ).json()
    return trip, meal


def _create_trip_with_snack(c):
    ingredient = c.post(
        "/api/ingredients",
        json={"name": "Nuts", "calories_per_oz": 160},
    ).json()
    catalog_item = c.post(
        "/api/snacks",
        json={
            "ingredient_id": ingredient["id"],
            "weight_per_serving": 2,
            "calories_per_serving": 320,
            "category": "salty",
        },
    ).json()
    trip = c.post(
        "/api/trips",
        json={"name": "Plan", "first_day_fraction": 0, "full_days": 1},
    ).json()
    snack = c.post(
        f"/api/trips/{trip['id']}/snacks",
        json={"catalog_item_id": catalog_item["id"], "servings": 1},
    ).json()
    return trip, snack


def test_rest_rejects_blank_trip_name(c):
    response = c.post("/api/trips", json={"name": "   "})

    assert response.status_code == 422
    assert response.json()["detail"] == "Trip name is required"


def test_rest_rejects_out_of_range_day_fraction(c):
    response = c.post(
        "/api/trips",
        json={"name": "Invalid", "first_day_fraction": 1.1},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "first_day_fraction must be between 0 and 1"


def test_rest_rejects_negative_full_days(c):
    response = c.post(
        "/api/trips",
        json={"name": "Invalid", "full_days": -1},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "full_days cannot be negative"


def test_rest_rejects_invalid_trip_update_without_changing_trip(c):
    created = c.post("/api/trips", json={"name": "Valid", "full_days": 2}).json()

    response = c.put(f"/api/trips/{created['id']}", json={"full_days": -1})

    assert response.status_code == 422
    assert c.get(f"/api/trips/{created['id']}").json()["full_days"] == 2


@pytest.mark.parametrize(
    ("field", "value", "detail"),
    [
        ("drink_mixes_per_day", -1, "drink_mixes_per_day cannot be negative"),
        ("oz_per_day", 0, "oz_per_day must be greater than zero"),
        ("cal_per_oz", -1, "cal_per_oz must be greater than zero"),
    ],
)
def test_rest_rejects_invalid_trip_targets(c, field, value, detail):
    response = c.post("/api/trips", json={"name": "Invalid", field: value})

    assert response.status_code == 422
    assert response.json()["detail"] == detail


def test_rest_rejects_duplicate_trip_name(c):
    assert c.post("/api/trips", json={"name": "Same Trip"}).status_code == 201

    response = c.post("/api/trips", json={"name": "  Same Trip  "})

    assert response.status_code == 409
    assert response.json()["detail"] == 'A trip named "Same Trip" already exists'


def test_rest_rejects_renaming_trip_to_an_existing_name(c):
    first = c.post("/api/trips", json={"name": "First"}).json()
    c.post("/api/trips", json={"name": "Second"})

    response = c.put(f"/api/trips/{first['id']}", json={"name": "Second"})

    assert response.status_code == 409
    assert c.get(f"/api/trips/{first['id']}").json()["name"] == "First"


def test_rest_trip_shape_change_invalidates_daily_plan(c):
    trip, _ = _create_trip_with_breakfast(c)
    filled = c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill").json()
    assert filled["days"][0]["items"]

    response = c.put(f"/api/trips/{trip['id']}", json={"full_days": 2})

    assert response.status_code == 200
    plan = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert all(not day["items"] for day in plan["days"])
    assert plan["unallocated"][0]["name"] == "Oatmeal"


def test_rest_meal_quantity_change_invalidates_daily_plan(c):
    trip, meal = _create_trip_with_breakfast(c)
    filled = c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill").json()
    assert filled["days"][0]["items"]

    response = c.put(
        f"/api/trips/{trip['id']}/meals/{meal['id']}",
        json={"quantity": 2},
    )

    assert response.status_code == 200
    plan = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert all(not day["items"] for day in plan["days"])
    assert plan["unallocated"][0]["remaining_servings"] == 2


def test_rest_snack_servings_change_invalidates_daily_plan(c):
    trip, snack = _create_trip_with_snack(c)
    filled = c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill").json()
    assert filled["days"][0]["items"]

    response = c.put(
        f"/api/trips/{trip['id']}/snacks/{snack['id']}",
        json={"servings": 2},
    )

    assert response.status_code == 200
    plan = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert all(not day["items"] for day in plan["days"])
    assert plan["unallocated"][0]["remaining_servings"] == 2


def test_rest_adding_meal_invalidates_daily_plan(c):
    trip, existing_meal = _create_trip_with_breakfast(c)
    filled = c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill").json()
    assert filled["days"][0]["items"]

    response = c.post(
        f"/api/trips/{trip['id']}/meals",
        json={"recipe_id": existing_meal["recipe_id"], "quantity": 1},
    )

    assert response.status_code == 201
    plan = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert all(not day["items"] for day in plan["days"])
    assert len(plan["unallocated"]) == 2


def test_rest_adding_snack_invalidates_daily_plan(c):
    trip, _ = _create_trip_with_breakfast(c)
    c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill")
    ingredient = c.post(
        "/api/ingredients",
        json={"name": "Nuts", "calories_per_oz": 160},
    ).json()
    catalog_item = c.post(
        "/api/snacks",
        json={
            "ingredient_id": ingredient["id"],
            "weight_per_serving": 2,
            "calories_per_serving": 320,
            "category": "salty",
        },
    ).json()

    response = c.post(
        f"/api/trips/{trip['id']}/snacks",
        json={"catalog_item_id": catalog_item["id"], "servings": 1},
    )

    assert response.status_code == 201
    plan = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert all(not day["items"] for day in plan["days"])
    assert {item["name"] for item in plan["unallocated"]} == {"Oatmeal", "Nuts"}


def test_rest_removing_meal_removes_its_daily_assignments(c):
    trip, meal = _create_trip_with_breakfast(c)
    c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill")

    response = c.delete(f"/api/trips/{trip['id']}/meals/{meal['id']}")

    assert response.status_code == 204
    plan = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert all(not day["items"] for day in plan["days"])
    assert plan["unallocated"] == []


def test_rest_removing_snack_removes_its_daily_assignments(c):
    trip, snack = _create_trip_with_snack(c)
    c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill")

    response = c.delete(f"/api/trips/{trip['id']}/snacks/{snack['id']}")

    assert response.status_code == 204
    plan = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert all(not day["items"] for day in plan["days"])
    assert plan["unallocated"] == []


def test_rest_deleting_trip_cannot_leak_assignments_into_reused_id(c):
    trip, _ = _create_trip_with_breakfast(c)
    c.post(f"/api/trips/{trip['id']}/daily-plan/auto-fill")
    assert c.delete(f"/api/trips/{trip['id']}").status_code == 204

    replacement = c.post(
        "/api/trips",
        json={"name": "Replacement", "first_day_fraction": 0, "full_days": 1},
    ).json()
    plan = c.get(f"/api/trips/{replacement['id']}/daily-plan").json()

    assert all(not day["items"] for day in plan["days"])
    assert plan["unallocated"] == []


def test_rest_rejects_assignment_to_day_outside_trip(c):
    trip, snack = _create_trip_with_snack(c)

    response = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 999,
            "slot": "afternoon_snacks",
            "source_type": "snack",
            "source_id": snack["id"],
            "servings": 1,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "day_number must be one of [1]"


def test_rest_rejects_unknown_assignment_source_type(c):
    trip, snack = _create_trip_with_snack(c)

    response = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "afternoon_snacks",
            "source_type": "bogus",
            "source_id": snack["id"],
            "servings": 1,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "source_type must be meal or snack"


def test_rest_rejects_unknown_assignment_slot(c):
    trip, snack = _create_trip_with_snack(c)

    response = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "teleport",
            "source_type": "snack",
            "source_id": snack["id"],
            "servings": 1,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown daily-plan slot: teleport"


def test_rest_rejects_assignment_source_not_on_trip(c):
    trip, _ = _create_trip_with_snack(c)

    response = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "afternoon_snacks",
            "source_type": "snack",
            "source_id": 999,
            "servings": 1,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Snack source is not on this trip"


def test_rest_rejects_nonpositive_assignment_servings(c):
    trip, snack = _create_trip_with_snack(c)

    response = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "afternoon_snacks",
            "source_type": "snack",
            "source_id": snack["id"],
            "servings": -1,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Assignment servings must be greater than zero"


def test_rest_rejects_assignment_beyond_selected_inventory(c):
    trip, snack = _create_trip_with_snack(c)

    response = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "afternoon_snacks",
            "source_type": "snack",
            "source_id": snack["id"],
            "servings": 2,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Cannot allocate 2 servings; only 1 is available"


def test_rest_rejects_assignment_update_beyond_selected_inventory(c):
    trip, snack = _create_trip_with_snack(c)
    plan = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "afternoon_snacks",
            "source_type": "snack",
            "source_id": snack["id"],
            "servings": 1,
        },
    ).json()
    assignment_id = plan["days"][0]["items"][0]["id"]

    response = c.patch(
        f"/api/trips/{trip['id']}/daily-plan/assignments/{assignment_id}",
        json={"servings": 2},
    )

    assert response.status_code == 422
    current = c.get(f"/api/trips/{trip['id']}/daily-plan").json()
    assert current["days"][0]["items"][0]["servings"] == 1


def test_rest_clone_preserves_inventory_and_uses_unique_names(c):
    trip, meal = _create_trip_with_breakfast(c)

    first = c.post(f"/api/trips/{trip['id']}/clone")
    second = c.post(f"/api/trips/{trip['id']}/clone")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["name"] == "Plan (copy)"
    assert second.json()["name"] == "Plan (copy 2)"
    assert first.json()["meals"][0]["recipe_id"] == meal["recipe_id"]
    assert second.json()["meals"][0]["quantity"] == 1


def test_rest_can_move_assignment_to_another_day_and_slot(c):
    trip, snack = _create_trip_with_snack(c)
    c.put(f"/api/trips/{trip['id']}", json={"full_days": 2})
    plan = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "afternoon_snacks",
            "source_type": "snack",
            "source_id": snack["id"],
            "servings": 1,
        },
    ).json()
    assignment_id = plan["days"][0]["items"][0]["id"]

    response = c.patch(
        f"/api/trips/{trip['id']}/daily-plan/assignments/{assignment_id}",
        json={"day_number": 2, "slot": "morning_snacks"},
    )

    assert response.status_code == 200
    moved = response.json()["days"][1]["items"][0]
    assert moved["id"] == assignment_id
    assert moved["slot"] == "morning_snacks"


def test_rest_can_delete_daily_assignment(c):
    trip, snack = _create_trip_with_snack(c)
    plan = c.post(
        f"/api/trips/{trip['id']}/daily-plan/assignments",
        json={
            "day_number": 1,
            "slot": "afternoon_snacks",
            "source_type": "snack",
            "source_id": snack["id"],
            "servings": 1,
        },
    ).json()
    assignment_id = plan["days"][0]["items"][0]["id"]

    response = c.delete(
        f"/api/trips/{trip['id']}/daily-plan/assignments/{assignment_id}"
    )

    assert response.status_code == 200
    assert response.json()["days"][0]["items"] == []
    assert response.json()["unallocated"][0]["remaining_servings"] == 1


def test_rest_rejects_negative_meal_quantity(c):
    trip, meal = _create_trip_with_breakfast(c)

    response = c.post(
        f"/api/trips/{trip['id']}/meals",
        json={"recipe_id": meal["recipe_id"], "quantity": -1},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Meal quantity must be greater than zero"


def test_rest_rejects_negative_snack_servings(c):
    trip, snack = _create_trip_with_snack(c)

    response = c.put(
        f"/api/trips/{trip['id']}/snacks/{snack['id']}",
        json={"servings": -1},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Snack servings cannot be negative"
