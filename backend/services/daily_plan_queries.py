"""Daily-plan read and regeneration implementation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import (
    AppSettings,
    Ingredient,
    Recipe,
    SnackCatalogItem,
    Trip,
    TripDayAssignment,
    TripMeal,
    TripSnack,
)
from services.autofill import auto_fill, build_day_list
from services.trip_queries import recipe_totals


def _autofill_inputs(db: Session, trip: Trip):
    recipe_weights: dict[int, float] = {}
    meals = []
    for selection in db.query(TripMeal).filter(TripMeal.trip_id == trip.id):
        recipe = db.get(Recipe, selection.recipe_id)
        if recipe.id not in recipe_weights:
            recipe_weights[recipe.id] = recipe_totals(db, recipe.id)["total_weight"]
        meals.append({
            "id": selection.id,
            "recipe_id": selection.recipe_id,
            "category": recipe.category,
            "quantity": selection.quantity,
        })
    snack_weights: dict[int, float] = {}
    snack_info: dict[int, dict] = {}
    snacks = []
    for selection in db.query(TripSnack).filter(TripSnack.trip_id == trip.id):
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        snack_weights[selection.id] = catalog_item.weight_per_serving or 0
        snack_info[selection.id] = {
            "drink_mix_type": catalog_item.drink_mix_type,
            "splittable": bool(catalog_item.splittable),
        }
        snacks.append({
            "id": selection.id,
            "slot": selection.slot,
            "servings": selection.servings,
            "category": catalog_item.category,
        })
    return meals, snacks, recipe_weights, snack_weights, snack_info


def _macro_target(db: Session) -> dict:
    settings = db.query(AppSettings).first()
    if not settings:
        return {"protein_pct": 20, "fat_pct": 30, "carb_pct": 50}
    return {
        "protein_pct": settings.macro_target_protein_pct,
        "fat_pct": settings.macro_target_fat_pct,
        "carb_pct": settings.macro_target_carb_pct,
    }


def _meal_info(db: Session, trip_id: int) -> dict[int, dict]:
    result = {}
    for selection in db.query(TripMeal).filter(TripMeal.trip_id == trip_id):
        recipe = db.get(Recipe, selection.recipe_id)
        totals = recipe_totals(db, recipe.id)
        result[selection.id] = {
            "name": recipe.name,
            "category": recipe.category,
            "weight": round(totals["total_weight"], 2),
            "calories": round(totals["total_calories"], 1),
            "quantity": selection.quantity,
            "protein_g": totals["protein_g"],
            "fat_g": totals["fat_g"],
            "carb_g": totals["carb_g"],
        }
    return result


def _snack_info(db: Session, trip_id: int) -> dict[int, dict]:
    result = {}
    for selection in db.query(TripSnack).filter(TripSnack.trip_id == trip_id):
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        ingredient = db.get(Ingredient, catalog_item.ingredient_id)
        weight_per_serving = catalog_item.weight_per_serving or 0
        result[selection.id] = {
            "name": ingredient.name,
            "category": catalog_item.category,
            "weight_per_serving": weight_per_serving,
            "calories_per_serving": catalog_item.calories_per_serving or 0,
            "total_servings": selection.servings,
            "slot": selection.slot,
            "protein_per_serving": (
                round((ingredient.protein_per_oz or 0) * weight_per_serving, 1)
                if ingredient.protein_per_oz is not None else None
            ),
            "fat_per_serving": (
                round((ingredient.fat_per_oz or 0) * weight_per_serving, 1)
                if ingredient.fat_per_oz is not None else None
            ),
            "carb_per_serving": (
                round((ingredient.carb_per_oz or 0) * weight_per_serving, 1)
                if ingredient.carb_per_oz is not None else None
            ),
        }
    return result


def _assignment_item(assignment: TripDayAssignment, info: dict) -> dict:
    if assignment.source_type == "meal":
        return {
            "id": assignment.id,
            "source_type": "meal",
            "source_id": assignment.source_id,
            "name": info.get("name", "?"),
            "category": info.get("category", "?"),
            "slot": assignment.slot,
            "servings": assignment.servings,
            "calories": round(info.get("calories", 0) * assignment.servings, 1),
            "weight": round(info.get("weight", 0) * assignment.servings, 2),
            "protein_g": round(info.get("protein_g", 0) * assignment.servings, 1),
            "fat_g": round(info.get("fat_g", 0) * assignment.servings, 1),
            "carb_g": round(info.get("carb_g", 0) * assignment.servings, 1),
        }
    return {
        "id": assignment.id,
        "source_type": "snack",
        "source_id": assignment.source_id,
        "name": info.get("name", "?"),
        "category": info.get("category", "?"),
        "slot": assignment.slot,
        "servings": assignment.servings,
        "calories": round(
            info.get("calories_per_serving", 0) * assignment.servings, 1
        ),
        "weight": round(
            info.get("weight_per_serving", 0) * assignment.servings, 2
        ),
        "protein_g": (
            round(info["protein_per_serving"] * assignment.servings, 1)
            if info.get("protein_per_serving") is not None else None
        ),
        "fat_g": (
            round(info["fat_per_serving"] * assignment.servings, 1)
            if info.get("fat_per_serving") is not None else None
        ),
        "carb_g": (
            round(info["carb_per_serving"] * assignment.servings, 1)
            if info.get("carb_per_serving") is not None else None
        ),
    }


def _add_day_macros(day: dict) -> None:
    items = day["items"]
    if not items:
        day["macros"] = None
        return
    macro_items = [
        item for item in items
        if any(item.get(key) is not None for key in ("protein_g", "fat_g", "carb_g"))
    ]
    if not macro_items:
        day["macros"] = None
        return
    protein = sum(item.get("protein_g") or 0 for item in macro_items)
    fat = sum(item.get("fat_g") or 0 for item in macro_items)
    carb = sum(item.get("carb_g") or 0 for item in macro_items)
    macro_calories = protein * 4 + fat * 9 + carb * 4
    total_calories = sum(item["calories"] for item in items)
    covered_calories = sum(item["calories"] for item in macro_items)
    day["macros"] = {
        "protein_g": round(protein, 1),
        "fat_g": round(fat, 1),
        "carb_g": round(carb, 1),
        "protein_pct": round(protein * 4 / macro_calories * 100, 1) if macro_calories else 0,
        "fat_pct": round(fat * 9 / macro_calories * 100, 1) if macro_calories else 0,
        "carb_pct": round(carb * 4 / macro_calories * 100, 1) if macro_calories else 0,
        "coverage_pct": (
            round(covered_calories / total_calories * 100, 1)
            if total_calories > 0 else None
        ),
    }


def daily_plan_view(db: Session, trip: Trip) -> dict:
    assignments = db.query(TripDayAssignment).filter(
        TripDayAssignment.trip_id == trip.id
    ).order_by(TripDayAssignment.day_number, TripDayAssignment.slot).all()
    days = build_day_list(trip)
    day_lookup = {day["day_number"]: day for day in days}
    total_days = sum(day["fraction"] for day in days)
    calories_per_full_day = (
        (trip.oz_per_day or 22) * (trip.cal_per_oz or 125) if total_days > 0 else 0
    )
    meals = _meal_info(db, trip.id)
    snacks = _snack_info(db, trip.id)
    days_out: dict[int, dict] = {}
    allocated: dict[str, float] = {}
    for assignment in assignments:
        day_info = day_lookup.get(
            assignment.day_number, {"fraction": 1.0, "type": "full"}
        )
        day = days_out.setdefault(assignment.day_number, {
            "day_number": assignment.day_number,
            "fraction": day_info["fraction"],
            "day_type": day_info["type"],
            "target_calories": round(
                calories_per_full_day * day_info["fraction"], 1
            ),
            "items": [],
        })
        info = (
            meals.get(assignment.source_id, {})
            if assignment.source_type == "meal"
            else snacks.get(assignment.source_id, {})
        )
        day["items"].append(_assignment_item(assignment, info))
        key = f"{assignment.source_type}:{assignment.source_id}"
        allocated[key] = allocated.get(key, 0) + assignment.servings
    for day_info in days:
        days_out.setdefault(day_info["day_number"], {
            "day_number": day_info["day_number"],
            "fraction": day_info["fraction"],
            "day_type": day_info["type"],
            "target_calories": round(
                calories_per_full_day * day_info["fraction"], 1
            ),
            "items": [],
        })
    for day in days_out.values():
        _add_day_macros(day)

    unallocated = []
    for source_id, info in meals.items():
        remaining = info["quantity"] - allocated.get(f"meal:{source_id}", 0)
        if remaining > 0:
            unallocated.append({
                "source_type": "meal",
                "source_id": source_id,
                "name": info["name"],
                "category": info["category"],
                "remaining_servings": remaining,
                "calories_per_serving": info["calories"],
                "weight_per_serving": info["weight"],
            })
    for source_id, info in snacks.items():
        remaining = info["total_servings"] - allocated.get(f"snack:{source_id}", 0)
        if remaining > 0.01:
            unallocated.append({
                "source_type": "snack",
                "source_id": source_id,
                "name": info["name"],
                "category": info["category"],
                "remaining_servings": round(remaining, 2),
                "calories_per_serving": info["calories_per_serving"],
                "weight_per_serving": info["weight_per_serving"],
            })
    return {
        "days": sorted(days_out.values(), key=lambda day: day["day_number"]),
        "unallocated": unallocated,
        "unallocated_summary": {
            "count": len(unallocated),
            "total_calories": round(sum(
                item["remaining_servings"] * item["calories_per_serving"]
                for item in unallocated
            ), 1),
            "total_weight": round(sum(
                item["remaining_servings"] * item["weight_per_serving"]
                for item in unallocated
            ), 1),
        },
        "warnings": [],
        "macro_target": _macro_target(db),
    }


def regenerate_daily_plan(db: Session, trip: Trip) -> dict:
    db.query(TripDayAssignment).filter(
        TripDayAssignment.trip_id == trip.id
    ).delete()
    inputs = _autofill_inputs(db, trip)
    assignments, warnings = auto_fill(trip, *inputs)
    for assignment in assignments:
        db.add(TripDayAssignment(trip_id=trip.id, **assignment))
    db.commit()
    response = daily_plan_view(db, trip)
    response["warnings"] = warnings
    return response
