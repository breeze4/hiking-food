"""HTTP adapter for daily-plan workflows."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal
from services.trip_planning import (
    TripNotFoundError,
    TripPlanningError,
    TripPlanningService,
    TripSelectionNotFoundError,
)


router = APIRouter(prefix="/api/trips", tags=["daily-plan"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _http_error(exc: TripPlanningError) -> HTTPException:
    status = 404 if isinstance(
        exc, (TripNotFoundError, TripSelectionNotFoundError)
    ) else 422
    return HTTPException(status_code=status, detail=str(exc))


class AssignmentCreate(BaseModel):
    day_number: int
    slot: str
    source_type: str
    source_id: int
    servings: float = 1


class AssignmentUpdate(BaseModel):
    day_number: Optional[int] = None
    slot: Optional[str] = None
    servings: Optional[float] = None


@router.get("/{trip_id}/daily-plan")
def get_daily_plan(trip_id: int, db: Session = Depends(get_db)):
    try:
        return TripPlanningService(db).read_daily_plan(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.post("/{trip_id}/daily-plan/auto-fill")
def run_auto_fill(trip_id: int, db: Session = Depends(get_db)):
    try:
        return TripPlanningService(db).regenerate_daily_plan(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.post("/{trip_id}/daily-plan/assignments", status_code=201)
def add_assignment(
    trip_id: int,
    data: AssignmentCreate,
    db: Session = Depends(get_db),
):
    service = TripPlanningService(db)
    try:
        service.add_assignment(trip_id, data.model_dump())
        return service.read_daily_plan(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.delete("/{trip_id}/daily-plan/assignments/{assignment_id}")
def delete_assignment(
    trip_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    service = TripPlanningService(db)
    try:
        service.remove_assignment(trip_id, assignment_id)
        return service.read_daily_plan(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.patch("/{trip_id}/daily-plan/assignments/{assignment_id}")
def update_assignment(
    trip_id: int,
    assignment_id: int,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
):
    service = TripPlanningService(db)
    try:
        service.update_assignment(
            trip_id,
            assignment_id,
            data.model_dump(exclude_unset=True),
        )
        return service.read_daily_plan(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc
