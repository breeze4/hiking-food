def compute_recipe_totals(ingredients):
    """Compute totals for a recipe given a list of dicts with amount_oz and calories_per_oz.

    Args:
        ingredients: list of dicts, each with 'amount_oz' (float), 'calories_per_oz' (float or None),
            and optionally 'protein_per_oz', 'fat_per_oz', 'carb_per_oz' (float or None)

    Returns:
        dict with total_weight, total_calories, cal_per_oz, protein_g, fat_g, carb_g
    """
    total_weight = sum(i["amount_oz"] for i in ingredients)
    total_calories = sum(
        i["amount_oz"] * (i["calories_per_oz"] or 0) for i in ingredients
    )
    cal_per_oz = round(total_calories / total_weight, 1) if total_weight > 0 else None
    protein_g = sum(
        i["amount_oz"] * (i.get("protein_per_oz") or 0) for i in ingredients
    )
    fat_g = sum(
        i["amount_oz"] * (i.get("fat_per_oz") or 0) for i in ingredients
    )
    carb_g = sum(
        i["amount_oz"] * (i.get("carb_per_oz") or 0) for i in ingredients
    )
    return {
        "total_weight": round(total_weight, 2),
        "total_calories": round(total_calories, 1),
        "cal_per_oz": cal_per_oz,
        "protein_g": round(protein_g, 1),
        "fat_g": round(fat_g, 1),
        "carb_g": round(carb_g, 1),
    }
