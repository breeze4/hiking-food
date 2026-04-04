def compute_trip_targets(first_day_fraction, full_days, last_day_fraction, meal_weights=None, oz_per_day_low=19, oz_per_day_high=24, cal_per_oz=125):
    """Compute trip food weight and calorie targets using the Skurka method.

    Args:
        first_day_fraction: fraction of first day (0-1)
        full_days: number of full days
        last_day_fraction: fraction of last day (0-1)
        meal_weights: list of meal weights in oz (each breakfast/dinner weight * quantity)
        oz_per_day_low: low end of oz/day target
        oz_per_day_high: high end of oz/day target
        cal_per_oz: calories per oz estimate

    Returns:
        dict with total_days, weight/calorie ranges, meal totals, daytime targets
    """
    total_days = first_day_fraction + full_days + last_day_fraction

    total_weight_low = total_days * oz_per_day_low
    total_weight_high = total_days * oz_per_day_high
    total_cal_low = total_weight_low * cal_per_oz
    total_cal_high = total_weight_high * cal_per_oz

    meal_weight = sum(meal_weights or [])
    meal_cal = meal_weight * cal_per_oz

    daytime_weight_low = total_weight_low - meal_weight
    daytime_weight_high = total_weight_high - meal_weight
    daytime_cal_low = daytime_weight_low * cal_per_oz
    daytime_cal_high = daytime_weight_high * cal_per_oz

    return {
        "total_days": total_days,
        "total_weight_low": total_weight_low,
        "total_weight_high": total_weight_high,
        "total_cal_low": total_cal_low,
        "total_cal_high": total_cal_high,
        "meal_weight": meal_weight,
        "meal_cal": meal_cal,
        "daytime_weight_low": daytime_weight_low,
        "daytime_weight_high": daytime_weight_high,
        "daytime_cal_low": daytime_cal_low,
        "daytime_cal_high": daytime_cal_high,
    }
