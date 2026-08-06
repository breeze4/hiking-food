"""Trip snack unit selections: quota math and per-selection projections.

Bag composition math is never repeated here. A bag's weight, calories, and
macros come from ``catalog_queries.snack_unit_type_view``; this module only
resolves a selection to its unit values, scales them by quantity, and answers
"how many units does this trip need?".
"""

from __future__ import annotations

import math

from sqlalchemy.orm import Session

from models import Ingredient, SnackCatalogItem, Trip, TripSnackUnit
from services.catalog_queries import (
    DEFAULT_OZ_PER_SNACK,
    snack_unit_type_list_view,
    snack_unit_weight_warning,
)

DEFAULT_SNACKS_PER_DAY = 4

MACRO_FIELDS = ("protein_per_oz", "fat_per_oz", "carb_per_oz")


def _round_half_up(value: float) -> int:
    """Round to a whole unit, halves upward.

    Python's built-in round() is banker's rounding, which would send a half day
    at 4 snacks/day to 2 units and a half day at 5 snacks/day to 2 as well. A
    partial day always rounds up at the halfway mark instead.
    """
    return math.floor(value + 0.5)


def trip_day_fractions(trip: Trip) -> list[float]:
    """The trip's days as fractions, first day through last.

    Ordered like ``autofill.build_day_list`` but derived here, because the
    daily plan owns day numbering and this module only needs the fractions.
    """
    fractions: list[float] = []
    if trip.first_day_fraction and trip.first_day_fraction > 0:
        fractions.append(trip.first_day_fraction)
    fractions.extend([1.0] * (trip.full_days or 0))
    if trip.last_day_fraction and trip.last_day_fraction > 0:
        fractions.append(trip.last_day_fraction)
    return fractions


def unit_quota(trip: Trip) -> dict:
    """How many snack units the trip needs, in total and day by day."""
    snacks_per_day = (
        trip.snacks_per_day if trip.snacks_per_day is not None
        else DEFAULT_SNACKS_PER_DAY
    )
    per_day = [
        _round_half_up(snacks_per_day * fraction)
        for fraction in trip_day_fractions(trip)
    ]
    return {"quota": sum(per_day), "per_day": per_day}


def trip_oz_per_snack(trip: Trip) -> float:
    return trip.oz_per_snack if trip.oz_per_snack is not None else DEFAULT_OZ_PER_SNACK


def _packaged_unit(db: Session, catalog_item: SnackCatalogItem) -> dict:
    """One packaged snack as a unit: catalog serving values, ingredient macros."""
    ingredient = db.get(Ingredient, catalog_item.ingredient_id)
    weight_oz = catalog_item.weight_per_serving or 0
    calories = catalog_item.calories_per_serving or 0
    has_macros = any(
        getattr(ingredient, field) is not None for field in MACRO_FIELDS
    )
    return {
        "kind": "packaged",
        "name": ingredient.name,
        "weight_oz": round(weight_oz, 2),
        "calories": round(calories, 1),
        "cal_per_oz": round(calories / weight_oz, 1) if weight_oz > 0 else None,
        "protein_g": round((ingredient.protein_per_oz or 0) * weight_oz, 1),
        "fat_g": round((ingredient.fat_per_oz or 0) * weight_oz, 1),
        "carb_g": round((ingredient.carb_per_oz or 0) * weight_oz, 1),
        # Calories come from the catalog serving, so only macros can be missing.
        "has_full_data": all(
            getattr(ingredient, field) is not None for field in MACRO_FIELDS
        ),
        # Same posture as the TripSnack loop in trip_summary_view: the serving's
        # calories count as macro-covered when the ingredient has any macro data.
        "macro_calories": round(calories, 1) if has_macros else 0.0,
    }


def _bag_unit(bag: dict) -> dict:
    """One library bag as a unit, reading the library's derived values."""
    covered = sum(
        row["calories"] for row in bag["composition"]
        if any(row[field] is not None for field in MACRO_FIELDS)
    )
    return {
        "kind": "bag",
        "name": bag["name"],
        "weight_oz": bag["weight_oz"],
        "calories": bag["calories"],
        "cal_per_oz": bag["cal_per_oz"],
        "protein_g": bag["protein_g"],
        "fat_g": bag["fat_g"],
        "carb_g": bag["carb_g"],
        "has_full_data": bag["has_full_data"],
        # Composition calories are each rounded, so their sum can drift a tenth
        # past the bag total; covered calories are a share, never a surplus.
        "macro_calories": min(covered, bag["calories"]),
    }


def _resolve_unit(
    db: Session, selection: TripSnackUnit, bags: dict[int, dict]
) -> dict | None:
    """The unit values behind one selection, or None if it references nothing.

    Selection CRUD enforces exactly one of the two references, so a None here
    means a row written straight to the table; callers skip it rather than
    failing the whole trip.
    """
    if selection.catalog_item_id is not None:
        catalog_item = db.get(SnackCatalogItem, selection.catalog_item_id)
        return _packaged_unit(db, catalog_item) if catalog_item else None
    if selection.unit_type_id is not None:
        bag = bags.get(selection.unit_type_id)
        return _bag_unit(bag) if bag else None
    return None


def _selections(db: Session, trip_id: int) -> list[TripSnackUnit]:
    return (
        db.query(TripSnackUnit)
        .filter(TripSnackUnit.trip_id == trip_id)
        .order_by(TripSnackUnit.id)
        .all()
    )


def _bag_index(db: Session) -> dict[int, dict]:
    """Every library bag keyed by id, in one pair of queries."""
    return {bag["id"]: bag for bag in snack_unit_type_list_view(db)}


def _resolved_rows(db: Session, trip: Trip) -> list[tuple[TripSnackUnit, dict]]:
    selections = _selections(db, trip.id)
    bags = _bag_index(db) if any(s.unit_type_id is not None for s in selections) else {}
    rows = []
    for selection in selections:
        unit = _resolve_unit(db, selection, bags)
        if unit is not None:
            rows.append((selection, unit))
    return rows


def _unit_view(selection: TripSnackUnit, unit: dict, target_oz: float) -> dict:
    quantity = selection.quantity or 0
    return {
        "id": selection.id,
        "catalog_item_id": selection.catalog_item_id,
        "unit_type_id": selection.unit_type_id,
        "kind": unit["kind"],
        "name": unit["name"],
        "quantity": quantity,
        "weight_oz": unit["weight_oz"],
        "calories": unit["calories"],
        "cal_per_oz": unit["cal_per_oz"],
        "protein_g": unit["protein_g"],
        "fat_g": unit["fat_g"],
        "carb_g": unit["carb_g"],
        "total_weight": round(unit["weight_oz"] * quantity, 2),
        "total_calories": round(unit["calories"] * quantity, 1),
        # Against this trip's target, not the library's 2 oz default.
        "weight_warning": snack_unit_weight_warning(unit["weight_oz"], target_oz),
        "has_full_data": unit["has_full_data"],
        "packed": bool(selection.packed),
        "actual_weight_oz": selection.actual_weight_oz,
        "trip_notes": selection.trip_notes,
    }


def trip_snack_unit_view(db: Session, selection: TripSnackUnit) -> dict:
    """One selection, shaped for the selection endpoints."""
    trip = db.get(Trip, selection.trip_id)
    bags = _bag_index(db) if selection.unit_type_id is not None else {}
    unit = _resolve_unit(db, selection, bags)
    if unit is None:
        unit = {
            "kind": "packaged" if selection.catalog_item_id is not None else "bag",
            "name": "Unknown unit",
            "weight_oz": 0, "calories": 0, "cal_per_oz": None,
            "protein_g": 0, "fat_g": 0, "carb_g": 0,
            "has_full_data": False, "macro_calories": 0.0,
        }
    return _unit_view(selection, unit, trip_oz_per_snack(trip))


def trip_snack_unit_list_view(db: Session, trip: Trip) -> list[dict]:
    """Every unit selection on the trip, in selection order."""
    target_oz = trip_oz_per_snack(trip)
    return [
        _unit_view(selection, unit, target_oz)
        for selection, unit in _resolved_rows(db, trip)
    ]


def trip_unit_totals(db: Session, trip: Trip) -> dict:
    """What the trip's unit selections contribute to the summary."""
    totals = {
        "filled": 0,
        "weight": 0.0,
        "calories": 0.0,
        "protein_g": 0.0,
        "fat_g": 0.0,
        "carb_g": 0.0,
        "all_calories": 0.0,
        "macro_covered_calories": 0.0,
    }
    for selection, unit in _resolved_rows(db, trip):
        quantity = selection.quantity or 0
        calories = unit["calories"] * quantity
        totals["filled"] += quantity
        totals["weight"] += unit["weight_oz"] * quantity
        totals["calories"] += calories
        totals["protein_g"] += unit["protein_g"] * quantity
        totals["fat_g"] += unit["fat_g"] * quantity
        totals["carb_g"] += unit["carb_g"] * quantity
        totals["all_calories"] += calories
        totals["macro_covered_calories"] += unit["macro_calories"] * quantity
    return totals
