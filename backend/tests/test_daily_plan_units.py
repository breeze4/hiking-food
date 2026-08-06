"""Daily plan on structured trips: unit distribution, assignments, legacy parity."""
import pytest

from database import Base
from models import Ingredient, Recipe, RecipeIngredient, SnackCatalogItem


@pytest.fixture(autouse=True)
def db_setup(test_engine, test_session):
    Base.metadata.create_all(bind=test_engine)
    db = test_session()

    # Macros are stated and calories derived (4/9/4), matching the ingredients
    # router, so a unit's calories are reproducible from its composition.
    almonds = Ingredient(name="Almonds", protein_per_oz=6.0, fat_per_oz=15.0,
                         carb_per_oz=6.0, calories_per_oz=183.0)
    candy = Ingredient(name="M&Ms", protein_per_oz=1.0, fat_per_oz=6.0,
                       carb_per_oz=20.0, calories_per_oz=138.0)
    jerky = Ingredient(name="Jerky", protein_per_oz=14.0, fat_per_oz=2.0,
                       carb_per_oz=3.0, calories_per_oz=86.0)
    oats = Ingredient(name="Oats", calories_per_oz=110)
    rice = Ingredient(name="Rice", calories_per_oz=100)
    crackers = Ingredient(name="Crackers", calories_per_oz=130)
    electrolytes = Ingredient(name="Electrolytes", calories_per_oz=10)
    for ingredient in [almonds, candy, jerky, oats, rice, crackers, electrolytes]:
        db.add(ingredient)
    db.flush()

    breakfast = Recipe(name="Oatmeal", category="breakfast")
    dinner = Recipe(name="Rice Bowl", category="dinner")
    db.add(breakfast)
    db.add(dinner)
    db.flush()
    db.add(RecipeIngredient(recipe_id=breakfast.id, ingredient_id=oats.id, amount_oz=3.0))
    db.add(RecipeIngredient(recipe_id=dinner.id, ingredient_id=rice.id, amount_oz=5.0))

    db.add(SnackCatalogItem(ingredient_id=candy.id, weight_per_serving=2.0,
                            calories_per_serving=250, category="bars_energy"))
    db.add(SnackCatalogItem(ingredient_id=crackers.id, weight_per_serving=1.0,
                            calories_per_serving=130, category="lunch"))
    db.add(SnackCatalogItem(ingredient_id=almonds.id, weight_per_serving=1.5,
                            calories_per_serving=275, category="salty"))
    db.add(SnackCatalogItem(ingredient_id=electrolytes.id, weight_per_serving=0.3,
                            calories_per_serving=10, category="drink_mix",
                            drink_mix_type="all_day"))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


NUT_BAG_CALORIES = 366.0  # 2 oz almonds
CANDY_BAG_CALORIES = 321.0  # 1 oz almonds + 1 oz M&Ms
JERKY_BAG_CALORIES = 129.0  # 1.5 oz jerky


def _ingredient_id(c, name):
    for row in c.get("/api/ingredients").json():
        if row["name"] == name:
            return row["id"]
    raise RuntimeError(f"Ingredient {name} not found")


def _catalog_id(c, name):
    for row in c.get("/api/snacks").json():
        if row["ingredient_name"] == name:
            return row["id"]
    raise RuntimeError(f"Snack {name} not found")


def _recipe_id(c, name):
    for row in c.get("/api/recipes").json():
        if row["name"] == name:
            return row["id"]
    raise RuntimeError(f"Recipe {name} not found")


def _bag(c, name, composition):
    resp = c.post("/api/snack-unit-types", json={
        "name": name,
        "composition": [
            {"ingredient_id": _ingredient_id(c, ingredient), "amount_oz": amount_oz}
            for ingredient, amount_oz in composition
        ],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bags(c):
    """The three library bags, heaviest first: 2 oz, 2 oz, 1.5 oz."""
    return (
        _bag(c, "Nut Bag", [("Almonds", 2.0)]),
        _bag(c, "Candy Bag", [("Almonds", 1.0), ("M&Ms", 1.0)]),
        _bag(c, "Jerky Bag", [("Jerky", 1.5)]),
    )


def _trip(c, name="Olympics 2026", snack_config=None, **fields):
    """A structured trip: 0.5 + 2 + 0.5 days at the 4 x 2 oz default."""
    payload = {
        "name": name,
        "first_day_fraction": 0.5,
        "full_days": 2,
        "last_day_fraction": 0.5,
        "drink_mixes_per_day": 0,
        **fields,
    }
    resp = c.post("/api/trips", json=payload)
    assert resp.status_code == 201, resp.text
    trip = resp.json()
    if snack_config:
        resp = c.put(f"/api/trips/{trip['id']}", json=snack_config)
        assert resp.status_code == 200, resp.text
        trip = resp.json()
    return trip


def _legacy_trip(c, name="Legacy Trip", **fields):
    trip = _trip(c, name=name, **fields)
    resp = c.put(f"/api/trips/{trip['id']}", json={"snack_model": "legacy"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _add_unit(c, trip_id, expected_status=201, **payload):
    resp = c.post(f"/api/trips/{trip_id}/snack-units", json=payload)
    assert resp.status_code == expected_status, resp.text
    return resp.json() if resp.content else None


def _add_snack(c, trip_id, name, servings, slot=None):
    payload = {"catalog_item_id": _catalog_id(c, name), "servings": servings}
    if slot:
        payload["slot"] = slot
    resp = c.post(f"/api/trips/{trip_id}/snacks", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _add_meal(c, trip_id, recipe_name, quantity=1):
    resp = c.post(f"/api/trips/{trip_id}/meals", json={
        "recipe_id": _recipe_id(c, recipe_name), "quantity": quantity,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _autofill(c, trip_id):
    resp = c.post(f"/api/trips/{trip_id}/daily-plan/auto-fill")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _get_plan(c, trip_id):
    resp = c.get(f"/api/trips/{trip_id}/daily-plan")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _unit_counts(plan):
    """Units placed per (day_number, slot), counting servings."""
    counts = {}
    for day in plan["days"]:
        for item in day["items"]:
            if item["source_type"] != "snack_unit":
                continue
            key = (day["day_number"], item["slot"])
            counts[key] = counts.get(key, 0) + item["servings"]
    return counts


def _split_by_day(plan):
    """(morning, afternoon) unit counts for every day, in day order."""
    counts = _unit_counts(plan)
    return [
        (counts.get((day["day_number"], "morning_snacks"), 0),
         counts.get((day["day_number"], "afternoon_snacks"), 0))
        for day in plan["days"]
    ]


def _names_on_day(plan, day_number, slot=None):
    for day in plan["days"]:
        if day["day_number"] != day_number:
            continue
        return [
            item["name"] for item in day["items"]
            if slot is None or item["slot"] == slot
        ]
    return []


def _plan_shape(plan):
    """Auto-fill output reduced to what the algorithm decides."""
    return {
        "days": [
            (
                day["day_number"],
                sorted(
                    (item["slot"], item["name"], item["servings"],
                     item["calories"], item["weight"])
                    for item in day["items"]
                ),
            )
            for day in plan["days"]
        ],
        "unallocated": sorted(
            (item["source_type"], item["name"], item["remaining_servings"])
            for item in plan["unallocated"]
        ),
        "warnings": sorted(plan["warnings"]),
    }


class TestUnitDistribution:
    def test_a_full_quota_fills_two_units_per_slot_scaled_on_partial_days(self, c):
        """0.5 + 2 + 0.5 at 4/day: 1 + 1 on the half days, 2 + 2 on the full ones."""
        trip = _trip(c)
        for bag in _bags(c):
            _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=4)

        plan = _autofill(c, trip["id"])

        assert _split_by_day(plan) == [(1, 1), (2, 2), (2, 2), (1, 1)]
        assert plan["unallocated"] == []

    def test_each_day_draws_from_a_spread_of_unit_types(self, c):
        """Round-robin dealing, so a day is not four of the same bag."""
        trip = _trip(c)
        for bag in _bags(c):
            _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=4)

        plan = _autofill(c, trip["id"])

        assert set(_names_on_day(plan, 2)) == {"Nut Bag", "Candy Bag", "Jerky Bag"}
        for day in plan["days"]:
            names = [item["name"] for item in day["items"]]
            assert len(set(names)) >= min(2, len(names))

    def test_an_odd_quota_favors_the_morning_slot(self, c):
        """A 3-unit day splits 2 + 1, not 1 + 2."""
        trip = _trip(
            c,
            first_day_fraction=0.5, full_days=0, last_day_fraction=0,
            snack_config={"snacks_per_day": 5},
        )
        nut_bag, candy_bag, _ = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=2)
        _add_unit(c, trip["id"], unit_type_id=candy_bag["id"], quantity=1)

        plan = _autofill(c, trip["id"])

        assert _split_by_day(plan) == [(2, 1)]

    def test_over_quota_units_spill_evenly_across_the_days(self, c):
        """16 units against a 12-unit quota: every day carries one more."""
        trip = _trip(c)
        nut_bag, candy_bag, jerky_bag = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=6)
        _add_unit(c, trip["id"], unit_type_id=candy_bag["id"], quantity=6)
        _add_unit(c, trip["id"], unit_type_id=jerky_bag["id"], quantity=4)

        plan = _autofill(c, trip["id"])

        per_day = [morning + afternoon for morning, afternoon in _split_by_day(plan)]
        assert per_day == [3, 5, 5, 3]
        assert sum(per_day) == 16
        assert plan["unallocated"] == []

    def test_under_quota_units_leave_the_later_slots_empty(self, c):
        """5 units against a 12-unit quota: days 3 and 4 get nothing, and
        nothing is left over either."""
        trip = _trip(c)
        nut_bag, candy_bag, _ = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=3)
        _add_unit(c, trip["id"], unit_type_id=candy_bag["id"], quantity=2)

        plan = _autofill(c, trip["id"])

        assert _split_by_day(plan) == [(1, 1), (2, 1), (0, 0), (0, 0)]
        assert plan["unallocated"] == []

    def test_a_packaged_unit_distributes_like_a_bag(self, c):
        trip = _trip(c)
        _add_unit(c, trip["id"], catalog_item_id=_catalog_id(c, "M&Ms"), quantity=4)

        plan = _autofill(c, trip["id"])

        assert _split_by_day(plan) == [(1, 1), (1, 1), (0, 0), (0, 0)]
        assert _names_on_day(plan, 1) == ["M&Ms", "M&Ms"]

    def test_lunch_snacks_and_drink_mixes_still_flow_on_a_structured_trip(self, c):
        trip = _trip(c, drink_mixes_per_day=2)
        nut_bag, _, _ = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=4)
        _add_snack(c, trip["id"], "Crackers", 3)
        _add_snack(c, trip["id"], "Electrolytes", 4)

        plan = _autofill(c, trip["id"])

        lunch = [(day["day_number"], item["slot"]) for day in plan["days"]
                 for item in day["items"] if item["name"] == "Crackers"]
        assert lunch == [(1, "lunch"), (2, "lunch"), (3, "lunch")]
        drinks = sorted(day["day_number"] for day in plan["days"]
                        for item in day["items"] if item["name"] == "Electrolytes")
        assert drinks == [1, 2, 3, 4]

    def test_a_legacy_snack_row_stays_out_of_the_unit_slots(self, c):
        """Only units fill morning/afternoon snacks on a structured trip; a
        snack the user moved into the slot waits in the unallocated pool."""
        trip = _trip(c)
        nut_bag, _, _ = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=4)
        _add_snack(c, trip["id"], "Almonds", 3)

        plan = _autofill(c, trip["id"])

        assigned = [item["name"] for day in plan["days"] for item in day["items"]]
        assert "Almonds" not in assigned
        leftover = [item for item in plan["unallocated"] if item["name"] == "Almonds"]
        assert leftover and leftover[0]["remaining_servings"] == 3

    def test_units_never_reach_a_legacy_trip(self, c):
        """A legacy trip keeps distributing TripSnack rows into the snack slots."""
        trip = _legacy_trip(c)
        _add_snack(c, trip["id"], "Almonds", 3)

        plan = _autofill(c, trip["id"])

        slots = {item["slot"] for day in plan["days"] for item in day["items"]}
        assert slots == {"afternoon_snacks"}
        assert all(
            item["source_type"] == "snack"
            for day in plan["days"] for item in day["items"]
        )


class TestUnitAssignments:
    def test_a_unit_assignment_reports_its_name_weight_and_calories(self, c):
        trip = _trip(c)
        nut_bag, _, _ = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=4)

        plan = _autofill(c, trip["id"])
        item = next(
            item for day in plan["days"] for item in day["items"]
            if item["source_type"] == "snack_unit"
        )

        assert item["name"] == "Nut Bag"
        assert item["weight"] == 2.0
        assert item["calories"] == NUT_BAG_CALORIES
        assert item["servings"] == 1

    def test_a_unit_assignment_round_trips_through_the_endpoints(self, c):
        trip = _trip(c)
        nut_bag, _, _ = _bags(c)
        selection = _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=3)

        added = c.post(f"/api/trips/{trip['id']}/daily-plan/assignments", json={
            "day_number": 2,
            "slot": "morning_snacks",
            "source_type": "snack_unit",
            "source_id": selection["id"],
            "servings": 1,
        })
        assert added.status_code == 201, added.text
        assert _unit_counts(added.json()) == {(2, "morning_snacks"): 1}

        assignment = next(
            item for day in added.json()["days"] for item in day["items"]
        )
        patched = c.patch(
            f"/api/trips/{trip['id']}/daily-plan/assignments/{assignment['id']}",
            json={"servings": 2, "slot": "afternoon_snacks"},
        )
        assert patched.status_code == 200, patched.text
        assert _unit_counts(patched.json()) == {(2, "afternoon_snacks"): 2}

        removed = c.delete(
            f"/api/trips/{trip['id']}/daily-plan/assignments/{assignment['id']}"
        )
        assert removed.status_code == 200, removed.text
        assert _unit_counts(removed.json()) == {}

    def test_removing_a_unit_assignment_returns_it_to_the_unallocated_pool(self, c):
        trip = _trip(c)
        nut_bag, _, _ = _bags(c)
        selection = _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=4)

        plan = _autofill(c, trip["id"])
        assert plan["unallocated"] == []
        assignment = next(
            item for day in plan["days"] for item in day["items"]
        )

        resp = c.delete(
            f"/api/trips/{trip['id']}/daily-plan/assignments/{assignment['id']}"
        )
        assert resp.status_code == 200, resp.text
        pool = resp.json()["unallocated"]

        assert len(pool) == 1
        assert pool[0]["source_type"] == "snack_unit"
        assert pool[0]["source_id"] == selection["id"]
        assert pool[0]["name"] == "Nut Bag"
        assert pool[0]["remaining_servings"] == 1
        assert pool[0]["weight_per_serving"] == 2.0
        assert pool[0]["calories_per_serving"] == NUT_BAG_CALORIES

    def test_a_unit_cannot_be_allocated_past_its_selected_quantity(self, c):
        trip = _trip(c)
        nut_bag, _, _ = _bags(c)
        selection = _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=2)

        resp = c.post(f"/api/trips/{trip['id']}/daily-plan/assignments", json={
            "day_number": 1,
            "slot": "morning_snacks",
            "source_type": "snack_unit",
            "source_id": selection["id"],
            "servings": 3,
        })

        assert resp.status_code == 422
        assert resp.json()["detail"] == (
            "Cannot allocate 3 servings; only 2 is available"
        )

    def test_a_unit_from_another_trip_is_not_on_this_trip(self, c):
        other = _trip(c, name="Other Trip")
        nut_bag, _, _ = _bags(c)
        selection = _add_unit(c, other["id"], unit_type_id=nut_bag["id"], quantity=2)
        trip = _trip(c)

        resp = c.post(f"/api/trips/{trip['id']}/daily-plan/assignments", json={
            "day_number": 1,
            "slot": "morning_snacks",
            "source_type": "snack_unit",
            "source_id": selection["id"],
            "servings": 1,
        })

        assert resp.status_code == 422
        assert resp.json()["detail"] == "Snack unit source is not on this trip"

    def test_unit_macros_roll_into_the_day_totals(self, c):
        trip = _trip(c)
        nut_bag, _, _ = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=2)

        plan = _autofill(c, trip["id"])
        day = plan["days"][0]

        # One 2 oz almond bag per slot: 12 g protein, 30 g fat, 12 g carb each.
        assert day["macros"]["protein_g"] == 24.0
        assert day["macros"]["fat_g"] == 60.0
        assert day["macros"]["carb_g"] == 24.0
        assert day["macros"]["coverage_pct"] == 100.0

    def test_changing_the_unit_inventory_clears_the_plan(self, c):
        trip = _trip(c)
        nut_bag, candy_bag, _ = _bags(c)
        _add_unit(c, trip["id"], unit_type_id=nut_bag["id"], quantity=4)
        _autofill(c, trip["id"])

        _add_unit(c, trip["id"], unit_type_id=candy_bag["id"], quantity=2)

        plan = _get_plan(c, trip["id"])
        assert all(day["items"] == [] for day in plan["days"])


# Captured by running this fixture against the pre-change tree: the legacy
# auto-fill path must be byte-identical after the structured branch lands.
LEGACY_AUTOFILL_SNAPSHOT = {
    "days": [
        (1, [
            ("afternoon_snacks", "Almonds", 1.0, 275.0, 1.5),
            ("afternoon_snacks", "M&Ms", 2.0, 500.0, 4.0),
            ("all_day_drinks", "Electrolytes", 1.0, 10.0, 0.3),
            ("dinner", "Rice Bowl", 1.0, 500.0, 5.0),
            ("lunch", "Crackers", 1.0, 130.0, 1.0),
        ]),
        (2, [
            ("afternoon_snacks", "Almonds", 2.0, 550.0, 3.0),
            ("afternoon_snacks", "M&Ms", 1.0, 250.0, 2.0),
            ("all_day_drinks", "Electrolytes", 1.0, 10.0, 0.3),
            ("breakfast", "Oatmeal", 1.0, 330.0, 3.0),
            ("dinner", "Rice Bowl", 1.0, 500.0, 5.0),
            ("lunch", "Crackers", 1.0, 130.0, 1.0),
        ]),
        (3, [
            ("afternoon_snacks", "Almonds", 2.0, 550.0, 3.0),
            ("afternoon_snacks", "M&Ms", 1.0, 250.0, 2.0),
            ("all_day_drinks", "Electrolytes", 1.0, 10.0, 0.3),
            ("breakfast", "Oatmeal", 1.0, 330.0, 3.0),
            ("dinner", "Rice Bowl", 1.0, 500.0, 5.0),
            ("lunch", "Crackers", 1.0, 130.0, 1.0),
        ]),
        (4, [("breakfast", "Oatmeal", 1.0, 330.0, 3.0)]),
    ],
    "unallocated": [("meal", "Rice Bowl", 1.0)],
    "warnings": [
        "Not enough all-day drink mixes to cover all 4 eligible days "
        "(3.0 available)"
    ],
}


def test_a_legacy_trip_auto_fill_matches_the_pre_change_snapshot(c):
    trip = _legacy_trip(c, drink_mixes_per_day=2)
    _add_meal(c, trip["id"], "Oatmeal", quantity=3)
    _add_meal(c, trip["id"], "Rice Bowl", quantity=4)
    _add_snack(c, trip["id"], "Almonds", 5)
    _add_snack(c, trip["id"], "M&Ms", 4)
    _add_snack(c, trip["id"], "Crackers", 3)
    _add_snack(c, trip["id"], "Electrolytes", 3)

    plan = _autofill(c, trip["id"])

    assert _plan_shape(plan) == LEGACY_AUTOFILL_SNAPSHOT
