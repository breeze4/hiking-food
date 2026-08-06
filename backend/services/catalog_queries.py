"""Shared recipe and snack catalog projections behind a query boundary.

REST routers and the MCP tool surface both call these functions so the catalog
list/response shapes have a single source. Plain dicts, ``db: Session`` first
argument, no FastAPI imports.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    SnackCatalogItem,
    SnackUnitIngredient,
    SnackUnitType,
)
from services.recipe_calc import compute_recipe_totals

# A snack unit is nominally this heavy when no trip says otherwise. Library
# entries are trip-independent, so they always compare against this default;
# per-trip re-evaluation passes the trip's own oz_per_snack.
DEFAULT_OZ_PER_SNACK = 2.0
# Real food weights drift, so the band warns and never blocks.
SNACK_UNIT_WEIGHT_TOLERANCE = 0.25
# Sums of ounces land on binary-float neighbours of the band edges; 1.5 oz must
# read as inside the band even when it arrives as 1.5000000000000002.
_WEIGHT_EPSILON = 1e-9


def recipe_ingredients(db: Session, recipe_id: int) -> list[dict]:
    """Recipe ingredient rows with ingredient names, cal/oz, and macros."""
    rows = (
        db.query(
            RecipeIngredient,
            Ingredient.name,
            Ingredient.calories_per_oz,
            Ingredient.protein_per_oz,
            Ingredient.fat_per_oz,
            Ingredient.carb_per_oz,
        )
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )
    return [
        {
            "id": ri.id,
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": name,
            "amount_oz": ri.amount_oz,
            "calories_per_oz": cal_per_oz,
            "protein_per_oz": protein_per_oz,
            "fat_per_oz": fat_per_oz,
            "carb_per_oz": carb_per_oz,
            "calories": round(ri.amount_oz * (cal_per_oz or 0), 1),
        }
        for ri, name, cal_per_oz, protein_per_oz, fat_per_oz, carb_per_oz in rows
    ]


def recipe_list_view(db: Session, category: str | None = None) -> list[dict]:
    query = db.query(Recipe)
    if category:
        query = query.filter(Recipe.category == category)
    result = []
    for recipe in query.all():
        ingredients_data = recipe_ingredients(db, recipe.id)
        totals = compute_recipe_totals([
            {
                "amount_oz": i["amount_oz"],
                "calories_per_oz": i["calories_per_oz"],
                "protein_per_oz": i.get("protein_per_oz"),
                "fat_per_oz": i.get("fat_per_oz"),
                "carb_per_oz": i.get("carb_per_oz"),
            }
            for i in ingredients_data
        ])
        result.append({
            "id": recipe.id,
            "name": recipe.name,
            "category": recipe.category,
            "rating": recipe.rating,
            **totals,
        })
    return result


def snack_view(item: SnackCatalogItem, ingredient: Ingredient) -> dict:
    cal_per_oz = None
    if item.weight_per_serving and item.calories_per_serving:
        cal_per_oz = round(item.calories_per_serving / item.weight_per_serving, 1)
    wps = item.weight_per_serving or 0
    protein = round(ingredient.protein_per_oz * wps, 2) if ingredient.protein_per_oz is not None and wps else None
    fat = round(ingredient.fat_per_oz * wps, 2) if ingredient.fat_per_oz is not None and wps else None
    carb = round(ingredient.carb_per_oz * wps, 2) if ingredient.carb_per_oz is not None and wps else None
    return {
        "id": item.id,
        "ingredient_id": item.ingredient_id,
        "ingredient_name": ingredient.name,
        "weight_per_serving": item.weight_per_serving,
        "calories_per_serving": item.calories_per_serving,
        "calories_per_oz": cal_per_oz,
        "protein_per_serving": protein,
        "fat_per_serving": fat,
        "carb_per_serving": carb,
        "category": item.category,
        "drink_mix_type": item.drink_mix_type,
        "splittable": bool(item.splittable) if item.splittable is not None else False,
        "notes": item.notes,
        "rating": item.rating,
    }


def snack_list_view(db: Session, category: str | None = None) -> list[dict]:
    q = db.query(SnackCatalogItem, Ingredient).join(
        Ingredient, SnackCatalogItem.ingredient_id == Ingredient.id
    )
    if category:
        q = q.filter(SnackCatalogItem.category == category)
    return [snack_view(item, ingredient) for item, ingredient in q.all()]


# --- Snack unit types (bags) ---
#
# All composition math for bags lives here: weight is the sum of composition
# ounces, calories and macros come from per-oz ingredient data. Every consumer
# (trip summary, shopping, packing, daily plan, MCP) reads these views instead
# of recomputing.


def snack_unit_weight_warning(
    weight_oz: float, target_oz: float = DEFAULT_OZ_PER_SNACK
) -> bool:
    """True when a unit weight sits outside +/-25% of its target weight."""
    if not target_oz:
        return False
    low = target_oz * (1 - SNACK_UNIT_WEIGHT_TOLERANCE)
    high = target_oz * (1 + SNACK_UNIT_WEIGHT_TOLERANCE)
    return weight_oz < low - _WEIGHT_EPSILON or weight_oz > high + _WEIGHT_EPSILON


def _snack_unit_composition_rows(
    db: Session, unit_type_id: int | None = None
) -> list[dict]:
    query = (
        db.query(
            SnackUnitIngredient,
            Ingredient.name,
            Ingredient.calories_per_oz,
            Ingredient.protein_per_oz,
            Ingredient.fat_per_oz,
            Ingredient.carb_per_oz,
        )
        .join(Ingredient, SnackUnitIngredient.ingredient_id == Ingredient.id)
        .order_by(SnackUnitIngredient.id)
    )
    if unit_type_id is not None:
        query = query.filter(SnackUnitIngredient.unit_type_id == unit_type_id)
    rows = []
    for sui, name, cal_per_oz, protein_per_oz, fat_per_oz, carb_per_oz in query.all():
        amount = sui.amount_oz or 0
        rows.append({
            "id": sui.id,
            "unit_type_id": sui.unit_type_id,
            "ingredient_id": sui.ingredient_id,
            "ingredient_name": name,
            "amount_oz": amount,
            "calories_per_oz": cal_per_oz,
            "protein_per_oz": protein_per_oz,
            "fat_per_oz": fat_per_oz,
            "carb_per_oz": carb_per_oz,
            "calories": round(amount * (cal_per_oz or 0), 1),
        })
    return rows


def snack_unit_composition(db: Session, unit_type_id: int) -> list[dict]:
    """Composition rows for one unit type, with ingredient names and per-oz data."""
    return _snack_unit_composition_rows(db, unit_type_id)


def snack_unit_type_view(unit_type: SnackUnitType, composition: list[dict]) -> dict:
    """One unit type with its composition and every derived value."""
    totals = compute_recipe_totals([
        {
            "amount_oz": row["amount_oz"],
            "calories_per_oz": row["calories_per_oz"],
            "protein_per_oz": row["protein_per_oz"],
            "fat_per_oz": row["fat_per_oz"],
            "carb_per_oz": row["carb_per_oz"],
        }
        for row in composition
    ])
    weight_oz = totals["total_weight"]
    # An ingredient missing per-oz data contributes 0 rather than blocking the
    # bag; the flag tells consumers the derived numbers understate reality.
    has_full_data = all(
        row[field] is not None
        for row in composition
        for field in (
            "calories_per_oz", "protein_per_oz", "fat_per_oz", "carb_per_oz",
        )
    )
    return {
        "id": unit_type.id,
        "name": unit_type.name,
        "notes": unit_type.notes,
        "composition": composition,
        "weight_oz": weight_oz,
        "calories": totals["total_calories"],
        "cal_per_oz": totals["cal_per_oz"],
        "protein_g": totals["protein_g"],
        "fat_g": totals["fat_g"],
        "carb_g": totals["carb_g"],
        "weight_warning": snack_unit_weight_warning(weight_oz),
        "has_full_data": has_full_data,
    }


def snack_unit_type_list_view(db: Session) -> list[dict]:
    """Every unit type with composition and derived values, in one response."""
    by_unit_type: dict[int, list[dict]] = {}
    for row in _snack_unit_composition_rows(db):
        by_unit_type.setdefault(row["unit_type_id"], []).append(row)
    return [
        snack_unit_type_view(unit_type, by_unit_type.get(unit_type.id, []))
        for unit_type in db.query(SnackUnitType).order_by(SnackUnitType.name).all()
    ]
