from pydantic import BaseModel
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    Trip, TripMeal, TripSnack, TripDayAssignment,
    SnackCatalogItem, Ingredient, Recipe, RecipeIngredient,
    AppSettings,
)
from calculator import compute_trip_targets
from services.autofill import auto_fill, build_day_list
from services.recipe_calc import compute_recipe_totals

router = APIRouter(prefix="/api/trips", tags=["daily-plan"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_recipe_weight(db: Session, recipe_id: int) -> float:
    rows = (
        db.query(RecipeIngredient, Ingredient.calories_per_oz)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )
    ingredients = [
        {"amount_oz": ri.amount_oz, "calories_per_oz": cal_per_oz}
        for ri, cal_per_oz in rows
    ]
    return compute_recipe_totals(ingredients)["total_weight"]


def _gather_autofill_inputs(db: Session, trip: Trip):
    """Gather all data needed for auto-fill algorithm."""
    trip_meals_raw = db.query(TripMeal).filter(TripMeal.trip_id == trip.id).all()
    trip_snacks_raw = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all()

    recipe_weights = {}
    trip_meals = []
    for tm in trip_meals_raw:
        recipe = db.get(Recipe, tm.recipe_id)
        if recipe.id not in recipe_weights:
            recipe_weights[recipe.id] = _get_recipe_weight(db, recipe.id)
        trip_meals.append({
            "id": tm.id, "recipe_id": tm.recipe_id,
            "category": recipe.category, "quantity": tm.quantity,
        })

    snack_weights = {}
    snack_info = {}
    trip_snacks = []
    for ts in trip_snacks_raw:
        cat_item = db.get(SnackCatalogItem, ts.catalog_item_id)
        snack_weights[ts.id] = cat_item.weight_per_serving or 0
        snack_info[ts.id] = {"drink_mix_type": cat_item.drink_mix_type}
        trip_snacks.append({
            "id": ts.id, "slot": ts.slot, "servings": ts.servings,
            "category": cat_item.category,
        })

    return trip_meals, trip_snacks, recipe_weights, snack_weights, snack_info


def _build_daily_plan_response(db: Session, trip: Trip):
    """Build the full daily plan response."""
    assignments = db.query(TripDayAssignment).filter(
        TripDayAssignment.trip_id == trip.id
    ).order_by(TripDayAssignment.day_number, TripDayAssignment.slot).all()

    days_list = build_day_list(trip)
    days_map = {d["day_number"]: d for d in days_list}

    # Compute per-day calorie target using Skurka method
    total_days = sum(d["fraction"] for d in days_list)
    # Midpoint of target range: (19+24)/2 * 125 = 2687.5 cal per full day
    cal_per_full_day = (19 + 24) / 2 * 125 if total_days > 0 else 0

    # Fetch macro targets from app settings
    settings = db.query(AppSettings).first()
    if settings:
        macro_target = {
            "protein_pct": settings.macro_target_protein_pct,
            "fat_pct": settings.macro_target_fat_pct,
            "carb_pct": settings.macro_target_carb_pct,
        }
    else:
        macro_target = {"protein_pct": 20, "fat_pct": 30, "carb_pct": 50}

    # Build name/calorie lookup for meals and snacks
    meal_info = {}
    for tm in db.query(TripMeal).filter(TripMeal.trip_id == trip.id).all():
        recipe = db.get(Recipe, tm.recipe_id)
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == recipe.id)
            .all()
        )
        totals = compute_recipe_totals([
            {
                "amount_oz": ri.amount_oz,
                "calories_per_oz": ing.calories_per_oz,
                "protein_per_oz": ing.protein_per_oz,
                "fat_per_oz": ing.fat_per_oz,
                "carb_per_oz": ing.carb_per_oz,
            }
            for ri, ing in rows
        ])
        meal_info[tm.id] = {
            "name": recipe.name, "category": recipe.category,
            "weight": round(totals["total_weight"], 2),
            "calories": round(totals["total_calories"], 1),
            "quantity": tm.quantity,
            "protein_g": totals["protein_g"],
            "fat_g": totals["fat_g"],
            "carb_g": totals["carb_g"],
        }

    snack_info = {}
    for ts in db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all():
        cat_item = db.get(SnackCatalogItem, ts.catalog_item_id)
        ingredient = db.get(Ingredient, cat_item.ingredient_id)
        wps = cat_item.weight_per_serving or 0
        snack_info[ts.id] = {
            "name": ingredient.name, "category": cat_item.category,
            "weight_per_serving": wps,
            "calories_per_serving": cat_item.calories_per_serving or 0,
            "total_servings": ts.servings,
            "slot": ts.slot,
            "protein_per_serving": round(
                (ingredient.protein_per_oz or 0) * wps, 1
            ) if ingredient.protein_per_oz is not None else None,
            "fat_per_serving": round(
                (ingredient.fat_per_oz or 0) * wps, 1
            ) if ingredient.fat_per_oz is not None else None,
            "carb_per_serving": round(
                (ingredient.carb_per_oz or 0) * wps, 1
            ) if ingredient.carb_per_oz is not None else None,
        }

    # Group assignments by day
    days_out = {}
    allocated = {}  # source_type:source_id -> total assigned servings
    for a in assignments:
        day_num = a.day_number
        if day_num not in days_out:
            day_info = days_map.get(day_num, {"fraction": 1.0, "type": "full"})
            days_out[day_num] = {
                "day_number": day_num,
                "fraction": day_info["fraction"],
                "day_type": day_info["type"],
                "target_calories": round(cal_per_full_day * day_info["fraction"], 1),
                "items": [],
            }

        if a.source_type == "meal":
            info = meal_info.get(a.source_id, {})
            item = {
                "id": a.id,
                "source_type": "meal",
                "source_id": a.source_id,
                "name": info.get("name", "?"),
                "category": info.get("category", "?"),
                "slot": a.slot,
                "servings": a.servings,
                "calories": round(info.get("calories", 0) * a.servings, 1),
                "weight": round(info.get("weight", 0) * a.servings, 2),
                "protein_g": round(info.get("protein_g", 0) * a.servings, 1),
                "fat_g": round(info.get("fat_g", 0) * a.servings, 1),
                "carb_g": round(info.get("carb_g", 0) * a.servings, 1),
            }
        else:
            info = snack_info.get(a.source_id, {})
            p_per = info.get("protein_per_serving")
            f_per = info.get("fat_per_serving")
            c_per = info.get("carb_per_serving")
            item = {
                "id": a.id,
                "source_type": "snack",
                "source_id": a.source_id,
                "name": info.get("name", "?"),
                "category": info.get("category", "?"),
                "slot": a.slot,
                "servings": a.servings,
                "calories": round(info.get("calories_per_serving", 0) * a.servings, 1),
                "weight": round(info.get("weight_per_serving", 0) * a.servings, 2),
                "protein_g": round(p_per * a.servings, 1) if p_per is not None else None,
                "fat_g": round(f_per * a.servings, 1) if f_per is not None else None,
                "carb_g": round(c_per * a.servings, 1) if c_per is not None else None,
            }

        days_out[day_num]["items"].append(item)
        key = f"{a.source_type}:{a.source_id}"
        allocated[key] = allocated.get(key, 0) + a.servings

    # Ensure all days present even if empty
    for d in days_list:
        if d["day_number"] not in days_out:
            days_out[d["day_number"]] = {
                "day_number": d["day_number"],
                "fraction": d["fraction"],
                "day_type": d["type"],
                "target_calories": round(cal_per_full_day * d["fraction"], 1),
                "items": [],
            }

    # Compute per-day macro breakdown
    for day_obj in days_out.values():
        items = day_obj["items"]
        if not items:
            day_obj["macros"] = None
            continue

        total_p = 0.0
        total_f = 0.0
        total_c = 0.0
        has_any_macro = False
        total_cal = sum(i["calories"] for i in items)
        macro_cal = 0.0  # calories from items that have macro data

        for item in items:
            p = item.get("protein_g")
            f = item.get("fat_g")
            c = item.get("carb_g")
            if p is not None or f is not None or c is not None:
                has_any_macro = True
                total_p += p or 0
                total_f += f or 0
                total_c += c or 0
                macro_cal += item["calories"]

        if not has_any_macro:
            day_obj["macros"] = None
            continue

        # Compute percentages from calorie equivalents
        cal_from_macros = total_p * 4 + total_f * 9 + total_c * 4
        if cal_from_macros > 0:
            p_pct = round(total_p * 4 / cal_from_macros * 100, 1)
            f_pct = round(total_f * 9 / cal_from_macros * 100, 1)
            c_pct = round(total_c * 4 / cal_from_macros * 100, 1)
        else:
            p_pct = f_pct = c_pct = 0

        coverage_pct = round(macro_cal / total_cal * 100, 1) if total_cal > 0 else None

        day_obj["macros"] = {
            "protein_g": round(total_p, 1),
            "fat_g": round(total_f, 1),
            "carb_g": round(total_c, 1),
            "protein_pct": p_pct,
            "fat_pct": f_pct,
            "carb_pct": c_pct,
            "coverage_pct": coverage_pct,
        }

    # Build unallocated pool
    unallocated = []
    for tm_id, info in meal_info.items():
        assigned = allocated.get(f"meal:{tm_id}", 0)
        remaining = info["quantity"] - assigned
        if remaining > 0:
            unallocated.append({
                "source_type": "meal",
                "source_id": tm_id,
                "name": info["name"],
                "category": info["category"],
                "remaining_servings": remaining,
                "calories_per_serving": info["calories"],
                "weight_per_serving": info["weight"],
            })
    for ts_id, info in snack_info.items():
        assigned = allocated.get(f"snack:{ts_id}", 0)
        remaining = info["total_servings"] - assigned
        if remaining > 0.01:
            unallocated.append({
                "source_type": "snack",
                "source_id": ts_id,
                "name": info["name"],
                "category": info["category"],
                "remaining_servings": round(remaining, 2),
                "calories_per_serving": info["calories_per_serving"],
                "weight_per_serving": info["weight_per_serving"],
            })

    return {
        "days": sorted(days_out.values(), key=lambda d: d["day_number"]),
        "unallocated": unallocated,
        "warnings": [],
        "macro_target": macro_target,
    }


@router.get("/{trip_id}/daily-plan")
def get_daily_plan(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return _build_daily_plan_response(db, trip)


@router.post("/{trip_id}/daily-plan/auto-fill")
def run_auto_fill(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Clear existing assignments
    db.query(TripDayAssignment).filter(TripDayAssignment.trip_id == trip_id).delete()

    # Run auto-fill
    trip_meals, trip_snacks, recipe_weights, snack_weights, snack_info_data = _gather_autofill_inputs(db, trip)
    assignments, warnings = auto_fill(
        trip, trip_meals, trip_snacks, recipe_weights, snack_weights, snack_info_data
    )

    # Save assignments
    for a in assignments:
        db.add(TripDayAssignment(trip_id=trip_id, **a))
    db.commit()

    response = _build_daily_plan_response(db, trip)
    response["warnings"] = warnings
    return response


# --- Assignment CRUD ---

class AssignmentCreate(BaseModel):
    day_number: int
    slot: str
    source_type: str  # meal or snack
    source_id: int
    servings: float = 1


class AssignmentUpdate(BaseModel):
    servings: Optional[float] = None


@router.post("/{trip_id}/daily-plan/assignments", status_code=201)
def add_assignment(trip_id: int, data: AssignmentCreate, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    assignment = TripDayAssignment(trip_id=trip_id, **data.model_dump())
    db.add(assignment)
    db.commit()
    return _build_daily_plan_response(db, trip)


@router.delete("/{trip_id}/daily-plan/assignments/{assignment_id}")
def delete_assignment(trip_id: int, assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.get(TripDayAssignment, assignment_id)
    if not assignment or assignment.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    trip = db.get(Trip, trip_id)
    return _build_daily_plan_response(db, trip)


@router.patch("/{trip_id}/daily-plan/assignments/{assignment_id}")
def update_assignment(trip_id: int, assignment_id: int, data: AssignmentUpdate, db: Session = Depends(get_db)):
    assignment = db.get(TripDayAssignment, assignment_id)
    if not assignment or assignment.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if data.servings is not None:
        assignment.servings = data.servings
    db.commit()
    trip = db.get(Trip, trip_id)
    return _build_daily_plan_response(db, trip)
