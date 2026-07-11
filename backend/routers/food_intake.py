from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import SessionLocal
from models import FoodIntake
from schemas import FoodIntakeCreate, FoodIntakeUpdate, FoodIntakeOut

router = APIRouter(prefix="/api/food-intake", tags=["food-intake"])

VALID_STATUSES = {"pending", "researched", "added"}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=list[FoodIntakeOut])
def list_food_intake(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}.",
        )
    query = db.query(FoodIntake)
    if status is not None:
        query = query.filter(FoodIntake.status == status)
    return query.order_by(FoodIntake.id).all()


@router.post("", response_model=FoodIntakeOut, status_code=201)
def create_food_intake(data: FoodIntakeCreate, db: Session = Depends(get_db)):
    row = FoodIntake(
        name=data.name,
        notes=data.notes,
        status="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{intake_id}", response_model=FoodIntakeOut)
def update_food_intake(intake_id: int, data: FoodIntakeUpdate, db: Session = Depends(get_db)):
    row = db.get(FoodIntake, intake_id)
    if not row:
        raise HTTPException(status_code=404, detail="Food intake row not found")
    updates = data.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{updates['status']}'. Must be one of {sorted(VALID_STATUSES)}.",
        )
    for key, value in updates.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{intake_id}", status_code=204)
def delete_food_intake(intake_id: int, db: Session = Depends(get_db)):
    row = db.get(FoodIntake, intake_id)
    if not row:
        raise HTTPException(status_code=404, detail="Food intake row not found")
    db.delete(row)
    db.commit()
