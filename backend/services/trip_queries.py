"""Read projections hidden behind the trip-planning application boundary."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import (
    AppSettings,
    Ingredient,
    Recipe,
    RecipeIngredient,
    SnackCatalogItem,
    Trip,
    TripMeal,
    TripSnack,
)
from calculator import compute_trip_targets
from services.autofill import build_day_list
from services.catalog_queries import snack_unit_type_list_view
from services.recipe_calc import compute_recipe_totals
from services.snack_units import (
    trip_oz_per_snack,
    trip_snack_unit_list_view,
    trip_unit_totals,
    unit_quota,
)


STRUCTURED_SNACK_MODEL = "structured"


def _is_structured(trip: Trip) -> bool:
    return (trip.snack_model or "legacy") == STRUCTURED_SNACK_MODEL


def recipe_totals(db: Session, recipe_id: int) -> dict:
    rows = (
        db.query(RecipeIngredient, Ingredient)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe_id)
        .all()
    )
    return compute_recipe_totals([
        {
            "amount_oz": recipe_ingredient.amount_oz,
            "calories_per_oz": ingredient.calories_per_oz,
            "protein_per_oz": ingredient.protein_per_oz,
            "fat_per_oz": ingredient.fat_per_oz,
            "carb_per_oz": ingredient.carb_per_oz,
        }
        for recipe_ingredient, ingredient in rows
    ])


def trip_snack_view(db: Session, selection: TripSnack) -> dict:
    catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
    ingredient = db.get(Ingredient, catalog_item.ingredient_id)
    weight_per_serving = catalog_item.weight_per_serving or 0
    calories_per_serving = catalog_item.calories_per_serving or 0
    return {
        "id": selection.id,
        "catalog_item_id": selection.catalog_item_id,
        "ingredient_name": ingredient.name,
        "weight_per_serving": catalog_item.weight_per_serving,
        "calories_per_serving": catalog_item.calories_per_serving,
        "calories_per_oz": (
            round(calories_per_serving / weight_per_serving, 1)
            if weight_per_serving > 0 else None
        ),
        "protein_per_serving": (
            round(ingredient.protein_per_oz * weight_per_serving, 2)
            if ingredient.protein_per_oz is not None and weight_per_serving else None
        ),
        "fat_per_serving": (
            round(ingredient.fat_per_oz * weight_per_serving, 2)
            if ingredient.fat_per_oz is not None and weight_per_serving else None
        ),
        "carb_per_serving": (
            round(ingredient.carb_per_oz * weight_per_serving, 2)
            if ingredient.carb_per_oz is not None and weight_per_serving else None
        ),
        "category": catalog_item.category,
        "slot": selection.slot,
        "servings": selection.servings,
        "total_weight": round(selection.servings * weight_per_serving, 2),
        "total_calories": round(selection.servings * calories_per_serving, 1),
        "packed": selection.packed,
        "actual_weight_oz": selection.actual_weight_oz,
        "trip_notes": selection.trip_notes,
    }


def trip_meal_view(db: Session, selection: TripMeal) -> dict:
    recipe = db.get(Recipe, selection.recipe_id)
    totals = recipe_totals(db, recipe.id)
    return {
        "id": selection.id,
        "recipe_id": selection.recipe_id,
        "recipe_name": recipe.name,
        "category": recipe.category,
        "quantity": selection.quantity,
        "weight_per_unit": totals["total_weight"],
        "total_weight": round(totals["total_weight"] * selection.quantity, 2),
        "total_calories": round(totals["total_calories"] * selection.quantity, 1),
        "packed": selection.packed,
        "actual_weight_oz": selection.actual_weight_oz,
    }


def trip_detail_view(db: Session, trip: Trip) -> dict:
    snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all()
    meals = db.query(TripMeal).filter(TripMeal.trip_id == trip.id).all()
    return {
        "id": trip.id,
        "name": trip.name,
        "first_day_fraction": trip.first_day_fraction,
        "full_days": trip.full_days,
        "last_day_fraction": trip.last_day_fraction,
        "drink_mixes_per_day": (
            trip.drink_mixes_per_day if trip.drink_mixes_per_day is not None else 2
        ),
        "oz_per_day": trip.oz_per_day if trip.oz_per_day is not None else 22,
        "cal_per_oz": trip.cal_per_oz if trip.cal_per_oz is not None else 125,
        "snack_model": trip.snack_model or "legacy",
        "snacks_per_day": (
            trip.snacks_per_day if trip.snacks_per_day is not None else 4
        ),
        "oz_per_snack": trip.oz_per_snack if trip.oz_per_snack is not None else 2,
        # Null on purpose when unset: the client renders the live
        # one-per-full-day default and must know it is not an override.
        "lunches": trip.lunches,
        "snacks": [trip_snack_view(db, selection) for selection in snacks],
        "snack_units": trip_snack_unit_list_view(db, trip),
        "meals": [trip_meal_view(db, selection) for selection in meals],
    }


def trip_list_view(db: Session, *, newest_first: bool = False) -> list[dict]:
    query = db.query(Trip)
    if newest_first:
        query = query.order_by(Trip.id.desc())
    return [
        {
            "id": trip.id,
            "name": trip.name,
            "total_days": round(
                sum(day["fraction"] for day in build_day_list(trip)), 2
            ),
            "first_day_fraction": trip.first_day_fraction,
            "full_days": trip.full_days,
            "last_day_fraction": trip.last_day_fraction,
            "snack_model": trip.snack_model or "legacy",
            "snacks_per_day": (
                trip.snacks_per_day if trip.snacks_per_day is not None else 4
            ),
            "oz_per_snack": trip.oz_per_snack if trip.oz_per_snack is not None else 2,
        }
        for trip in query.all()
    ]


def _lunches_needed(trip: Trip) -> int:
    """The trip's lunch count: an explicit trips.lunches override, or one
    lunch per full day when unset."""
    return trip.lunches if trip.lunches is not None else (trip.full_days or 0)


def trip_summary_view(db: Session, trip: Trip) -> dict:
    trip_meals = db.query(TripMeal).filter(TripMeal.trip_id == trip.id).all()
    meal_weights: list[float] = []
    meal_weight_actual = meal_calories_actual = 0.0
    breakfast_weight = breakfast_calories = dinner_weight = dinner_calories = 0.0
    breakfast_count = dinner_count = 0
    total_protein_g = total_fat_g = total_carb_g = 0.0
    macro_covered_calories = total_all_calories = 0.0

    for selection in trip_meals:
        recipe = db.get(Recipe, selection.recipe_id)
        totals = recipe_totals(db, selection.recipe_id)
        weight = totals["total_weight"] * selection.quantity
        calories = totals["total_calories"] * selection.quantity
        if recipe.category == "breakfast":
            breakfast_weight += weight
            breakfast_calories += calories
            breakfast_count += selection.quantity
        else:
            dinner_weight += weight
            dinner_calories += calories
            dinner_count += selection.quantity
        meal_weights.extend([totals["total_weight"]] * selection.quantity)
        meal_weight_actual += weight
        meal_calories_actual += calories
        total_protein_g += totals["protein_g"] * selection.quantity
        total_fat_g += totals["fat_g"] * selection.quantity
        total_carb_g += totals["carb_g"] * selection.quantity
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == selection.recipe_id)
            .all()
        )
        for recipe_ingredient, ingredient in rows:
            ingredient_calories = (
                recipe_ingredient.amount_oz
                * (ingredient.calories_per_oz or 0)
                * selection.quantity
            )
            total_all_calories += ingredient_calories
            if any(value is not None for value in (
                ingredient.protein_per_oz,
                ingredient.fat_per_oz,
                ingredient.carb_per_oz,
            )):
                macro_covered_calories += ingredient_calories

    targets = compute_trip_targets(
        trip.first_day_fraction or 0,
        trip.full_days or 0,
        trip.last_day_fraction or 0,
        meal_weights,
        oz_per_day=trip.oz_per_day or 22,
        cal_per_oz=trip.cal_per_oz or 125,
    )

    snack_weight = snack_calories = drink_mix_weight = drink_mix_calories = 0.0
    slot_subtotals: dict[str, dict] = {}
    trip_snacks = db.query(TripSnack).filter(TripSnack.trip_id == trip.id).all()
    for selection in trip_snacks:
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        ingredient = db.get(Ingredient, catalog_item.ingredient_id)
        weight = selection.servings * (catalog_item.weight_per_serving or 0)
        calories = selection.servings * (catalog_item.calories_per_serving or 0)
        snack_weight += weight
        snack_calories += calories
        if catalog_item.category == "drink_mix":
            drink_mix_weight += weight
            drink_mix_calories += calories
        else:
            slot = selection.slot or "snacks"
            subtotal = slot_subtotals.setdefault(slot, {"weight": 0, "calories": 0})
            subtotal["weight"] += weight
            subtotal["calories"] += calories
        weight_per_serving = catalog_item.weight_per_serving or 0
        has_macros = any(value is not None for value in (
            ingredient.protein_per_oz,
            ingredient.fat_per_oz,
            ingredient.carb_per_oz,
        ))
        if ingredient.protein_per_oz is not None:
            total_protein_g += (
                ingredient.protein_per_oz * weight_per_serving * selection.servings
            )
        if ingredient.fat_per_oz is not None:
            total_fat_g += (
                ingredient.fat_per_oz * weight_per_serving * selection.servings
            )
        if ingredient.carb_per_oz is not None:
            total_carb_g += (
                ingredient.carb_per_oz * weight_per_serving * selection.servings
            )
        total_all_calories += calories
        if has_macros:
            macro_covered_calories += calories

    structured = _is_structured(trip)
    snack_units_block = None
    if structured:
        units = trip_unit_totals(db, trip)
        snack_weight += units["weight"]
        snack_calories += units["calories"]
        unit_subtotal = slot_subtotals.setdefault("snacks", {"weight": 0, "calories": 0})
        unit_subtotal["weight"] += units["weight"]
        unit_subtotal["calories"] += units["calories"]
        total_protein_g += units["protein_g"]
        total_fat_g += units["fat_g"]
        total_carb_g += units["carb_g"]
        total_all_calories += units["all_calories"]
        macro_covered_calories += units["macro_covered_calories"]
        snack_units_block = {**unit_quota(trip), "filled": units["filled"]}

    remaining_calories = targets["daytime_cal"] - drink_mix_calories
    total_days = targets["total_days"]
    # On a structured trip the unit meter replaces the snacks calorie band;
    # lunch keeps its 40% band exactly as it is on a legacy trip.
    slot_percentages = (
        {"lunch": 0.40} if structured else {"lunch": 0.40, "snacks": 0.60}
    )
    for slot, percentage in slot_percentages.items():
        subtotal = slot_subtotals.setdefault(slot, {"weight": 0, "calories": 0})
        target = round(remaining_calories * percentage, 1)
        daily_target = (
            remaining_calories * percentage / total_days if total_days > 0 else 0
        )
        subtotal.update({
            "target_cal": target,
            "target_cal_low": round(target * 0.9, 1),
            "target_cal_high": round(target * 1.1, 1),
            "days_covered": (
                round(subtotal["calories"] / daily_target, 1)
                if daily_target > 0 else None
            ),
            "weight": round(subtotal["weight"], 2),
            "calories": round(subtotal["calories"], 1),
        })
        if slot == "lunch":
            subtotal["lunches_needed"] = _lunches_needed(trip)
    if structured:
        snacks_subtotal = slot_subtotals.setdefault(
            "snacks", {"weight": 0, "calories": 0}
        )
        snacks_subtotal.update({
            "weight": round(snacks_subtotal["weight"], 2),
            "calories": round(snacks_subtotal["calories"], 1),
        })

    total_macro_calories = total_protein_g * 4 + total_fat_g * 9 + total_carb_g * 4
    macro_actual = None
    if total_macro_calories > 0:
        macro_actual = {
            "protein_g": round(total_protein_g, 1),
            "fat_g": round(total_fat_g, 1),
            "carb_g": round(total_carb_g, 1),
            "protein_pct": round(total_protein_g * 4 / total_macro_calories * 100, 1),
            "fat_pct": round(total_fat_g * 9 / total_macro_calories * 100, 1),
            "carb_pct": round(total_carb_g * 4 / total_macro_calories * 100, 1),
        }
    settings = db.query(AppSettings).first()
    macro_target = (
        {
            "protein_pct": settings.macro_target_protein_pct,
            "fat_pct": settings.macro_target_fat_pct,
            "carb_pct": settings.macro_target_carb_pct,
        }
        if settings else {"protein_pct": 20, "fat_pct": 30, "carb_pct": 50}
    )
    combined_weight = snack_weight + meal_weight_actual
    combined_calories = snack_calories + meal_calories_actual
    summary = {
        **targets,
        "snack_weight": round(snack_weight, 2),
        "snack_calories": round(snack_calories, 1),
        "snack_cal_per_oz": (
            round(snack_calories / snack_weight, 1) if snack_weight > 0 else None
        ),
        "drink_mix_weight": round(drink_mix_weight, 2),
        "drink_mix_calories": round(drink_mix_calories, 1),
        "slot_subtotals": slot_subtotals,
        "meal_weight_actual": round(meal_weight_actual, 2),
        "meal_calories_actual": round(meal_calories_actual, 1),
        "breakfast_weight": round(breakfast_weight, 2),
        "breakfast_calories": round(breakfast_calories, 1),
        "breakfast_count": breakfast_count,
        "dinner_weight": round(dinner_weight, 2),
        "dinner_calories": round(dinner_calories, 1),
        "dinner_count": dinner_count,
        "combined_weight": round(combined_weight, 2),
        "combined_calories": round(combined_calories, 1),
        "weight_per_day": (
            round(combined_weight / total_days, 1) if total_days > 0 else None
        ),
        "cal_per_day": (
            round(combined_calories / total_days, 1) if total_days > 0 else None
        ),
        "macro_actual": macro_actual,
        "macro_target": macro_target,
        "macro_coverage_pct": (
            round(macro_covered_calories / total_all_calories * 100, 1)
            if total_all_calories > 0 else None
        ),
    }
    # A legacy trip's summary never grows a key it did not have before.
    if snack_units_block is not None:
        summary["snack_units"] = snack_units_block
    return summary


def _bags_by_id(db: Session, selections: list[dict]) -> dict[int, dict]:
    """The library bags behind these selections, keyed by id.

    One list query serves every bag on the trip; the library owns composition
    and derived values, so nothing here re-derives them.
    """
    if not any(selection["unit_type_id"] is not None for selection in selections):
        return {}
    return {bag["id"]: bag for bag in snack_unit_type_list_view(db)}


def _packing_units(db: Session, trip: Trip) -> list[dict]:
    """Unit selections as an assembly checklist, grouped by unit type or item.

    A group is one thing to make N of: "make 6 x trail mix bag at 2.0 oz". The
    count is the units to build, `target_weight` is the trip's per-unit target,
    and `unit_weight` is what the composition actually derives. Packed state and
    actual weights stay per selection, because that is where the columns live;
    the group repeats them so a single-selection group (the normal case) reads
    as one row.
    """
    selections = trip_snack_unit_list_view(db, trip)
    bags = _bags_by_id(db, selections)
    target_weight = trip_oz_per_snack(trip)
    groups: dict[tuple[str, int], dict] = {}
    for selection in selections:
        kind = selection["kind"]
        bag = bags.get(selection["unit_type_id"]) if kind == "bag" else None
        key = (
            kind,
            selection["unit_type_id"] if kind == "bag" else selection["catalog_item_id"],
        )
        group = groups.get(key)
        if group is None:
            group = groups[key] = {
                "kind": kind,
                "unit_type_id": selection["unit_type_id"],
                "catalog_item_id": selection["catalog_item_id"],
                "name": selection["name"],
                "count": 0,
                "target_weight": target_weight,
                "unit_weight": selection["weight_oz"],
                "unit_calories": selection["calories"],
                "total_weight": 0.0,
                "total_calories": 0.0,
                "weight_warning": selection["weight_warning"],
                "packed": True,
                "actual_weight_oz": None,
                # What goes in the bag, so packing day does not need the library.
                "composition": [
                    {
                        "ingredient_name": row["ingredient_name"],
                        "amount_oz": row["amount_oz"],
                    }
                    for row in (bag["composition"] if bag else [])
                ],
                "selections": [],
            }
        group["count"] += selection["quantity"]
        group["total_weight"] += selection["total_weight"]
        group["total_calories"] += selection["total_calories"]
        group["packed"] = group["packed"] and selection["packed"]
        if group["actual_weight_oz"] is None:
            group["actual_weight_oz"] = selection["actual_weight_oz"]
        group["selections"].append({
            "id": selection["id"],
            "quantity": selection["quantity"],
            "packed": selection["packed"],
            "actual_weight_oz": selection["actual_weight_oz"],
        })
    for group in groups.values():
        group["total_weight"] = round(group["total_weight"], 2)
        group["total_calories"] = round(group["total_calories"], 1)
    return list(groups.values())


def packing_view(db: Session, trip: Trip) -> dict:
    meals = []
    for selection in db.query(TripMeal).filter(TripMeal.trip_id == trip.id):
        recipe = db.get(Recipe, selection.recipe_id)
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == recipe.id)
            .all()
        )
        meals.append({
            "id": selection.id,
            "recipe_name": recipe.name,
            "category": recipe.category,
            "quantity": selection.quantity,
            "at_home_prep": recipe.at_home_prep,
            "ingredients": [
                {
                    "name": ingredient.name,
                    # amount_oz is per single serving/baggie; total_oz is the
                    # combined amount across all `quantity` servings. Assembly
                    # packs one baggie per serving, so the per-serving amount is
                    # what the user measures out N times.
                    "amount_oz": round(recipe_ingredient.amount_oz, 2),
                    "total_oz": round(recipe_ingredient.amount_oz * selection.quantity, 2),
                    "essentials": bool(ingredient.essentials),
                    "packing_method": ingredient.packing_method,
                }
                for recipe_ingredient, ingredient in rows
            ],
            "packed": selection.packed,
            "actual_weight_oz": selection.actual_weight_oz,
        })
    snacks = []
    for selection in db.query(TripSnack).filter(TripSnack.trip_id == trip.id):
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        ingredient = db.get(Ingredient, catalog_item.ingredient_id)
        snacks.append({
            "id": selection.id,
            "ingredient_name": ingredient.name,
            "slot": selection.slot,
            "target_weight": round(
                selection.servings * (catalog_item.weight_per_serving or 0), 2
            ),
            "target_calories": round(
                selection.servings * (catalog_item.calories_per_serving or 0), 1
            ),
            "servings": selection.servings,
            "packed": selection.packed,
            "actual_weight_oz": selection.actual_weight_oz,
            "packing_method": ingredient.packing_method,
        })
    packing = {"trip_name": trip.name, "meals": meals, "snacks": snacks}
    # A legacy trip's packing detail never grows a key it did not have before.
    if _is_structured(trip):
        packing["units"] = _packing_units(db, trip)
    return packing


def _shopping_line(totals: dict[int, dict], ingredient: Ingredient) -> dict:
    """The shopping line for one ingredient, created the first time it is seen.

    Every source merges into the same line — recipe amounts, catalog servings,
    and the bulk ounces a bag unit expands into — so an ingredient bought for
    two reasons is bought once, and on_hand / essentials / packing_method come
    from the ingredient no matter which source found it.
    """
    return totals.setdefault(ingredient.id, {
        "ingredient_id": ingredient.id,
        "ingredient_name": ingredient.name,
        "total_oz": 0,
        "on_hand": bool(ingredient.on_hand),
        "essentials": bool(ingredient.essentials),
        "packing_method": ingredient.packing_method,
    })


def _unit_ingredient_ounces(db: Session, trip: Trip) -> list[tuple[int, float]]:
    """(ingredient_id, ounces) that this trip's unit selections add to shopping.

    A bag expands into its composition: six bags of 1 oz nuts + 1 oz M&Ms buy
    six ounces of each. A packaged unit buys its catalog serving weight, the
    same line a TripSnack row of the same item would produce.
    """
    selections = trip_snack_unit_list_view(db, trip)
    bags = _bags_by_id(db, selections)
    ounces: list[tuple[int, float]] = []
    for selection in selections:
        quantity = selection["quantity"]
        if selection["kind"] == "bag":
            bag = bags.get(selection["unit_type_id"])
            for row in (bag["composition"] if bag else []):
                ounces.append((row["ingredient_id"], row["amount_oz"] * quantity))
        else:
            catalog_item = db.get(SnackCatalogItem, selection["catalog_item_id"])
            if catalog_item is not None:
                ounces.append((
                    catalog_item.ingredient_id,
                    (catalog_item.weight_per_serving or 0) * quantity,
                ))
    return ounces


def shopping_view(db: Session, trip: Trip) -> dict:
    totals: dict[int, dict] = {}
    for selection in db.query(TripMeal).filter(TripMeal.trip_id == trip.id):
        rows = (
            db.query(RecipeIngredient, Ingredient)
            .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .filter(RecipeIngredient.recipe_id == selection.recipe_id)
            .all()
        )
        for recipe_ingredient, ingredient in rows:
            item = _shopping_line(totals, ingredient)
            item["total_oz"] += recipe_ingredient.amount_oz * selection.quantity
    for selection in db.query(TripSnack).filter(TripSnack.trip_id == trip.id):
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        ingredient = db.get(Ingredient, catalog_item.ingredient_id)
        item = _shopping_line(totals, ingredient)
        item["total_oz"] += selection.servings * (catalog_item.weight_per_serving or 0)
    if _is_structured(trip):
        for ingredient_id, amount_oz in _unit_ingredient_ounces(db, trip):
            ingredient = db.get(Ingredient, ingredient_id)
            if ingredient is None:
                continue
            item = _shopping_line(totals, ingredient)
            item["total_oz"] += amount_oz
    for item in totals.values():
        item["total_oz"] = round(item["total_oz"], 2)
    regular = [item for item in totals.values() if not item["essentials"]]
    essentials = [item for item in totals.values() if item["essentials"]]
    regular.sort(key=lambda item: (item["on_hand"], item["ingredient_name"]))
    essentials.sort(key=lambda item: item["ingredient_name"])
    return {"items": regular, "essentials": essentials}
