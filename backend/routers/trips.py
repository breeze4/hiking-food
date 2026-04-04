import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    Trip, TripSnack, TripMeal, SnackCatalogItem, Ingredient,
    Recipe, RecipeIngredient, AppSettings,
)
from schemas import (
    TripCreate, TripUpdate, TripListRead, TripDetailRead,
    TripSnackCreate, TripSnackUpdate, TripSnackRead,
    TripMealCreate, TripMealUpdate, TripMealRead,
    TripSummaryRead,
)
from calculator import compute_trip_targets
from services.recipe_calc import compute_recipe_totals

router = APIRouter(prefix="/api/trips", tags=["trips"])

CATEGORY_TO_SLOT = {
    "drink_mix": "snacks",
    "bars_energy": "snacks",
    "lunch": "lunch",
    "salty": "snacks",
    "sweet": "snacks",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _build_trip_snack(ts: TripSnack, db: Session) -> dict:
    cat_item = db.get(SnackCatalogItem, ts.catalog_item_id)
    ingredient = db.get(Ingredient, cat_item.ingredient_id)
    wps = cat_item.weight_per_serving or 0
    cps = cat_item.calories_per_serving or 0
    cal_per_oz = round(cps / wps, 1) if wps > 0 else None
    protein = round(ingredient.protein_per_oz * wps, 2) if ingredient.protein_per_oz is not None and wps else None
    fat = round(ingredient.fat_per_oz * wps, 2) if ingredient.fat_per_oz is not None and wps else None
    carb = round(ingredient.carb_per_oz * wps, 2) if ingredient.carb_per_oz is not None and wps else None
    return {
        "id": ts.id,
        "catalog_item_id": ts.catalog_item_id,
        "ingredient_name": ingredient.name,
        "weight_per_serving": cat_item.weight_per_serving,
        "calories_per_serving": cat_item.calories_per_serving,
        "calories_per_oz": cal_per_oz,
        "protein_per_serving": protein,
        "fat_per_serving": fat,
        "carb_per_serving": carb,
        "category": cat_item.category,
        "slot": ts.slot,
        "servings": ts.servings,
        "total_weight": round(ts.servings * wps, 2),
        "total_calories": round(ts.servings * cps, 1),
        "packed": ts.packed,
        "actual_weight_oz": ts.actual_weight_oz,
        "trip_notes": ts.trip_notes,
    }


def _get_recipe_totals(db: Session, recipe_id: int):
    rows = (
        db.query(RecipeIngredient, Ingredient)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )
    ingredients = [
        {
            "amount_oz": ri.amount_oz,
            "calories_per_oz": ing.calories_per_oz,
            "protein_per_oz": ing.protein_per_oz,
            "fat_per_oz": ing.fat_per_oz,
            "carb_per_oz": ing.carb_per_oz,
        }
        for ri, ing in rows
    ]
    return compute_recipe_totals(ingredients)


def _build_trip_meal(tm: TripMeal, db: Session) -> dict:
    recipe = db.get(Recipe, tm.recipe_id)
    totals = _get_recipe_totals(db, recipe.id)
    return {
        "id": tm.id,
        "recipe_id": tm.recipe_id,
        "recipe_name": recipe.name,
        "category": recipe.category,
        "quantity": tm.quantity,
        "weight_per_unit": totals["total_weight"],
        "total_weight": round(totals["total_weight"] * tm.quantity, 2),
        "total_calories": round(totals["total_calories"] * tm.quantity, 1),
        "packed": tm.packed,
        "actual_weight_oz": tm.actual_weight_oz,
    }


def _build_trip_detail(trip: Trip, db: Session) -> dict:
    snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all()
    meals = db.query(TripMeal).filter(TripMeal.trip_id == trip.id).all()
    return {
        "id": trip.id,
        "name": trip.name,
        "first_day_fraction": trip.first_day_fraction,
        "full_days": trip.full_days,
        "last_day_fraction": trip.last_day_fraction,
        "drink_mixes_per_day": trip.drink_mixes_per_day if trip.drink_mixes_per_day is not None else 2,
        "oz_per_day": trip.oz_per_day if trip.oz_per_day is not None else 22,
        "cal_per_oz": trip.cal_per_oz if trip.cal_per_oz is not None else 125,
        "snacks": [_build_trip_snack(ts, db) for ts in snacks],
        "meals": [_build_trip_meal(tm, db) for tm in meals],
    }


def _get_total_days(trip: Trip) -> float:
    return (trip.first_day_fraction or 0) + (trip.full_days or 0) + (trip.last_day_fraction or 0)


# --- Trip CRUD ---

@router.get("", response_model=list[TripListRead])
def list_trips(db: Session = Depends(get_db)):
    return db.query(Trip).all()


@router.get("/{trip_id}", response_model=TripDetailRead)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return _build_trip_detail(trip, db)


@router.post("", response_model=TripDetailRead, status_code=201)
def create_trip(data: TripCreate, db: Session = Depends(get_db)):
    trip = Trip(**data.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return _build_trip_detail(trip, db)


@router.put("/{trip_id}", response_model=TripDetailRead)
def update_trip(trip_id: int, data: TripUpdate, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(trip, key, value)
    db.commit()
    db.refresh(trip)
    return _build_trip_detail(trip, db)


@router.delete("/{trip_id}", status_code=204)
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    db.query(TripSnack).filter(TripSnack.trip_id == trip_id).delete()
    db.query(TripMeal).filter(TripMeal.trip_id == trip_id).delete()
    db.delete(trip)
    db.commit()


# --- Trip Snacks ---

@router.post("/{trip_id}/snacks", response_model=TripSnackRead, status_code=201)
def add_trip_snack(trip_id: int, data: TripSnackCreate, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    cat_item = db.get(SnackCatalogItem, data.catalog_item_id)
    if not cat_item:
        raise HTTPException(status_code=400, detail="Snack catalog item not found")
    fields = data.model_dump()
    if not fields.get("slot"):
        fields["slot"] = CATEGORY_TO_SLOT.get(cat_item.category, "snacks")
    if cat_item.category == "drink_mix":
        fields["servings"] = max(1, math.ceil(fields.get("servings") or 1))
    ts = TripSnack(trip_id=trip_id, **fields)
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return _build_trip_snack(ts, db)


@router.put("/{trip_id}/snacks/{snack_id}", response_model=TripSnackRead)
def update_trip_snack(trip_id: int, snack_id: int, data: TripSnackUpdate, db: Session = Depends(get_db)):
    ts = db.get(TripSnack, snack_id)
    if not ts or ts.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Trip snack not found")
    updates = data.model_dump(exclude_unset=True)
    if "servings" in updates:
        cat_item = db.get(SnackCatalogItem, ts.catalog_item_id)
        if cat_item and cat_item.category == "drink_mix":
            updates["servings"] = math.ceil(updates["servings"])
    for key, value in updates.items():
        setattr(ts, key, value)
    db.commit()
    db.refresh(ts)
    return _build_trip_snack(ts, db)


@router.delete("/{trip_id}/snacks/{snack_id}", status_code=204)
def remove_trip_snack(trip_id: int, snack_id: int, db: Session = Depends(get_db)):
    ts = db.get(TripSnack, snack_id)
    if not ts or ts.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Trip snack not found")
    db.delete(ts)
    db.commit()


# --- Trip Meals ---

@router.post("/{trip_id}/meals", response_model=TripMealRead, status_code=201)
def add_trip_meal(trip_id: int, data: TripMealCreate, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if not db.get(Recipe, data.recipe_id):
        raise HTTPException(status_code=400, detail="Recipe not found")
    tm = TripMeal(trip_id=trip_id, **data.model_dump())
    db.add(tm)
    db.commit()
    db.refresh(tm)
    return _build_trip_meal(tm, db)


@router.put("/{trip_id}/meals/{meal_id}", response_model=TripMealRead)
def update_trip_meal(trip_id: int, meal_id: int, data: TripMealUpdate, db: Session = Depends(get_db)):
    tm = db.get(TripMeal, meal_id)
    if not tm or tm.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Trip meal not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tm, key, value)
    db.commit()
    db.refresh(tm)
    return _build_trip_meal(tm, db)


@router.delete("/{trip_id}/meals/{meal_id}", status_code=204)
def remove_trip_meal(trip_id: int, meal_id: int, db: Session = Depends(get_db)):
    tm = db.get(TripMeal, meal_id)
    if not tm or tm.trip_id != trip_id:
        raise HTTPException(status_code=404, detail="Trip meal not found")
    db.delete(tm)
    db.commit()


# --- Summary ---

@router.get("/{trip_id}/summary", response_model=TripSummaryRead)
def get_trip_summary(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Compute meal weights for calculator
    trip_meals = db.query(TripMeal).filter(TripMeal.trip_id == trip_id).all()
    meal_weights = []
    meal_weight_actual = 0
    meal_calories_actual = 0
    breakfast_weight = 0
    breakfast_cal = 0
    breakfast_count = 0
    dinner_weight = 0
    dinner_cal = 0
    dinner_count = 0
    # Macro accumulators
    total_protein_g = 0.0
    total_fat_g = 0.0
    total_carb_g = 0.0
    # Track calories from ingredients that have macro data vs total
    macro_covered_calories = 0.0
    total_all_calories = 0.0
    for tm in trip_meals:
        recipe = db.get(Recipe, tm.recipe_id)
        totals = _get_recipe_totals(db, tm.recipe_id)
        w = totals["total_weight"] * tm.quantity
        c = totals["total_calories"] * tm.quantity
        if recipe.category == "breakfast":
            breakfast_weight += w
            breakfast_cal += c
            breakfast_count += tm.quantity
        else:
            dinner_weight += w
            dinner_cal += c
            dinner_count += tm.quantity
        for _ in range(tm.quantity):
            meal_weights.append(totals["total_weight"])
        meal_weight_actual += w
        meal_calories_actual += c
        # Accumulate macros from meals
        total_protein_g += totals["protein_g"] * tm.quantity
        total_fat_g += totals["fat_g"] * tm.quantity
        total_carb_g += totals["carb_g"] * tm.quantity
        # Compute macro coverage for this meal's ingredients
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == tm.recipe_id)
            .all()
        )
        for ri, ing in rows:
            ing_cal = ri.amount_oz * (ing.calories_per_oz or 0) * tm.quantity
            total_all_calories += ing_cal
            has_macros = (ing.protein_per_oz is not None
                          or ing.fat_per_oz is not None
                          or ing.carb_per_oz is not None)
            if has_macros:
                macro_covered_calories += ing_cal

    targets = compute_trip_targets(
        trip.first_day_fraction or 0,
        trip.full_days or 0,
        trip.last_day_fraction or 0,
        meal_weights,
        oz_per_day=trip.oz_per_day or 22,
        cal_per_oz=trip.cal_per_oz or 125,
    )

    # Compute snack totals
    trip_snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip_id).all()
    snack_weight = 0
    snack_calories = 0
    drink_mix_weight = 0
    drink_mix_calories = 0
    slot_subtotals = {}
    for ts in trip_snacks:
        cat_item = db.get(SnackCatalogItem, ts.catalog_item_id)
        ingredient = db.get(Ingredient, cat_item.ingredient_id)
        w = ts.servings * (cat_item.weight_per_serving or 0)
        c = ts.servings * (cat_item.calories_per_serving or 0)
        snack_weight += w
        snack_calories += c
        if cat_item.category == "drink_mix":
            drink_mix_weight += w
            drink_mix_calories += c
        else:
            slot = ts.slot or "snacks"
            if slot not in slot_subtotals:
                slot_subtotals[slot] = {"weight": 0, "calories": 0}
            slot_subtotals[slot]["weight"] += w
            slot_subtotals[slot]["calories"] += c
        # Accumulate snack macros
        wps = cat_item.weight_per_serving or 0
        has_macros = (ingredient.protein_per_oz is not None
                      or ingredient.fat_per_oz is not None
                      or ingredient.carb_per_oz is not None)
        if ingredient.protein_per_oz is not None:
            total_protein_g += (ingredient.protein_per_oz * wps) * ts.servings
        if ingredient.fat_per_oz is not None:
            total_fat_g += (ingredient.fat_per_oz * wps) * ts.servings
        if ingredient.carb_per_oz is not None:
            total_carb_g += (ingredient.carb_per_oz * wps) * ts.servings
        total_all_calories += c
        if has_macros:
            macro_covered_calories += c

    # Compute per-slot targets and days_covered
    # Slot percentages: lunch 40%, snacks 60%
    slot_pcts = {"lunch": 0.40, "snacks": 0.60}
    # Remaining calories = daytime minus drink mixes
    remaining_cal = targets["daytime_cal"] - drink_mix_calories
    total_days = targets["total_days"]

    for slot_name in ("lunch", "snacks"):
        if slot_name not in slot_subtotals:
            slot_subtotals[slot_name] = {"weight": 0, "calories": 0}
        st = slot_subtotals[slot_name]
        pct = slot_pcts[slot_name]
        st["target_cal"] = round(remaining_cal * pct, 1)
        daily_target = (remaining_cal * pct / total_days) if total_days > 0 else 0
        st["days_covered"] = round(st["calories"] / daily_target, 1) if daily_target > 0 else None
        st["weight"] = round(st["weight"], 2)
        st["calories"] = round(st["calories"], 1)

    snack_cal_per_oz = round(snack_calories / snack_weight, 1) if snack_weight > 0 else None

    combined_weight = snack_weight + meal_weight_actual
    combined_calories = snack_calories + meal_calories_actual

    # Compute macro percentages
    total_macro_calories = total_protein_g * 4 + total_fat_g * 9 + total_carb_g * 4
    if total_macro_calories > 0:
        macro_actual = {
            "protein_g": round(total_protein_g, 1),
            "fat_g": round(total_fat_g, 1),
            "carb_g": round(total_carb_g, 1),
            "protein_pct": round(total_protein_g * 4 / total_macro_calories * 100, 1),
            "fat_pct": round(total_fat_g * 9 / total_macro_calories * 100, 1),
            "carb_pct": round(total_carb_g * 4 / total_macro_calories * 100, 1),
        }
    else:
        macro_actual = None

    macro_coverage_pct = (
        round(macro_covered_calories / total_all_calories * 100, 1)
        if total_all_calories > 0 else None
    )

    # Fetch macro targets from settings
    settings = db.query(AppSettings).first()
    if settings:
        macro_target = {
            "protein_pct": settings.macro_target_protein_pct,
            "fat_pct": settings.macro_target_fat_pct,
            "carb_pct": settings.macro_target_carb_pct,
        }
    else:
        macro_target = {"protein_pct": 20, "fat_pct": 30, "carb_pct": 50}

    return {
        **targets,
        "snack_weight": round(snack_weight, 2),
        "snack_calories": round(snack_calories, 1),
        "snack_cal_per_oz": snack_cal_per_oz,
        "drink_mix_weight": round(drink_mix_weight, 2),
        "drink_mix_calories": round(drink_mix_calories, 1),
        "slot_subtotals": slot_subtotals,
        "meal_weight_actual": round(meal_weight_actual, 2),
        "meal_calories_actual": round(meal_calories_actual, 1),
        "breakfast_weight": round(breakfast_weight, 2),
        "breakfast_calories": round(breakfast_cal, 1),
        "breakfast_count": breakfast_count,
        "dinner_weight": round(dinner_weight, 2),
        "dinner_calories": round(dinner_cal, 1),
        "dinner_count": dinner_count,
        "combined_weight": round(combined_weight, 2),
        "combined_calories": round(combined_calories, 1),
        "weight_per_day": round(combined_weight / total_days, 1) if total_days > 0 else None,
        "cal_per_day": round(combined_calories / total_days, 1) if total_days > 0 else None,
        "macro_actual": macro_actual,
        "macro_target": macro_target,
        "macro_coverage_pct": macro_coverage_pct,
    }


# --- Packing Detail ---

@router.get("/{trip_id}/packing")
def get_packing_detail(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    meals = []
    for tm in db.query(TripMeal).filter(TripMeal.trip_id == trip_id).all():
        recipe = db.get(Recipe, tm.recipe_id)
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == recipe.id)
            .all()
        )
        ingredients = [
            {
                "name": ing.name,
                "amount_oz": round(ri.amount_oz * tm.quantity, 2),
                "essentials": bool(ing.essentials),
                "packing_method": ing.packing_method,
            }
            for ri, ing in rows
        ]
        meals.append({
            "id": tm.id,
            "recipe_name": recipe.name,
            "category": recipe.category,
            "quantity": tm.quantity,
            "at_home_prep": recipe.at_home_prep,
            "ingredients": ingredients,
            "packed": tm.packed,
            "actual_weight_oz": tm.actual_weight_oz,
        })

    snacks = []
    for ts in db.query(TripSnack).filter(TripSnack.trip_id == trip_id).all():
        cat_item = db.get(SnackCatalogItem, ts.catalog_item_id)
        ingredient = db.get(Ingredient, cat_item.ingredient_id)
        snacks.append({
            "id": ts.id,
            "ingredient_name": ingredient.name,
            "slot": ts.slot,
            "target_weight": round(ts.servings * (cat_item.weight_per_serving or 0), 2),
            "target_calories": round(ts.servings * (cat_item.calories_per_serving or 0), 1),
            "servings": ts.servings,
            "packed": ts.packed,
            "actual_weight_oz": ts.actual_weight_oz,
            "packing_method": ingredient.packing_method,
        })

    return {"trip_name": trip.name, "meals": meals, "snacks": snacks}


# --- Shopping List ---

@router.get("/{trip_id}/shopping-list")
def get_shopping_list(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    totals = {}  # ingredient_id -> {name, total_oz, on_hand, essentials, packing_method}

    # Aggregate from meals
    for tm in db.query(TripMeal).filter(TripMeal.trip_id == trip_id).all():
        ris = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == tm.recipe_id)
            .all()
        )
        for ri, ing in ris:
            key = ri.ingredient_id
            if key not in totals:
                totals[key] = {
                    "ingredient_id": key, "ingredient_name": ing.name, "total_oz": 0,
                    "on_hand": bool(ing.on_hand), "essentials": bool(ing.essentials),
                    "packing_method": ing.packing_method,
                }
            totals[key]["total_oz"] += ri.amount_oz * tm.quantity

    # Aggregate from snacks
    for ts in db.query(TripSnack).filter(TripSnack.trip_id == trip_id).all():
        cat_item = db.get(SnackCatalogItem, ts.catalog_item_id)
        ingredient = db.get(Ingredient, cat_item.ingredient_id)
        key = cat_item.ingredient_id
        if key not in totals:
            totals[key] = {
                "ingredient_id": key, "ingredient_name": ingredient.name, "total_oz": 0,
                "on_hand": bool(ingredient.on_hand), "essentials": bool(ingredient.essentials),
                "packing_method": ingredient.packing_method,
            }
        totals[key]["total_oz"] += ts.servings * (cat_item.weight_per_serving or 0)

    for item in totals.values():
        item["total_oz"] = round(item["total_oz"], 2)

    # Split essentials from regular items
    regular = [v for v in totals.values() if not v["essentials"]]
    essentials = [v for v in totals.values() if v["essentials"]]

    # Sort regular: need-to-buy first (not on_hand), then on-hand, alphabetical within
    regular.sort(key=lambda x: (x["on_hand"], x["ingredient_name"]))
    essentials.sort(key=lambda x: x["ingredient_name"])

    return {"items": regular, "essentials": essentials}


# --- Clone ---

@router.post("/{trip_id}/clone", response_model=TripDetailRead, status_code=201)
def clone_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.get(Trip, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    new_trip = Trip(
        name=f"{trip.name} (copy)",
        first_day_fraction=trip.first_day_fraction,
        full_days=trip.full_days,
        last_day_fraction=trip.last_day_fraction,
        drink_mixes_per_day=trip.drink_mixes_per_day,
        oz_per_day=trip.oz_per_day,
        cal_per_oz=trip.cal_per_oz,
    )
    db.add(new_trip)
    db.flush()

    for ts in db.query(TripSnack).filter(TripSnack.trip_id == trip_id).all():
        db.add(TripSnack(
            trip_id=new_trip.id,
            catalog_item_id=ts.catalog_item_id,
            servings=ts.servings,
            slot=ts.slot,
            trip_notes=ts.trip_notes,
        ))

    for tm in db.query(TripMeal).filter(TripMeal.trip_id == trip_id).all():
        db.add(TripMeal(
            trip_id=new_trip.id,
            recipe_id=tm.recipe_id,
            quantity=tm.quantity,
        ))

    db.commit()
    db.refresh(new_trip)
    return _build_trip_detail(new_trip, db)
