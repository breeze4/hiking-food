"""Application boundary for cohesive REST and MCP trip-planning workflows."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from models import (
    Ingredient,
    Recipe,
    SnackCatalogItem,
    Trip,
    TripDayAssignment,
    TripMeal,
    TripSnack,
)
from services.autofill import SLOT_RULES, build_day_list
from services.daily_plan_queries import daily_plan_view, regenerate_daily_plan
from services.trip_queries import (
    packing_view,
    shopping_view,
    trip_detail_view,
    trip_list_view,
    trip_summary_view,
)


ALLOCATION_SHAPE_FIELDS = {
    "first_day_fraction",
    "full_days",
    "last_day_fraction",
}

CATEGORY_TO_SLOT = {
    "drink_mix": "snacks",
    "bars_energy": "snacks",
    "lunch": "lunch",
    "salty": "snacks",
    "sweet": "snacks",
}


@dataclass(frozen=True)
class SelectionChangeResult:
    action: str
    name: str
    amount: float


class TripPlanningError(ValueError):
    """A caller supplied a trip-planning operation that violates domain rules."""


class TripNotFoundError(TripPlanningError):
    """The requested trip does not exist."""


class TripConflictError(TripPlanningError):
    """The requested change conflicts with an existing trip."""


class TripSelectionNotFoundError(TripPlanningError):
    """The requested meal, snack, or assignment is not on the trip."""


class FoodOptionNotFoundError(TripPlanningError):
    """The requested recipe or snack catalog option does not exist."""


class TripPlanningService:
    """Own trip-planning validation and transaction boundaries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_trips(self, *, newest_first: bool = False) -> list[dict]:
        return trip_list_view(self.db, newest_first=newest_first)

    def read_trip(self, trip_id: int) -> dict:
        trip = self.db.get(Trip, trip_id)
        if not trip:
            raise TripNotFoundError("Trip not found")
        return trip_detail_view(self.db, trip)

    def read_summary(self, trip_id: int) -> dict:
        trip = self._trip(trip_id)
        return trip_summary_view(self.db, trip)

    def read_packing(self, trip_id: int) -> dict:
        trip = self._trip(trip_id)
        return packing_view(self.db, trip)

    def read_shopping(self, trip_id: int) -> dict:
        trip = self._trip(trip_id)
        return shopping_view(self.db, trip)

    def read_daily_plan(self, trip_id: int) -> dict:
        return daily_plan_view(self.db, self._trip(trip_id))

    def regenerate_daily_plan(self, trip_id: int) -> dict:
        return regenerate_daily_plan(self.db, self._trip(trip_id))

    def _trip(self, trip_id: int) -> Trip:
        trip = self.db.get(Trip, trip_id)
        if not trip:
            raise TripNotFoundError("Trip not found")
        return trip

    def create_trip(self, values: Mapping[str, Any]) -> Trip:
        fields = dict(values)
        self._validate_trip_fields(fields, require_name=True)
        self._ensure_unique_name(fields["name"])

        trip = Trip(**fields)
        self.db.add(trip)
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def clone_trip(
        self,
        source_trip_id: int,
        values: Mapping[str, Any],
    ) -> Trip:
        source = self.db.get(Trip, source_trip_id)
        if not source:
            raise TripNotFoundError("Trip not found")
        overrides = dict(values)
        name = overrides.get("name") or self._next_copy_name(source.name)
        fields = {
            "name": name,
            "first_day_fraction": source.first_day_fraction,
            "full_days": source.full_days,
            "last_day_fraction": source.last_day_fraction,
            "drink_mixes_per_day": source.drink_mixes_per_day,
            "oz_per_day": source.oz_per_day,
            "cal_per_oz": source.cal_per_oz,
        }
        fields.update({key: value for key, value in overrides.items() if value is not None})
        self._validate_trip_fields(fields, require_name=True)
        self._ensure_unique_name(fields["name"])

        destination = Trip(**fields)
        self.db.add(destination)
        self.db.flush()
        for snack in self.db.query(TripSnack).filter(
            TripSnack.trip_id == source_trip_id
        ):
            self.db.add(TripSnack(
                trip_id=destination.id,
                catalog_item_id=snack.catalog_item_id,
                servings=snack.servings,
                slot=snack.slot,
                trip_notes=snack.trip_notes,
            ))
        for meal in self.db.query(TripMeal).filter(TripMeal.trip_id == source_trip_id):
            self.db.add(TripMeal(
                trip_id=destination.id,
                recipe_id=meal.recipe_id,
                quantity=meal.quantity,
            ))
        self.db.commit()
        self.db.refresh(destination)
        return destination

    def _next_copy_name(self, source_name: str) -> str:
        candidate = f"{source_name} (copy)"
        suffix = 2
        while self.db.query(Trip).filter(Trip.name == candidate).first():
            candidate = f"{source_name} (copy {suffix})"
            suffix += 1
        return candidate

    def _ensure_unique_name(self, name: str, *, exclude_id: int | None = None) -> None:
        query = self.db.query(Trip).filter(Trip.name == name)
        if exclude_id is not None:
            query = query.filter(Trip.id != exclude_id)
        if query.first():
            raise TripConflictError(f'A trip named "{name}" already exists')

    def update_trip(self, trip_id: int, values: Mapping[str, Any]) -> Trip:
        trip = self.db.get(Trip, trip_id)
        if not trip:
            raise TripNotFoundError("Trip not found")
        fields = dict(values)
        self._validate_trip_fields(fields, require_name=False)
        if "name" in fields:
            self._ensure_unique_name(fields["name"], exclude_id=trip_id)
        for field, value in fields.items():
            setattr(trip, field, value)
        if fields.keys() & ALLOCATION_SHAPE_FIELDS:
            self._clear_assignments(trip_id)
        self.db.commit()
        self.db.refresh(trip)
        return trip

    def _clear_assignments(self, trip_id: int) -> None:
        self.db.query(TripDayAssignment).filter(
            TripDayAssignment.trip_id == trip_id
        ).delete()

    def update_meal(
        self,
        trip_id: int,
        meal_id: int,
        values: Mapping[str, Any],
    ) -> TripMeal:
        meal = self.db.get(TripMeal, meal_id)
        if not meal or meal.trip_id != trip_id:
            raise TripSelectionNotFoundError("Trip meal not found")
        fields = dict(values)
        if "quantity" in fields and fields["quantity"] <= 0:
            raise TripPlanningError("Meal quantity must be greater than zero")
        for field, value in fields.items():
            setattr(meal, field, value)
        if "quantity" in fields:
            self._clear_assignments(trip_id)
        self.db.commit()
        self.db.refresh(meal)
        return meal

    def add_meal(self, trip_id: int, values: Mapping[str, Any]) -> TripMeal:
        if not self.db.get(Trip, trip_id):
            raise TripNotFoundError("Trip not found")
        fields = dict(values)
        if not self.db.get(Recipe, fields.get("recipe_id")):
            raise FoodOptionNotFoundError("Recipe not found")
        if fields.get("quantity", 0) <= 0:
            raise TripPlanningError("Meal quantity must be greater than zero")
        meal = TripMeal(trip_id=trip_id, **fields)
        self.db.add(meal)
        self._clear_assignments(trip_id)
        self.db.commit()
        self.db.refresh(meal)
        return meal

    def set_meal_quantity(
        self,
        trip_id: int,
        recipe_id: int,
        quantity: int,
    ) -> SelectionChangeResult:
        if quantity < 0:
            raise TripPlanningError("quantity cannot be negative")
        if not self.db.get(Trip, trip_id):
            raise TripNotFoundError("Trip not found")
        recipe = self.db.get(Recipe, recipe_id)
        if not recipe:
            raise FoodOptionNotFoundError(f"Recipe {recipe_id} was not found")
        rows = self.db.query(TripMeal).filter(
            TripMeal.trip_id == trip_id,
            TripMeal.recipe_id == recipe_id,
        ).all()
        if quantity == 0:
            for row in rows:
                self.db.delete(row)
            action = "removed"
        elif rows:
            rows[0].quantity = quantity
            for duplicate in rows[1:]:
                self.db.delete(duplicate)
            action = "updated"
        else:
            self.db.add(TripMeal(
                trip_id=trip_id,
                recipe_id=recipe_id,
                quantity=quantity,
            ))
            action = "added"
        self._clear_assignments(trip_id)
        self.db.commit()
        return SelectionChangeResult(action, recipe.name, float(quantity))

    def remove_meal(self, trip_id: int, meal_id: int) -> None:
        meal = self.db.get(TripMeal, meal_id)
        if not meal or meal.trip_id != trip_id:
            raise TripSelectionNotFoundError("Trip meal not found")
        self._clear_assignments(trip_id)
        self.db.delete(meal)
        self.db.commit()

    def update_snack(
        self,
        trip_id: int,
        snack_id: int,
        values: Mapping[str, Any],
    ) -> TripSnack:
        snack = self.db.get(TripSnack, snack_id)
        if not snack or snack.trip_id != trip_id:
            raise TripSelectionNotFoundError("Trip snack not found")
        fields = dict(values)
        if "servings" in fields:
            if fields["servings"] < 0:
                raise TripPlanningError("Snack servings cannot be negative")
            catalog_item = self.db.get(SnackCatalogItem, snack.catalog_item_id)
            if catalog_item and catalog_item.category == "drink_mix":
                fields["servings"] = math.ceil(fields["servings"])
        for field, value in fields.items():
            setattr(snack, field, value)
        if fields.keys() & {"servings", "slot"}:
            self._clear_assignments(trip_id)
        self.db.commit()
        self.db.refresh(snack)
        return snack

    def add_snack(self, trip_id: int, values: Mapping[str, Any]) -> TripSnack:
        if not self.db.get(Trip, trip_id):
            raise TripNotFoundError("Trip not found")
        fields = dict(values)
        catalog_item = self.db.get(SnackCatalogItem, fields.get("catalog_item_id"))
        if not catalog_item:
            raise FoodOptionNotFoundError("Snack catalog item not found")
        if fields.get("servings", 0) < 0:
            raise TripPlanningError("Snack servings cannot be negative")
        if not fields.get("slot"):
            fields["slot"] = CATEGORY_TO_SLOT.get(catalog_item.category, "snacks")
        if catalog_item.category == "drink_mix":
            fields["servings"] = max(1, math.ceil(fields.get("servings") or 1))
        snack = TripSnack(trip_id=trip_id, **fields)
        self.db.add(snack)
        self._clear_assignments(trip_id)
        self.db.commit()
        self.db.refresh(snack)
        return snack

    def set_snack_servings(
        self,
        trip_id: int,
        catalog_item_id: int,
        servings: float,
        slot: str | None = None,
    ) -> SelectionChangeResult:
        if servings < 0:
            raise TripPlanningError("servings cannot be negative")
        if slot is not None and slot not in {"lunch", "snacks"}:
            raise TripPlanningError("slot must be lunch or snacks")
        if not self.db.get(Trip, trip_id):
            raise TripNotFoundError("Trip not found")
        item = self.db.get(SnackCatalogItem, catalog_item_id)
        if not item:
            raise FoodOptionNotFoundError(
                f"Snack catalog item {catalog_item_id} was not found"
            )
        ingredient = self.db.get(Ingredient, item.ingredient_id)
        actual_servings = servings
        if item.category == "drink_mix" and servings > 0:
            actual_servings = math.ceil(servings)
        rows = self.db.query(TripSnack).filter(
            TripSnack.trip_id == trip_id,
            TripSnack.catalog_item_id == catalog_item_id,
        ).all()
        if actual_servings == 0:
            for row in rows:
                self.db.delete(row)
            action = "removed"
        elif rows:
            rows[0].servings = actual_servings
            if slot is not None:
                rows[0].slot = slot
            for duplicate in rows[1:]:
                self.db.delete(duplicate)
            action = "updated"
        else:
            default_slot = CATEGORY_TO_SLOT.get(item.category, "snacks")
            self.db.add(TripSnack(
                trip_id=trip_id,
                catalog_item_id=catalog_item_id,
                servings=actual_servings,
                slot=slot or default_slot,
            ))
            action = "added"
        self._clear_assignments(trip_id)
        self.db.commit()
        return SelectionChangeResult(action, ingredient.name, float(actual_servings))

    def remove_snack(self, trip_id: int, snack_id: int) -> None:
        snack = self.db.get(TripSnack, snack_id)
        if not snack or snack.trip_id != trip_id:
            raise TripSelectionNotFoundError("Trip snack not found")
        self._clear_assignments(trip_id)
        self.db.delete(snack)
        self.db.commit()

    def delete_trip(self, trip_id: int) -> None:
        trip = self.db.get(Trip, trip_id)
        if not trip:
            raise TripNotFoundError("Trip not found")
        self._clear_assignments(trip_id)
        self.db.query(TripSnack).filter(TripSnack.trip_id == trip_id).delete()
        self.db.query(TripMeal).filter(TripMeal.trip_id == trip_id).delete()
        self.db.delete(trip)
        self.db.commit()

    def add_assignment(
        self,
        trip_id: int,
        values: Mapping[str, Any],
    ) -> TripDayAssignment:
        trip = self.db.get(Trip, trip_id)
        if not trip:
            raise TripNotFoundError("Trip not found")
        fields = dict(values)
        valid_days = {day["day_number"] for day in build_day_list(trip)}
        if fields.get("day_number") not in valid_days:
            raise TripPlanningError(
                f"day_number must be one of {sorted(valid_days)}"
            )
        if fields.get("source_type") not in {"meal", "snack"}:
            raise TripPlanningError("source_type must be meal or snack")
        if fields.get("slot") not in SLOT_RULES:
            raise TripPlanningError(
                f"Unknown daily-plan slot: {fields.get('slot')}"
            )
        if fields.get("servings", 0) <= 0:
            raise TripPlanningError(
                "Assignment servings must be greater than zero"
            )
        source_model = TripMeal if fields["source_type"] == "meal" else TripSnack
        source = self.db.get(source_model, fields.get("source_id"))
        if not source or source.trip_id != trip_id:
            label = fields["source_type"].capitalize()
            raise TripPlanningError(f"{label} source is not on this trip")
        selected = source.quantity if fields["source_type"] == "meal" else source.servings
        allocated = sum(
            row.servings
            for row in self.db.query(TripDayAssignment).filter(
                TripDayAssignment.trip_id == trip_id,
                TripDayAssignment.source_type == fields["source_type"],
                TripDayAssignment.source_id == fields["source_id"],
            )
        )
        available = (selected or 0) - allocated
        requested = fields["servings"]
        if requested > available + 1e-9:
            raise TripPlanningError(
                f"Cannot allocate {requested:g} servings; only {available:g} is available"
            )
        assignment = TripDayAssignment(trip_id=trip_id, **fields)
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def update_assignment(
        self,
        trip_id: int,
        assignment_id: int,
        values: Mapping[str, Any],
    ) -> TripDayAssignment:
        assignment = self.db.get(TripDayAssignment, assignment_id)
        if not assignment or assignment.trip_id != trip_id:
            raise TripSelectionNotFoundError("Assignment not found")
        fields = dict(values)
        if "day_number" in fields:
            trip = self.db.get(Trip, trip_id)
            valid_days = {day["day_number"] for day in build_day_list(trip)}
            if fields["day_number"] not in valid_days:
                raise TripPlanningError(
                    f"day_number must be one of {sorted(valid_days)}"
                )
        if "slot" in fields and fields["slot"] not in SLOT_RULES:
            raise TripPlanningError(
                f"Unknown daily-plan slot: {fields['slot']}"
            )
        if "servings" in fields:
            requested = fields["servings"]
            if requested <= 0:
                raise TripPlanningError(
                    "Assignment servings must be greater than zero"
                )
            source_model = (
                TripMeal if assignment.source_type == "meal" else TripSnack
            )
            source = self.db.get(source_model, assignment.source_id)
            if not source or source.trip_id != trip_id:
                raise TripPlanningError(
                    f"{assignment.source_type.capitalize()} source is not on this trip"
                )
            selected = (
                source.quantity if assignment.source_type == "meal" else source.servings
            )
            allocated_elsewhere = sum(
                row.servings
                for row in self.db.query(TripDayAssignment).filter(
                    TripDayAssignment.trip_id == trip_id,
                    TripDayAssignment.source_type == assignment.source_type,
                    TripDayAssignment.source_id == assignment.source_id,
                    TripDayAssignment.id != assignment_id,
                )
            )
            available = (selected or 0) - allocated_elsewhere
            if requested > available + 1e-9:
                raise TripPlanningError(
                    f"Cannot allocate {requested:g} servings; only {available:g} is available"
                )
        for field, value in fields.items():
            setattr(assignment, field, value)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def remove_assignment(self, trip_id: int, assignment_id: int) -> None:
        assignment = self.db.get(TripDayAssignment, assignment_id)
        if not assignment or assignment.trip_id != trip_id:
            raise TripSelectionNotFoundError("Assignment not found")
        self.db.delete(assignment)
        self.db.commit()

    @staticmethod
    def _validate_trip_fields(fields: dict[str, Any], *, require_name: bool) -> None:
        if require_name or "name" in fields:
            name = str(fields.get("name", "")).strip()
            if not name:
                raise TripPlanningError("Trip name is required")
            fields["name"] = name
        for field in ("first_day_fraction", "last_day_fraction"):
            value = fields.get(field)
            if value is not None and not 0 <= value <= 1:
                raise TripPlanningError(f"{field} must be between 0 and 1")
        if fields.get("full_days", 0) < 0:
            raise TripPlanningError("full_days cannot be negative")
        if fields.get("drink_mixes_per_day", 0) < 0:
            raise TripPlanningError("drink_mixes_per_day cannot be negative")
        for field in ("oz_per_day", "cal_per_oz"):
            value = fields.get(field)
            if value is not None and value <= 0:
                raise TripPlanningError(f"{field} must be greater than zero")
