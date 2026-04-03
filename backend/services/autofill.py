"""Auto-fill algorithm for distributing trip food across days."""


# Slot rules: which slots are eligible for each day type
SLOT_RULES = {
    "breakfast":          {"first_partial": False, "full": True,  "last_partial": True},
    "breakfast_drinks":   {"first_partial": False, "full": True,  "last_partial": True},
    "morning_snacks":     {"first_partial": False, "full": True,  "last_partial": True},
    "lunch":              {"first_partial": False, "full": True,  "last_partial": False},
    "afternoon_snacks":   {"first_partial": True,  "full": True,  "last_partial": False},
    "dinner":             {"first_partial": True,  "full": True,  "last_partial": False},
    "evening_drinks":     {"first_partial": True,  "full": True,  "last_partial": False},
    "all_day_drinks":     {"first_partial": True,  "full": True,  "last_partial": True},
}

# Map drink_mix_type to assignment slot
DRINK_TYPE_TO_SLOT = {
    "breakfast": "breakfast_drinks",
    "dinner": "evening_drinks",
    "all_day": "all_day_drinks",
}

# Map trip_snack.slot to daily plan slot
SNACK_SLOT_MAP = {
    "lunch": "lunch",
    "snacks": "afternoon_snacks",
}


def build_day_list(trip):
    """Build list of days with their type and fraction."""
    days = []
    day_num = 1

    if trip.first_day_fraction and trip.first_day_fraction > 0:
        days.append({"day_number": day_num, "type": "first_partial", "fraction": trip.first_day_fraction})
        day_num += 1

    for _ in range(trip.full_days or 0):
        days.append({"day_number": day_num, "type": "full", "fraction": 1.0})
        day_num += 1

    if trip.last_day_fraction and trip.last_day_fraction > 0:
        days.append({"day_number": day_num, "type": "last_partial", "fraction": trip.last_day_fraction})

    return days


def eligible_days(days, slot):
    """Return list of days where the given slot is allowed."""
    rule = SLOT_RULES[slot]
    return [d for d in days if rule[d["type"]]]


def distribute_meals(days, trip_meals, recipe_weights):
    """Distribute meals across eligible days. Returns list of assignment dicts.

    trip_meals: list of {id, recipe_id, category, quantity}
    recipe_weights: dict of recipe_id -> total_weight
    """
    assignments = []

    for category, slot in [("breakfast", "breakfast"), ("dinner", "dinner")]:
        # Collect servings: each trip_meal with quantity N produces N servings
        servings = []
        cat_meals = [m for m in trip_meals if m["category"] == category]
        # Sort by weight descending (heaviest first), then by id for determinism
        cat_meals.sort(key=lambda m: (-recipe_weights.get(m["recipe_id"], 0), m["id"]))
        for meal in cat_meals:
            for _ in range(meal["quantity"]):
                servings.append(meal)

        elig = eligible_days(days, slot)
        for i, meal in enumerate(servings):
            if i >= len(elig):
                break
            assignments.append({
                "day_number": elig[i]["day_number"],
                "slot": slot,
                "source_type": "meal",
                "source_id": meal["id"],
                "servings": 1,
            })

    return assignments


def distribute_snacks(days, trip_snacks, snack_weights):
    """Distribute snacks across eligible days. Returns list of assignment dicts.

    trip_snacks: list of {id, slot, servings, category}
    snack_weights: dict of trip_snack_id -> weight_per_serving
    """
    assignments = []

    # Filter out drink mixes
    snacks = [s for s in trip_snacks if s["category"] != "drink_mix"]

    # Sort by weight_per_serving descending (heaviest first), then by id for determinism
    snacks.sort(key=lambda s: (-snack_weights.get(s["id"], 0), s["id"]))

    for snack in snacks:
        plan_slot = SNACK_SLOT_MAP.get(snack["slot"], "afternoon_snacks")
        elig = eligible_days(days, plan_slot)
        remaining = snack["servings"]
        num_days = len(elig)
        if num_days == 0 or remaining <= 0:
            continue

        # How many days we can fill (1 serving per day)
        fill_count = min(int(remaining), num_days)

        # Pick evenly-spaced day indices so servings spread across the trip
        if fill_count >= num_days:
            chosen = list(range(num_days))
        else:
            chosen = [round(i * num_days / fill_count) for i in range(fill_count)]
            # Clamp and deduplicate (shouldn't happen but safety)
            chosen = sorted(set(min(idx, num_days - 1) for idx in chosen))

        for idx in chosen:
            if remaining <= 0:
                break
            assign_qty = min(1, remaining)
            assignments.append({
                "day_number": elig[idx]["day_number"],
                "slot": plan_slot,
                "source_type": "snack",
                "source_id": snack["id"],
                "servings": assign_qty,
            })
            remaining -= assign_qty

    return assignments


def distribute_drink_mixes(days, trip_snacks, snack_info):
    """Distribute drink mixes by subcategory. Returns (assignments, warnings).

    trip_snacks: list of {id, servings, category, drink_mix_type}
    snack_info: dict of trip_snack_id -> {drink_mix_type, ...}
    """
    assignments = []
    warnings = []

    # Group drink mix snacks by type
    by_type = {}  # drink_mix_type -> list of {id, servings}
    for snack in trip_snacks:
        if snack["category"] != "drink_mix":
            continue
        dmt = snack_info.get(snack["id"], {}).get("drink_mix_type") or "all_day"
        if dmt not in by_type:
            by_type[dmt] = []
        by_type[dmt].append(snack)

    for dmt, items in by_type.items():
        slot = DRINK_TYPE_TO_SLOT.get(dmt, "all_day_drinks")
        elig = eligible_days(days, slot)
        if not elig:
            continue

        # Sort items by id for determinism
        items.sort(key=lambda s: s["id"])

        # Total servings available
        total_servings = sum(s["servings"] for s in items)
        needed = len(elig)

        if total_servings < needed:
            type_label = {"breakfast": "breakfast", "dinner": "evening", "all_day": "all-day"}.get(dmt, dmt)
            warnings.append(f"Not enough {type_label} drink mixes to cover all {needed} eligible days ({int(total_servings)} available)")

        # Distribute evenly: cycle through items, 1 serving per day
        item_idx = 0
        remaining_per_item = {s["id"]: s["servings"] for s in items}

        for day in elig:
            # Find next item with remaining servings
            attempts = 0
            while attempts < len(items):
                item = items[item_idx % len(items)]
                if remaining_per_item[item["id"]] >= 1:
                    assignments.append({
                        "day_number": day["day_number"],
                        "slot": slot,
                        "source_type": "snack",
                        "source_id": item["id"],
                        "servings": 1,
                    })
                    remaining_per_item[item["id"]] -= 1
                    item_idx += 1
                    break
                item_idx += 1
                attempts += 1

    return assignments, warnings


def auto_fill(trip, trip_meals, trip_snacks, recipe_weights, snack_weights, snack_info):
    """Run the full auto-fill algorithm. Returns (assignments, warnings).

    trip: Trip model instance
    trip_meals: list of {id, recipe_id, category, quantity}
    trip_snacks: list of {id, slot, servings, category}
    recipe_weights: dict of recipe_id -> total_weight
    snack_weights: dict of trip_snack_id -> weight_per_serving
    snack_info: dict of trip_snack_id -> {drink_mix_type, ...}
    """
    days = build_day_list(trip)
    if not days:
        return [], []

    assignments = []
    warnings = []

    assignments.extend(distribute_meals(days, trip_meals, recipe_weights))
    assignments.extend(distribute_snacks(days, trip_snacks, snack_weights))

    drink_assignments, drink_warnings = distribute_drink_mixes(days, trip_snacks, snack_info)
    assignments.extend(drink_assignments)
    warnings.extend(drink_warnings)

    return assignments, warnings
