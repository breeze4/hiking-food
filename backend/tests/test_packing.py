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


NUTS_CAL_PER_OZ = 183.0
CANDY_CAL_PER_OZ = 138.0


def _ingredient(c, name, **fields):
    resp = c.post("/api/ingredients", json={"name": name, **fields})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bag(c, name, composition):
    resp = c.post("/api/snack-unit-types", json={
        "name": name,
        "composition": [
            {"ingredient_id": ingredient_id, "amount_oz": amount_oz}
            for ingredient_id, amount_oz in composition
        ],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _trail_mix_bag(c, name="Trail Mix Bag", nuts_oz=1.0, candy_oz=1.0):
    nuts = _ingredient(c, f"Almonds for {name}", calories_per_oz=NUTS_CAL_PER_OZ)
    candy = _ingredient(c, f"M&Ms for {name}", calories_per_oz=CANDY_CAL_PER_OZ)
    return _bag(c, name, [(nuts["id"], nuts_oz), (candy["id"], candy_oz)])


def _structured_trip(c, name="Olympics 2026", snack_config=None):
    resp = c.post("/api/trips", json={
        "name": name, "first_day_fraction": 0.5,
        "full_days": 2, "last_day_fraction": 0.5,
    })
    assert resp.status_code == 201, resp.text
    trip = resp.json()
    assert trip["snack_model"] == "structured"
    if snack_config:
        assert c.put(
            f"/api/trips/{trip['id']}", json=snack_config,
        ).status_code == 200
    return trip


def _add_unit(c, trip_id, **payload):
    resp = c.post(f"/api/trips/{trip_id}/snack-units", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _units(c, trip_id):
    return c.get(f"/api/trips/{trip_id}/packing").json()["units"]


class TestUnitAssembly:
    """The units section reads as "make N x <type> @ <target> oz"."""

    def test_a_bag_reports_its_count_target_and_derived_weight(self, c):
        trip = _structured_trip(c)
        bag = _trail_mix_bag(c)
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)

        group = _units(c, trip["id"])[0]

        assert group["kind"] == "bag"
        assert group["name"] == "Trail Mix Bag"
        assert group["count"] == 6
        assert group["target_weight"] == 2.0  # the trip's oz_per_snack
        assert group["unit_weight"] == 2.0  # what the composition derives
        assert group["total_weight"] == 12.0
        assert group["packed"] is False
        assert group["actual_weight_oz"] is None

    def test_a_bag_lists_what_goes_into_it(self, c):
        trip = _structured_trip(c)
        bag = _trail_mix_bag(c, nuts_oz=1.2, candy_oz=0.8)
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)

        group = _units(c, trip["id"])[0]

        assert group["composition"] == [
            {"ingredient_name": "Almonds for Trail Mix Bag", "amount_oz": 1.2},
            {"ingredient_name": "M&Ms for Trail Mix Bag", "amount_oz": 0.8},
        ]

    def test_selections_of_the_same_type_pack_as_one_group(self, c):
        trip = _structured_trip(c)
        bag = _trail_mix_bag(c)
        first = _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=4)
        second = _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=2)

        units = _units(c, trip["id"])

        assert len(units) == 1
        assert units[0]["count"] == 6
        assert [s["id"] for s in units[0]["selections"]] == [first["id"], second["id"]]

    def test_a_packaged_unit_packs_under_its_catalog_item(self, c):
        trip = _structured_trip(c)
        ingredient = _ingredient(c, "Energy Bar", calories_per_oz=125)
        item = c.post("/api/snacks", json={
            "ingredient_id": ingredient["id"], "weight_per_serving": 2.0,
            "calories_per_serving": 250, "category": "bars_energy",
        }).json()
        _add_unit(c, trip["id"], catalog_item_id=item["id"], quantity=5)

        group = _units(c, trip["id"])[0]

        assert group["kind"] == "packaged"
        assert group["catalog_item_id"] == item["id"]
        assert group["unit_type_id"] is None
        assert group["name"] == "Energy Bar"
        assert group["count"] == 5
        assert group["unit_calories"] == 250
        assert group["composition"] == []

    def test_a_bag_off_the_trip_target_is_flagged(self, c):
        trip = _structured_trip(c, snack_config={"oz_per_snack": 3.0})
        bag = _trail_mix_bag(c)  # 2 oz against a 3 oz target
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)

        group = _units(c, trip["id"])[0]

        assert group["target_weight"] == 3.0
        assert group["weight_warning"] is True

    def test_packing_a_unit_records_its_actual_weight(self, c):
        trip = _structured_trip(c)
        bag = _trail_mix_bag(c)
        unit = _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)
        assert c.put(
            f"/api/trips/{trip['id']}/snack-units/{unit['id']}",
            json={"packed": True, "actual_weight_oz": 2.1},
        ).status_code == 200

        group = _units(c, trip["id"])[0]

        assert group["packed"] is True
        assert group["actual_weight_oz"] == 2.1
        assert group["selections"] == [{
            "id": unit["id"], "quantity": 6,
            "packed": True, "actual_weight_oz": 2.1,
        }]

    def test_a_structured_trip_without_selections_has_an_empty_checklist(self, c):
        trip = _structured_trip(c)

        assert _units(c, trip["id"]) == []


LEGACY_PACKING_SNAPSHOT = {
    "trip_name": "Legacy Plan",
    "meals": [
        {
            "id": 1,
            "recipe_name": "Breakfast",
            "category": "breakfast",
            "quantity": 4,
            "at_home_prep": None,
            "ingredients": [
                {
                    "name": "Granola", "amount_oz": 4.0, "total_oz": 16.0,
                    "essentials": False, "packing_method": "bag",
                },
            ],
            "packed": False,
            "actual_weight_oz": None,
        },
    ],
    "snacks": [
        {
            "id": 1,
            "ingredient_name": "Nuts",
            "slot": "lunch",
            "target_weight": 2.0,
            "target_calories": 366.0,
            "servings": 2.0,
            "packed": False,
            "actual_weight_oz": None,
            "packing_method": "bag",
        },
    ],
}


def _legacy_trip_with_a_meal_and_a_snack(c):
    """The fixture behind the snapshot, built exactly as it was on capture."""
    granola = _ingredient(c, "Granola", calories_per_oz=130, packing_method="bag")
    nuts = _ingredient(c, "Nuts", calories_per_oz=183, packing_method="bag")
    recipe = c.post("/api/recipes", json={
        "name": "Breakfast", "category": "breakfast",
        "ingredients": [{"ingredient_id": granola["id"], "amount_oz": 4}],
    }).json()
    item = c.post("/api/snacks", json={
        "ingredient_id": nuts["id"], "weight_per_serving": 1.0,
        "calories_per_serving": 183, "category": "lunch",
    }).json()
    trip = c.post("/api/trips", json={
        "name": "Legacy Plan", "first_day_fraction": 0, "full_days": 4,
    }).json()
    assert c.put(
        f"/api/trips/{trip['id']}", json={"snack_model": "legacy"},
    ).status_code == 200
    c.post(f"/api/trips/{trip['id']}/meals", json={
        "recipe_id": recipe["id"], "quantity": 4,
    })
    c.post(f"/api/trips/{trip['id']}/snacks", json={
        "catalog_item_id": item["id"], "servings": 2, "slot": "lunch",
    })
    return trip


def test_a_legacy_trip_packing_matches_the_pre_change_snapshot(c):
    """Captured from the pre-change tree; units must not disturb it.

    The units section is absent, not empty: a legacy trip's packing detail keeps
    exactly the keys it had.
    """
    trip = _legacy_trip_with_a_meal_and_a_snack(c)

    packing = c.get(f"/api/trips/{trip['id']}/packing").json()

    assert packing == LEGACY_PACKING_SNAPSHOT
    assert "units" not in packing
