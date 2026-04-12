"""Tests for food intake queue CRUD."""
import pytest
from database import Base


@pytest.fixture(autouse=True)
def db_setup(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_list_empty(c):
    resp = c.get("/api/food-intake")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_sets_pending_and_created_at(c):
    resp = c.post("/api/food-intake", json={"name": "Chomps beef sticks"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] > 0
    assert data["name"] == "Chomps beef sticks"
    assert data["notes"] is None
    assert data["status"] == "pending"
    assert data["created_at"] is not None
    # ISO-ish shape check
    assert "T" in data["created_at"]


def test_create_with_notes(c):
    resp = c.post(
        "/api/food-intake",
        json={"name": "Honey Stinger Waffles", "notes": "REI, tried on Utah"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["notes"] == "REI, tried on Utah"
    assert data["status"] == "pending"


def test_create_ignores_client_status(c):
    """POST must always set status to pending regardless of payload."""
    # FoodIntakeCreate doesn't accept status but pydantic v2 default ignores extras
    resp = c.post("/api/food-intake", json={"name": "X"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


def test_list_returns_all(c):
    c.post("/api/food-intake", json={"name": "A"})
    c.post("/api/food-intake", json={"name": "B"})
    resp = c.get("/api/food-intake")
    assert resp.status_code == 200
    names = [r["name"] for r in resp.json()]
    assert names == ["A", "B"]


def test_list_status_filter(c):
    r1 = c.post("/api/food-intake", json={"name": "A"}).json()
    c.post("/api/food-intake", json={"name": "B"}).json()
    # Promote A to added
    c.patch(f"/api/food-intake/{r1['id']}", json={"status": "added"})

    resp = c.get("/api/food-intake?status=pending")
    assert [r["name"] for r in resp.json()] == ["B"]

    resp = c.get("/api/food-intake?status=added")
    assert [r["name"] for r in resp.json()] == ["A"]

    resp = c.get("/api/food-intake?status=researched")
    assert resp.json() == []


def test_list_invalid_status_filter(c):
    resp = c.get("/api/food-intake?status=bogus")
    assert resp.status_code == 422


def test_patch_name_and_notes(c):
    row = c.post("/api/food-intake", json={"name": "typo"}).json()
    resp = c.patch(
        f"/api/food-intake/{row['id']}",
        json={"name": "fixed", "notes": "added later"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "fixed"
    assert data["notes"] == "added later"
    assert data["status"] == "pending"


def test_patch_status_valid(c):
    row = c.post("/api/food-intake", json={"name": "X"}).json()
    for status in ("researched", "added", "pending"):
        resp = c.patch(f"/api/food-intake/{row['id']}", json={"status": status})
        assert resp.status_code == 200
        assert resp.json()["status"] == status


def test_patch_status_invalid(c):
    row = c.post("/api/food-intake", json={"name": "X"}).json()
    resp = c.patch(f"/api/food-intake/{row['id']}", json={"status": "rejected"})
    assert resp.status_code == 422


def test_patch_nonexistent(c):
    resp = c.patch("/api/food-intake/9999", json={"name": "nope"})
    assert resp.status_code == 404


def test_delete(c):
    row = c.post("/api/food-intake", json={"name": "X"}).json()
    resp = c.delete(f"/api/food-intake/{row['id']}")
    assert resp.status_code == 204

    # Confirm gone
    resp = c.get("/api/food-intake")
    assert resp.json() == []


def test_delete_nonexistent(c):
    resp = c.delete("/api/food-intake/9999")
    assert resp.status_code == 404
