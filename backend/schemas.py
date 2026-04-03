from pydantic import BaseModel
from typing import Optional


class IngredientCreate(BaseModel):
    name: str
    calories_per_oz: float
    notes: Optional[str] = None


class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    calories_per_oz: Optional[float] = None
    notes: Optional[str] = None


class IngredientRead(BaseModel):
    id: int
    name: str
    calories_per_oz: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Snack Catalog ---

class SnackCreate(BaseModel):
    ingredient_id: int
    weight_per_serving: float
    calories_per_serving: float
    category: Optional[str] = None
    drink_mix_type: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None


class SnackUpdate(BaseModel):
    weight_per_serving: Optional[float] = None
    calories_per_serving: Optional[float] = None
    category: Optional[str] = None
    drink_mix_type: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None


class SnackRead(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    weight_per_serving: Optional[float] = None
    calories_per_serving: Optional[float] = None
    calories_per_oz: Optional[float] = None
    category: Optional[str] = None
    drink_mix_type: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None


# --- Recipes ---

class RecipeIngredientCreate(BaseModel):
    ingredient_id: int
    amount_oz: float


class RecipeIngredientRead(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: str
    amount_oz: float
    calories: Optional[float] = None


class RecipeCreate(BaseModel):
    name: str
    category: str  # "breakfast" or "dinner"
    at_home_prep: Optional[str] = None
    field_prep: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    ingredients: list[RecipeIngredientCreate] = []


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    at_home_prep: Optional[str] = None
    field_prep: Optional[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    ingredients: Optional[list[RecipeIngredientCreate]] = None


class RecipeListRead(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    rating: Optional[int] = None
    total_weight: float
    total_calories: float
    cal_per_oz: Optional[float] = None


class RecipeDetailRead(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    rating: Optional[int] = None
    at_home_prep: Optional[str] = None
    field_prep: Optional[str] = None
    notes: Optional[str] = None
    ingredients: list[RecipeIngredientRead] = []
    total_weight: float
    total_calories: float
    cal_per_oz: Optional[float] = None


# --- Trips ---

class TripCreate(BaseModel):
    name: str
    first_day_fraction: float = 1.0
    full_days: int = 0
    last_day_fraction: float = 0.0
    drink_mixes_per_day: int = 2


class TripUpdate(BaseModel):
    name: Optional[str] = None
    first_day_fraction: Optional[float] = None
    full_days: Optional[int] = None
    last_day_fraction: Optional[float] = None
    drink_mixes_per_day: Optional[int] = None


class TripListRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TripSnackRead(BaseModel):
    id: int
    catalog_item_id: int
    ingredient_name: str
    weight_per_serving: Optional[float] = None
    calories_per_serving: Optional[float] = None
    calories_per_oz: Optional[float] = None
    category: Optional[str] = None
    slot: Optional[str] = None
    servings: float
    total_weight: Optional[float] = None
    total_calories: Optional[float] = None
    packed: bool = False
    actual_weight_oz: Optional[float] = None
    trip_notes: Optional[str] = None


class TripSnackCreate(BaseModel):
    catalog_item_id: int
    servings: float
    slot: Optional[str] = None


class TripSnackUpdate(BaseModel):
    servings: Optional[float] = None
    slot: Optional[str] = None
    packed: Optional[bool] = None
    actual_weight_oz: Optional[float] = None
    trip_notes: Optional[str] = None


class TripMealRead(BaseModel):
    id: int
    recipe_id: int
    recipe_name: str
    category: Optional[str] = None
    quantity: int = 1
    weight_per_unit: Optional[float] = None
    total_weight: Optional[float] = None
    total_calories: Optional[float] = None
    packed: bool = False
    actual_weight_oz: Optional[float] = None


class TripMealCreate(BaseModel):
    recipe_id: int
    quantity: int = 1


class TripMealUpdate(BaseModel):
    quantity: Optional[int] = None
    packed: Optional[bool] = None
    actual_weight_oz: Optional[float] = None


class TripDetailRead(BaseModel):
    id: int
    name: str
    first_day_fraction: Optional[float] = None
    full_days: Optional[int] = None
    last_day_fraction: Optional[float] = None
    drink_mixes_per_day: int = 2
    snacks: list[TripSnackRead] = []
    meals: list[TripMealRead] = []


class SlotSubtotal(BaseModel):
    weight: float
    calories: float
    target_cal_low: float = 0
    target_cal_high: float = 0
    days_covered: Optional[float] = None


class TripSummaryRead(BaseModel):
    total_days: float
    total_weight_low: float
    total_weight_high: float
    total_cal_low: float
    total_cal_high: float
    meal_weight: float
    meal_cal: float
    daytime_weight_low: float
    daytime_weight_high: float
    daytime_cal_low: float
    daytime_cal_high: float
    snack_weight: float
    snack_calories: float
    snack_cal_per_oz: Optional[float] = None
    drink_mix_weight: float = 0
    drink_mix_calories: float = 0
    slot_subtotals: dict[str, SlotSubtotal] = {}
    meal_weight_actual: float
    meal_calories_actual: float
    breakfast_weight: float = 0
    breakfast_calories: float = 0
    breakfast_count: int = 0
    dinner_weight: float = 0
    dinner_calories: float = 0
    dinner_count: int = 0
    combined_weight: float
    combined_calories: float
    weight_per_day: Optional[float] = None
    cal_per_day: Optional[float] = None
