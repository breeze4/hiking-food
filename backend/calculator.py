def compute_trip_targets(first_day_fraction, full_days, last_day_fraction, meal_weights=None, oz_per_day=22, cal_per_oz=125):
    """Compute trip food weight and calorie targets using the Skurka method."""
    total_days = first_day_fraction + full_days + last_day_fraction

    total_weight = total_days * oz_per_day
    total_cal = total_weight * cal_per_oz

    meal_weight = sum(meal_weights or [])
    meal_cal = meal_weight * cal_per_oz

    daytime_weight = total_weight - meal_weight
    daytime_cal = daytime_weight * cal_per_oz

    return {
        "total_days": total_days,
        "total_weight": total_weight,
        "total_cal": total_cal,
        "meal_weight": meal_weight,
        "meal_cal": meal_cal,
        "daytime_weight": daytime_weight,
        "daytime_cal": daytime_cal,
    }
