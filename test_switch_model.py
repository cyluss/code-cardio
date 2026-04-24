# /// script
# requires-python = ">=3.10"
# ///
"""MECE test matrix: 3 day types × 2 holiday × 2 hour = 12 cases."""
from datetime import date, datetime

from switch_model import OPUS, SONNET, pick_model

#   2026-04-25 = Saturday
#   2026-04-26 = Sunday
#   2026-04-27 = Monday
HOLIDAY = date(2026, 4, 27)
HOLIDAYS = {HOLIDAY}
NO_HOLIDAYS: set[date] = set()

SAT_IN = datetime(2026, 4, 25, 14, 0)
SAT_OUT = datetime(2026, 4, 25, 9, 0)
SUN_IN = datetime(2026, 4, 26, 14, 0)
SUN_OUT = datetime(2026, 4, 26, 9, 0)
WKD_IN = datetime(2026, 4, 27, 14, 0)
WKD_OUT = datetime(2026, 4, 27, 9, 0)


# --- Saturday ---
def test_sat_no_holiday_in():      assert pick_model(SAT_IN,  NO_HOLIDAYS) == (OPUS,   "Saturday")
def test_sat_no_holiday_out():     assert pick_model(SAT_OUT, NO_HOLIDAYS) == (SONNET, "Saturday")
def test_sat_holiday_in():         assert pick_model(SAT_IN,  HOLIDAYS)    == (OPUS,   "Saturday")
def test_sat_holiday_out():        assert pick_model(SAT_OUT, HOLIDAYS)    == (SONNET, "Saturday")

# --- Sunday ---
def test_sun_no_holiday_in():      assert pick_model(SUN_IN,  NO_HOLIDAYS) == (SONNET, "Sunday")
def test_sun_no_holiday_out():     assert pick_model(SUN_OUT, NO_HOLIDAYS) == (SONNET, "Sunday")
def test_sun_holiday_in():         assert pick_model(SUN_IN,  {date(2026, 4, 26)}) == (SONNET, "Sunday")
def test_sun_holiday_out():        assert pick_model(SUN_OUT, {date(2026, 4, 26)}) == (SONNET, "Sunday")

# --- Weekday ---
def test_wkd_no_holiday_in():      assert pick_model(WKD_IN,  NO_HOLIDAYS) == (SONNET, "Monday")
def test_wkd_no_holiday_out():     assert pick_model(WKD_OUT, NO_HOLIDAYS) == (SONNET, "Monday")
def test_wkd_holiday_in():         assert pick_model(WKD_IN,  HOLIDAYS)    == (OPUS,   "holiday")
def test_wkd_holiday_out():        assert pick_model(WKD_OUT, HOLIDAYS)    == (SONNET, "Monday")

# --- Boundaries ---
def test_boundary_start():         assert pick_model(datetime(2026, 4, 25, 10, 0),  NO_HOLIDAYS) == (OPUS,   "Saturday")
def test_boundary_end_inclusive():  assert pick_model(datetime(2026, 4, 25, 18, 59), NO_HOLIDAYS) == (OPUS,   "Saturday")
def test_boundary_end_exclusive():  assert pick_model(datetime(2026, 4, 25, 19, 0),  NO_HOLIDAYS) == (SONNET, "Saturday")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS  {name}")
    print("All tests passed.")
