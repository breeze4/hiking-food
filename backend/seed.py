"""Seed script for hiking food planner.

Seeds Skurka recipes and Utah 2026 snack data. Idempotent — safe to run multiple times.
Run from backend directory: python seed.py
"""
import json
import sys
from pathlib import Path

from database import SessionLocal, engine, Base
from models import (
    Ingredient, SnackCatalogItem, Recipe, RecipeIngredient, Trip, TripSnack,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def get_or_create_ingredient(db, name, calories_per_oz, notes=None):
    existing = db.query(Ingredient).filter(Ingredient.name == name).first()
    if existing:
        return existing, False
    ing = Ingredient(name=name, calories_per_oz=calories_per_oz, notes=notes)
    db.add(ing)
    db.flush()
    return ing, True


def seed_skurka_recipes(db):
    data = json.loads((DATA_DIR / "skurka-recipes.json").read_text())
    created_ingredients = 0
    created_recipes = 0

    # Track ingredient cal/oz discrepancies
    seen_ingredients = {}

    for recipe_data in data["recipes"]:
        # Get or create ingredients
        for ing_data in recipe_data["ingredients"]:
            name = ing_data["name"]
            cal_per_oz = ing_data["calories_per_oz"]

            if name in seen_ingredients and seen_ingredients[name] != cal_per_oz:
                # Discrepancy — keep first value
                pass
            else:
                seen_ingredients[name] = cal_per_oz

            ing, was_created = get_or_create_ingredient(
                db, name, seen_ingredients[name], ing_data.get("notes")
            )
            if was_created:
                created_ingredients += 1

        # Get or create recipe
        existing_recipe = db.query(Recipe).filter(Recipe.name == recipe_data["name"]).first()
        if existing_recipe:
            continue

        recipe = Recipe(
            name=recipe_data["name"],
            category=recipe_data["category"],
            at_home_prep=recipe_data.get("at_home_prep"),
            field_prep=recipe_data.get("field_prep"),
            notes=recipe_data.get("notes"),
        )
        db.add(recipe)
        db.flush()

        for ing_data in recipe_data["ingredients"]:
            ingredient = db.query(Ingredient).filter(Ingredient.name == ing_data["name"]).first()
            db.add(RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                amount_oz=ing_data["amount_oz"],
            ))

        created_recipes += 1

    print(f"Skurka: {created_ingredients} ingredients created, {created_recipes} recipes created")


def seed_utah_2026_snacks(db):
    data = json.loads((DATA_DIR / "utah-2026-snacks.json").read_text())
    created_ingredients = 0
    created_catalog = 0

    for snack_data in data["snacks"]:
        ing, was_created = get_or_create_ingredient(
            db, snack_data["name"], snack_data["calories_per_oz"],
            snack_data.get("notes"),
        )
        if was_created:
            created_ingredients += 1

        # Get or create snack catalog item
        existing = db.query(SnackCatalogItem).filter(
            SnackCatalogItem.ingredient_id == ing.id
        ).first()
        if not existing:
            db.add(SnackCatalogItem(
                ingredient_id=ing.id,
                weight_per_serving=snack_data["weight_per_serving"],
                calories_per_serving=snack_data["calories_per_serving"],
                notes=snack_data.get("notes"),
            ))
            created_catalog += 1

    print(f"Utah snacks: {created_ingredients} ingredients created, {created_catalog} catalog items created")


def seed_utah_2026_trip(db):
    data = json.loads((DATA_DIR / "utah-2026-snacks.json").read_text())
    trip_data = data["trip"]

    existing = db.query(Trip).filter(Trip.name == trip_data["name"]).first()
    if existing:
        trip = existing
        existing_snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).count()
        if existing_snacks > 0:
            print(f"Trip '{trip_data['name']}' already exists with {existing_snacks} snacks")
            return
        print(f"Trip '{trip_data['name']}' exists but has no snacks, adding them")
    else:
        trip = Trip(
            name=trip_data["name"],
            first_day_fraction=trip_data["first_day_fraction"],
            full_days=trip_data["full_days"],
            last_day_fraction=trip_data["last_day_fraction"],
        )
        db.add(trip)
        db.flush()

    added = 0
    for snack_data in data["snacks"]:
        if snack_data["servings"] <= 0:
            continue
        ingredient = db.query(Ingredient).filter(Ingredient.name == snack_data["name"]).first()
        catalog_item = db.query(SnackCatalogItem).filter(
            SnackCatalogItem.ingredient_id == ingredient.id
        ).first()
        db.add(TripSnack(
            trip_id=trip.id,
            catalog_item_id=catalog_item.id,
            servings=snack_data["servings"],
        ))
        added += 1

    print(f"Trip '{trip_data['name']}': created with {added} snack selections")


def verify(db):
    print("\n--- Verification ---")
    recipes = db.query(Recipe).all()
    breakfasts = [r for r in recipes if r.category == "breakfast"]
    dinners = [r for r in recipes if r.category == "dinner"]
    status = "PASS" if len(recipes) == 12 and len(breakfasts) == 6 and len(dinners) == 6 else "FAIL"
    print(f"[{status}] Recipe count: {len(recipes)} (breakfast={len(breakfasts)}, dinner={len(dinners)})")

    # Check Quickstart Cereal
    qc = db.query(Recipe).filter(Recipe.name == "Quickstart Cereal").first()
    if qc:
        ris = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == qc.id).all()
        total_weight = sum(ri.amount_oz for ri in ris)
        total_cal = sum(
            ri.amount_oz * (db.query(Ingredient).get(ri.ingredient_id).calories_per_oz or 0)
            for ri in ris
        )
        status = "PASS" if abs(total_weight - 4.5) < 0.1 and abs(total_cal - 617) < 10 else "FAIL"
        print(f"[{status}] Quickstart Cereal: {total_weight} oz, {total_cal:.0f} cal")

    # Check Cheesy Potatoes
    cp = db.query(Recipe).filter(Recipe.name == "Cheesy Potatoes").first()
    if cp:
        ris = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == cp.id).all()
        total_weight = sum(ri.amount_oz for ri in ris)
        total_cal = sum(
            ri.amount_oz * (db.query(Ingredient).get(ri.ingredient_id).calories_per_oz or 0)
            for ri in ris
        )
        status = "PASS" if abs(total_weight - 4.5) < 0.1 and abs(total_cal - 537) < 10 else "FAIL"
        print(f"[{status}] Cheesy Potatoes: {total_weight} oz, {total_cal:.0f} cal")

    # Check Utah 2026 snack totals
    trip = db.query(Trip).filter(Trip.name == "Utah 2026").first()
    if trip:
        trip_snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all()
        total_weight = 0
        total_cal = 0
        for ts in trip_snacks:
            cat_item = db.query(SnackCatalogItem).get(ts.catalog_item_id)
            total_weight += ts.servings * (cat_item.weight_per_serving or 0)
            total_cal += ts.servings * (cat_item.calories_per_serving or 0)
        avg_cal_per_oz = total_cal / total_weight if total_weight > 0 else 0
        wt_ok = abs(total_weight - 103) < 5
        cal_ok = abs(total_cal - 11745) < 200
        status = "PASS" if wt_ok and cal_ok else "FAIL"
        print(f"[{status}] Utah 2026 snacks: {total_weight:.1f} oz, {total_cal:.0f} cal, {avg_cal_per_oz:.0f} cal/oz")
    else:
        print("[FAIL] Utah 2026 trip not found")


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_skurka_recipes(db)
        seed_utah_2026_snacks(db)
        seed_utah_2026_trip(db)
        db.commit()
        verify(db)
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
