import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from calculator import compute_trip_targets


def test_seven_day_trip():
    result = compute_trip_targets(0.75, 5, 0.75)
    assert result["total_days"] == 6.5
    assert result["total_weight_low"] == 6.5 * 19  # 123.5
    assert result["total_weight_high"] == 6.5 * 24  # 156
    assert result["total_cal_low"] == 123.5 * 125  # 15437.5
    assert result["total_cal_high"] == 156 * 125  # 19500


def test_with_meals():
    # 6 breakfasts * 4.5oz + 6 dinners * 5.5oz = 60oz
    meals = [4.5] * 6 + [5.5] * 6
    result = compute_trip_targets(0.75, 5, 0.75, meals)
    assert result["meal_weight"] == 60
    assert result["daytime_weight_low"] == 123.5 - 60  # 63.5
    assert result["daytime_weight_high"] == 156 - 60  # 96


def test_one_day_trip():
    result = compute_trip_targets(1, 0, 0)
    assert result["total_days"] == 1
    assert result["total_weight_low"] == 19
    assert result["total_weight_high"] == 24


def test_zero_fractions():
    result = compute_trip_targets(0, 3, 0)
    assert result["total_days"] == 3
    assert result["total_weight_low"] == 57
    assert result["total_weight_high"] == 72


def test_custom_targets():
    result = compute_trip_targets(1, 0, 0, oz_per_day_low=16, oz_per_day_high=20, cal_per_oz=130)
    assert result["total_days"] == 1
    assert result["total_weight_low"] == 16
    assert result["total_weight_high"] == 20
    assert result["total_cal_low"] == 16 * 130
    assert result["total_cal_high"] == 20 * 130
