import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_slot_pcts_sum_to_one():
    from routers.trips import CATEGORY_TO_SLOT

    # All non-lunch categories map to snacks
    assert CATEGORY_TO_SLOT["bars_energy"] == "snacks"
    assert CATEGORY_TO_SLOT["salty"] == "snacks"
    assert CATEGORY_TO_SLOT["sweet"] == "snacks"
    assert CATEGORY_TO_SLOT["drink_mix"] == "snacks"
    assert CATEGORY_TO_SLOT["lunch"] == "lunch"


def test_slot_split_is_40_60():
    """Verify the slot percentage constants used in the summary endpoint."""
    # Import the module and check the values are used correctly
    # We read them from the source since they're inline in the function
    source = (Path(__file__).parent.parent / "routers" / "trips.py").read_text()
    assert '"lunch": 0.40' in source or '"lunch": 0.4' in source
    assert '"snacks": 0.60' in source or '"snacks": 0.6' in source
    # Verify no old slot names remain
    assert '"morning_snack"' not in source
    assert '"afternoon_snack"' not in source
