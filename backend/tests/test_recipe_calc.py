import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.recipe_calc import compute_recipe_totals


def test_empty_ingredients():
    result = compute_recipe_totals([])
    assert result["total_weight"] == 0
    assert result["total_calories"] == 0
    assert result["cal_per_oz"] is None
    assert result["protein_g"] == 0
    assert result["fat_g"] == 0
    assert result["carb_g"] == 0


def test_single_ingredient():
    result = compute_recipe_totals([
        {"amount_oz": 2.0, "calories_per_oz": 100.0}
    ])
    assert result["total_weight"] == 2.0
    assert result["total_calories"] == 200.0
    assert result["cal_per_oz"] == 100.0
    assert result["protein_g"] == 0
    assert result["fat_g"] == 0
    assert result["carb_g"] == 0


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


def test_full_macro_data():
    """All ingredients have macro values."""
    result = compute_recipe_totals([
        {
            "amount_oz": 2.0,
            "calories_per_oz": 100.0,
            "protein_per_oz": 5.0,
            "fat_per_oz": 3.0,
            "carb_per_oz": 10.0,
        },
        {
            "amount_oz": 3.0,
            "calories_per_oz": 80.0,
            "protein_per_oz": 2.0,
            "fat_per_oz": 1.0,
            "carb_per_oz": 15.0,
        },
    ])
    assert result["total_weight"] == 5.0
    assert result["total_calories"] == 440.0
    # protein: 2*5 + 3*2 = 16
    assert result["protein_g"] == 16.0
    # fat: 2*3 + 3*1 = 9
    assert result["fat_g"] == 9.0
    # carb: 2*10 + 3*15 = 65
    assert result["carb_g"] == 65.0


def test_partial_macro_data():
    """Some ingredients have macros, some don't. Missing macros contribute 0."""
    result = compute_recipe_totals([
        {
            "amount_oz": 2.0,
            "calories_per_oz": 100.0,
            "protein_per_oz": 5.0,
            "fat_per_oz": 3.0,
            "carb_per_oz": 10.0,
        },
        {
            "amount_oz": 1.0,
            "calories_per_oz": 50.0,
            # no macro fields at all
        },
    ])
    assert result["total_weight"] == 3.0
    assert result["total_calories"] == 250.0
    # Only first ingredient contributes macros
    assert result["protein_g"] == 10.0
    assert result["fat_g"] == 6.0
    assert result["carb_g"] == 20.0


def test_null_macro_fields():
    """Ingredients with explicit None macro fields contribute 0."""
    result = compute_recipe_totals([
        {
            "amount_oz": 4.0,
            "calories_per_oz": 120.0,
            "protein_per_oz": None,
            "fat_per_oz": None,
            "carb_per_oz": None,
        },
    ])
    assert result["total_weight"] == 4.0
    assert result["total_calories"] == 480.0
    assert result["protein_g"] == 0
    assert result["fat_g"] == 0
    assert result["carb_g"] == 0


def test_mixed_null_and_present_macros():
    """Some macro fields null, others present on same ingredient."""
    result = compute_recipe_totals([
        {
            "amount_oz": 2.0,
            "calories_per_oz": 100.0,
            "protein_per_oz": 5.0,
            "fat_per_oz": None,
            "carb_per_oz": 10.0,
        },
    ])
    assert result["protein_g"] == 10.0
    assert result["fat_g"] == 0
    assert result["carb_g"] == 20.0
