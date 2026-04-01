def compute_recipe_totals(ingredients):
    """Compute totals for a recipe given a list of dicts with amount_oz and calories_per_oz.

    Args:
        ingredients: list of dicts, each with 'amount_oz' (float) and 'calories_per_oz' (float or None)

    Returns:
        dict with total_weight, total_calories, cal_per_oz
    """
    total_weight = sum(i["amount_oz"] for i in ingredients)
    total_calories = sum(
        i["amount_oz"] * (i["calories_per_oz"] or 0) for i in ingredients
    )
    cal_per_oz = round(total_calories / total_weight, 1) if total_weight > 0 else None
    return {
        "total_weight": round(total_weight, 2),
        "total_calories": round(total_calories, 1),
        "cal_per_oz": cal_per_oz,
    }
