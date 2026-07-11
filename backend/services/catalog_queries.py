"""Shared recipe and snack catalog projections behind a query boundary.

REST routers and the MCP tool surface both call these functions so the catalog
list/response shapes have a single source. Plain dicts, ``db: Session`` first
argument, no FastAPI imports.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import Ingredient, Recipe, RecipeIngredient, SnackCatalogItem
from services.recipe_calc import compute_recipe_totals


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
