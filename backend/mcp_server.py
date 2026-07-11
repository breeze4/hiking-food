"""Conversational tool surface for planning hiking food over remote MCP."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Literal
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Ingredient, SnackCatalogItem
from routers.recipes import list_recipes as build_recipe_list
from routers.snacks import _to_response as build_snack
from services.trip_planning import TripPlanningService


READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True)
WRITE_NEW = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
WRITE_UPDATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)

DEFAULT_MCP_ALLOWED_HOSTS = ["localhost:8000", "127.0.0.1:8000", "beebaby:8000"]
DEFAULT_MCP_ALLOWED_ORIGINS = [
    "http://localhost:8000", "http://127.0.0.1:8000", "http://beebaby:8000",
]


def _env_list(name: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


def _issuer_host_and_origin() -> tuple[str, str]:
    parsed = urlparse(
        os.environ.get("HIKING_FOOD_OAUTH_ISSUER", "http://localhost:8000/hiking-food")
    )
    if not parsed.scheme or not parsed.netloc:
        return "", ""
    return parsed.netloc, f"{parsed.scheme}://{parsed.netloc}"


def build_transport_security() -> TransportSecuritySettings:
    """Enable DNS-rebinding protection with an env-configurable host/origin policy.

    Allowed hosts/origins come from ``HIKING_FOOD_MCP_ALLOWED_HOSTS`` /
    ``HIKING_FOOD_MCP_ALLOWED_ORIGINS`` (comma-separated). When unset, the
    defaults cover localhost, 127.0.0.1, beebaby, and the host of
    ``HIKING_FOOD_OAUTH_ISSUER`` so the production Funnel hostname is accepted
    without extra configuration.
    """
    issuer_host, issuer_origin = _issuer_host_and_origin()
    default_hosts = list(DEFAULT_MCP_ALLOWED_HOSTS)
    default_origins = list(DEFAULT_MCP_ALLOWED_ORIGINS)
    if issuer_host and issuer_host not in default_hosts:
        default_hosts.append(issuer_host)
    if issuer_origin and issuer_origin not in default_origins:
        default_origins.append(issuer_origin)
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_env_list("HIKING_FOOD_MCP_ALLOWED_HOSTS") or default_hosts,
        allowed_origins=_env_list("HIKING_FOOD_MCP_ALLOWED_ORIGINS") or default_origins,
    )


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
        transport_security=build_transport_security(),
    )

    @mcp.tool(annotations=READ_ONLY)
    def list_trips() -> dict:
        """List existing trips before choosing a source or destination. This is read-only."""
        with _session() as db:
            return {"trips": TripPlanningService(db).list_trips(newest_first=True)}

    @mcp.tool(annotations=READ_ONLY)
    def get_trip_plan(
        trip_id: int,
        section: Literal["overview", "daily_plan", "packing", "shopping", "all"] = "overview",
    ) -> dict:
        """Read one trip. Use overview for planning; request heavier sections only when needed."""
        with _session() as db:
            planner = TripPlanningService(db)
            result: dict = {"trip": planner.read_trip(trip_id)}
            if section in {"overview", "all"}:
                result["summary"] = planner.read_summary(trip_id)
            if section in {"daily_plan", "all"}:
                result["daily_plan"] = planner.read_daily_plan(trip_id)
            if section in {"packing", "all"}:
                result["packing"] = planner.read_packing(trip_id)
            if section in {"shopping", "all"}:
                result["shopping"] = planner.read_shopping(trip_id)
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
        with _session() as db:
            trip = TripPlanningService(db).create_trip({
                "name": name,
                "first_day_fraction": first_day_fraction,
                "full_days": full_days,
                "last_day_fraction": last_day_fraction,
                "drink_mixes_per_day": drink_mixes_per_day,
                "oz_per_day": oz_per_day,
                "cal_per_oz": cal_per_oz,
            })
            return {
                "trip": TripPlanningService(db).read_trip(trip.id),
                "daily_plan_needs_autofill": True,
            }

    @mcp.tool(annotations=WRITE_NEW)
    def clone_trip(
        source_trip_id: int, name: str,
        first_day_fraction: float | None = None, full_days: int | None = None,
        last_day_fraction: float | None = None, drink_mixes_per_day: int | None = None,
        oz_per_day: float | None = None, cal_per_oz: float | None = None,
    ) -> dict:
        """Clone a prior trip into a uniquely named destination and optionally change its shape."""
        with _session() as db:
            destination = TripPlanningService(db).clone_trip(source_trip_id, {
                "name": name,
                "first_day_fraction": first_day_fraction,
                "full_days": full_days,
                "last_day_fraction": last_day_fraction,
                "drink_mixes_per_day": drink_mixes_per_day,
                "oz_per_day": oz_per_day,
                "cal_per_oz": cal_per_oz,
            })
            return {
                "source_trip_id": source_trip_id,
                "trip": TripPlanningService(db).read_trip(destination.id),
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
            "name": name,
            "first_day_fraction": first_day_fraction, "full_days": full_days,
            "last_day_fraction": last_day_fraction,
            "drink_mixes_per_day": drink_mixes_per_day,
            "oz_per_day": oz_per_day, "cal_per_oz": cal_per_oz,
        }
        with _session() as db:
            trip = TripPlanningService(db).update_trip(
                trip_id,
                {field: value for field, value in updates.items() if value is not None},
            )
            return {
                "trip": TripPlanningService(db).read_trip(trip.id),
                "daily_plan_needs_autofill": True,
            }

    @mcp.tool(annotations=WRITE_UPDATE)
    def set_trip_meal_quantity(trip_id: int, recipe_id: int, quantity: int) -> dict:
        """Set a recipe's total quantity on a trip. Use zero to remove it."""
        with _session() as db:
            result = TripPlanningService(db).set_meal_quantity(
                trip_id, recipe_id, quantity
            )
            return {
                "trip_id": trip_id, "recipe_id": recipe_id, "recipe_name": result.name,
                "quantity": int(result.amount), "action": result.action,
                "daily_plan_needs_autofill": True,
            }

    @mcp.tool(annotations=WRITE_UPDATE)
    def set_trip_snack_servings(
        trip_id: int, catalog_item_id: int, servings: float, slot: str | None = None,
    ) -> dict:
        """Set a snack catalog item's total servings on a trip. Use zero to remove it."""
        with _session() as db:
            result = TripPlanningService(db).set_snack_servings(
                trip_id, catalog_item_id, servings, slot
            )
            return {
                "trip_id": trip_id, "catalog_item_id": catalog_item_id,
                "ingredient_name": result.name, "servings": result.amount,
                "action": result.action, "daily_plan_needs_autofill": True,
            }

    @mcp.tool(annotations=WRITE_UPDATE)
    def auto_fill_daily_plan(trip_id: int) -> dict:
        """Regenerate all day assignments after trip inventory or duration changes."""
        with _session() as db:
            return {
                "trip_id": trip_id,
                "daily_plan": TripPlanningService(db).regenerate_daily_plan(trip_id),
            }

    @mcp.tool(annotations=WRITE_UPDATE)
    def update_daily_assignment(
        trip_id: int, assignment_id: int, day_number: int | None = None,
        slot: Literal[
            "breakfast", "breakfast_drinks", "morning_snacks", "lunch",
            "snacks", "afternoon_snacks", "dinner", "evening_drinks",
            "all_day_drinks",
        ] | None = None,
        servings: float | None = None,
    ) -> dict:
        """Move, resize, or remove one existing daily-plan assignment. Set servings to zero to remove."""
        with _session() as db:
            planner = TripPlanningService(db)
            if servings == 0:
                planner.remove_assignment(trip_id, assignment_id)
            else:
                fields = {
                    "day_number": day_number,
                    "slot": "afternoon_snacks" if slot == "snacks" else slot,
                    "servings": servings,
                }
                planner.update_assignment(
                    trip_id,
                    assignment_id,
                    {field: value for field, value in fields.items() if value is not None},
                )
            return {"trip_id": trip_id, "daily_plan": planner.read_daily_plan(trip_id)}

    return mcp
