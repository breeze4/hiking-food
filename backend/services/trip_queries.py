"""Read projections hidden behind the trip-planning application boundary."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import (
    AppSettings,
    Ingredient,
    Recipe,
    RecipeIngredient,
    SnackCatalogItem,
    Trip,
    TripMeal,
    TripSnack,
)
from calculator import compute_trip_targets
from services.autofill import build_day_list
from services.recipe_calc import compute_recipe_totals


def recipe_totals(db: Session, recipe_id: int) -> dict:
    rows = (
        db.query(RecipeIngredient, Ingredient)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )
    return compute_recipe_totals([
        {
            "amount_oz": recipe_ingredient.amount_oz,
            "calories_per_oz": ingredient.calories_per_oz,
            "protein_per_oz": ingredient.protein_per_oz,
            "fat_per_oz": ingredient.fat_per_oz,
            "carb_per_oz": ingredient.carb_per_oz,
        }
        for recipe_ingredient, ingredient in rows
    ])


def trip_snack_view(db: Session, selection: TripSnack) -> dict:
    catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
    ingredient = db.get(Ingredient, catalog_item.ingredient_id)
    weight_per_serving = catalog_item.weight_per_serving or 0
    calories_per_serving = catalog_item.calories_per_serving or 0
    return {
        "id": selection.id,
        "catalog_item_id": selection.catalog_item_id,
        "ingredient_name": ingredient.name,
        "weight_per_serving": catalog_item.weight_per_serving,
        "calories_per_serving": catalog_item.calories_per_serving,
        "calories_per_oz": (
            round(calories_per_serving / weight_per_serving, 1)
            if weight_per_serving > 0 else None
        ),
        "protein_per_serving": (
            round(ingredient.protein_per_oz * weight_per_serving, 2)
            if ingredient.protein_per_oz is not None and weight_per_serving else None
        ),
        "fat_per_serving": (
            round(ingredient.fat_per_oz * weight_per_serving, 2)
            if ingredient.fat_per_oz is not None and weight_per_serving else None
        ),
        "carb_per_serving": (
            round(ingredient.carb_per_oz * weight_per_serving, 2)
            if ingredient.carb_per_oz is not None and weight_per_serving else None
        ),
        "category": catalog_item.category,
        "slot": selection.slot,
        "servings": selection.servings,
        "total_weight": round(selection.servings * weight_per_serving, 2),
        "total_calories": round(selection.servings * calories_per_serving, 1),
        "packed": selection.packed,
        "actual_weight_oz": selection.actual_weight_oz,
        "trip_notes": selection.trip_notes,
    }


def trip_meal_view(db: Session, selection: TripMeal) -> dict:
    recipe = db.get(Recipe, selection.recipe_id)
    totals = recipe_totals(db, recipe.id)
    return {
        "id": selection.id,
        "recipe_id": selection.recipe_id,
        "recipe_name": recipe.name,
        "category": recipe.category,
        "quantity": selection.quantity,
        "weight_per_unit": totals["total_weight"],
        "total_weight": round(totals["total_weight"] * selection.quantity, 2),
        "total_calories": round(totals["total_calories"] * selection.quantity, 1),
        "packed": selection.packed,
        "actual_weight_oz": selection.actual_weight_oz,
    }


def trip_detail_view(db: Session, trip: Trip) -> dict:
    snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all()
    meals = db.query(TripMeal).filter(TripMeal.trip_id == trip.id).all()
    return {
        "id": trip.id,
        "name": trip.name,
        "first_day_fraction": trip.first_day_fraction,
        "full_days": trip.full_days,
        "last_day_fraction": trip.last_day_fraction,
        "drink_mixes_per_day": (
            trip.drink_mixes_per_day if trip.drink_mixes_per_day is not None else 2
        ),
        "oz_per_day": trip.oz_per_day if trip.oz_per_day is not None else 22,
        "cal_per_oz": trip.cal_per_oz if trip.cal_per_oz is not None else 125,
        "snacks": [trip_snack_view(db, selection) for selection in snacks],
        "meals": [trip_meal_view(db, selection) for selection in meals],
    }


def trip_list_view(db: Session, *, newest_first: bool = False) -> list[dict]:
    query = db.query(Trip)
    if newest_first:
        query = query.order_by(Trip.id.desc())
    return [
        {
            "id": trip.id,
            "name": trip.name,
            "total_days": round(
                sum(day["fraction"] for day in build_day_list(trip)), 2
            ),
            "first_day_fraction": trip.first_day_fraction,
            "full_days": trip.full_days,
            "last_day_fraction": trip.last_day_fraction,
        }
        for trip in query.all()
    ]


def trip_summary_view(db: Session, trip: Trip) -> dict:
    trip_meals = db.query(TripMeal).filter(TripMeal.trip_id == trip.id).all()
    meal_weights: list[float] = []
    meal_weight_actual = meal_calories_actual = 0.0
    breakfast_weight = breakfast_calories = dinner_weight = dinner_calories = 0.0
    breakfast_count = dinner_count = 0
    total_protein_g = total_fat_g = total_carb_g = 0.0
    macro_covered_calories = total_all_calories = 0.0

    for selection in trip_meals:
        recipe = db.get(Recipe, selection.recipe_id)
        totals = recipe_totals(db, selection.recipe_id)
        weight = totals["total_weight"] * selection.quantity
        calories = totals["total_calories"] * selection.quantity
        if recipe.category == "breakfast":
            breakfast_weight += weight
            breakfast_calories += calories
            breakfast_count += selection.quantity
        else:
            dinner_weight += weight
            dinner_calories += calories
            dinner_count += selection.quantity
        meal_weights.extend([totals["total_weight"]] * selection.quantity)
        meal_weight_actual += weight
        meal_calories_actual += calories
        total_protein_g += totals["protein_g"] * selection.quantity
        total_fat_g += totals["fat_g"] * selection.quantity
        total_carb_g += totals["carb_g"] * selection.quantity
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == selection.recipe_id)
            .all()
        )
        for recipe_ingredient, ingredient in rows:
            ingredient_calories = (
                recipe_ingredient.amount_oz
                * (ingredient.calories_per_oz or 0)
                * selection.quantity
            )
            total_all_calories += ingredient_calories
            if any(value is not None for value in (
                ingredient.protein_per_oz,
                ingredient.fat_per_oz,
                ingredient.carb_per_oz,
            )):
                macro_covered_calories += ingredient_calories

    targets = compute_trip_targets(
        trip.first_day_fraction or 0,
        trip.full_days or 0,
        trip.last_day_fraction or 0,
        meal_weights,
        oz_per_day=trip.oz_per_day or 22,
        cal_per_oz=trip.cal_per_oz or 125,
    )

    snack_weight = snack_calories = drink_mix_weight = drink_mix_calories = 0.0
    slot_subtotals: dict[str, dict] = {}
    trip_snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all()
    for selection in trip_snacks:
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        ingredient = db.get(Ingredient, catalog_item.ingredient_id)
        weight = selection.servings * (catalog_item.weight_per_serving or 0)
        calories = selection.servings * (catalog_item.calories_per_serving or 0)
        snack_weight += weight
        snack_calories += calories
        if catalog_item.category == "drink_mix":
            drink_mix_weight += weight
            drink_mix_calories += calories
        else:
            slot = selection.slot or "snacks"
            subtotal = slot_subtotals.setdefault(slot, {"weight": 0, "calories": 0})
            subtotal["weight"] += weight
            subtotal["calories"] += calories
        weight_per_serving = catalog_item.weight_per_serving or 0
        has_macros = any(value is not None for value in (
            ingredient.protein_per_oz,
            ingredient.fat_per_oz,
            ingredient.carb_per_oz,
        ))
        if ingredient.protein_per_oz is not None:
            total_protein_g += (
                ingredient.protein_per_oz * weight_per_serving * selection.servings
            )
        if ingredient.fat_per_oz is not None:
            total_fat_g += (
                ingredient.fat_per_oz * weight_per_serving * selection.servings
            )
        if ingredient.carb_per_oz is not None:
            total_carb_g += (
                ingredient.carb_per_oz * weight_per_serving * selection.servings
            )
        total_all_calories += calories
        if has_macros:
            macro_covered_calories += calories

    remaining_calories = targets["daytime_cal"] - drink_mix_calories
    total_days = targets["total_days"]
    for slot, percentage in {"lunch": 0.40, "snacks": 0.60}.items():
        subtotal = slot_subtotals.setdefault(slot, {"weight": 0, "calories": 0})
        target = round(remaining_calories * percentage, 1)
        daily_target = (
            remaining_calories * percentage / total_days if total_days > 0 else 0
        )
        subtotal.update({
            "target_cal": target,
            "target_cal_low": round(target * 0.9, 1),
            "target_cal_high": round(target * 1.1, 1),
            "days_covered": (
                round(subtotal["calories"] / daily_target, 1)
                if daily_target > 0 else None
            ),
            "weight": round(subtotal["weight"], 2),
            "calories": round(subtotal["calories"], 1),
        })

    total_macro_calories = total_protein_g * 4 + total_fat_g * 9 + total_carb_g * 4
    macro_actual = None
    if total_macro_calories > 0:
        macro_actual = {
            "protein_g": round(total_protein_g, 1),
            "fat_g": round(total_fat_g, 1),
            "carb_g": round(total_carb_g, 1),
            "protein_pct": round(total_protein_g * 4 / total_macro_calories * 100, 1),
            "fat_pct": round(total_fat_g * 9 / total_macro_calories * 100, 1),
            "carb_pct": round(total_carb_g * 4 / total_macro_calories * 100, 1),
        }
    settings = db.query(AppSettings).first()
    macro_target = (
        {
            "protein_pct": settings.macro_target_protein_pct,
            "fat_pct": settings.macro_target_fat_pct,
            "carb_pct": settings.macro_target_carb_pct,
        }
        if settings else {"protein_pct": 20, "fat_pct": 30, "carb_pct": 50}
    )
    combined_weight = snack_weight + meal_weight_actual
    combined_calories = snack_calories + meal_calories_actual
    return {
        **targets,
        "snack_weight": round(snack_weight, 2),
        "snack_calories": round(snack_calories, 1),
        "snack_cal_per_oz": (
            round(snack_calories / snack_weight, 1) if snack_weight > 0 else None
        ),
        "drink_mix_weight": round(drink_mix_weight, 2),
        "drink_mix_calories": round(drink_mix_calories, 1),
        "slot_subtotals": slot_subtotals,
        "meal_weight_actual": round(meal_weight_actual, 2),
        "meal_calories_actual": round(meal_calories_actual, 1),
        "breakfast_weight": round(breakfast_weight, 2),
        "breakfast_calories": round(breakfast_calories, 1),
        "breakfast_count": breakfast_count,
        "dinner_weight": round(dinner_weight, 2),
        "dinner_calories": round(dinner_calories, 1),
        "dinner_count": dinner_count,
        "combined_weight": round(combined_weight, 2),
        "combined_calories": round(combined_calories, 1),
        "weight_per_day": (
            round(combined_weight / total_days, 1) if total_days > 0 else None
        ),
        "cal_per_day": (
            round(combined_calories / total_days, 1) if total_days > 0 else None
        ),
        "macro_actual": macro_actual,
        "macro_target": macro_target,
        "macro_coverage_pct": (
            round(macro_covered_calories / total_all_calories * 100, 1)
            if total_all_calories > 0 else None
        ),
    }


def packing_view(db: Session, trip: Trip) -> dict:
    meals = []
    for selection in db.query(TripMeal).filter(TripMeal.trip_id == trip.id):
        recipe = db.get(Recipe, selection.recipe_id)
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == recipe.id)
            .all()
        )
        meals.append({
            "id": selection.id,
            "recipe_name": recipe.name,
            "category": recipe.category,
            "quantity": selection.quantity,
            "at_home_prep": recipe.at_home_prep,
            "ingredients": [
                {
                    "name": ingredient.name,
                    "amount_oz": round(recipe_ingredient.amount_oz * selection.quantity, 2),
                    "essentials": bool(ingredient.essentials),
                    "packing_method": ingredient.packing_method,
                }
                for recipe_ingredient, ingredient in rows
            ],
            "packed": selection.packed,
            "actual_weight_oz": selection.actual_weight_oz,
        })
    snacks = []
    for selection in db.query(TripSnack).filter(TripSnack.trip_id == trip.id):
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        ingredient = db.get(Ingredient, catalog_item.ingredient_id)
        snacks.append({
            "id": selection.id,
            "ingredient_name": ingredient.name,
            "slot": selection.slot,
            "target_weight": round(
                selection.servings * (catalog_item.weight_per_serving or 0), 2
            ),
            "target_calories": round(
                selection.servings * (catalog_item.calories_per_serving or 0), 1
            ),
            "servings": selection.servings,
            "packed": selection.packed,
            "actual_weight_oz": selection.actual_weight_oz,
            "packing_method": ingredient.packing_method,
        })
    return {"trip_name": trip.name, "meals": meals, "snacks": snacks}


def shopping_view(db: Session, trip: Trip) -> dict:
    totals: dict[int, dict] = {}
    for selection in db.query(TripMeal).filter(TripMeal.trip_id == trip.id):
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == selection.recipe_id)
            .all()
        )
        for recipe_ingredient, ingredient in rows:
            item = totals.setdefault(recipe_ingredient.ingredient_id, {
                "ingredient_id": recipe_ingredient.ingredient_id,
                "ingredient_name": ingredient.name,
                "total_oz": 0,
                "on_hand": bool(ingredient.on_hand),
                "essentials": bool(ingredient.essentials),
                "packing_method": ingredient.packing_method,
            })
            item["total_oz"] += recipe_ingredient.amount_oz * selection.quantity
    for selection in db.query(TripSnack).filter(TripSnack.trip_id == trip.id):
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        ingredient = db.get(Ingredient, catalog_item.ingredient_id)
        item = totals.setdefault(catalog_item.ingredient_id, {
            "ingredient_id": catalog_item.ingredient_id,
            "ingredient_name": ingredient.name,
            "total_oz": 0,
            "on_hand": bool(ingredient.on_hand),
            "essentials": bool(ingredient.essentials),
            "packing_method": ingredient.packing_method,
        })
        item["total_oz"] += selection.servings * (catalog_item.weight_per_serving or 0)
    for item in totals.values():
        item["total_oz"] = round(item["total_oz"], 2)
    regular = [item for item in totals.values() if not item["essentials"]]
    essentials = [item for item in totals.values() if item["essentials"]]
    regular.sort(key=lambda item: (item["on_hand"], item["ingredient_name"]))
    essentials.sort(key=lambda item: item["ingredient_name"])
    return {"items": regular, "essentials": essentials}
