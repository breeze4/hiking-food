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


def _apply_macro_derivation(fields: dict) -> dict:
    """Apply calorie derivation rules to a dict of ingredient fields.

    - All three macros present: derive calories from macros (p*4 + f*9 + c*4)
    - Macros absent but calories present: null out macros, keep calories
    - Both macros and calories present: macros win
    """
    p = fields.get("protein_per_oz")
    f = fields.get("fat_per_oz")
    c = fields.get("carb_per_oz")

    if p is not None and f is not None and c is not None:
        # Macros win — derive calories
        fields["calories_per_oz"] = round(p * 4 + f * 9 + c * 4, 2)
    elif "calories_per_oz" in fields and fields["calories_per_oz"] is not None:
        # Direct calories — null out macros
        fields["protein_per_oz"] = None
        fields["fat_per_oz"] = None
        fields["carb_per_oz"] = None

    return fields


@router.get("", response_model=list[IngredientRead])
def list_ingredients(db: Session = Depends(get_db)):
    return db.query(Ingredient).all()


@router.post("", response_model=IngredientRead, status_code=201)
def create_ingredient(data: IngredientCreate, db: Session = Depends(get_db)):
    fields = _apply_macro_derivation(data.model_dump())
    ingredient = Ingredient(**fields)
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.put("/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(ingredient_id: int, data: IngredientUpdate, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).get(ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    updates = data.model_dump(exclude_unset=True)

    # For derivation, we need the full picture: merge existing values with updates
    p = updates.get("protein_per_oz", ingredient.protein_per_oz)
    f = updates.get("fat_per_oz", ingredient.fat_per_oz)
    c = updates.get("carb_per_oz", ingredient.carb_per_oz)

    has_macros = p is not None and f is not None and c is not None
    has_calories_update = "calories_per_oz" in updates and updates["calories_per_oz"] is not None
    has_macro_update = any(k in updates for k in ("protein_per_oz", "fat_per_oz", "carb_per_oz"))

    if has_macros and (has_macro_update or not has_calories_update):
        # Macros win — derive calories
        updates["calories_per_oz"] = round(p * 4 + f * 9 + c * 4, 2)
    elif has_calories_update and not has_macro_update:
        # Direct calories — null out macros
        updates["protein_per_oz"] = None
        updates["fat_per_oz"] = None
        updates["carb_per_oz"] = None

    for key, value in updates.items():
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
