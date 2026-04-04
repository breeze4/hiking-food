import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from calculator import compute_trip_targets


def test_seven_day_trip():
    result = compute_trip_targets(0.75, 5, 0.75, oz_per_day=22)
    assert result["total_days"] == 6.5
    assert result["total_weight"] == 6.5 * 22  # 143
    assert result["total_cal"] == 143 * 125  # 17875


def test_with_meals():
    meals = [4.5] * 6 + [5.5] * 6
    result = compute_trip_targets(0.75, 5, 0.75, meals, oz_per_day=22)
    assert result["meal_weight"] == 60
    assert result["daytime_weight"] == 143 - 60  # 83


def test_one_day_trip():
    result = compute_trip_targets(1, 0, 0)
    assert result["total_days"] == 1
    assert result["total_weight"] == 22


def test_zero_fractions():
    result = compute_trip_targets(0, 3, 0)
    assert result["total_days"] == 3
    assert result["total_weight"] == 66


def test_custom_targets():
    result = compute_trip_targets(1, 0, 0, oz_per_day=20, cal_per_oz=130)
    assert result["total_days"] == 1
    assert result["total_weight"] == 20
    assert result["total_cal"] == 20 * 130
