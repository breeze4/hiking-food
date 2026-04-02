from sqlalchemy import Column, Integer, Text, Float, Boolean, ForeignKey
from database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    calories_per_oz = Column(Float)
    notes = Column(Text)


class SnackCatalogItem(Base):
    __tablename__ = "snack_catalog"

    id = Column(Integer, primary_key=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    weight_per_serving = Column(Float)
    calories_per_serving = Column(Float)
    category = Column(Text)  # drink_mix, lunch, salty, sweet, bars_energy
    notes = Column(Text)
    rating = Column(Integer)


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    category = Column(Text)  # "breakfast" or "dinner"
    at_home_prep = Column(Text)
    field_prep = Column(Text)
    notes = Column(Text)
    rating = Column(Integer)


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    amount_oz = Column(Float)


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    first_day_fraction = Column(Float)
    full_days = Column(Integer)
    last_day_fraction = Column(Float)


class TripMeal(Base):
    __tablename__ = "trip_meals"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    quantity = Column(Integer, default=1)
    packed = Column(Boolean, default=False)
    actual_weight_oz = Column(Float)


class TripSnack(Base):
    __tablename__ = "trip_snacks"

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    catalog_item_id = Column(Integer, ForeignKey("snack_catalog.id"), nullable=False)
    servings = Column(Float)
    packed = Column(Boolean, default=False)
    actual_weight_oz = Column(Float)
    trip_notes = Column(Text)
