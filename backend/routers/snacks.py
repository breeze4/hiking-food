from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import SessionLocal
from models import SnackCatalogItem, Ingredient, TripSnack
from schemas import SnackCreate, SnackUpdate, SnackRead
from services import catalog_queries

router = APIRouter(prefix="/api/snacks", tags=["snacks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[SnackRead])
def list_snacks(category: Optional[str] = Query(None), db: Session = Depends(get_db)):
    return catalog_queries.snack_list_view(db, category)


@router.post("", response_model=SnackRead, status_code=201)
def create_snack(data: SnackCreate, db: Session = Depends(get_db)):
    ingredient = db.get(Ingredient, data.ingredient_id)
    if not ingredient:
        raise HTTPException(status_code=400, detail="Ingredient not found")
    item = SnackCatalogItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return catalog_queries.snack_view(item, ingredient)


@router.put("/{snack_id}", response_model=SnackRead)
def update_snack(snack_id: int, data: SnackUpdate, db: Session = Depends(get_db)):
    item = db.get(SnackCatalogItem, snack_id)
    if not item:
        raise HTTPException(status_code=404, detail="Snack catalog item not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    ingredient = db.get(Ingredient, item.ingredient_id)
    return catalog_queries.snack_view(item, ingredient)


@router.delete("/{snack_id}", status_code=204)
def delete_snack(snack_id: int, db: Session = Depends(get_db)):
    item = db.get(SnackCatalogItem, snack_id)
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
