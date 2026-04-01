import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recipe_calc import compute_recipe_totals


def test_empty_ingredients():
    result = compute_recipe_totals([])
    assert result["total_weight"] == 0
    assert result["total_calories"] == 0
    assert result["cal_per_oz"] is None


def test_single_ingredient():
    result = compute_recipe_totals([
        {"amount_oz": 2.0, "calories_per_oz": 100.0}
    ])
    assert result["total_weight"] == 2.0
    assert result["total_calories"] == 200.0
    assert result["cal_per_oz"] == 100.0


def test_multiple_ingredients():
    result = compute_recipe_totals([
        {"amount_oz": 1.0, "calories_per_oz": 100.0},
        {"amount_oz": 3.0, "calories_per_oz": 50.0},
    ])
    assert result["total_weight"] == 4.0
    assert result["total_calories"] == 250.0
    assert result["cal_per_oz"] == 62.5


def test_none_calories_per_oz():
    result = compute_recipe_totals([
        {"amount_oz": 2.0, "calories_per_oz": None}
    ])
    assert result["total_weight"] == 2.0
    assert result["total_calories"] == 0
    assert result["cal_per_oz"] == 0.0
