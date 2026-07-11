"""Conversational tool surface for planning hiking food over remote MCP."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from sqlalchemy.orm import Session

from database import SessionLocal
from models import (
    Ingredient, Recipe, SnackCatalogItem, Trip, TripDayAssignment, TripMeal, TripSnack,
)
from routers.daily_plan import get_daily_plan as build_daily_plan
from routers.daily_plan import run_auto_fill
from routers.recipes import list_recipes as build_recipe_list
from routers.snacks import _to_response as build_snack
from routers.trips import (
    _build_trip_detail, get_packing_detail, get_shopping_list, get_trip_summary,
)
from services.autofill import build_day_list


READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
WRITE_NEW = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
WRITE_UPDATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)


@contextmanager
def _session():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _trip(db: Session, trip_id: int) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip:
        raise ValueError(f"Trip {trip_id} was not found")
    return trip


def _ensure_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    query = db.query(Trip).filter(Trip.name == name.strip())
    if exclude_id is not None:
        query = query.filter(Trip.id != exclude_id)
    if query.first():
        raise ValueError(f'A trip named "{name.strip()}" already exists')


def _clear_assignments(db: Session, trip_id: int) -> None:
    db.query(TripDayAssignment).filter(TripDayAssignment.trip_id == trip_id).delete()


def build_mcp_server() -> FastMCP:
    mcp = FastMCP(
        "Hiking Food",
        instructions=(
            "Use these tools to inspect, create, clone, and refine hiking-trip food plans. "
            "Before writing, list trips and inspect the intended source or destination. "
            "Never create a duplicate destination trip. Prefer cloning a relevant prior trip, "
            "then make targeted quantity changes and run auto_fill_daily_plan. After changes, "
            "read the overview and daily plan to verify totals and unallocated food."
        ),
        streamable_http_path="/",
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool(annotations=READ_ONLY)
    def list_trips() -> dict:
        """List existing trips before choosing a source or destination. This is read-only."""
        with _session() as db:
            trips = db.query(Trip).order_by(Trip.id.desc()).all()
            return {
                "trips": [
                    {
                        "id": trip.id, "name": trip.name,
                        "total_days": round(sum(d["fraction"] for d in build_day_list(trip)), 2),
                        "first_day_fraction": trip.first_day_fraction,
                        "full_days": trip.full_days,
                        "last_day_fraction": trip.last_day_fraction,
                    }
                    for trip in trips
                ]
            }

    @mcp.tool(annotations=READ_ONLY)
    def get_trip_plan(
        trip_id: int,
        section: Literal["overview", "daily_plan", "packing", "shopping", "all"] = "overview",
    ) -> dict:
        """Read one trip. Use overview for planning; request heavier sections only when needed."""
        with _session() as db:
            trip = _trip(db, trip_id)
            result: dict = {"trip": _build_trip_detail(trip, db)}
            if section in {"overview", "all"}:
                result["summary"] = get_trip_summary(trip_id, db)
            if section in {"daily_plan", "all"}:
                result["daily_plan"] = build_daily_plan(trip_id, db)
            if section in {"packing", "all"}:
                result["packing"] = get_packing_detail(trip_id, db)
            if section in {"shopping", "all"}:
                result["shopping"] = get_shopping_list(trip_id, db)
            return result

    @mcp.tool(annotations=READ_ONLY)
    def list_food_options(
        kind: Literal["recipes", "snacks", "all"] = "all",
        category: str | None = None,
        query: str | None = None,
    ) -> dict:
        """List recipe and snack catalog choices for targeted trip-plan changes."""
        needle = query.strip().lower() if query else None
        with _session() as db:
            result: dict = {}
            if kind in {"recipes", "all"}:
                recipes = build_recipe_list(category=category, db=db)
                result["recipes"] = [
                    item for item in recipes
                    if not needle or needle in str(item["name"]).lower()
                ]
            if kind in {"snacks", "all"}:
                q = db.query(SnackCatalogItem, Ingredient).join(
                    Ingredient, SnackCatalogItem.ingredient_id == Ingredient.id
                )
                if category:
                    q = q.filter(SnackCatalogItem.category == category)
                snacks = [build_snack(item, ingredient) for item, ingredient in q.all()]
                result["snacks"] = [
                    item for item in snacks
                    if not needle or needle in str(item["ingredient_name"]).lower()
                ]
            return result

    @mcp.tool(annotations=WRITE_NEW)
    def create_trip(
        name: str, first_day_fraction: float = 1.0, full_days: int = 0,
        last_day_fraction: float = 0.0, drink_mixes_per_day: int = 2,
        oz_per_day: float = 22.0, cal_per_oz: float = 125.0,
    ) -> dict:
        """Create a new empty trip. Prefer clone_trip when a relevant prior plan exists."""
        if not name.strip() or full_days < 0:
            raise ValueError("name is required and full_days cannot be negative")
        if first_day_fraction < 0 or last_day_fraction < 0:
            raise ValueError("day fractions cannot be negative")
        with _session() as db:
            _ensure_unique_name(db, name)
            trip = Trip(
                name=name.strip(), first_day_fraction=first_day_fraction,
                full_days=full_days, last_day_fraction=last_day_fraction,
                drink_mixes_per_day=drink_mixes_per_day,
                oz_per_day=oz_per_day, cal_per_oz=cal_per_oz,
            )
            db.add(trip)
            db.commit()
            db.refresh(trip)
            return {"trip": _build_trip_detail(trip, db), "daily_plan_needs_autofill": True}

    @mcp.tool(annotations=WRITE_NEW)
    def clone_trip(
        source_trip_id: int, name: str,
        first_day_fraction: float | None = None, full_days: int | None = None,
        last_day_fraction: float | None = None, drink_mixes_per_day: int | None = None,
        oz_per_day: float | None = None, cal_per_oz: float | None = None,
    ) -> dict:
        """Clone a prior trip into a uniquely named destination and optionally change its shape."""
        with _session() as db:
            source = _trip(db, source_trip_id)
            _ensure_unique_name(db, name)
            destination = Trip(
                name=name.strip(),
                first_day_fraction=source.first_day_fraction if first_day_fraction is None else first_day_fraction,
                full_days=source.full_days if full_days is None else full_days,
                last_day_fraction=source.last_day_fraction if last_day_fraction is None else last_day_fraction,
                drink_mixes_per_day=(source.drink_mixes_per_day if drink_mixes_per_day is None else drink_mixes_per_day),
                oz_per_day=source.oz_per_day if oz_per_day is None else oz_per_day,
                cal_per_oz=source.cal_per_oz if cal_per_oz is None else cal_per_oz,
            )
            db.add(destination)
            db.flush()
            for snack in db.query(TripSnack).filter(TripSnack.trip_id == source.id).all():
                db.add(TripSnack(
                    trip_id=destination.id, catalog_item_id=snack.catalog_item_id,
                    servings=snack.servings, slot=snack.slot, trip_notes=snack.trip_notes,
                ))
            for meal in db.query(TripMeal).filter(TripMeal.trip_id == source.id).all():
                db.add(TripMeal(
                    trip_id=destination.id, recipe_id=meal.recipe_id, quantity=meal.quantity,
                ))
            db.commit()
            db.refresh(destination)
            return {
                "source_trip_id": source.id,
                "trip": _build_trip_detail(destination, db),
                "daily_plan_needs_autofill": True,
            }

    @mcp.tool(annotations=WRITE_UPDATE)
    def update_trip(
        trip_id: int, name: str | None = None,
        first_day_fraction: float | None = None, full_days: int | None = None,
        last_day_fraction: float | None = None, drink_mixes_per_day: int | None = None,
        oz_per_day: float | None = None, cal_per_oz: float | None = None,
    ) -> dict:
        """Update a trip's name, duration, drink-mix target, or calorie/weight targets."""
        updates = {
            "name": name.strip() if name is not None else None,
            "first_day_fraction": first_day_fraction, "full_days": full_days,
            "last_day_fraction": last_day_fraction,
            "drink_mixes_per_day": drink_mixes_per_day,
            "oz_per_day": oz_per_day, "cal_per_oz": cal_per_oz,
        }
        with _session() as db:
            trip = _trip(db, trip_id)
            if name is not None:
                if not name.strip():
                    raise ValueError("name cannot be blank")
                _ensure_unique_name(db, name, exclude_id=trip_id)
            for field, value in updates.items():
                if value is not None:
                    setattr(trip, field, value)
            _clear_assignments(db, trip_id)
            db.commit()
            db.refresh(trip)
            return {"trip": _build_trip_detail(trip, db), "daily_plan_needs_autofill": True}

    @mcp.tool(annotations=WRITE_UPDATE)
    def set_trip_meal_quantity(trip_id: int, recipe_id: int, quantity: int) -> dict:
        """Set a recipe's total quantity on a trip. Use zero to remove it."""
        if quantity < 0:
            raise ValueError("quantity cannot be negative")
        with _session() as db:
            _trip(db, trip_id)
            recipe = db.get(Recipe, recipe_id)
            if not recipe:
                raise ValueError(f"Recipe {recipe_id} was not found")
            rows = db.query(TripMeal).filter(
                TripMeal.trip_id == trip_id, TripMeal.recipe_id == recipe_id
            ).all()
            if quantity == 0:
                for row in rows:
                    db.delete(row)
                action = "removed"
            elif rows:
                rows[0].quantity = quantity
                for duplicate in rows[1:]:
                    db.delete(duplicate)
                action = "updated"
            else:
                db.add(TripMeal(trip_id=trip_id, recipe_id=recipe_id, quantity=quantity))
                action = "added"
            _clear_assignments(db, trip_id)
            db.commit()
            return {
                "trip_id": trip_id, "recipe_id": recipe_id, "recipe_name": recipe.name,
                "quantity": quantity, "action": action, "daily_plan_needs_autofill": True,
            }

    @mcp.tool(annotations=WRITE_UPDATE)
    def set_trip_snack_servings(
        trip_id: int, catalog_item_id: int, servings: float, slot: str | None = None,
    ) -> dict:
        """Set a snack catalog item's total servings on a trip. Use zero to remove it."""
        if servings < 0:
            raise ValueError("servings cannot be negative")
        if slot is not None and slot not in {"lunch", "snacks"}:
            raise ValueError("slot must be lunch or snacks")
        with _session() as db:
            _trip(db, trip_id)
            item = db.get(SnackCatalogItem, catalog_item_id)
            if not item:
                raise ValueError(f"Snack catalog item {catalog_item_id} was not found")
            ingredient = db.get(Ingredient, item.ingredient_id)
            rows = db.query(TripSnack).filter(
                TripSnack.trip_id == trip_id,
                TripSnack.catalog_item_id == catalog_item_id,
            ).all()
            if servings == 0:
                for row in rows:
                    db.delete(row)
                action = "removed"
            elif rows:
                rows[0].servings = servings
                if slot is not None:
                    rows[0].slot = slot
                for duplicate in rows[1:]:
                    db.delete(duplicate)
                action = "updated"
            else:
                default_slot = "lunch" if item.category == "lunch" else "snacks"
                db.add(TripSnack(
                    trip_id=trip_id, catalog_item_id=catalog_item_id,
                    servings=servings, slot=slot or default_slot,
                ))
                action = "added"
            _clear_assignments(db, trip_id)
            db.commit()
            return {
                "trip_id": trip_id, "catalog_item_id": catalog_item_id,
                "ingredient_name": ingredient.name, "servings": servings,
                "action": action, "daily_plan_needs_autofill": True,
            }

    @mcp.tool(annotations=WRITE_UPDATE)
    def auto_fill_daily_plan(trip_id: int) -> dict:
        """Regenerate all day assignments after trip inventory or duration changes."""
        with _session() as db:
            _trip(db, trip_id)
            return {"trip_id": trip_id, "daily_plan": run_auto_fill(trip_id, db)}

    @mcp.tool(annotations=WRITE_UPDATE)
    def update_daily_assignment(
        trip_id: int, assignment_id: int, day_number: int | None = None,
        slot: Literal["breakfast", "lunch", "snacks", "dinner"] | None = None,
        servings: float | None = None,
    ) -> dict:
        """Move, resize, or remove one existing daily-plan assignment. Set servings to zero to remove."""
        with _session() as db:
            trip = _trip(db, trip_id)
            assignment = db.get(TripDayAssignment, assignment_id)
            if not assignment or assignment.trip_id != trip_id:
                raise ValueError(f"Assignment {assignment_id} was not found on trip {trip_id}")
            if day_number is not None:
                valid_days = {day["day_number"] for day in build_day_list(trip)}
                if day_number not in valid_days:
                    raise ValueError(f"day_number must be one of {sorted(valid_days)}")
                assignment.day_number = day_number
            if slot is not None:
                assignment.slot = slot
            if servings is not None:
                if servings < 0:
                    raise ValueError("servings cannot be negative")
                if servings == 0:
                    db.delete(assignment)
                else:
                    assignment.servings = servings
            db.commit()
            return {"trip_id": trip_id, "daily_plan": build_daily_plan(trip_id, db)}

    return mcp
