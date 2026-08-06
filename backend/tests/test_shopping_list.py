"""Tests for shopping list enhancements: sorting, essentials, on_hand toggle."""
import pytest
from database import Base
from models import Ingredient, SnackCatalogItem, Recipe, RecipeIngredient


@pytest.fixture(autouse=True)
def db_setup(test_engine, test_session):
    Base.metadata.create_all(bind=test_engine)
    db = test_session()

    # Create ingredients with various on_hand/essentials states
    salt = Ingredient(name="Salt", calories_per_oz=0, on_hand=True, essentials=True, packing_method="bag")
    oil = Ingredient(name="Olive Oil", calories_per_oz=240, on_hand=True, essentials=True)
    cheese = Ingredient(name="Cheese", calories_per_oz=110, on_hand=False, essentials=False, packing_method="container")
    crackers = Ingredient(name="Crackers", calories_per_oz=130, on_hand=True, essentials=False, packing_method="bag")
    salami = Ingredient(name="Salami", calories_per_oz=150, on_hand=False, essentials=False, packing_method="original")
    for ing in [salt, oil, cheese, crackers, salami]:
        db.add(ing)
    db.flush()

    # Create a recipe using salt (essential) and cheese (non-essential)
    recipe = Recipe(name="Cheese Quesadilla", category="dinner")
    db.add(recipe)
    db.flush()
    db.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=cheese.id, amount_oz=2.0))
    db.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=salt.id, amount_oz=0.1))
    db.flush()

    # Create snack catalog items
    db.add(SnackCatalogItem(ingredient_id=crackers.id, weight_per_serving=1.0, calories_per_serving=130, category="lunch"))
    db.add(SnackCatalogItem(ingredient_id=salami.id, weight_per_serving=1.5, calories_per_serving=225, category="lunch"))

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_trip(c):
    resp = c.post("/api/trips", json={
        "name": "Test Trip", "first_day_fraction": 0.5,
        "full_days": 2, "last_day_fraction": 0.5,
    })
    assert resp.status_code == 201
    return resp.json()


def _legacy_trip(c, name="Legacy Trip"):
    resp = c.post("/api/trips", json={
        "name": name, "first_day_fraction": 0.5,
        "full_days": 2, "last_day_fraction": 0.5,
    })
    assert resp.status_code == 201
    trip = resp.json()
    assert c.put(
        f"/api/trips/{trip['id']}", json={"snack_model": "legacy"},
    ).status_code == 200
    return trip


def _ingredient(c, name, **fields):
    resp = c.post("/api/ingredients", json={"name": name, **fields})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bag(c, name, composition):
    """A unit type from (ingredient_id, amount_oz) pairs."""
    resp = c.post("/api/snack-unit-types", json={
        "name": name,
        "composition": [
            {"ingredient_id": ingredient_id, "amount_oz": amount_oz}
            for ingredient_id, amount_oz in composition
        ],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _add_unit(c, trip_id, **payload):
    resp = c.post(f"/api/trips/{trip_id}/snack-units", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _ingredient_id(c, name):
    return next(i["id"] for i in c.get("/api/ingredients").json() if i["name"] == name)


def _line(shopping, name, section="items"):
    return next(
        item for item in shopping[section] if item["ingredient_name"] == name
    )


def test_shopping_list_sort_order(c):
    """Need-to-buy (not on_hand) before on-hand, alphabetical within groups."""
    trip = _create_trip(c)
    # Add meal (uses cheese + salt)
    recipes = c.get("/api/recipes").json()
    recipe_id = recipes[0]["id"]
    c.post(f"/api/trips/{trip['id']}/meals", json={"recipe_id": recipe_id})

    # Add snacks (crackers = on_hand, salami = not on_hand)
    snack_items = c.get("/api/snacks").json()
    for item in snack_items:
        c.post(f"/api/trips/{trip['id']}/snacks", json={
            "catalog_item_id": item["id"], "servings": 2,
        })

    shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()
    items = shop["items"]
    # Non-essentials only in items list
    names = [i["ingredient_name"] for i in items]
    # Need-to-buy first: Cheese, Salami (not on_hand, alphabetical)
    # Then on-hand: Crackers
    assert names == ["Cheese", "Salami", "Crackers"]


def test_essentials_separated(c):
    """Essentials appear in separate list, not in main items."""
    trip = _create_trip(c)
    recipes = c.get("/api/recipes").json()
    recipe_id = recipes[0]["id"]
    c.post(f"/api/trips/{trip['id']}/meals", json={"recipe_id": recipe_id})

    shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()
    essential_names = [i["ingredient_name"] for i in shop["essentials"]]
    item_names = [i["ingredient_name"] for i in shop["items"]]

    assert "Salt" in essential_names
    assert "Salt" not in item_names
    assert "Cheese" in item_names
    assert "Cheese" not in essential_names


def test_on_hand_toggle(c):
    """PATCH endpoint toggles on_hand status."""
    ings = c.get("/api/ingredients").json()
    cheese = next(i for i in ings if i["name"] == "Cheese")
    assert cheese["on_hand"] is False

    resp = c.patch(f"/api/ingredients/{cheese['id']}/on-hand")
    assert resp.status_code == 200
    assert resp.json()["on_hand"] is True

    # Toggle back
    resp = c.patch(f"/api/ingredients/{cheese['id']}/on-hand")
    assert resp.status_code == 200
    assert resp.json()["on_hand"] is False


def test_shopping_list_includes_packing_method(c):
    """Shopping list items include packing_method from ingredient."""
    trip = _create_trip(c)
    snack_items = c.get("/api/snacks").json()
    for item in snack_items:
        c.post(f"/api/trips/{trip['id']}/snacks", json={
            "catalog_item_id": item["id"], "servings": 1,
        })

    shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()
    salami_item = next(i for i in shop["items"] if i["ingredient_name"] == "Salami")
    assert salami_item["packing_method"] == "original"

    crackers_item = next(i for i in shop["items"] if i["ingredient_name"] == "Crackers")
    assert crackers_item["packing_method"] == "bag"


def test_on_hand_toggle_not_found(c):
    """PATCH returns 404 for non-existent ingredient."""
    resp = c.patch("/api/ingredients/99999/on-hand")
    assert resp.status_code == 404


class TestSnackUnitExpansion:
    """Structured trips: bags become bulk ounces, packaged units become servings."""

    def test_a_bag_buys_its_composition_ounces_per_unit(self, c):
        """6 bags of 1 oz nuts + 1 oz M&Ms buy 6 oz of each."""
        trip = _create_trip(c)
        nuts = _ingredient(c, "Almonds", calories_per_oz=183)
        candy = _ingredient(c, "M&Ms", calories_per_oz=138)
        bag = _bag(c, "Trail Mix Bag", [(nuts["id"], 1.0), (candy["id"], 1.0)])
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)

        shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

        assert _line(shop, "Almonds")["total_oz"] == 6.0
        assert _line(shop, "M&Ms")["total_oz"] == 6.0

    def test_bag_ounces_merge_with_the_same_ingredient_from_other_sources(self, c):
        """Crackers in a bag and crackers in the lunch slot are one line."""
        trip = _create_trip(c)
        crackers_id = _ingredient_id(c, "Crackers")
        crackers_item = next(
            item for item in c.get("/api/snacks").json()
            if item["ingredient_name"] == "Crackers"
        )
        c.post(f"/api/trips/{trip['id']}/snacks", json={
            "catalog_item_id": crackers_item["id"], "servings": 2,
        })
        bag = _bag(c, "Cracker Bag", [(crackers_id, 0.5)])
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=4)

        shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

        crackers = [i for i in shop["items"] if i["ingredient_name"] == "Crackers"]
        # 2 servings x 1 oz from the lunch slot + 4 bags x 0.5 oz, on one line.
        assert len(crackers) == 1
        assert crackers[0]["total_oz"] == 4.0

    def test_a_packaged_unit_buys_its_catalog_serving_weight(self, c):
        """A packaged unit aggregates through its catalog item, like a TripSnack."""
        trip = _create_trip(c)
        salami_item = next(
            item for item in c.get("/api/snacks").json()
            if item["ingredient_name"] == "Salami"
        )
        _add_unit(c, trip["id"], catalog_item_id=salami_item["id"], quantity=3)

        shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

        assert _line(shop, "Salami")["total_oz"] == 4.5  # 3 x 1.5 oz

    def test_a_packaged_unit_merges_with_the_same_catalog_item_in_a_slot(self, c):
        trip = _create_trip(c)
        salami_item = next(
            item for item in c.get("/api/snacks").json()
            if item["ingredient_name"] == "Salami"
        )
        c.post(f"/api/trips/{trip['id']}/snacks", json={
            "catalog_item_id": salami_item["id"], "servings": 2,
        })
        _add_unit(c, trip["id"], catalog_item_id=salami_item["id"], quantity=3)

        shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

        salami = [i for i in shop["items"] if i["ingredient_name"] == "Salami"]
        assert len(salami) == 1
        assert salami[0]["total_oz"] == 7.5  # 2 x 1.5 + 3 x 1.5

    def test_an_essential_inside_a_bag_lands_in_the_essentials_list(self, c):
        """Bag ingredients follow the ingredient's own essentials flag."""
        trip = _create_trip(c)
        nuts = _ingredient(c, "Almonds", calories_per_oz=183)
        bag = _bag(c, "Salted Almond Bag", [
            (nuts["id"], 1.9), (_ingredient_id(c, "Salt"), 0.1),
        ])
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=4)

        shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

        assert _line(shop, "Salt", "essentials")["total_oz"] == 0.4
        assert "Salt" not in [i["ingredient_name"] for i in shop["items"]]
        assert _line(shop, "Almonds")["total_oz"] == 7.6

    def test_bag_ingredients_carry_on_hand_and_packing_method(self, c):
        """An on-hand bag ingredient sorts and renders like any other line."""
        trip = _create_trip(c)
        bag = _bag(c, "Cracker Bag", [
            (_ingredient_id(c, "Crackers"), 1.0),
            (_ingredient_id(c, "Salami"), 1.0),
        ])
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=2)

        shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

        crackers = _line(shop, "Crackers")
        assert crackers["on_hand"] is True
        assert crackers["packing_method"] == "bag"
        # Need-to-buy first, on-hand last: Salami before Crackers.
        assert [i["ingredient_name"] for i in shop["items"]] == ["Salami", "Crackers"]

    def test_a_legacy_trip_ignores_stray_unit_rows(self, c):
        """Units belong to the structured model; a legacy list never expands them."""
        trip = _create_trip(c)
        nuts = _ingredient(c, "Almonds", calories_per_oz=183)
        bag = _bag(c, "Trail Mix Bag", [(nuts["id"], 1.0)])
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)
        assert c.put(
            f"/api/trips/{trip['id']}", json={"snack_model": "legacy"},
        ).status_code == 200

        shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

        assert "Almonds" not in [i["ingredient_name"] for i in shop["items"]]


# Captured from the pre-change tree (git worktree at the step-4 commit) with the
# same fixture, meal, and snacks this test builds. Units must not disturb it.
LEGACY_SHOPPING_SNAPSHOT = {
    "items": [
        {
            "ingredient_id": 3, "ingredient_name": "Cheese", "total_oz": 4.0,
            "on_hand": False, "essentials": False, "packing_method": "container",
        },
        {
            "ingredient_id": 5, "ingredient_name": "Salami", "total_oz": 3.0,
            "on_hand": False, "essentials": False, "packing_method": "original",
        },
        {
            "ingredient_id": 4, "ingredient_name": "Crackers", "total_oz": 2.0,
            "on_hand": True, "essentials": False, "packing_method": "bag",
        },
    ],
    "essentials": [
        {
            "ingredient_id": 1, "ingredient_name": "Salt", "total_oz": 0.2,
            "on_hand": True, "essentials": True, "packing_method": "bag",
        },
    ],
}


def test_a_legacy_trip_shopping_list_matches_the_pre_change_snapshot(c):
    trip = _legacy_trip(c)
    recipe_id = c.get("/api/recipes").json()[0]["id"]
    c.post(f"/api/trips/{trip['id']}/meals", json={
        "recipe_id": recipe_id, "quantity": 2,
    })
    for item in c.get("/api/snacks").json():
        c.post(f"/api/trips/{trip['id']}/snacks", json={
            "catalog_item_id": item["id"], "servings": 2,
        })

    shop = c.get(f"/api/trips/{trip['id']}/shopping-list").json()

    assert shop == LEGACY_SHOPPING_SNAPSHOT
