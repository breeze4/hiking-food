from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import SessionLocal
from models import SnackCatalogItem, Ingredient, TripSnack
from schemas import SnackCreate, SnackUpdate, SnackRead

router = APIRouter(prefix="/api/snacks", tags=["snacks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _to_response(item: SnackCatalogItem, ingredient: Ingredient) -> dict:
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
        "notes": item.notes,
        "rating": item.rating,
    }


@router.get("", response_model=list[SnackRead])
def list_snacks(category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(SnackCatalogItem, Ingredient).join(
        Ingredient, SnackCatalogItem.ingredient_id == Ingredient.id
    )
    if category:
        q = q.filter(SnackCatalogItem.category == category)
    rows = q.all()
    return [_to_response(item, ing) for item, ing in rows]


@router.post("", response_model=SnackRead, status_code=201)
def create_snack(data: SnackCreate, db: Session = Depends(get_db)):
    ingredient = db.query(Ingredient).get(data.ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=400, detail="Ingredient not found")
    item = SnackCatalogItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_response(item, ingredient)


@router.put("/{snack_id}", response_model=SnackRead)
def update_snack(snack_id: int, data: SnackUpdate, db: Session = Depends(get_db)):
    item = db.query(SnackCatalogItem).get(snack_id)
    if not item:
        raise HTTPException(status_code=404, detail="Snack catalog item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    ingredient = db.query(Ingredient).get(item.ingredient_id)
    return _to_response(item, ingredient)


@router.delete("/{snack_id}", status_code=204)
def delete_snack(snack_id: int, db: Session = Depends(get_db)):
    item = db.query(SnackCatalogItem).get(snack_id)
    if not item:
        raise HTTPException(status_code=404, detail="Snack catalog item not found")
    trip_ref = db.query(TripSnack).filter(TripSnack.catalog_item_id == snack_id).first()
    if trip_ref:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: snack item is referenced by trip snack selections",
        )
    db.delete(item)
    db.commit()
