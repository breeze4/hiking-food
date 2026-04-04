"""Tests for daily plan auto-fill algorithm."""
import pytest
from database import Base
from models import Ingredient, SnackCatalogItem, Recipe, RecipeIngredient


@pytest.fixture(autouse=True)
def db_setup(test_engine, test_session):
    Base.metadata.create_all(bind=test_engine)
    db = test_session()

    # Ingredients
    oats = Ingredient(name="Oats", calories_per_oz=110)
    rice = Ingredient(name="Rice", calories_per_oz=100)
    beans = Ingredient(name="Beans", calories_per_oz=95)
    cheese = Ingredient(name="Cheese", calories_per_oz=110)
    crackers = Ingredient(name="Crackers", calories_per_oz=130)
    salami = Ingredient(name="Salami", calories_per_oz=150)
    nuts = Ingredient(name="Mixed Nuts", calories_per_oz=160)
    coffee = Ingredient(name="Coffee Mix", calories_per_oz=50)
    tea = Ingredient(name="Tea Packets", calories_per_oz=0)
    electrolytes = Ingredient(name="Electrolytes", calories_per_oz=10)
    for ing in [oats, rice, beans, cheese, crackers, salami, nuts, coffee, tea, electrolytes]:
        db.add(ing)
    db.flush()

    # Recipes: breakfast and dinner
    # Oatmeal: 3oz oats = lighter breakfast
    r1 = Recipe(name="Oatmeal", category="breakfast")
    db.add(r1)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r1.id, ingredient_id=oats.id, amount_oz=3.0))

    # Rice & Beans: 4oz rice + 2oz beans = heavier dinner (6oz)
    r2 = Recipe(name="Rice & Beans", category="dinner")
    db.add(r2)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r2.id, ingredient_id=rice.id, amount_oz=4.0))
    db.add(RecipeIngredient(recipe_id=r2.id, ingredient_id=beans.id, amount_oz=2.0))

    # Cheese Quesadilla: 4oz cheese = heavier dinner (4oz but same category)
    r3 = Recipe(name="Cheese Quesadilla", category="dinner")
    db.add(r3)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r3.id, ingredient_id=cheese.id, amount_oz=4.0))

    # Snack catalog items
    db.add(SnackCatalogItem(ingredient_id=crackers.id, weight_per_serving=1.0,
                            calories_per_serving=130, category="lunch"))
    db.add(SnackCatalogItem(ingredient_id=salami.id, weight_per_serving=1.5,
                            calories_per_serving=225, category="lunch"))
    db.add(SnackCatalogItem(ingredient_id=nuts.id, weight_per_serving=2.0,
                            calories_per_serving=320, category="salty"))
    # Drink mixes
    db.add(SnackCatalogItem(ingredient_id=coffee.id, weight_per_serving=0.5,
                            calories_per_serving=25, category="drink_mix",
                            drink_mix_type="breakfast"))
    db.add(SnackCatalogItem(ingredient_id=tea.id, weight_per_serving=0.1,
                            calories_per_serving=0, category="drink_mix",
                            drink_mix_type="dinner"))
    db.add(SnackCatalogItem(ingredient_id=electrolytes.id, weight_per_serving=0.3,
                            calories_per_serving=10, category="drink_mix",
                            drink_mix_type="all_day"))

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_trip(c, **overrides):
    payload = {
        "name": "Test Trip", "first_day_fraction": 0.5,
        "full_days": 2, "last_day_fraction": 0.5,
        "drink_mixes_per_day": 2,
    }
    payload.update(overrides)
    resp = c.post("/api/trips", json=payload)
    assert resp.status_code == 201
    return resp.json()


def _get_recipe_id(c, name):
    for r in c.get("/api/recipes").json():
        if r["name"] == name:
            return r["id"]
    raise RuntimeError(f"Recipe {name} not found")


def _get_catalog_id(c, name):
    for s in c.get("/api/snacks").json():
        if s["ingredient_name"] == name:
            return s["id"]
    raise RuntimeError(f"Snack {name} not found")


def _add_meal(c, trip_id, recipe_name, quantity=1):
    rid = _get_recipe_id(c, recipe_name)
    resp = c.post(f"/api/trips/{trip_id}/meals", json={"recipe_id": rid, "quantity": quantity})
    assert resp.status_code == 201
    return resp.json()


def _add_snack(c, trip_id, name, servings):
    cid = _get_catalog_id(c, name)
    resp = c.post(f"/api/trips/{trip_id}/snacks", json={"catalog_item_id": cid, "servings": servings})
    assert resp.status_code == 201
    return resp.json()


def _autofill(c, trip_id):
    resp = c.post(f"/api/trips/{trip_id}/daily-plan/auto-fill")
    assert resp.status_code == 200
    return resp.json()


def _get_plan(c, trip_id):
    resp = c.get(f"/api/trips/{trip_id}/daily-plan")
    assert resp.status_code == 200
    return resp.json()


def _day_items(plan, day_number, slot=None):
    for d in plan["days"]:
        if d["day_number"] == day_number:
            items = d["items"]
            if slot:
                items = [i for i in items if i["slot"] == slot]
            return items
    return []


# --- Meal Distribution Tests ---

def test_meals_distributed_to_correct_slots(c):
    """Breakfast meals go to breakfast slot, dinners to dinner slot."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Oatmeal", quantity=3)
    _add_meal(c, trip["id"], "Rice & Beans", quantity=3)

    plan = _autofill(c, trip["id"])
    # 4 days (0.5 + 2 + 0.5), breakfast eligible on days 2,3,4 (not first partial)
    breakfast_items = []
    dinner_items = []
    for d in plan["days"]:
        for item in d["items"]:
            if item["slot"] == "breakfast":
                breakfast_items.append((d["day_number"], item["name"]))
            elif item["slot"] == "dinner":
                dinner_items.append((d["day_number"], item["name"]))

    # Breakfast on days 2, 3, 4 (3 eligible)
    assert len(breakfast_items) == 3
    assert all(d >= 2 for d, _ in breakfast_items)

    # Dinner on days 1, 2, 3 (3 eligible, not last partial)
    assert len(dinner_items) == 3
    assert all(d <= 3 for d, _ in dinner_items)


def test_meals_heaviest_first(c):
    """Heavier meals assigned to earlier eligible days."""
    trip = _create_trip(c)
    # Rice & Beans = 6oz, Cheese Quesadilla = 4oz
    _add_meal(c, trip["id"], "Rice & Beans", quantity=2)
    _add_meal(c, trip["id"], "Cheese Quesadilla", quantity=1)

    plan = _autofill(c, trip["id"])
    dinner_by_day = {}
    for d in plan["days"]:
        for item in d["items"]:
            if item["slot"] == "dinner":
                dinner_by_day[d["day_number"]] = item["name"]

    # Day 1 (first eligible for dinner) should get heaviest: Rice & Beans
    assert dinner_by_day.get(1) == "Rice & Beans"


def test_meal_quantity_spread_across_days(c):
    """A meal with quantity 3 gets 1 serving per day across 3 days."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Oatmeal", quantity=3)

    plan = _autofill(c, trip["id"])
    bkf_days = [d["day_number"] for d in plan["days"]
                for item in d["items"] if item["slot"] == "breakfast"]
    # 3 breakfasts across eligible days (2, 3, 4)
    assert len(bkf_days) == 3
    assert sorted(bkf_days) == [2, 3, 4]


# --- Partial Day Tests ---

def test_first_partial_no_breakfast(c):
    """First partial day should not get breakfast or morning items."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Oatmeal", quantity=4)

    plan = _autofill(c, trip["id"])
    day1_breakfast = _day_items(plan, 1, "breakfast")
    assert len(day1_breakfast) == 0


def test_last_partial_no_dinner(c):
    """Last partial day should not get dinner or afternoon items."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Rice & Beans", quantity=4)

    plan = _autofill(c, trip["id"])
    day4_dinner = _day_items(plan, 4, "dinner")
    assert len(day4_dinner) == 0


def test_first_partial_gets_dinner(c):
    """First partial day should get dinner (arrives afternoon, eats dinner)."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Rice & Beans", quantity=3)

    plan = _autofill(c, trip["id"])
    day1_dinner = _day_items(plan, 1, "dinner")
    assert len(day1_dinner) == 1


def test_last_partial_gets_breakfast(c):
    """Last partial day should get breakfast (wakes up, eats, hikes out)."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Oatmeal", quantity=3)

    plan = _autofill(c, trip["id"])
    # Day 4 is last partial
    day4_breakfast = _day_items(plan, 4, "breakfast")
    assert len(day4_breakfast) == 1


# --- Snack Distribution Tests ---

def test_snacks_1_per_day(c):
    """Each snack gets 1 serving per eligible day until servings run out."""
    trip = _create_trip(c)
    _add_snack(c, trip["id"], "Mixed Nuts", 3)

    plan = _autofill(c, trip["id"])
    nut_days = [d["day_number"] for d in plan["days"]
                for item in d["items"] if item["name"] == "Mixed Nuts"]
    assert len(nut_days) == 3


def test_snacks_heaviest_first(c):
    """Heavier snacks assigned to earlier days."""
    trip = _create_trip(c)
    # Nuts = 2oz/serving (heaviest), Salami = 1.5oz, Crackers = 1.0oz
    _add_snack(c, trip["id"], "Mixed Nuts", 1)
    _add_snack(c, trip["id"], "Salami", 1)
    _add_snack(c, trip["id"], "Crackers", 1)

    plan = _autofill(c, trip["id"])
    # All are snacks slot -> afternoon_snacks, eligible days 1,2,3 (not last partial)
    # Heaviest (nuts) should be on earliest eligible day
    day1_snacks = [i["name"] for i in _day_items(plan, 1, "afternoon_snacks")]
    assert "Mixed Nuts" in day1_snacks


def test_lunch_snacks_go_to_lunch_slot(c):
    """Snacks with slot=lunch go to lunch slot (eligible on full days only)."""
    trip = _create_trip(c)
    _add_snack(c, trip["id"], "Crackers", 3)

    plan = _autofill(c, trip["id"])
    lunch_items = []
    for d in plan["days"]:
        for item in d["items"]:
            if item["name"] == "Crackers":
                lunch_items.append((d["day_number"], item["slot"]))

    # Lunch only eligible on days 2, 3 (full days)
    assert all(slot == "lunch" for _, slot in lunch_items)
    assert all(day in [2, 3] for day, _ in lunch_items)


# --- Drink Mix Distribution Tests ---

def test_drink_mix_breakfast_type(c):
    """Breakfast drink mixes go to breakfast_drinks slot, not on first partial."""
    trip = _create_trip(c)
    _add_snack(c, trip["id"], "Coffee Mix", 3)

    plan = _autofill(c, trip["id"])
    coffee_days = []
    for d in plan["days"]:
        for item in d["items"]:
            if item["name"] == "Coffee Mix":
                coffee_days.append((d["day_number"], item["slot"]))

    # breakfast_drinks eligible on days 2, 3, 4 (not first partial)
    assert all(slot == "breakfast_drinks" for _, slot in coffee_days)
    assert 1 not in [d for d, _ in coffee_days]


def test_drink_mix_dinner_type(c):
    """Dinner drink mixes go to evening_drinks slot, not on last partial."""
    trip = _create_trip(c)
    _add_snack(c, trip["id"], "Tea Packets", 3)

    plan = _autofill(c, trip["id"])
    tea_days = []
    for d in plan["days"]:
        for item in d["items"]:
            if item["name"] == "Tea Packets":
                tea_days.append((d["day_number"], item["slot"]))

    # evening_drinks eligible on days 1, 2, 3 (not last partial)
    assert all(slot == "evening_drinks" for _, slot in tea_days)
    assert 4 not in [d for d, _ in tea_days]


def test_drink_mix_all_day_type(c):
    """All-day drink mixes go to all_day_drinks slot, eligible all days."""
    trip = _create_trip(c)
    _add_snack(c, trip["id"], "Electrolytes", 4)

    plan = _autofill(c, trip["id"])
    elec_days = [d["day_number"] for d in plan["days"]
                 for item in d["items"] if item["name"] == "Electrolytes"]
    assert sorted(elec_days) == [1, 2, 3, 4]


def test_drink_mix_shortage_warning(c):
    """Warning when fewer drink mix servings than eligible days."""
    trip = _create_trip(c)
    _add_snack(c, trip["id"], "Coffee Mix", 1)  # Only 1 but 3 eligible days

    plan = _autofill(c, trip["id"])
    assert any("breakfast" in w.lower() for w in plan["warnings"])


def test_drink_mix_even_distribution(c):
    """Multiple drink mix items of same type distributed evenly."""
    trip = _create_trip(c)
    _add_snack(c, trip["id"], "Electrolytes", 4)

    plan = _autofill(c, trip["id"])
    # 4 servings across 4 eligible days = exactly 1 per day
    for day_num in [1, 2, 3, 4]:
        items = _day_items(plan, day_num, "all_day_drinks")
        assert len(items) == 1


# --- Edge Cases ---

def test_more_meals_than_days(c):
    """When more meal servings than days, extras go to unallocated pool."""
    trip = _create_trip(c, first_day_fraction=0.0, full_days=1, last_day_fraction=0.0)
    _add_meal(c, trip["id"], "Oatmeal", quantity=3)

    plan = _autofill(c, trip["id"])
    # 1 full day, 1 eligible breakfast day = 1 assigned, 2 unallocated
    bkf = [i for d in plan["days"] for i in d["items"] if i["slot"] == "breakfast"]
    assert len(bkf) == 1

    unalloc_meals = [u for u in plan["unallocated"] if u["source_type"] == "meal"]
    assert len(unalloc_meals) == 1
    assert unalloc_meals[0]["remaining_servings"] == 2


def test_single_full_day_trip(c):
    """Trip with only 1 full day works correctly."""
    trip = _create_trip(c, first_day_fraction=0.0, full_days=1, last_day_fraction=0.0)
    _add_meal(c, trip["id"], "Oatmeal", quantity=1)
    _add_meal(c, trip["id"], "Rice & Beans", quantity=1)
    _add_snack(c, trip["id"], "Mixed Nuts", 1)

    plan = _autofill(c, trip["id"])
    assert len(plan["days"]) == 1
    items = plan["days"][0]["items"]
    names = [i["name"] for i in items]
    assert "Oatmeal" in names
    assert "Rice & Beans" in names
    assert "Mixed Nuts" in names


def test_all_partial_trip(c):
    """Trip with only partial days (half + half, no full days)."""
    trip = _create_trip(c, first_day_fraction=0.5, full_days=0, last_day_fraction=0.5)
    _add_meal(c, trip["id"], "Oatmeal", quantity=1)
    _add_meal(c, trip["id"], "Rice & Beans", quantity=1)

    plan = _autofill(c, trip["id"])
    assert len(plan["days"]) == 2

    # Day 1 (first partial): no breakfast, gets dinner
    day1_items = _day_items(plan, 1)
    assert not any(i["slot"] == "breakfast" for i in day1_items)
    assert any(i["slot"] == "dinner" for i in day1_items)

    # Day 2 (last partial): gets breakfast, no dinner
    day2_items = _day_items(plan, 2)
    assert any(i["slot"] == "breakfast" for i in day2_items)
    assert not any(i["slot"] == "dinner" for i in day2_items)


def test_zero_servings_snack(c):
    """Snack with 0 servings produces no assignments."""
    trip = _create_trip(c)
    cid = _get_catalog_id(c, "Mixed Nuts")
    # Add with 0 servings (edge case)
    resp = c.post(f"/api/trips/{trip['id']}/snacks", json={"catalog_item_id": cid, "servings": 0})
    assert resp.status_code == 201

    plan = _autofill(c, trip["id"])
    nut_items = [i for d in plan["days"] for i in d["items"] if i["name"] == "Mixed Nuts"]
    assert len(nut_items) == 0


def test_autofill_replaces_previous(c):
    """Running auto-fill again replaces all previous assignments."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Oatmeal", quantity=2)

    plan1 = _autofill(c, trip["id"])
    bkf1 = [i for d in plan1["days"] for i in d["items"] if i["slot"] == "breakfast"]

    plan2 = _autofill(c, trip["id"])
    bkf2 = [i for d in plan2["days"] for i in d["items"] if i["slot"] == "breakfast"]

    # Same number of assignments (not doubled)
    assert len(bkf1) == len(bkf2)


def test_deterministic(c):
    """Same inputs produce same output."""
    trip = _create_trip(c)
    _add_meal(c, trip["id"], "Oatmeal", quantity=2)
    _add_meal(c, trip["id"], "Rice & Beans", quantity=2)
    _add_snack(c, trip["id"], "Mixed Nuts", 3)

    plan1 = _autofill(c, trip["id"])
    plan2 = _autofill(c, trip["id"])

    # Compare day-by-day item assignments
    for d1, d2 in zip(plan1["days"], plan2["days"]):
        items1 = [(i["name"], i["slot"], i["servings"]) for i in d1["items"]]
        items2 = [(i["name"], i["slot"], i["servings"]) for i in d2["items"]]
        assert sorted(items1) == sorted(items2)


def test_get_empty_plan(c):
    """GET daily plan when no auto-fill has run returns empty days."""
    trip = _create_trip(c)
    plan = _get_plan(c, trip["id"])
    assert len(plan["days"]) == 4  # 0.5 + 2 + 0.5
    assert all(len(d["items"]) == 0 for d in plan["days"])


def test_unallocated_pool(c):
    """Unallocated pool shows remaining servings after partial distribution."""
    trip = _create_trip(c)
    # 10 servings of nuts, only ~3 eligible afternoon_snack days
    _add_snack(c, trip["id"], "Mixed Nuts", 10)

    plan = _autofill(c, trip["id"])
    unalloc = [u for u in plan["unallocated"] if u["name"] == "Mixed Nuts"]
    assert len(unalloc) == 1
    # 3 eligible days for afternoon_snacks (1, 2, 3), 10-3=7 remaining
    assert unalloc[0]["remaining_servings"] == 7


def test_snacks_distributed_evenly_not_front_loaded(c):
    """Snacks with fewer servings than days should spread evenly, not pile on day 1."""
    # Utah-like trip: 0.5 + 5 + 0.5 = 7 days, many snack items with 2 servings each
    trip = _create_trip(c, first_day_fraction=0.5, full_days=5, last_day_fraction=0.5)

    # Add many snack items with 2 servings each (like the real Utah trip)
    _add_snack(c, trip["id"], "Mixed Nuts", 2)
    _add_snack(c, trip["id"], "Salami", 2)
    _add_snack(c, trip["id"], "Crackers", 2)  # lunch slot

    plan = _autofill(c, trip["id"])

    # Count afternoon_snacks per day
    snack_counts = {}
    for d in plan["days"]:
        count = len([i for i in d["items"] if i["slot"] == "afternoon_snacks"])
        snack_counts[d["day_number"]] = count

    # With 2 items × 2 servings across 6 eligible afternoon_snack days (1-6, not day 7),
    # no single day should have more than 2 snack items
    max_snacks_per_day = max(snack_counts.values()) if snack_counts else 0
    assert max_snacks_per_day <= 2, (
        f"Snacks should be spread evenly but day had {max_snacks_per_day} snacks: {snack_counts}"
    )

    # The two items should NOT both be on day 1
    assert snack_counts.get(1, 0) <= 1, (
        f"Day 1 got {snack_counts.get(1, 0)} snacks — should spread across days"
    )


def test_utah_trip_realistic(c):
    """Realistic Utah trip: snacks spread across days, not front-loaded.

    Reproduces the bug where all snack items with 2 servings piled onto days 1-2.
    """
    trip = _create_trip(c, first_day_fraction=0.5, full_days=5, last_day_fraction=0.5)

    # 6 breakfasts
    _add_meal(c, trip["id"], "Oatmeal", quantity=6)
    # 2 each of 3 different dinners = 6 dinners
    _add_meal(c, trip["id"], "Rice & Beans", quantity=2)
    _add_meal(c, trip["id"], "Cheese Quesadilla", quantity=2)

    # Lots of 2-serving snack items (the problematic pattern)
    _add_snack(c, trip["id"], "Mixed Nuts", 4)
    _add_snack(c, trip["id"], "Salami", 2)

    plan = _autofill(c, trip["id"])

    # Count total snack items per day across all snack slots
    snack_counts = {}
    for d in plan["days"]:
        count = len([i for i in d["items"]
                     if i["slot"] in ("afternoon_snacks", "morning_snacks")])
        snack_counts[d["day_number"]] = count

    # Key assertion: the spread should be roughly even.
    # With 6 total snack servings across 6 eligible days, each day should get ~1.
    # Definitely no day should get more than 3.
    if snack_counts:
        max_count = max(snack_counts.values())
        min_count = min(snack_counts.get(d, 0) for d in range(1, 7))
        assert max_count <= 3, (
            f"Worst day got {max_count} snacks — distribution is front-loaded: {snack_counts}"
        )
        assert max_count - min_count <= 2, (
            f"Snack spread too uneven: max={max_count}, min={min_count}: {snack_counts}"
        )


# --- Unallocated Summary Tests ---

def test_unallocated_summary(c):
    """unallocated_summary has correct count, calories, and weight."""
    # Create a short trip with more food than fits
    trip = _create_trip(c, full_days=1, first_day_fraction=0.5, last_day_fraction=0.5)
    _add_meal(c, trip["id"], "Oatmeal", quantity=3)
    _add_meal(c, trip["id"], "Rice & Beans", quantity=3)
    _add_snack(c, trip["id"], "Crackers", servings=10)
    plan = _autofill(c, trip["id"])

    summary = plan["unallocated_summary"]
    assert "count" in summary
    assert "total_calories" in summary
    assert "total_weight" in summary

    # With 3 oatmeal + 3 dinners + 10 snack servings on a 3-day trip,
    # there should be unallocated items
    assert summary["count"] > 0
    assert summary["total_calories"] > 0
    assert summary["total_weight"] > 0

    # Now test all-allocated: create a trip with exactly enough food.
    # first_partial gets dinner but not breakfast; full gets both;
    # last_partial gets breakfast but not dinner. So 2 breakfasts, 2 dinners.
    trip2 = _create_trip(c, name="Exact Trip", full_days=1,
                         first_day_fraction=1.0, last_day_fraction=1.0)
    _add_meal(c, trip2["id"], "Oatmeal", quantity=2)
    _add_meal(c, trip2["id"], "Rice & Beans", quantity=2)
    plan2 = _autofill(c, trip2["id"])

    summary2 = plan2["unallocated_summary"]
    assert summary2["count"] == 0
    assert summary2["total_calories"] == 0
    assert summary2["total_weight"] == 0
