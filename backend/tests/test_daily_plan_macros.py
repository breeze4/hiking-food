"""Tests for per-day macronutrient breakdown in daily plan."""
import pytest
from database import Base
from models import Ingredient, SnackCatalogItem, Recipe, RecipeIngredient


@pytest.fixture(autouse=True)
def db_setup(test_engine, test_session):
    Base.metadata.create_all(bind=test_engine)
    db = test_session()

    # Ingredients WITH macro data
    oats = Ingredient(
        name="Oats", calories_per_oz=110,
        protein_per_oz=4.0, fat_per_oz=2.0, carb_per_oz=20.0,
    )
    rice = Ingredient(
        name="Rice", calories_per_oz=100,
        protein_per_oz=2.5, fat_per_oz=0.5, carb_per_oz=22.0,
    )
    nuts = Ingredient(
        name="Mixed Nuts", calories_per_oz=160,
        protein_per_oz=5.0, fat_per_oz=14.0, carb_per_oz=6.0,
    )

    # Ingredient WITHOUT macro data
    coffee = Ingredient(name="Coffee Mix", calories_per_oz=50)

    for ing in [oats, rice, nuts, coffee]:
        db.add(ing)
    db.flush()

    # Recipe: Oatmeal (3oz oats) — has macros
    r1 = Recipe(name="Oatmeal", category="breakfast")
    db.add(r1)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r1.id, ingredient_id=oats.id, amount_oz=3.0))

    # Recipe: Plain Rice (4oz rice) — has macros
    r2 = Recipe(name="Plain Rice", category="dinner")
    db.add(r2)
    db.flush()
    db.add(RecipeIngredient(recipe_id=r2.id, ingredient_id=rice.id, amount_oz=4.0))

    # Snack catalog items
    db.add(SnackCatalogItem(
        ingredient_id=nuts.id, weight_per_serving=2.0,
        calories_per_serving=320, category="salty",
    ))
    db.add(SnackCatalogItem(
        ingredient_id=coffee.id, weight_per_serving=0.5,
        calories_per_serving=25, category="drink_mix",
        drink_mix_type="breakfast",
    ))

    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_trip(c, **overrides):
    payload = {
        "name": "Macro Trip",
        "first_day_fraction": 0.0,
        "full_days": 1,
        "last_day_fraction": 0.0,
        "drink_mixes_per_day": 0,
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


def _add_snack(c, trip_id, name, servings):
    cid = _get_catalog_id(c, name)
    resp = c.post(f"/api/trips/{trip_id}/snacks", json={"catalog_item_id": cid, "servings": servings})
    assert resp.status_code == 201


def _autofill(c, trip_id):
    resp = c.post(f"/api/trips/{trip_id}/daily-plan/auto-fill")
    assert resp.status_code == 200
    return resp.json()


def _get_plan(c, trip_id):
    resp = c.get(f"/api/trips/{trip_id}/daily-plan")
    assert resp.status_code == 200
    return resp.json()


# --- Tests ---

def test_day_macros_with_full_data(c):
    """Day with all items having macros shows correct grams and percentages."""
    trip = _create_trip(c)
    # Oatmeal: 3oz oats -> protein=12g, fat=6g, carb=60g
    _add_meal(c, trip["id"], "Oatmeal", quantity=1)
    # Nuts: 2oz serving -> protein=10g, fat=28g, carb=12g
    _add_snack(c, trip["id"], "Mixed Nuts", 1)

    plan = _autofill(c, trip["id"])

    day = plan["days"][0]
    macros = day["macros"]
    assert macros is not None

    # Oatmeal: p=12, f=6, c=60; Nuts: p=10, f=28, c=12
    assert macros["protein_g"] == 22.0
    assert macros["fat_g"] == 34.0
    assert macros["carb_g"] == 72.0

    # Calorie equivalents: p=22*4=88, f=34*9=306, c=72*4=288 -> total=682
    total_macro_cal = 88 + 306 + 288
    assert macros["protein_pct"] == round(88 / total_macro_cal * 100, 1)
    assert macros["fat_pct"] == round(306 / total_macro_cal * 100, 1)
    assert macros["carb_pct"] == round(288 / total_macro_cal * 100, 1)

    # All items have macros, so coverage = 100%
    assert macros["coverage_pct"] == 100.0


def test_day_macros_partial_data(c):
    """Day with some items lacking macros shows coverage < 100%."""
    trip = _create_trip(c, drink_mixes_per_day=1)
    _add_meal(c, trip["id"], "Oatmeal", quantity=1)
    _add_snack(c, trip["id"], "Coffee Mix", 1)  # no macros

    plan = _autofill(c, trip["id"])

    day = plan["days"][0]
    macros = day["macros"]
    assert macros is not None

    # Only oatmeal contributes macros: p=12, f=6, c=60
    assert macros["protein_g"] == 12.0
    assert macros["fat_g"] == 6.0
    assert macros["carb_g"] == 60.0

    # Coverage: oatmeal cal / (oatmeal cal + coffee cal) < 100%
    assert macros["coverage_pct"] is not None
    assert macros["coverage_pct"] < 100


def test_day_macros_no_data(c):
    """Day with only no-macro items gets null macros."""
    trip = _create_trip(c, drink_mixes_per_day=1)
    _add_snack(c, trip["id"], "Coffee Mix", 1)

    plan = _autofill(c, trip["id"])

    day = plan["days"][0]
    assert day["macros"] is None


def test_empty_day_macros_null(c):
    """Empty day (no items) gets null macros."""
    trip = _create_trip(c)
    plan = _get_plan(c, trip["id"])

    day = plan["days"][0]
    assert day["macros"] is None


def test_macro_target_in_response(c):
    """Response includes macro_target from app settings."""
    trip = _create_trip(c)
    plan = _get_plan(c, trip["id"])

    assert "macro_target" in plan
    target = plan["macro_target"]
    assert target["protein_pct"] == 20
    assert target["fat_pct"] == 30
    assert target["carb_pct"] == 50


def test_macro_target_reflects_settings(c):
    """After updating settings, macro_target changes."""
    c.put("/api/settings", json={
        "macro_target_protein_pct": 30,
        "macro_target_fat_pct": 40,
        "macro_target_carb_pct": 30,
    })

    trip = _create_trip(c)
    plan = _get_plan(c, trip["id"])

    target = plan["macro_target"]
    assert target["protein_pct"] == 30
    assert target["fat_pct"] == 40
    assert target["carb_pct"] == 30


def test_multiday_per_day_macros(c):
    """Each day in a multi-day trip gets its own macro breakdown."""
    trip = _create_trip(c, first_day_fraction=0.5, full_days=1, last_day_fraction=0.5)
    _add_meal(c, trip["id"], "Oatmeal", quantity=2)
    _add_meal(c, trip["id"], "Plain Rice", quantity=2)
    _add_snack(c, trip["id"], "Mixed Nuts", 3)

    plan = _autofill(c, trip["id"])

    # Each day should have its own macros dict (or null)
    for day in plan["days"]:
        if day["items"]:
            assert day["macros"] is not None
            assert "protein_g" in day["macros"]
            assert "protein_pct" in day["macros"]
        else:
            assert day["macros"] is None
