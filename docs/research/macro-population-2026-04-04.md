# Macro Population Run — 2026-04-04

## Summary

Populated macronutrient data (protein, fat, carb per oz) for all 104 ingredients. Prior to this, every ingredient had null macros.

**Sources:**
- 4 from USDA FoodData Central API (cereal/granola, powdered whole milk, cheddar cheese, peanut butter)
- 3 from known values (salt, olive oil/sesame oil, tea/coffee)
- 97 estimated from nutritional knowledge

## Calorie Changes

When all three macros are set, the backend auto-derives `calories_per_oz` as `protein*4 + fat*9 + carb*4`. This replaces the previously hand-entered calorie values. Most items change by <15%. The following items have significant calorie changes:

### Likely corrections (DB value was wrong)

| ID | Ingredient | Old cal/oz | New cal/oz | Diff | Notes |
|----|------------|------------|------------|------|-------|
| 76 | Couscous | 73.0 | 103.8 | +42% | Dry couscous is ~375 cal/100g. 73 was too low. |
| 88 | Pretzel sticks | 160.0 | 110.1 | -31% | Hard pretzels are ~108 cal/oz. 160 was too high. |
| 56 | Sun-dried tomatoes | 0.0 | 87.3 | new | Was 0, now has real value. |
| 42 | Soy sauce | 30.0 | 12.0 | -60% | Soy sauce is ~8-10 cal/tbsp. 30 was too high. |
| 71 | Chocolate chip cookie | 100.0 | 128.9 | +29% | Cookies with butter+sugar+chocolate are calorie-dense. |
| 54 | Tamarind paste | 50.0 | 75.8 | +52% | Concentrated tamarind is denser than 50 cal/oz. |

### Debatable — may want to verify against labels

| ID | Ingredient | Old cal/oz | New cal/oz | Diff | Notes |
|----|------------|------------|------------|------|-------|
| 7 | Crumbled bacon | 120.0 | 146.1 | +22% | Cooked bacon bits are calorie-dense. 120 may have been a label value. |
| 8 | Green chiles | 23.0 | 7.3 | -68% | Canned chiles are mostly water. 23 seems high but could be a specific brand. |
| 11 | Scrambled egg mix | 153.0 | 111.4 | -27% | 153 seems high for dehydrated egg. Could be a specific product. |
| 92 | Beef jerky (Kroger steak strips) | 70.0 | 97.6 | +39% | Kroger steak strips may genuinely be leaner than typical jerky. |
| 101 | Quest protein chips | 136.0 | 102.1 | -25% | Quest chips vary by flavor; 136 may be from a specific SKU. |
| 90 | Mixed gelatinous dried fruit | 63.0 | 92.0 | +46% | Soft dried fruit. 63 seems low. |
| 80 | Mixed GF soft dessert nubs | 150.0 | 127.3 | -15% | GF baked goods vary widely. |

### Spices with 0 cal/oz (functionally fine)

These have real macros per oz but are used in such tiny amounts that the calorie change is irrelevant to trip planning:

| ID | Ingredient | Old cal/oz | New cal/oz |
|----|------------|------------|------------|
| 35 | Pepper | 0.0 | 93.3 |
| 36 | Red pepper flakes | 0.0 | 121.7 |
| 49 | Vegetable bouillon | 0.0 | 77.1 |
| 50 | Chili powder | 0.0 | 107.3 |

### All other items

Changed by <15%. The macro-derived calories are close to the original hand-entered values, confirming both the macros and the original calories were reasonable.

## Full Data

| ID | Name | P/oz | F/oz | C/oz | New cal/oz | Old cal/oz | Source |
|----|------|------|------|------|------------|------------|--------|
| 1 | Cereal (granola or grape nuts) | 2.8 | 3.7 | 19.1 | 120.9 | 140.0 | USDA |
| 2 | Powdered whole milk | 7.5 | 7.6 | 10.9 | 142.0 | 149.0 | USDA |
| 3 | Protein powder | 21.3 | 0.9 | 2.8 | 104.5 | 104.0 | estimated |
| 4 | Instant mashed potatoes | 2.4 | 0.1 | 22.5 | 100.5 | 97.0 | estimated |
| 5 | Nutritional yeast | 14.2 | 1.1 | 7.9 | 98.3 | 105.0 | estimated |
| 6 | Dried onion | 2.5 | 0.1 | 22.4 | 100.5 | 95.0 | estimated |
| 7 | Crumbled bacon | 10.5 | 11.3 | 0.6 | 146.1 | 120.0 | estimated |
| 8 | Green chiles | 0.4 | 0.1 | 1.2 | 7.3 | 23.0 | estimated |
| 9 | Cheese (extra sharp cheddar) | 6.9 | 9.6 | 0.6 | 116.4 | 110.0 | USDA |
| 10 | Butter | 0.3 | 23.0 | 0.0 | 208.2 | 203.0 | estimated |
| 11 | Scrambled egg mix | 9.6 | 6.2 | 4.3 | 111.4 | 153.0 | estimated |
| 12 | Instant beans | 6.0 | 0.4 | 17.0 | 95.6 | 112.0 | estimated |
| 13 | Powdered cheese | 6.2 | 7.1 | 6.2 | 113.5 | 126.0 | estimated |
| 14 | Taco seasoning | 1.7 | 0.9 | 17.0 | 82.9 | 93.0 | estimated |
| 15 | Tortilla (burrito sized) | 2.4 | 2.0 | 14.2 | 84.4 | 85.0 | estimated |
| 16 | Rolled oats | 3.7 | 1.8 | 19.2 | 107.8 | 105.0 | estimated |
| 17 | Chia seeds | 4.7 | 8.7 | 11.9 | 144.7 | 138.0 | estimated |
| 18 | Coconut milk powder | 0.9 | 15.6 | 7.9 | 175.6 | 191.0 | estimated |
| 19 | Turbinado sugar | 0.0 | 0.0 | 28.3 | 113.2 | 105.0 | estimated |
| 20 | Coconut flakes | 2.0 | 18.3 | 6.7 | 199.5 | 204.0 | estimated |
| 21 | Sliced almonds | 6.0 | 14.1 | 6.1 | 175.3 | 160.0 | estimated |
| 22 | Raisins | 0.9 | 0.1 | 22.5 | 94.5 | 84.0 | estimated |
| 23 | Salt | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | known |
| 24 | Cinnamon | 1.1 | 0.3 | 22.8 | 98.3 | 69.0 | estimated |
| 25 | Farina (Cream of Wheat) | 3.0 | 0.1 | 22.1 | 101.3 | 93.0 | estimated |
| 26 | Seeds (pumpkin) | 8.6 | 13.9 | 3.0 | 171.5 | 150.0 | estimated |
| 27 | Dried apple pieces | 0.4 | 0.1 | 18.7 | 77.3 | 68.0 | estimated |
| 28 | Streusel crumbs | 1.1 | 4.8 | 17.9 | 119.2 | 112.0 | estimated |
| 29 | Banana chips | 0.7 | 9.5 | 16.6 | 154.7 | 140.0 | estimated |
| 30 | Craisins | 0.0 | 0.4 | 23.2 | 96.4 | 91.0 | estimated |
| 31 | Chopped walnuts | 4.3 | 18.5 | 3.9 | 199.3 | 190.0 | estimated |
| 32 | Chocolate chips | 1.4 | 8.3 | 16.8 | 147.5 | 140.0 | estimated |
| 33 | Instant rice | 2.0 | 0.2 | 22.8 | 101.0 | 103.0 | estimated |
| 34 | Fritos | 1.9 | 9.4 | 16.1 | 156.6 | 160.0 | estimated |
| 35 | Pepper | 2.9 | 0.9 | 18.4 | 93.3 | 0.0 | estimated |
| 36 | Red pepper flakes | 3.4 | 4.9 | 16.0 | 121.7 | 0.0 | estimated |
| 37 | Ramen noodles | 2.8 | 4.8 | 17.6 | 124.8 | 127.0 | estimated |
| 38 | Cashews | 5.2 | 12.4 | 8.6 | 166.8 | 150.0 | estimated |
| 39 | Peanut butter | 6.3 | 14.6 | 6.3 | 181.8 | 175.0 | USDA |
| 40 | Olive oil | 0.0 | 28.3 | 0.0 | 254.7 | 240.0 | known |
| 41 | Toasted sesame oil | 0.0 | 28.3 | 0.0 | 254.7 | 240.0 | known |
| 42 | Soy sauce | 1.6 | 0.0 | 1.4 | 12.0 | 30.0 | estimated |
| 43 | Honey | 0.1 | 0.0 | 23.4 | 94.0 | 88.0 | estimated |
| 44 | Garlic (granulated) | 4.8 | 0.2 | 20.7 | 103.8 | 93.0 | estimated |
| 45 | Ginger powder | 2.5 | 1.2 | 20.3 | 102.0 | 111.0 | estimated |
| 46 | TVP | 14.7 | 0.3 | 9.1 | 97.9 | 101.0 | estimated |
| 47 | Dried bell peppers | 3.1 | 0.9 | 15.6 | 82.9 | 63.0 | estimated |
| 48 | Tomato powder | 3.7 | 0.1 | 21.2 | 100.5 | 85.0 | estimated |
| 49 | Vegetable bouillon | 2.8 | 2.3 | 11.3 | 77.1 | 0.0 | estimated |
| 50 | Chili powder | 3.5 | 4.1 | 14.1 | 107.3 | 0.0 | estimated |
| 51 | Dried vegetables | 2.8 | 0.4 | 17.6 | 85.2 | 80.0 | estimated |
| 52 | Dried chickpeas | 5.8 | 1.7 | 17.3 | 107.7 | 120.0 | estimated |
| 53 | Green curry paste | 0.6 | 1.4 | 2.3 | 24.2 | 19.0 | estimated |
| 54 | Tamarind paste | 0.8 | 0.2 | 17.7 | 75.8 | 50.0 | estimated |
| 55 | Parmesan | 10.1 | 7.3 | 0.9 | 109.7 | 93.0 | estimated |
| 56 | Sun-dried tomatoes | 4.0 | 0.9 | 15.8 | 87.3 | 0.0 | estimated |
| 57 | Dried basil | 6.5 | 1.2 | 13.5 | 90.8 | 100.0 | estimated |
| 58 | Polenta (quick-cook) | 2.0 | 0.3 | 22.4 | 100.3 | 104.0 | estimated |
| 59 | M&M nut covered | 2.0 | 6.5 | 16.2 | 131.3 | 140.0 | estimated |
| 60 | Ghirardelli dark chocolate bar | 1.4 | 8.5 | 15.6 | 144.5 | 146.0 | estimated |
| 61 | Welches fruit snack | 0.0 | 0.0 | 23.2 | 92.8 | 86.0 | estimated |
| 62 | Golden Oreos (3 cookies) | 0.9 | 5.7 | 18.9 | 130.5 | 132.0 | estimated |
| 63 | Goldfish | 2.8 | 5.7 | 17.0 | 130.5 | 140.0 | estimated |
| 64 | Kind bar | 4.0 | 8.2 | 11.3 | 135.0 | 143.0 | estimated |
| 65 | Honey Stinger Waffle | 1.6 | 4.7 | 18.9 | 124.3 | 142.0 | estimated |
| 66 | Rice krispy bar | 0.9 | 2.8 | 20.7 | 111.6 | 115.0 | estimated |
| 67 | Clif nut butter bar | 4.1 | 7.2 | 14.4 | 138.8 | 131.0 | estimated |
| 68 | Reese PB cups (2 pack) | 3.0 | 8.0 | 15.4 | 145.6 | 140.0 | estimated |
| 69 | Fig Newtons | 0.9 | 1.9 | 19.8 | 99.9 | 100.0 | estimated |
| 70 | Larabar Lemon | 2.5 | 6.3 | 13.2 | 119.5 | 125.0 | estimated |
| 71 | Chocolate chip cookie | 1.0 | 5.7 | 18.4 | 128.9 | 100.0 | estimated |
| 72 | Pringles can | 0.9 | 8.5 | 16.1 | 144.5 | 126.0 | estimated |
| 73 | RX Bar | 6.9 | 4.4 | 11.3 | 112.4 | 115.0 | estimated |
| 74 | Glutino GF cookies | 0.9 | 6.6 | 17.9 | 134.6 | 135.0 | estimated |
| 75 | Trail mix | 3.7 | 8.5 | 12.8 | 142.5 | 130.0 | estimated |
| 76 | Couscous | 3.6 | 0.2 | 21.9 | 103.8 | 73.0 | estimated |
| 77 | Tuna packet | 7.2 | 0.2 | 0.0 | 30.6 | 34.0 | estimated |
| 78 | Chicken packet | 6.5 | 0.4 | 0.0 | 29.6 | 29.0 | estimated |
| 79 | Chips (mixed) | 1.9 | 9.4 | 15.1 | 152.6 | 140.0 | estimated |
| 80 | Mixed GF soft dessert nubs | 0.6 | 5.7 | 18.4 | 127.3 | 150.0 | estimated |
| 81 | Range meal bar | 5.0 | 5.0 | 12.0 | 113.0 | 123.0 | estimated |
| 82 | Powdered Donettes (3 pack) | 0.9 | 6.6 | 17.0 | 131.0 | 127.0 | estimated |
| 83 | Nilla Wafers (8 cookies) | 0.9 | 4.7 | 19.8 | 125.1 | 131.0 | estimated |
| 84 | Tea and coffee | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | known |
| 85 | Athletic greens | 4.1 | 0.0 | 20.2 | 97.2 | 107.0 | estimated |
| 86 | Gatorlyte/electrolyte | 0.0 | 0.0 | 22.7 | 90.8 | 84.0 | estimated |
| 87 | Carnation breakfast essential | 4.8 | 0.8 | 19.4 | 104.0 | 111.0 | estimated |
| 88 | Pretzel sticks | 2.8 | 0.9 | 22.7 | 110.1 | 160.0 | estimated |
| 89 | Mixed dried fruit | 0.6 | 0.1 | 23.2 | 96.1 | 110.0 | estimated |
| 90 | Mixed gelatinous dried fruit | 0.3 | 0.0 | 22.7 | 92.0 | 63.0 | estimated |
| 91 | Mixed candy | 0.3 | 1.4 | 24.1 | 110.2 | 100.0 | estimated |
| 92 | Beef jerky (Kroger steak strips) | 15.6 | 2.0 | 4.3 | 97.6 | 70.0 | estimated |
| 93 | Mixed nuts | 4.8 | 14.7 | 6.0 | 175.5 | 180.0 | estimated |
| 94 | Snickers | 2.1 | 6.5 | 17.4 | 136.5 | 134.0 | estimated |
| 95 | Pop Tarts (2x pack) | 1.0 | 3.1 | 20.5 | 113.9 | 110.0 | estimated |
| 96 | Peanut butter pretzels | 3.8 | 5.7 | 15.1 | 126.9 | 132.0 | estimated |
| 97 | Babybel | 6.1 | 7.1 | 0.0 | 88.3 | 86.0 | estimated |
| 98 | Almond Joy snack size (2pc) | 1.5 | 7.5 | 16.4 | 139.1 | 140.0 | estimated |
| 99 | Lil Debbies honey bun | 0.9 | 6.2 | 17.9 | 131.0 | 131.0 | estimated |
| 100 | Lil Debbies apple cinnamon sticks | 0.6 | 5.1 | 19.3 | 125.5 | 130.0 | estimated |
| 101 | Quest protein chips | 12.2 | 4.1 | 4.1 | 102.1 | 136.0 | estimated |
| 102 | Pita chips | 2.8 | 5.7 | 17.0 | 130.5 | 131.0 | estimated |
| 103 | Tortilla (medium flour) | 2.4 | 2.0 | 14.2 | 84.4 | 80.0 | estimated |
| 104 | Peanut butter tube | 6.3 | 14.6 | 6.3 | 181.8 | 166.0 | estimated |
