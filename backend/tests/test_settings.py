"""Tests for app settings CRUD and validation."""
import pytest
from database import Base


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_get_defaults(c):
    """First GET auto-creates settings with default values."""
    resp = c.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["macro_target_protein_pct"] == 20
    assert data["macro_target_fat_pct"] == 30
    assert data["macro_target_carb_pct"] == 50


def test_update_settings(c):
    """PUT updates settings and returns new values."""
    resp = c.put("/api/settings", json={
        "macro_target_protein_pct": 25,
        "macro_target_fat_pct": 35,
        "macro_target_carb_pct": 40,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["macro_target_protein_pct"] == 25
    assert data["macro_target_fat_pct"] == 35
    assert data["macro_target_carb_pct"] == 40

    # Verify GET returns updated values
    resp2 = c.get("/api/settings")
    assert resp2.json() == data


def test_validation_sum_not_100(c):
    """Percentages not summing to 100 should be rejected."""
    resp = c.put("/api/settings", json={
        "macro_target_protein_pct": 30,
        "macro_target_fat_pct": 30,
        "macro_target_carb_pct": 30,
    })
    assert resp.status_code == 422


def test_validation_sum_over_100(c):
    """Percentages summing to more than 100 should be rejected."""
    resp = c.put("/api/settings", json={
        "macro_target_protein_pct": 40,
        "macro_target_fat_pct": 40,
        "macro_target_carb_pct": 40,
    })
    assert resp.status_code == 422


def test_update_without_prior_get(c):
    """PUT should work even if settings row doesn't exist yet."""
    resp = c.put("/api/settings", json={
        "macro_target_protein_pct": 30,
        "macro_target_fat_pct": 30,
        "macro_target_carb_pct": 40,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["macro_target_protein_pct"] == 30


def test_trip_summary_includes_macro_target(c):
    """Trip summary should include macro_target from settings."""
    # Create a trip
    resp = c.post("/api/trips", json={
        "name": "Target Test",
        "first_day_fraction": 1.0,
        "full_days": 0,
        "last_day_fraction": 0.0,
    })
    trip_id = resp.json()["id"]

    # Check default target in summary
    resp = c.get(f"/api/trips/{trip_id}/summary")
    data = resp.json()
    assert data["macro_target"] == {
        "protein_pct": 20,
        "fat_pct": 30,
        "carb_pct": 50,
    }

    # Update settings and verify summary reflects change
    c.put("/api/settings", json={
        "macro_target_protein_pct": 25,
        "macro_target_fat_pct": 35,
        "macro_target_carb_pct": 40,
    })
    resp = c.get(f"/api/trips/{trip_id}/summary")
    data = resp.json()
    assert data["macro_target"] == {
        "protein_pct": 25,
        "fat_pct": 35,
        "carb_pct": 40,
    }
