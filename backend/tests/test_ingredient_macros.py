"""Tests for ingredient macronutrient fields and calorie derivation."""
import pytest
from database import Base


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


class TestCreateWithMacros:
    def test_macros_derive_calories(self, c):
        """All three macros set -> calories derived as p*4 + f*9 + c*4."""
        resp = c.post("/api/ingredients", json={
            "name": "Almonds",
            "protein_per_oz": 6.0,
            "fat_per_oz": 14.0,
            "carb_per_oz": 6.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        # 6*4 + 14*9 + 6*4 = 24 + 126 + 24 = 174
        assert data["calories_per_oz"] == 174.0
        assert data["protein_per_oz"] == 6.0
        assert data["fat_per_oz"] == 14.0
        assert data["carb_per_oz"] == 6.0

    def test_macros_win_over_direct_calories(self, c):
        """When both macros and calories_per_oz provided, macros win."""
        resp = c.post("/api/ingredients", json={
            "name": "Almonds",
            "calories_per_oz": 999.0,
            "protein_per_oz": 6.0,
            "fat_per_oz": 14.0,
            "carb_per_oz": 6.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["calories_per_oz"] == 174.0

    def test_direct_calories_nulls_macros(self, c):
        """calories_per_oz set without macros -> macros are null."""
        resp = c.post("/api/ingredients", json={
            "name": "Coffee",
            "calories_per_oz": 5.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["calories_per_oz"] == 5.0
        assert data["protein_per_oz"] is None
        assert data["fat_per_oz"] is None
        assert data["carb_per_oz"] is None

    def test_no_macros_no_calories(self, c):
        """Neither macros nor calories -> all null."""
        resp = c.post("/api/ingredients", json={
            "name": "Water",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["calories_per_oz"] is None
        assert data["protein_per_oz"] is None


class TestUpdateDerivation:
    def _create(self, c, **kwargs):
        defaults = {"name": "Test Ingredient", "calories_per_oz": 100.0}
        defaults.update(kwargs)
        resp = c.post("/api/ingredients", json=defaults)
        assert resp.status_code == 201
        return resp.json()

    def test_update_macros_derives_calories(self, c):
        """Updating all three macros recomputes calories."""
        ing = self._create(c)
        resp = c.put(f"/api/ingredients/{ing['id']}", json={
            "protein_per_oz": 5.0,
            "fat_per_oz": 10.0,
            "carb_per_oz": 20.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        # 5*4 + 10*9 + 20*4 = 20 + 90 + 80 = 190
        assert data["calories_per_oz"] == 190.0
        assert data["protein_per_oz"] == 5.0

    def test_update_calories_nulls_macros(self, c):
        """Updating calories directly nulls out macros."""
        ing = self._create(c, protein_per_oz=5.0, fat_per_oz=10.0, carb_per_oz=20.0)
        assert ing["protein_per_oz"] == 5.0  # had macros

        resp = c.put(f"/api/ingredients/{ing['id']}", json={
            "calories_per_oz": 50.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["calories_per_oz"] == 50.0
        assert data["protein_per_oz"] is None
        assert data["fat_per_oz"] is None
        assert data["carb_per_oz"] is None

    def test_update_macros_and_calories_macros_win(self, c):
        """When both macros and calories provided on update, macros win."""
        ing = self._create(c)
        resp = c.put(f"/api/ingredients/{ing['id']}", json={
            "calories_per_oz": 999.0,
            "protein_per_oz": 5.0,
            "fat_per_oz": 10.0,
            "carb_per_oz": 20.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["calories_per_oz"] == 190.0

    def test_update_one_macro_keeps_existing(self, c):
        """Updating one macro when others already exist keeps macros and re-derives."""
        ing = self._create(c, protein_per_oz=5.0, fat_per_oz=10.0, carb_per_oz=20.0)
        resp = c.put(f"/api/ingredients/{ing['id']}", json={
            "protein_per_oz": 8.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        # 8*4 + 10*9 + 20*4 = 32 + 90 + 80 = 202
        assert data["calories_per_oz"] == 202.0
        assert data["protein_per_oz"] == 8.0
        assert data["fat_per_oz"] == 10.0
        assert data["carb_per_oz"] == 20.0

    def test_update_non_macro_field_preserves_macros(self, c):
        """Updating name or notes doesn't disturb macros."""
        ing = self._create(c, protein_per_oz=5.0, fat_per_oz=10.0, carb_per_oz=20.0)
        resp = c.put(f"/api/ingredients/{ing['id']}", json={
            "notes": "updated note",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["protein_per_oz"] == 5.0
        assert data["calories_per_oz"] == 190.0


class TestGetIngredients:
    def test_list_returns_macro_fields(self, c):
        c.post("/api/ingredients", json={
            "name": "Oats",
            "protein_per_oz": 4.0,
            "fat_per_oz": 2.0,
            "carb_per_oz": 20.0,
        })
        c.post("/api/ingredients", json={
            "name": "Coffee",
            "calories_per_oz": 5.0,
        })
        resp = c.get("/api/ingredients")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2

        oats = next(i for i in items if i["name"] == "Oats")
        assert oats["protein_per_oz"] == 4.0
        assert oats["fat_per_oz"] == 2.0
        assert oats["carb_per_oz"] == 20.0

        coffee = next(i for i in items if i["name"] == "Coffee")
        assert coffee["protein_per_oz"] is None
        assert coffee["fat_per_oz"] is None
        assert coffee["carb_per_oz"] is None
        assert coffee["calories_per_oz"] == 5.0
