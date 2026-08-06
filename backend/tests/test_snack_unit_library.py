"""Tests for the snack unit type library: CRUD, composition math, delete protection."""
import pytest

from database import Base
from models import TripSnackUnit


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_ingredient(c, name="Almonds", **kwargs):
    resp = c.post("/api/ingredients", json={"name": name, **kwargs})
    assert resp.status_code == 201
    return resp.json()


# The ingredients router derives calories_per_oz from macros (4/9/4), so these
# fixtures state macros only and the tests use the resulting per-oz calories.
NUTS_CAL_PER_OZ = 183.0  # 6*4 + 15*9 + 6*4
CANDY_CAL_PER_OZ = 138.0  # 1*4 + 6*9 + 20*4


def _nuts(c):
    return _create_ingredient(
        c, name="Almonds", protein_per_oz=6.0, fat_per_oz=15.0, carb_per_oz=6.0,
    )


def _candy(c):
    return _create_ingredient(
        c, name="M&Ms", protein_per_oz=1.0, fat_per_oz=6.0, carb_per_oz=20.0,
    )


def _create_unit_type(c, name="Trail Mix Bag", composition=(), notes=None):
    resp = c.post("/api/snack-unit-types", json={
        "name": name,
        "notes": notes,
        "composition": [
            {"ingredient_id": ingredient_id, "amount_oz": amount_oz}
            for ingredient_id, amount_oz in composition
        ],
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestSnackUnitTypeCrud:
    def test_create_read_update_delete_round_trip(self, c):
        nuts, candy = _nuts(c), _candy(c)
        created = _create_unit_type(
            c, composition=[(nuts["id"], 1.0), (candy["id"], 1.0)], notes="the classic",
        )
        assert created["name"] == "Trail Mix Bag"
        assert created["notes"] == "the classic"
        assert [row["ingredient_name"] for row in created["composition"]] == [
            "Almonds", "M&Ms",
        ]

        fetched = c.get(f"/api/snack-unit-types/{created['id']}")
        assert fetched.status_code == 200
        assert fetched.json() == created

        updated = c.put(f"/api/snack-unit-types/{created['id']}", json={
            "name": "Nut Bag",
            "composition": [{"ingredient_id": nuts["id"], "amount_oz": 2.0}],
        })
        assert updated.status_code == 200
        assert updated.json()["name"] == "Nut Bag"
        assert updated.json()["weight_oz"] == 2.0
        assert [row["ingredient_name"] for row in updated.json()["composition"]] == [
            "Almonds",
        ]

        assert c.delete(f"/api/snack-unit-types/{created['id']}").status_code == 204
        assert c.get(f"/api/snack-unit-types/{created['id']}").status_code == 404

    def test_update_without_composition_keeps_the_existing_rows(self, c):
        nuts = _nuts(c)
        created = _create_unit_type(c, composition=[(nuts["id"], 1.75)])
        resp = c.put(f"/api/snack-unit-types/{created['id']}", json={"notes": "renamed"})
        assert resp.status_code == 200
        assert resp.json()["notes"] == "renamed"
        assert resp.json()["weight_oz"] == 1.75
        assert len(resp.json()["composition"]) == 1

    def test_unknown_ingredient_is_rejected(self, c):
        resp = c.post("/api/snack-unit-types", json={
            "name": "Ghost Bag",
            "composition": [{"ingredient_id": 9999, "amount_oz": 1.0}],
        })
        assert resp.status_code == 400
        assert "9999" in resp.json()["detail"]

    def test_missing_unit_type_returns_404(self, c):
        assert c.get("/api/snack-unit-types/9999").status_code == 404
        assert c.put("/api/snack-unit-types/9999", json={"name": "x"}).status_code == 404
        assert c.delete("/api/snack-unit-types/9999").status_code == 404


class TestDerivedValues:
    def test_weight_is_the_sum_of_composition_ounces(self, c):
        nuts, candy = _nuts(c), _candy(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], 1.25), (candy["id"], 0.75)])
        assert bag["weight_oz"] == 2.0

    def test_calories_come_from_per_oz_ingredient_data(self, c):
        nuts, candy = _nuts(c), _candy(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], 1.0), (candy["id"], 1.0)])
        assert bag["calories"] == NUTS_CAL_PER_OZ + CANDY_CAL_PER_OZ
        assert bag["cal_per_oz"] == round((NUTS_CAL_PER_OZ + CANDY_CAL_PER_OZ) / 2, 1)
        assert [row["calories"] for row in bag["composition"]] == [
            NUTS_CAL_PER_OZ, CANDY_CAL_PER_OZ,
        ]

    def test_macros_come_from_per_oz_ingredient_data(self, c):
        nuts, candy = _nuts(c), _candy(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], 1.5), (candy["id"], 0.5)])
        # protein 1.5*6 + 0.5*1, fat 1.5*15 + 0.5*6, carb 1.5*6 + 0.5*20
        assert bag["protein_g"] == 9.5
        assert bag["fat_g"] == 25.5
        assert bag["carb_g"] == 19.0

    def test_ingredients_without_per_oz_data_contribute_zero(self, c):
        nuts = _nuts(c)
        blank = _create_ingredient(c, name="Mystery Powder")
        bag = _create_unit_type(c, composition=[(nuts["id"], 1.0), (blank["id"], 1.0)])
        assert bag["weight_oz"] == 2.0
        assert bag["calories"] == NUTS_CAL_PER_OZ
        assert bag["protein_g"] == 6.0
        assert bag["has_full_data"] is False

    def test_full_data_flag_is_true_when_every_ingredient_is_complete(self, c):
        nuts, candy = _nuts(c), _candy(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], 1.0), (candy["id"], 1.0)])
        assert bag["has_full_data"] is True

    def test_an_empty_bag_derives_zeros(self, c):
        bag = _create_unit_type(c, name="Empty Bag")
        assert bag["weight_oz"] == 0
        assert bag["calories"] == 0
        assert bag["cal_per_oz"] is None
        assert bag["composition"] == []


class TestWeightWarning:
    @pytest.mark.parametrize("amount_oz, expected", [
        (1.4, True),
        (1.5, False),
        (2.0, False),
        (2.5, False),
        (2.6, True),
    ])
    def test_warning_marks_bags_outside_25_percent_of_two_ounces(
        self, c, amount_oz, expected
    ):
        nuts = _nuts(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], amount_oz)])
        assert bag["weight_oz"] == amount_oz
        assert bag["weight_warning"] is expected

    def test_a_band_edge_reached_by_addition_does_not_warn(self, c):
        """1.2 + 0.3 is 1.5000000000000002 in binary floats; still inside the band."""
        nuts, candy = _nuts(c), _candy(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], 1.2), (candy["id"], 0.3)])
        assert bag["weight_oz"] == 1.5
        assert bag["weight_warning"] is False


class TestListEndpoint:
    def test_list_returns_composition_and_derived_values_in_one_response(self, c):
        nuts, candy = _nuts(c), _candy(c)
        _create_unit_type(c, name="Trail Mix Bag",
                          composition=[(nuts["id"], 1.0), (candy["id"], 1.0)])
        _create_unit_type(c, name="Big Nut Bag", composition=[(nuts["id"], 3.0)])

        resp = c.get("/api/snack-unit-types")
        assert resp.status_code == 200
        bags = resp.json()
        assert [bag["name"] for bag in bags] == ["Big Nut Bag", "Trail Mix Bag"]

        big, trail = bags
        assert big["weight_oz"] == 3.0
        assert big["weight_warning"] is True
        assert [row["ingredient_name"] for row in big["composition"]] == ["Almonds"]

        assert trail["weight_oz"] == 2.0
        assert trail["calories"] == NUTS_CAL_PER_OZ + CANDY_CAL_PER_OZ
        assert trail["weight_warning"] is False
        assert [row["ingredient_name"] for row in trail["composition"]] == [
            "Almonds", "M&Ms",
        ]


class TestDeleteProtection:
    def test_a_unit_type_in_use_by_a_trip_cannot_be_deleted(self, c, test_session):
        nuts = _nuts(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], 2.0)])
        trip = c.post("/api/trips", json={"name": "Olympics 2026"}).json()

        # Trip unit selections have no endpoint yet (plan -03 owns them), so the
        # reference is written straight to the table the guard reads.
        db = test_session()
        db.add(TripSnackUnit(trip_id=trip["id"], unit_type_id=bag["id"], quantity=6))
        db.commit()
        db.close()

        resp = c.delete(f"/api/snack-unit-types/{bag['id']}")
        assert resp.status_code == 409
        assert "Cannot delete" in resp.json()["detail"]
        assert c.get(f"/api/snack-unit-types/{bag['id']}").status_code == 200

    def test_an_unreferenced_unit_type_deletes(self, c):
        nuts = _nuts(c)
        bag = _create_unit_type(c, composition=[(nuts["id"], 2.0)])
        assert c.delete(f"/api/snack-unit-types/{bag['id']}").status_code == 204
        assert c.get("/api/snack-unit-types").json() == []
