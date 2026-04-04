"""Tests for snack catalog macronutrient per-serving derivation."""
import pytest
from database import Base


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def _create_ingredient(c, name="Trail Mix", **kwargs):
    resp = c.post("/api/ingredients", json={"name": name, **kwargs})
    assert resp.status_code == 201
    return resp.json()


def _create_snack(c, ingredient_id, weight=2.0, calories=300.0, category="salty"):
    resp = c.post("/api/snacks", json={
        "ingredient_id": ingredient_id,
        "weight_per_serving": weight,
        "calories_per_serving": calories,
        "category": category,
    })
    assert resp.status_code == 201
    return resp.json()


class TestSnackMacroPerServing:
    def test_macros_derived_from_ingredient(self, c):
        """Snack macro per-serving = ingredient macro_per_oz * weight_per_serving."""
        ing = _create_ingredient(c, protein_per_oz=6.0, fat_per_oz=14.0, carb_per_oz=6.0)
        snack = _create_snack(c, ing["id"], weight=2.0)
        assert snack["protein_per_serving"] == 12.0
        assert snack["fat_per_serving"] == 28.0
        assert snack["carb_per_serving"] == 12.0

    def test_null_macros_propagate(self, c):
        """If ingredient has no macros, snack macros are null."""
        ing = _create_ingredient(c, name="Coffee", calories_per_oz=5.0)
        snack = _create_snack(c, ing["id"], weight=1.0, calories=5.0)
        assert snack["protein_per_serving"] is None
        assert snack["fat_per_serving"] is None
        assert snack["carb_per_serving"] is None

    def test_zero_weight_per_serving(self, c):
        """Zero weight_per_serving results in null macros."""
        ing = _create_ingredient(c, protein_per_oz=6.0, fat_per_oz=14.0, carb_per_oz=6.0)
        snack = _create_snack(c, ing["id"], weight=0.0, calories=0.0)
        assert snack["protein_per_serving"] is None
        assert snack["fat_per_serving"] is None
        assert snack["carb_per_serving"] is None

    def test_list_includes_macros(self, c):
        """GET /api/snacks returns macro per-serving."""
        ing = _create_ingredient(c, protein_per_oz=6.0, fat_per_oz=14.0, carb_per_oz=6.0)
        _create_snack(c, ing["id"], weight=1.5)
        resp = c.get("/api/snacks")
        assert resp.status_code == 200
        snacks = resp.json()
        assert snacks[0]["protein_per_serving"] == 9.0
        assert snacks[0]["fat_per_serving"] == 21.0
        assert snacks[0]["carb_per_serving"] == 9.0

    def test_update_preserves_macros(self, c):
        """Updating snack fields still returns correct macros."""
        ing = _create_ingredient(c, protein_per_oz=6.0, fat_per_oz=14.0, carb_per_oz=6.0)
        snack = _create_snack(c, ing["id"], weight=2.0)
        resp = c.put(f"/api/snacks/{snack['id']}", json={"notes": "tasty"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["protein_per_serving"] == 12.0
        assert data["notes"] == "tasty"


class TestTripSnackMacros:
    def test_trip_snack_includes_macros(self, c):
        """Trip snack response includes macro per-serving from ingredient."""
        ing = _create_ingredient(c, protein_per_oz=6.0, fat_per_oz=14.0, carb_per_oz=6.0)
        snack = _create_snack(c, ing["id"], weight=2.0)
        trip = c.post("/api/trips", json={"name": "Test Trip"}).json()
        resp = c.post(f"/api/trips/{trip['id']}/snacks", json={
            "catalog_item_id": snack["id"],
            "servings": 3.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["protein_per_serving"] == 12.0
        assert data["fat_per_serving"] == 28.0
        assert data["carb_per_serving"] == 12.0

    def test_trip_snack_null_macros(self, c):
        """Trip snack with no ingredient macros has null macro per-serving."""
        ing = _create_ingredient(c, name="Coffee", calories_per_oz=5.0)
        snack = _create_snack(c, ing["id"], weight=1.0, calories=5.0)
        trip = c.post("/api/trips", json={"name": "Test Trip"}).json()
        resp = c.post(f"/api/trips/{trip['id']}/snacks", json={
            "catalog_item_id": snack["id"],
            "servings": 2.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["protein_per_serving"] is None
        assert data["fat_per_serving"] is None
        assert data["carb_per_serving"] is None
