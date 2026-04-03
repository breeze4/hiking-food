from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Ingredient, RecipeIngredient, SnackCatalogItem
from schemas import IngredientCreate, IngredientUpdate, IngredientRead

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[IngredientRead])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(Ingredient).all()


@router.post("", response_model=IngredientRead, status_code=201)
def create_ingredient(data: IngredientCreate, db: Session = Depends(get_db)):
    ingredient = Ingredient(**data.model_dump())
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.put("/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(ingredient_id: int, data: IngredientUpdate, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).get(ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(ingredient, key, value)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.patch("/{ingredient_id}/on-hand", response_model=IngredientRead)
def toggle_on_hand(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = db.get(Ingredient, ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    ingredient.on_hand = not ingredient.on_hand
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.delete("/{ingredient_id}", status_code=204)
def delete_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).get(ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    # Check for references
    recipe_ref = db.query(RecipeIngredient).filter(
        RecipeIngredient.ingredient_id == ingredient_id
    ).first()
    snack_ref = db.query(SnackCatalogItem).filter(
        SnackCatalogItem.ingredient_id == ingredient_id
    ).first()
    if recipe_ref or snack_ref:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: ingredient is referenced by recipes or snack catalog items",
        )
    db.delete(ingredient)
    db.commit()
