import pytest

from database import Base
from models import (
    Ingredient, Recipe, RecipeIngredient, SnackCatalogItem,
    Trip, TripDayAssignment, TripMeal, TripSnack,
)
import mcp_server
from main import app as outer_app, lifespan as production_lifespan
from services.snack_units import unit_quota


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


def _ingredient_ids(test_session):
    with test_session() as db:
        return {row.name: row.id for row in db.query(Ingredient).all()}


def _legacy_trip_id(tools):
    return next(
        trip["id"] for trip in tools["list_trips"].fn()["trips"]
        if trip["snack_model"] == "legacy"
    )


def _structured_trip(tools, name="Structured Destination"):
    """A half + 2 + half day trip at the default 4 snacks/day: a quota of 12."""
    return tools["create_trip"].fn(
        name=name, first_day_fraction=0.5, full_days=2, last_day_fraction=0.5,
    )["trip"]


def _packaged_snack_id(tools):
    return tools["list_food_options"].fn(kind="snacks")["snacks"][0]["id"]


def test_tool_surface_is_small_and_stable():
    assert set(_tools()) == {
        "list_trips", "get_trip_plan", "list_food_options", "create_trip",
        "clone_trip", "update_trip", "set_trip_meal_quantity",
        "set_trip_snack_servings", "list_snack_unit_types",
        "create_snack_unit_type", "set_trip_snack_unit", "remove_trip_snack_unit",
        "auto_fill_daily_plan", "update_daily_assignment",
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


def test_mcp_overview_matches_rest_trip_and_summary(c):
    tools = _tools()
    trip_id = tools["list_trips"].fn()["trips"][0]["id"]

    mcp_view = tools["get_trip_plan"].fn(trip_id, "overview")
    rest_trip = c.get(f"/api/trips/{trip_id}").json()
    rest_summary = c.get(f"/api/trips/{trip_id}/summary").json()

    assert mcp_view["trip"] == rest_trip
    assert mcp_view["summary"] == rest_summary


def test_list_food_options_returns_recipes_and_snacks():
    options = _tools()["list_food_options"].fn()
    assert "Oatmeal" in [item["name"] for item in options["recipes"]]
    assert "Nuts" in [item["ingredient_name"] for item in options["snacks"]]


def test_list_food_options_kind_selects_one_catalog():
    tools = _tools()
    recipes_only = tools["list_food_options"].fn(kind="recipes")
    assert "recipes" in recipes_only and "snacks" not in recipes_only
    snacks_only = tools["list_food_options"].fn(kind="snacks")
    assert "snacks" in snacks_only and "recipes" not in snacks_only


def test_list_food_options_category_filters_each_catalog():
    tools = _tools()
    breakfast = tools["list_food_options"].fn(category="breakfast")
    assert [item["name"] for item in breakfast["recipes"]] == ["Oatmeal"]
    assert breakfast["snacks"] == []
    salty = tools["list_food_options"].fn(category="salty")
    assert salty["recipes"] == []
    assert [item["ingredient_name"] for item in salty["snacks"]] == ["Nuts"]


def test_list_food_options_query_filters_by_name():
    tools = _tools()
    oat = tools["list_food_options"].fn(query="oat")
    assert [item["name"] for item in oat["recipes"]] == ["Oatmeal"]
    assert oat["snacks"] == []
    nut = tools["list_food_options"].fn(query="nut")
    assert nut["recipes"] == []
    assert [item["ingredient_name"] for item in nut["snacks"]] == ["Nuts"]
    empty = tools["list_food_options"].fn(query="zzz")
    assert empty["recipes"] == []
    assert empty["snacks"] == []


def test_list_food_options_matches_rest_catalog(c):
    options = _tools()["list_food_options"].fn()
    assert options["recipes"] == c.get("/api/recipes").json()
    assert options["snacks"] == c.get("/api/snacks").json()


def test_a_created_bag_lists_with_its_derived_values(test_session):
    tools = _tools()
    ingredients = _ingredient_ids(test_session)
    created = tools["create_snack_unit_type"].fn(
        name="Trail Bag",
        composition=[
            {"ingredient_id": ingredients["Oats"], "amount_oz": 1},
            {"ingredient_id": ingredients["Nuts"], "amount_oz": 1},
        ],
        notes="oats and nuts",
    )["unit_type"]
    assert created["weight_oz"] == 2.0
    assert created["calories"] == 290.0

    listed = tools["list_snack_unit_types"].fn()["unit_types"]
    assert [bag["name"] for bag in listed] == ["Trail Bag"]
    assert listed[0]["cal_per_oz"] == 145.0
    assert listed[0]["weight_warning"] is False
    assert [row["ingredient_name"] for row in listed[0]["composition"]] == [
        "Oats", "Nuts",
    ]


def test_a_bag_cannot_name_an_unknown_ingredient():
    tools = _tools()
    with pytest.raises(ValueError, match="Ingredient 999 not found"):
        tools["create_snack_unit_type"].fn(
            name="Ghost Bag", composition=[{"ingredient_id": 999, "amount_oz": 1}],
        )
    assert tools["list_snack_unit_types"].fn()["unit_types"] == []


def test_units_fill_the_quota_of_a_structured_trip(test_session):
    tools = _tools()
    trip = _structured_trip(tools)
    assert trip["snack_model"] == "structured"
    bag_id = tools["create_snack_unit_type"].fn(
        name="Trail Bag",
        composition=[
            {"ingredient_id": _ingredient_ids(test_session)["Nuts"], "amount_oz": 2},
        ],
    )["unit_type"]["id"]

    packaged = tools["set_trip_snack_unit"].fn(
        trip["id"], catalog_item_id=_packaged_snack_id(tools), quantity=7,
    )
    assert packaged["action"] == "added"
    assert packaged["unit"]["kind"] == "packaged"
    assert packaged["unit"]["name"] == "Nuts"
    assert packaged["daily_plan_needs_autofill"] is True
    assert packaged["snack_units"] == {"quota": 12, "per_day": [2, 4, 4, 2], "filled": 7}

    bagged = tools["set_trip_snack_unit"].fn(trip["id"], unit_type_id=bag_id, quantity=5)
    assert bagged["unit"]["kind"] == "bag"
    assert bagged["snack_units"]["filled"] == 12

    overview = tools["get_trip_plan"].fn(trip["id"], "overview")
    assert overview["summary"]["snack_units"] == {
        "quota": 12, "per_day": [2, 4, 4, 2], "filled": 12,
    }
    assert [
        (unit["name"], unit["quantity"])
        for unit in overview["trip"]["snack_units"]
    ] == [("Nuts", 7), ("Trail Bag", 5)]


def test_the_quota_readout_matches_the_quota_service(test_session):
    tools = _tools()
    trip = tools["create_trip"].fn(
        name="Quota Trip", first_day_fraction=0.5, full_days=3, last_day_fraction=0.25,
    )["trip"]
    with test_session() as db:
        expected = unit_quota(db.get(Trip, trip["id"]))
    readout = tools["get_trip_plan"].fn(trip["id"], "overview")["summary"]["snack_units"]
    assert {"quota": readout["quota"], "per_day": readout["per_day"]} == expected


def test_setting_a_unit_to_zero_removes_it():
    tools = _tools()
    trip = _structured_trip(tools)
    catalog_item_id = _packaged_snack_id(tools)
    tools["set_trip_snack_unit"].fn(trip["id"], catalog_item_id=catalog_item_id, quantity=6)

    lowered = tools["set_trip_snack_unit"].fn(
        trip["id"], catalog_item_id=catalog_item_id, quantity=4,
    )
    assert lowered["action"] == "updated"
    assert lowered["snack_units"]["filled"] == 4

    zeroed = tools["set_trip_snack_unit"].fn(
        trip["id"], catalog_item_id=catalog_item_id, quantity=0,
    )
    assert zeroed["action"] == "removed"
    assert zeroed["snack_units"]["filled"] == 0
    assert tools["get_trip_plan"].fn(trip["id"])["trip"]["snack_units"] == []


def test_a_unit_selection_can_be_removed_by_its_id():
    tools = _tools()
    trip = _structured_trip(tools)
    added = tools["set_trip_snack_unit"].fn(
        trip["id"], catalog_item_id=_packaged_snack_id(tools), quantity=3,
    )
    removed = tools["remove_trip_snack_unit"].fn(trip["id"], added["unit"]["id"])
    assert removed["action"] == "removed"
    assert removed["snack_units"]["filled"] == 0
    with pytest.raises(ValueError, match="Trip snack unit not found"):
        tools["remove_trip_snack_unit"].fn(trip["id"], added["unit"]["id"])


def test_a_unit_names_exactly_one_reference():
    tools = _tools()
    trip = _structured_trip(tools)
    catalog_item_id = _packaged_snack_id(tools)
    for arguments in (
        {"quantity": 2},
        {"quantity": 0},
        {"catalog_item_id": catalog_item_id, "unit_type_id": 1, "quantity": 2},
    ):
        with pytest.raises(
            ValueError, match="exactly one of catalog_item_id or unit_type_id"
        ):
            tools["set_trip_snack_unit"].fn(trip["id"], **arguments)


def test_a_unit_change_clears_stale_assignments(test_session):
    tools = _tools()
    trip = _structured_trip(tools)
    catalog_item_id = _packaged_snack_id(tools)
    tools["set_trip_snack_unit"].fn(trip["id"], catalog_item_id=catalog_item_id, quantity=12)
    tools["auto_fill_daily_plan"].fn(trip["id"])
    with test_session() as db:
        assert db.query(TripDayAssignment).filter_by(trip_id=trip["id"]).count() > 0

    tools["set_trip_snack_unit"].fn(trip["id"], catalog_item_id=catalog_item_id, quantity=8)
    with test_session() as db:
        assert db.query(TripDayAssignment).filter_by(trip_id=trip["id"]).count() == 0


def test_unit_tools_reject_a_legacy_trip():
    tools = _tools()
    legacy_id = _legacy_trip_id(tools)
    catalog_item_id = _packaged_snack_id(tools)
    calls = (
        lambda: tools["set_trip_snack_unit"].fn(
            legacy_id, catalog_item_id=catalog_item_id, quantity=2,
        ),
        # Even the paths that would otherwise do nothing: removing a unit the
        # legacy trip does not have is still a refusal, not a silent success.
        lambda: tools["set_trip_snack_unit"].fn(
            legacy_id, catalog_item_id=catalog_item_id, quantity=0,
        ),
        lambda: tools["remove_trip_snack_unit"].fn(legacy_id, 1),
    )
    for call in calls:
        with pytest.raises(
            ValueError, match="Trip does not use the structured snack model"
        ):
            call()


def test_a_legacy_trip_plan_carries_no_unit_quota():
    tools = _tools()
    plan = tools["get_trip_plan"].fn(_legacy_trip_id(tools), "all")
    assert "snack_units" not in plan["summary"]
    assert plan["trip"]["snack_units"] == []
    assert "units" not in plan["packing"]
    assert plan["summary"]["slot_subtotals"]["snacks"]["target_cal"] > 0
