"""FastAPI adapter for the trip-planning application boundary."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from schemas import (
    TripCreate,
    TripDetailRead,
    TripListRead,
    TripMealCreate,
    TripMealRead,
    TripMealUpdate,
    TripSnackCreate,
    TripSnackRead,
    TripSnackUpdate,
    TripSummaryRead,
    TripUpdate,
)
from services.trip_planning import (
    FoodOptionNotFoundError,
    TripConflictError,
    TripNotFoundError,
    TripPlanningError,
    TripPlanningService,
    TripSelectionNotFoundError,
)
from services.trip_queries import trip_meal_view, trip_snack_view


router = APIRouter(prefix="/api/trips", tags=["trips"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _http_error(exc: TripPlanningError) -> HTTPException:
    if isinstance(exc, (TripNotFoundError, TripSelectionNotFoundError)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, TripConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, FoodOptionNotFoundError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


@router.get("", response_model=list[TripListRead])
def list_trips(db: Session = Depends(get_db)):
    return TripPlanningService(db).list_trips()


@router.get("/{trip_id}", response_model=TripDetailRead)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    try:
        return TripPlanningService(db).read_trip(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.post("", response_model=TripDetailRead, status_code=201)
def create_trip(data: TripCreate, db: Session = Depends(get_db)):
    planner = TripPlanningService(db)
    try:
        trip = planner.create_trip(data.model_dump())
        return planner.read_trip(trip.id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.put("/{trip_id}", response_model=TripDetailRead)
def update_trip(trip_id: int, data: TripUpdate, db: Session = Depends(get_db)):
    planner = TripPlanningService(db)
    try:
        trip = planner.update_trip(trip_id, data.model_dump(exclude_unset=True))
        return planner.read_trip(trip.id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.delete("/{trip_id}", status_code=204)
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    try:
        TripPlanningService(db).delete_trip(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.post("/{trip_id}/snacks", response_model=TripSnackRead, status_code=201)
def add_trip_snack(
    trip_id: int,
    data: TripSnackCreate,
    db: Session = Depends(get_db),
):
    try:
        selection = TripPlanningService(db).add_snack(trip_id, data.model_dump())
        return trip_snack_view(db, selection)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.put("/{trip_id}/snacks/{snack_id}", response_model=TripSnackRead)
def update_trip_snack(
    trip_id: int,
    snack_id: int,
    data: TripSnackUpdate,
    db: Session = Depends(get_db),
):
    try:
        selection = TripPlanningService(db).update_snack(
            trip_id,
            snack_id,
            data.model_dump(exclude_unset=True),
        )
        return trip_snack_view(db, selection)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.delete("/{trip_id}/snacks/{snack_id}", status_code=204)
def remove_trip_snack(
    trip_id: int,
    snack_id: int,
    db: Session = Depends(get_db),
):
    try:
        TripPlanningService(db).remove_snack(trip_id, snack_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.post("/{trip_id}/meals", response_model=TripMealRead, status_code=201)
def add_trip_meal(
    trip_id: int,
    data: TripMealCreate,
    db: Session = Depends(get_db),
):
    try:
        selection = TripPlanningService(db).add_meal(trip_id, data.model_dump())
        return trip_meal_view(db, selection)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.put("/{trip_id}/meals/{meal_id}", response_model=TripMealRead)
def update_trip_meal(
    trip_id: int,
    meal_id: int,
    data: TripMealUpdate,
    db: Session = Depends(get_db),
):
    try:
        selection = TripPlanningService(db).update_meal(
            trip_id,
            meal_id,
            data.model_dump(exclude_unset=True),
        )
        return trip_meal_view(db, selection)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.delete("/{trip_id}/meals/{meal_id}", status_code=204)
def remove_trip_meal(
    trip_id: int,
    meal_id: int,
    db: Session = Depends(get_db),
):
    try:
        TripPlanningService(db).remove_meal(trip_id, meal_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.get("/{trip_id}/summary", response_model=TripSummaryRead)
def get_trip_summary(trip_id: int, db: Session = Depends(get_db)):
    try:
        return TripPlanningService(db).read_summary(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.get("/{trip_id}/packing")
def get_packing_detail(trip_id: int, db: Session = Depends(get_db)):
    try:
        return TripPlanningService(db).read_packing(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.get("/{trip_id}/shopping-list")
def get_shopping_list(trip_id: int, db: Session = Depends(get_db)):
    try:
        return TripPlanningService(db).read_shopping(trip_id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc


@router.post("/{trip_id}/clone", response_model=TripDetailRead, status_code=201)
def clone_trip(trip_id: int, db: Session = Depends(get_db)):
    planner = TripPlanningService(db)
    try:
        clone = planner.clone_trip(trip_id, {})
        return planner.read_trip(clone.id)
    except TripPlanningError as exc:
        raise _http_error(exc) from exc
