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
