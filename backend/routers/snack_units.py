from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Ingredient, SnackUnitIngredient, SnackUnitType, TripSnackUnit
from schemas import SnackUnitTypeCreate, SnackUnitTypeRead, SnackUnitTypeUpdate
from services import catalog_queries

router = APIRouter(prefix="/api/snack-unit-types", tags=["snack-unit-types"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _detail(db: Session, unit_type: SnackUnitType) -> dict:
    return catalog_queries.snack_unit_type_view(
        unit_type, catalog_queries.snack_unit_composition(db, unit_type.id)
    )


def _set_composition(db: Session, unit_type_id: int, composition: list):
    """Replace all composition rows for a unit type."""
    db.query(SnackUnitIngredient).filter(
        SnackUnitIngredient.unit_type_id == unit_type_id
    ).delete()
    for row in composition:
        if not db.get(Ingredient, row.ingredient_id):
            raise HTTPException(
                status_code=400, detail=f"Ingredient {row.ingredient_id} not found"
            )
        db.add(SnackUnitIngredient(
            unit_type_id=unit_type_id,
            ingredient_id=row.ingredient_id,
            amount_oz=row.amount_oz,
        ))


@router.get("", response_model=list[SnackUnitTypeRead])
def list_snack_unit_types(db: Session = Depends(get_db)):
    return catalog_queries.snack_unit_type_list_view(db)


@router.get("/{unit_type_id}", response_model=SnackUnitTypeRead)
def get_snack_unit_type(unit_type_id: int, db: Session = Depends(get_db)):
    unit_type = db.get(SnackUnitType, unit_type_id)
    if not unit_type:
        raise HTTPException(status_code=404, detail="Snack unit type not found")
    return _detail(db, unit_type)


@router.post("", response_model=SnackUnitTypeRead, status_code=201)
def create_snack_unit_type(data: SnackUnitTypeCreate, db: Session = Depends(get_db)):
    unit_type = SnackUnitType(name=data.name, notes=data.notes)
    db.add(unit_type)
    db.flush()
    _set_composition(db, unit_type.id, data.composition)
    db.commit()
    db.refresh(unit_type)
    return _detail(db, unit_type)


@router.put("/{unit_type_id}", response_model=SnackUnitTypeRead)
def update_snack_unit_type(
    unit_type_id: int, data: SnackUnitTypeUpdate, db: Session = Depends(get_db)
):
    unit_type = db.get(SnackUnitType, unit_type_id)
    if not unit_type:
        raise HTTPException(status_code=404, detail="Snack unit type not found")
    update_data = data.model_dump(exclude_unset=True)
    composition = update_data.pop("composition", None)
    for key, value in update_data.items():
        setattr(unit_type, key, value)
    if composition is not None:
        _set_composition(db, unit_type.id, data.composition)
    db.commit()
    db.refresh(unit_type)
    return _detail(db, unit_type)


@router.delete("/{unit_type_id}", status_code=204)
def delete_snack_unit_type(unit_type_id: int, db: Session = Depends(get_db)):
    unit_type = db.get(SnackUnitType, unit_type_id)
    if not unit_type:
        raise HTTPException(status_code=404, detail="Snack unit type not found")
    trip_ref = db.query(TripSnackUnit).filter(
        TripSnackUnit.unit_type_id == unit_type_id
    ).first()
    if trip_ref:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete: snack unit type is used in trip snack selections",
        )
    db.query(SnackUnitIngredient).filter(
        SnackUnitIngredient.unit_type_id == unit_type_id
    ).delete()
    db.delete(unit_type)
    db.commit()
