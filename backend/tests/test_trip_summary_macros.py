"""Tests for macro aggregation in trip summary."""
import pytest
from database import Base
from models import Ingredient, SnackCatalogItem, Recipe, RecipeIngredient


@pytest.fixture(autouse=True)
def db_setup(test_engine, test_session):
    Base.metadata.create_all(bind=test_engine)
    db = test_session()

    # Ingredients with full macro data
    oats = Ingredient(name="Oats", calories_per_oz=110,
                      protein_per_oz=4.0, fat_per_oz=2.0, carb_per_oz=20.0)
    rice = Ingredient(name="Rice", calories_per_oz=100,
                      protein_per_oz=2.0, fat_per_oz=0.5, carb_per_oz=22.0)
    # Ingredient with NO macro data
    coffee = Ingredient(name="Coffee Mix", calories_per_oz=50)
    # Snack ingredient with macros
    nuts = Ingredient(name="Mixed Nuts", calories_per_oz=160,
                      protein_per_oz=6.0, fat_per_oz=14.0, carb_per_oz=4.0)
    # Snack ingredient without macros
    candy = Ingredient(name="Candy", calories_per_oz=120)

    for ing in [oats, rice, coffee, nuts, candy]:
        db.add(ing)
    db.flush()

    # Recipes
    r1 = Recipe(name="Oatmeal", category="breakfast")
    db.add(r1)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r1.id, ingredient_id=oats.id, amount_oz=3.0))

    r2 = Recipe(name="Rice Bowl", category="dinner")
    db.add(r2)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r2.id, ingredient_id=rice.id, amount_oz=4.0))

    # Recipe with mixed macro/no-macro ingredients
    r3 = Recipe(name="Coffee Oats", category="breakfast")
    db.add(r3)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r3.id, ingredient_id=oats.id, amount_oz=2.0))
    db.add(RecipeIngredient(recipe_id=r3.id, ingredient_id=coffee.id, amount_oz=0.5))

    # Snack catalog items
    db.add(SnackCatalogItem(ingredient_id=nuts.id, weight_per_serving=2.0,
                            calories_per_serving=320, category="salty"))
    db.add(SnackCatalogItem(ingredient_id=candy.id, weight_per_serving=1.5,
                            calories_per_serving=180, category="sweet"))

    db.commit()
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_trip(c, meals=None, snacks=None):
    """Helper: create a 2-day trip and add meals/snacks."""
    resp = c.post("/api/trips", json={
        "name": "Macro Test Trip",
        "first_day_fraction": 1.0,
        "full_days": 0,
        "last_day_fraction": 1.0,
    })
    trip_id = resp.json()["id"]

    if meals:
        for recipe_name, qty in meals:
            # Find recipe id by listing recipes
            recipes = c.get("/api/recipes").json()
            recipe = next(r for r in recipes if r["name"] == recipe_name)
            c.post(f"/api/trips/{trip_id}/meals", json={
                "recipe_id": recipe["id"], "quantity": qty,
            })

    if snacks:
        for ing_name, servings in snacks:
            catalog = c.get("/api/snacks").json()
            item = next(s for s in catalog if s["ingredient_name"] == ing_name)
            c.post(f"/api/trips/{trip_id}/snacks", json={
                "catalog_item_id": item["id"], "servings": servings,
            })

    return trip_id


def test_full_macro_data(c):
    """All items have macro data — percentages and coverage should be computed."""
    trip_id = _create_trip(c,
        meals=[("Oatmeal", 2), ("Rice Bowl", 2)],
        snacks=[("Mixed Nuts", 4)],
    )
    resp = c.get(f"/api/trips/{trip_id}/summary")
    assert resp.status_code == 200
    data = resp.json()

    macro = data["macro_actual"]
    assert macro is not None

    # Oatmeal: 3oz * (4p, 2f, 20c) = 12p, 6f, 60c per unit, x2 = 24p, 12f, 120c
    # Rice Bowl: 4oz * (2p, 0.5f, 22c) = 8p, 2f, 88c per unit, x2 = 16p, 4f, 176c
    # Nuts: 2oz * (6p, 14f, 4c) = 12p, 28f, 8c per serving, x4 = 48p, 112f, 32c
    expected_p = 24 + 16 + 48  # 88
    expected_f = 12 + 4 + 112  # 128
    expected_carb = 120 + 176 + 32  # 328

    assert macro["protein_g"] == expected_p
    assert macro["fat_g"] == expected_f
    assert macro["carb_g"] == expected_carb

    total_macro_cal = expected_p * 4 + expected_f * 9 + expected_carb * 4
    assert macro["protein_pct"] == round(expected_p * 4 / total_macro_cal * 100, 1)
    assert macro["fat_pct"] == round(expected_f * 9 / total_macro_cal * 100, 1)
    assert macro["carb_pct"] == round(expected_carb * 4 / total_macro_cal * 100, 1)

    # All ingredients have macros, so coverage should be 100%
    assert data["macro_coverage_pct"] == 100.0


def test_partial_macro_data(c):
    """Mix of items with and without macro data — coverage < 100%."""
    trip_id = _create_trip(c,
        meals=[("Coffee Oats", 1)],
        snacks=[("Mixed Nuts", 2), ("Candy", 3)],
    )
    resp = c.get(f"/api/trips/{trip_id}/summary")
    data = resp.json()

    macro = data["macro_actual"]
    assert macro is not None

    # Coffee Oats: oats 2oz (has macros) + coffee 0.5oz (no macros)
    # Oats contribution: 2*4=8p, 2*2=4f, 2*20=40c
    # Coffee: no macros, 0 contribution
    # Nuts: 2oz * (6p, 14f, 4c) * 2 servings = 24p, 56f, 16c
    # Candy: no macros, 0 contribution
    expected_p = 8 + 24  # 32
    expected_f = 4 + 56  # 60
    expected_carb = 40 + 16  # 56

    assert macro["protein_g"] == expected_p
    assert macro["fat_g"] == expected_f
    assert macro["carb_g"] == expected_carb

    # Coverage: calories with macros / total calories
    # Oats cal: 2 * 110 = 220 (has macros)
    # Coffee cal: 0.5 * 50 = 25 (no macros)
    # Nuts cal: 320 * 2 = 640 (has macros)
    # Candy cal: 180 * 3 = 540 (no macros)
    # Total = 220 + 25 + 640 + 540 = 1425
    # Covered = 220 + 640 = 860
    expected_coverage = round(860 / 1425 * 100, 1)
    assert data["macro_coverage_pct"] == expected_coverage
    assert data["macro_coverage_pct"] < 100


def test_no_macro_data(c):
    """No ingredients have macro data — macro_actual should be null."""
    # Create ingredients without macros for a recipe
    # Use Coffee Mix (no macros) as a snack ingredient... but we need a recipe with no macros
    # We'll just add candy snacks only (no meals)
    trip_id = _create_trip(c,
        snacks=[("Candy", 5)],
    )
    resp = c.get(f"/api/trips/{trip_id}/summary")
    data = resp.json()

    assert data["macro_actual"] is None
    # Coverage should be 0% (no macro data but there are calories)
    assert data["macro_coverage_pct"] == 0.0


def test_empty_trip_macros(c):
    """Trip with no meals or snacks — macro fields should be null."""
    trip_id = _create_trip(c)
    resp = c.get(f"/api/trips/{trip_id}/summary")
    data = resp.json()

    assert data["macro_actual"] is None
    assert data["macro_coverage_pct"] is None
