from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import SessionLocal
from models import Recipe, RecipeIngredient, Ingredient, TripMeal
from schemas import (
    RecipeCreate, RecipeUpdate, RecipeListRead, RecipeDetailRead,
    RecipeIngredientRead,
)
from services.recipe_calc import compute_recipe_totals

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_recipe_ingredients(db: Session, recipe_id: int):
    """Get recipe ingredients with their ingredient names and cal/oz."""
    rows = (
        db.query(RecipeIngredient, Ingredient.name, Ingredient.calories_per_oz)
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
            "calories": round(ri.amount_oz * (cal_per_oz or 0), 1),
        }
        for ri, name, cal_per_oz in rows
    ]


def _build_detail(recipe: Recipe, ingredients_data: list) -> dict:
    totals = compute_recipe_totals([
        {"amount_oz": i["amount_oz"], "calories_per_oz": i["calories_per_oz"]}
        for i in ingredients_data
    ])
    return {
        "id": recipe.id,
        "name": recipe.name,
        "category": recipe.category,
        "rating": recipe.rating,
        "at_home_prep": recipe.at_home_prep,
        "field_prep": recipe.field_prep,
        "notes": recipe.notes,
        "ingredients": [
            RecipeIngredientRead(
                id=i["id"],
                ingredient_id=i["ingredient_id"],
                ingredient_name=i["ingredient_name"],
                amount_oz=i["amount_oz"],
                calories=i["calories"],
            )
            for i in ingredients_data
        ],
        **totals,
    }


def _set_recipe_ingredients(db: Session, recipe_id: int, ingredients: list):
    """Replace all recipe ingredients."""
    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()
    for ing in ingredients:
        # Validate ingredient exists
        if not db.query(Ingredient).get(ing.ingredient_id):
            raise HTTPException(status_code=400, detail=f"Ingredient {ing.ingredient_id} not found")
        db.add(RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=ing.ingredient_id,
            amount_oz=ing.amount_oz,
        ))


@router.get("", response_model=list[RecipeListRead])
def list_recipes(category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Recipe)
    if category:
        query = query.filter(Recipe.category == category)
    recipes = query.all()
    result = []
    for recipe in recipes:
        ingredients_data = _get_recipe_ingredients(db, recipe.id)
        totals = compute_recipe_totals([
            {"amount_oz": i["amount_oz"], "calories_per_oz": i["calories_per_oz"]}
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


@router.get("/{recipe_id}", response_model=RecipeDetailRead)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    ingredients_data = _get_recipe_ingredients(db, recipe.id)
    return _build_detail(recipe, ingredients_data)


@router.post("", response_model=RecipeDetailRead, status_code=201)
def create_recipe(data: RecipeCreate, db: Session = Depends(get_db)):
    recipe = Recipe(
        name=data.name,
        category=data.category,
        at_home_prep=data.at_home_prep,
        field_prep=data.field_prep,
        notes=data.notes,
        rating=data.rating,
    )
    db.add(recipe)
    db.flush()
    _set_recipe_ingredients(db, recipe.id, data.ingredients)
    db.commit()
    db.refresh(recipe)
    ingredients_data = _get_recipe_ingredients(db, recipe.id)
    return _build_detail(recipe, ingredients_data)


@router.put("/{recipe_id}", response_model=RecipeDetailRead)
def update_recipe(recipe_id: int, data: RecipeUpdate, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    update_data = data.model_dump(exclude_unset=True)
    ingredients_list = update_data.pop("ingredients", None)
    for key, value in update_data.items():
        setattr(recipe, key, value)
    if ingredients_list is not None:
        _set_recipe_ingredients(db, recipe.id, data.ingredients)
    db.commit()
    db.refresh(recipe)
    ingredients_data = _get_recipe_ingredients(db, recipe.id)
    return _build_detail(recipe, ingredients_data)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    trip_ref = db.query(TripMeal).filter(TripMeal.recipe_id == recipe_id).first()
    if trip_ref:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: recipe is used in trip meal plans",
        )
    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).delete()
    db.delete(recipe)
    db.commit()
