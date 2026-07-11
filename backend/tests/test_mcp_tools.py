import pytest

from database import Base
from models import (
    Ingredient, Recipe, RecipeIngredient, SnackCatalogItem,
    Trip, TripDayAssignment, TripMeal, TripSnack,
)
import mcp_server
from main import app as outer_app, lifespan as production_lifespan


@pytest.fixture(autouse=True)
def db_setup(test_engine, test_session, monkeypatch):
    Base.metadata.create_all(bind=test_engine)
    monkeypatch.setattr(mcp_server, "SessionLocal", test_session)
    db = test_session()
    oats = Ingredient(name="Oats", calories_per_oz=120)
    nuts = Ingredient(name="Nuts", calories_per_oz=170)
    db.add_all([oats, nuts])
    db.flush()
    breakfast = Recipe(name="Oatmeal", category="breakfast")
    db.add(breakfast)
    db.flush()
    db.add(RecipeIngredient(recipe_id=breakfast.id, ingredient_id=oats.id, amount_oz=3))
    snack = SnackCatalogItem(
        ingredient_id=nuts.id, weight_per_serving=2,
        calories_per_serving=340, category="salty",
    )
    db.add(snack)
    db.flush()
    trip = Trip(
        name="Summer Source", first_day_fraction=1, full_days=1,
        last_day_fraction=0, drink_mixes_per_day=0, oz_per_day=22, cal_per_oz=125,
    )
    db.add(trip)
    db.flush()
    db.add(TripMeal(trip_id=trip.id, recipe_id=breakfast.id, quantity=2))
    db.add(TripSnack(trip_id=trip.id, catalog_item_id=snack.id, servings=4, slot="snacks"))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


def _tools():
    return mcp_server.build_mcp_server()._tool_manager._tools


def test_tool_surface_is_small_and_stable():
    assert set(_tools()) == {
        "list_trips", "get_trip_plan", "list_food_options", "create_trip",
        "clone_trip", "update_trip", "set_trip_meal_quantity",
        "set_trip_snack_servings", "auto_fill_daily_plan", "update_daily_assignment",
    }


def test_outer_production_app_owns_lifespan():
    """Uvicorn serves the outer app; mounted inner lifespans are not started."""
    assert outer_app.router.lifespan_context is production_lifespan


def test_clone_adjust_autofill_and_read_workflow(test_session):
    tools = _tools()
    listed = tools["list_trips"].fn()
    source_id = listed["trips"][0]["id"]
    cloned = tools["clone_trip"].fn(
        source_trip_id=source_id, name="Autumn Destination", full_days=2,
    )
    destination_id = cloned["trip"]["id"]
    assert cloned["trip"]["name"] == "Autumn Destination"
    assert cloned["trip"]["full_days"] == 2
    assert cloned["trip"]["meals"][0]["quantity"] == 2

    recipe_id = cloned["trip"]["meals"][0]["recipe_id"]
    tools["set_trip_meal_quantity"].fn(destination_id, recipe_id, 3)
    snack_id = cloned["trip"]["snacks"][0]["catalog_item_id"]
    tools["set_trip_snack_servings"].fn(destination_id, snack_id, 6, "snacks")
    filled = tools["auto_fill_daily_plan"].fn(destination_id)
    assert filled["daily_plan"]["days"]

    overview = tools["get_trip_plan"].fn(destination_id, "overview")
    assert overview["trip"]["meals"][0]["quantity"] == 3
    assert overview["trip"]["snacks"][0]["servings"] == 6
    with test_session() as db:
        assert db.query(TripDayAssignment).filter_by(trip_id=destination_id).count() > 0


def test_duplicate_destination_is_rejected():
    tools = _tools()
    source_id = tools["list_trips"].fn()["trips"][0]["id"]
    with pytest.raises(ValueError, match="already exists"):
        tools["clone_trip"].fn(source_id, "Summer Source")


def test_inventory_change_clears_stale_assignments(test_session):
    tools = _tools()
    source_id = tools["list_trips"].fn()["trips"][0]["id"]
    tools["auto_fill_daily_plan"].fn(source_id)
    with test_session() as db:
        assert db.query(TripDayAssignment).filter_by(trip_id=source_id).count() > 0
        recipe_id = db.query(TripMeal).filter_by(trip_id=source_id).one().recipe_id
    tools["set_trip_meal_quantity"].fn(source_id, recipe_id, 1)
    with test_session() as db:
        assert db.query(TripDayAssignment).filter_by(trip_id=source_id).count() == 0


def test_assignment_update_cannot_exceed_trip_inventory():
    tools = _tools()
    trip_id = tools["list_trips"].fn()["trips"][0]["id"]
    plan = tools["auto_fill_daily_plan"].fn(trip_id)["daily_plan"]
    assignment = next(
        item
        for day in plan["days"]
        for item in day["items"]
        if item["source_type"] == "snack"
    )

    with pytest.raises(ValueError, match="Cannot allocate"):
        tools["update_daily_assignment"].fn(
            trip_id,
            assignment["id"],
            servings=5,
        )
