"""Trip snack unit selections: quota math, selection CRUD, summary integration."""
import pytest

from database import Base
from models import (
    AppSettings, Ingredient, Recipe, RecipeIngredient, SnackCatalogItem,
    Trip, TripMeal, TripSnack,
)
from services.snack_units import unit_quota
from services.trip_queries import trip_summary_view


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# The ingredients router derives calories_per_oz from macros (4/9/4), so the
# fixtures state macros only and the tests use the resulting per-oz calories.
NUTS_CAL_PER_OZ = 183.0  # 6*4 + 15*9 + 6*4
CANDY_CAL_PER_OZ = 138.0  # 1*4 + 6*9 + 20*4
BAG_CALORIES = NUTS_CAL_PER_OZ + CANDY_CAL_PER_OZ  # 1 oz of each
BAR_CALORIES = 250.0  # the catalog serving value, not 2 oz x the per-oz value


def _ingredient(c, name, **macros):
    resp = c.post("/api/ingredients", json={"name": name, **macros})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _nuts(c):
    return _ingredient(c, "Almonds", protein_per_oz=6.0, fat_per_oz=15.0, carb_per_oz=6.0)


def _candy(c):
    return _ingredient(c, "M&Ms", protein_per_oz=1.0, fat_per_oz=6.0, carb_per_oz=20.0)


def _bar_item(c, weight=2.0, calories=BAR_CALORIES):
    """A packaged snack: 2 oz, 250 cal per serving, macros from its ingredient."""
    ingredient = _ingredient(
        c, "Energy Bar", protein_per_oz=5.0, fat_per_oz=10.0, carb_per_oz=25.0,
    )
    resp = c.post("/api/snacks", json={
        "ingredient_id": ingredient["id"],
        "weight_per_serving": weight,
        "calories_per_serving": calories,
        "category": "bars_energy",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _bag(c, name="Trail Mix Bag", composition=None):
    if composition is None:
        composition = [(_nuts(c)["id"], 1.0), (_candy(c)["id"], 1.0)]
    resp = c.post("/api/snack-unit-types", json={
        "name": name,
        "composition": [
            {"ingredient_id": ingredient_id, "amount_oz": amount_oz}
            for ingredient_id, amount_oz in composition
        ],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def _trip(c, name="Olympics 2026", snack_config=None, **fields):
    """A structured trip: 0.5 + 2 + 0.5 days at the 4 x 2 oz default.

    TripCreate does not expose the snack configuration (new trips are
    structured, full stop), so a retuned trip is created then updated.
    """
    payload = {
        "name": name,
        "first_day_fraction": 0.5,
        "full_days": 2,
        "last_day_fraction": 0.5,
        "drink_mixes_per_day": 0,
        **fields,
    }
    resp = c.post("/api/trips", json=payload)
    assert resp.status_code == 201, resp.text
    assert resp.json()["snack_model"] == "structured"
    if snack_config:
        resp = c.put(f"/api/trips/{resp.json()['id']}", json=snack_config)
        assert resp.status_code == 200, resp.text
    return resp.json()


def _legacy_trip(c, **fields):
    trip = _trip(c, **fields)
    assert c.put(
        f"/api/trips/{trip['id']}", json={"snack_model": "legacy"},
    ).status_code == 200
    return trip


def _add_unit(c, trip_id, expected_status=201, **payload):
    resp = c.post(f"/api/trips/{trip_id}/snack-units", json=payload)
    assert resp.status_code == expected_status, resp.text
    return resp.json() if resp.content else None


class TestUnitQuota:
    def test_half_days_at_each_end_round_to_two_units(self):
        trip = Trip(
            first_day_fraction=0.5, full_days=2, last_day_fraction=0.5,
            snacks_per_day=4,
        )
        assert unit_quota(trip) == {"quota": 12, "per_day": [2, 4, 4, 2]}

    def test_a_quarter_day_rounds_up_to_one_unit(self):
        trip = Trip(
            first_day_fraction=0.25, full_days=0, last_day_fraction=0,
            snacks_per_day=4,
        )
        assert unit_quota(trip) == {"quota": 1, "per_day": [1]}

    def test_a_half_unit_rounds_up_rather_than_to_even(self):
        """Python's round() would send 2.5 to 2; a partial day rounds up."""
        trip = Trip(
            first_day_fraction=0.5, full_days=0, last_day_fraction=0,
            snacks_per_day=5,
        )
        assert unit_quota(trip) == {"quota": 3, "per_day": [3]}

    def test_zero_length_days_are_left_out(self):
        trip = Trip(
            first_day_fraction=0, full_days=2, last_day_fraction=0,
            snacks_per_day=4,
        )
        assert unit_quota(trip) == {"quota": 8, "per_day": [4, 4]}

    def test_an_unconfigured_trip_falls_back_to_four_per_day(self):
        trip = Trip(
            first_day_fraction=1, full_days=0, last_day_fraction=0,
            snacks_per_day=None,
        )
        assert unit_quota(trip) == {"quota": 4, "per_day": [4]}


class TestSelectionCrud:
    def test_a_packaged_selection_reports_its_catalog_serving_values(self, c):
        trip, bar = _trip(c), _bar_item(c)
        unit = _add_unit(c, trip["id"], catalog_item_id=bar["id"], quantity=3)

        assert unit["kind"] == "packaged"
        assert unit["name"] == "Energy Bar"
        assert unit["unit_type_id"] is None
        assert unit["weight_oz"] == 2.0
        assert unit["calories"] == BAR_CALORIES
        assert unit["total_weight"] == 6.0
        assert unit["total_calories"] == 3 * BAR_CALORIES
        # Macros come from the ingredient's per-oz data x the serving weight.
        assert (unit["protein_g"], unit["fat_g"], unit["carb_g"]) == (10.0, 20.0, 50.0)
        assert unit["weight_warning"] is False

    def test_a_bag_selection_reports_the_library_derived_values(self, c):
        trip, bag = _trip(c), _bag(c)
        unit = _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)

        assert unit["kind"] == "bag"
        assert unit["name"] == "Trail Mix Bag"
        assert unit["catalog_item_id"] is None
        assert unit["weight_oz"] == bag["weight_oz"] == 2.0
        assert unit["calories"] == bag["calories"] == BAG_CALORIES
        assert unit["total_weight"] == 12.0
        assert unit["total_calories"] == 6 * BAG_CALORIES
        assert (unit["protein_g"], unit["fat_g"], unit["carb_g"]) == (7.0, 21.0, 26.0)

    def test_the_trip_detail_lists_its_selections(self, c):
        trip, bar, bag = _trip(c), _bar_item(c), _bag(c)
        _add_unit(c, trip["id"], catalog_item_id=bar["id"], quantity=2)
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=4)

        detail = c.get(f"/api/trips/{trip['id']}").json()
        assert [(u["name"], u["quantity"]) for u in detail["snack_units"]] == [
            ("Energy Bar", 2), ("Trail Mix Bag", 4),
        ]

    def test_quantity_packed_and_actual_weight_round_trip(self, c):
        trip, bag = _trip(c), _bag(c)
        unit = _add_unit(c, trip["id"], unit_type_id=bag["id"])
        assert unit["quantity"] == 1
        assert unit["packed"] is False

        resp = c.put(
            f"/api/trips/{trip['id']}/snack-units/{unit['id']}",
            json={"quantity": 5, "packed": True, "actual_weight_oz": 2.3,
                  "trip_notes": "double bagged"},
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 5
        assert resp.json()["packed"] is True
        assert resp.json()["actual_weight_oz"] == 2.3
        assert resp.json()["trip_notes"] == "double bagged"
        assert resp.json()["total_weight"] == 10.0

    def test_removing_a_selection_drops_it_from_the_trip(self, c):
        trip, bag = _trip(c), _bag(c)
        unit = _add_unit(c, trip["id"], unit_type_id=bag["id"])

        assert c.delete(
            f"/api/trips/{trip['id']}/snack-units/{unit['id']}"
        ).status_code == 204
        assert c.get(f"/api/trips/{trip['id']}").json()["snack_units"] == []

    def test_a_selection_names_exactly_one_kind_of_unit(self, c):
        trip, bar, bag = _trip(c), _bar_item(c), _bag(c)

        both = c.post(f"/api/trips/{trip['id']}/snack-units", json={
            "catalog_item_id": bar["id"], "unit_type_id": bag["id"],
        })
        neither = c.post(f"/api/trips/{trip['id']}/snack-units", json={})

        assert both.status_code == 422
        assert neither.status_code == 422
        assert "exactly one" in both.json()["detail"]

    def test_an_unknown_unit_reference_is_rejected(self, c):
        trip = _trip(c)
        assert _add_unit(
            c, trip["id"], catalog_item_id=9999, expected_status=400,
        )["detail"] == "Snack catalog item not found"
        assert _add_unit(
            c, trip["id"], unit_type_id=9999, expected_status=400,
        )["detail"] == "Snack unit type not found"

    def test_quantity_must_be_greater_than_zero(self, c):
        trip, bag = _trip(c), _bag(c)
        assert _add_unit(
            c, trip["id"], unit_type_id=bag["id"], quantity=0, expected_status=422,
        )["detail"] == "Unit quantity must be greater than zero"

        unit = _add_unit(c, trip["id"], unit_type_id=bag["id"])
        resp = c.put(
            f"/api/trips/{trip['id']}/snack-units/{unit['id']}", json={"quantity": 0},
        )
        assert resp.status_code == 422

    def test_a_selection_from_another_trip_is_not_found(self, c):
        trip, other, bag = _trip(c), _trip(c, name="Cascades"), _bag(c)
        unit = _add_unit(c, other["id"], unit_type_id=bag["id"])

        assert c.put(
            f"/api/trips/{trip['id']}/snack-units/{unit['id']}", json={"quantity": 2},
        ).status_code == 404
        assert c.delete(
            f"/api/trips/{trip['id']}/snack-units/{unit['id']}"
        ).status_code == 404


class TestToleranceBand:
    def test_a_unit_is_measured_against_this_trip_s_target(self, c):
        """The library flags 3 oz against its 2 oz default; a 3 oz trip does not."""
        default_trip = _trip(c)
        heavy_trip = _trip(
            c, name="Winter Traverse", snack_config={"oz_per_snack": 3},
        )
        big_bag = _bag(c, name="Big Bag", composition=[(_nuts(c)["id"], 3.0)])
        assert big_bag["weight_warning"] is True

        on_default = _add_unit(c, default_trip["id"], unit_type_id=big_bag["id"])
        on_heavy = _add_unit(c, heavy_trip["id"], unit_type_id=big_bag["id"])

        assert on_default["weight_warning"] is True
        assert on_heavy["weight_warning"] is False


class TestStructuredOnlyGuard:
    def test_unit_endpoints_reject_a_legacy_trip(self, c):
        legacy, bag = _legacy_trip(c), _bag(c)

        created = c.post(
            f"/api/trips/{legacy['id']}/snack-units", json={"unit_type_id": bag["id"]},
        )
        assert created.status_code == 409
        assert created.json()["detail"] == "Trip does not use the structured snack model"
        assert c.put(
            f"/api/trips/{legacy['id']}/snack-units/1", json={"quantity": 2},
        ).status_code == 409
        assert c.delete(f"/api/trips/{legacy['id']}/snack-units/1").status_code == 409

    def test_a_missing_trip_is_still_a_404(self, c):
        assert c.post("/api/trips/9999/snack-units", json={}).status_code == 404


class TestClone:
    def test_clone_copies_selections_and_resets_the_packing_record(self, c):
        trip, bar, bag = _trip(c), _bar_item(c), _bag(c)
        packed = _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=6)
        c.put(f"/api/trips/{trip['id']}/snack-units/{packed['id']}", json={
            "packed": True, "actual_weight_oz": 2.4, "trip_notes": "keep",
        })
        _add_unit(c, trip["id"], catalog_item_id=bar["id"], quantity=3)

        clone = c.post(f"/api/trips/{trip['id']}/clone")
        assert clone.status_code == 201

        units = clone.json()["snack_units"]
        assert [(u["name"], u["quantity"], u["trip_notes"]) for u in units] == [
            ("Trail Mix Bag", 6, "keep"), ("Energy Bar", 3, None),
        ]
        assert [u["packed"] for u in units] == [False, False]
        assert [u["actual_weight_oz"] for u in units] == [None, None]


class TestStructuredSummary:
    def _trip_with_units(self, c):
        trip, bar, bag = _trip(c), _bar_item(c), _bag(c)
        _add_unit(c, trip["id"], catalog_item_id=bar["id"], quantity=4)
        _add_unit(c, trip["id"], unit_type_id=bag["id"], quantity=3)
        return c.get(f"/api/trips/{trip['id']}/summary").json()

    def test_the_summary_reports_units_filled_against_the_quota(self, c):
        summary = self._trip_with_units(c)
        assert summary["snack_units"] == {
            "quota": 12, "filled": 7, "per_day": [2, 4, 4, 2],
        }

    def test_the_snacks_slot_trades_its_calorie_band_for_the_meter(self, c):
        summary = self._trip_with_units(c)
        # Weight and calories stay as secondary readouts; the band is gone.
        assert summary["slot_subtotals"]["snacks"] == {
            "weight": 14.0, "calories": 4 * BAR_CALORIES + 3 * BAG_CALORIES,
        }
        # Lunch keeps its 40% band exactly as on a legacy trip.
        assert summary["slot_subtotals"]["lunch"]["target_cal"] > 0
        assert summary["slot_subtotals"]["lunch"]["target_cal_low"] > 0

    def test_unit_weight_and_calories_roll_into_the_trip_totals(self, c):
        summary = self._trip_with_units(c)
        # Packaged units count their catalog serving values (250 cal for a 2 oz
        # bar, not its ingredient's per-oz calories); bags count the library's.
        assert summary["snack_weight"] == 14.0
        assert summary["snack_calories"] == 4 * BAR_CALORIES + 3 * BAG_CALORIES
        assert summary["combined_weight"] == 14.0
        assert summary["combined_calories"] == 4 * BAR_CALORIES + 3 * BAG_CALORIES

    def test_unit_macros_roll_into_the_trip_totals(self, c):
        summary = self._trip_with_units(c)
        assert summary["macro_actual"]["protein_g"] == 4 * 10.0 + 3 * 7.0
        assert summary["macro_actual"]["fat_g"] == 4 * 20.0 + 3 * 21.0
        assert summary["macro_actual"]["carb_g"] == 4 * 50.0 + 3 * 26.0
        assert summary["macro_coverage_pct"] == 100.0

    def test_a_unit_without_macro_data_lowers_the_coverage(self, c):
        trip = _trip(c)
        blank = _ingredient(c, "Mystery Powder")
        plain = c.post("/api/snacks", json={
            "ingredient_id": blank["id"], "weight_per_serving": 2.0,
            "calories_per_serving": 200.0, "category": "sweet",
        }).json()
        _add_unit(c, trip["id"], catalog_item_id=plain["id"], quantity=1)
        _add_unit(c, trip["id"], unit_type_id=_bag(c)["id"], quantity=1)

        summary = c.get(f"/api/trips/{trip['id']}/summary").json()
        covered = BAG_CALORIES / (BAG_CALORIES + 200.0) * 100
        assert summary["macro_coverage_pct"] == round(covered, 1)

    def test_a_structured_trip_without_selections_reports_an_empty_meter(self, c):
        trip = _trip(c)
        summary = c.get(f"/api/trips/{trip['id']}/summary").json()
        assert summary["snack_units"] == {
            "quota": 12, "filled": 0, "per_day": [2, 4, 4, 2],
        }
        assert summary["slot_subtotals"]["snacks"] == {"weight": 0, "calories": 0}


# Captured from the summary this fixture produced before trip unit selections
# existed. A legacy trip's summary must keep matching it key for key.
LEGACY_SUMMARY_SNAPSHOT = {
    'breakfast_calories': 1155.0,
    'breakfast_count': 3,
    'breakfast_weight': 10.5,
    'cal_per_day': 1098.0,
    'combined_calories': 3294.0,
    'combined_weight': 31.5,
    'daytime_cal': 6300.0,
    'daytime_weight': 52.5,
    'dinner_calories': 0.0,
    'dinner_count': 0,
    'dinner_weight': 0.0,
    'drink_mix_calories': 378.0,
    'drink_mix_weight': 4.2,
    'macro_actual': {'carb_g': 253.5,
                     'carb_pct': 37.3,
                     'fat_g': 147.0,
                     'fat_pct': 48.6,
                     'protein_g': 96.0,
                     'protein_pct': 14.1},
    'macro_coverage_pct': 80.2,
    'macro_target': {'carb_pct': 50.0, 'fat_pct': 30.0, 'protein_pct': 20.0},
    'meal_cal': 1260.0,
    'meal_calories_actual': 1155.0,
    'meal_weight': 10.5,
    'meal_weight_actual': 10.5,
    'slot_subtotals': {'lunch': {'calories': 273.0,
                                 'days_covered': 0.3,
                                 'target_cal': 2368.8,
                                 'target_cal_high': 2605.7,
                                 'target_cal_low': 2131.9,
                                 'weight': 7.8},
                       'snacks': {'calories': 1488.0,
                                  'days_covered': 1.3,
                                  'target_cal': 3553.2,
                                  'target_cal_high': 3908.5,
                                  'target_cal_low': 3197.9,
                                  'weight': 9.0}},
    'snack_cal_per_oz': 101.9,
    'snack_calories': 2139.0,
    'snack_weight': 21.0,
    'total_cal': 7560.0,
    'total_days': 3.0,
    'total_weight': 63.0,
    'weight_per_day': 10.5,
}


def _seed_legacy_trip(db):
    """The fixture the snapshot above was captured from."""
    db.add(AppSettings(id=1))
    db.add_all([
        Ingredient(id=1, name="Oats", calories_per_oz=110,
                   protein_per_oz=4, fat_per_oz=2, carb_per_oz=19),
        Ingredient(id=2, name="Almonds", calories_per_oz=165,
                   protein_per_oz=6, fat_per_oz=14, carb_per_oz=6),
        Ingredient(id=3, name="Tuna", calories_per_oz=35),
        Ingredient(id=4, name="Electrolyte Mix", calories_per_oz=90),
    ])
    db.add(Recipe(id=1, name="Oatmeal", category="breakfast"))
    db.flush()
    db.add(RecipeIngredient(id=1, recipe_id=1, ingredient_id=1, amount_oz=3.5))
    db.add_all([
        SnackCatalogItem(id=1, ingredient_id=2, weight_per_serving=1.5,
                         calories_per_serving=248, category="salty"),
        SnackCatalogItem(id=2, ingredient_id=3, weight_per_serving=2.6,
                         calories_per_serving=91, category="lunch"),
        SnackCatalogItem(id=3, ingredient_id=4, weight_per_serving=0.7,
                         calories_per_serving=63, category="drink_mix"),
    ])
    db.add(Trip(id=1, name="Wonderland", first_day_fraction=0.5, full_days=2,
                last_day_fraction=0.5, drink_mixes_per_day=2, oz_per_day=21,
                cal_per_oz=120, snack_model="legacy", snacks_per_day=4,
                oz_per_snack=2))
    db.flush()
    db.add(TripMeal(id=1, trip_id=1, recipe_id=1, quantity=3))
    db.add_all([
        TripSnack(id=1, trip_id=1, catalog_item_id=1, servings=6, slot="snacks"),
        TripSnack(id=2, trip_id=1, catalog_item_id=2, servings=3, slot="lunch"),
        TripSnack(id=3, trip_id=1, catalog_item_id=3, servings=6, slot="snacks"),
    ])
    db.commit()


def test_a_legacy_trip_summary_matches_the_pre_change_snapshot(test_session):
    db = test_session()
    try:
        _seed_legacy_trip(db)
        assert trip_summary_view(db, db.get(Trip, 1)) == LEGACY_SUMMARY_SNAPSHOT
    finally:
        db.close()
