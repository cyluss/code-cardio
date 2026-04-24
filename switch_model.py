# /// script
# requires-python = ">=3.10"
# ///
"""Set Claude Code model based on day of week + Korean public holidays.

Saturday or holiday = Opus (deep work), Sunday = Haiku (cooldown),
Weekday = Sonnet (routine).
Holidays sourced from south-korea-holidays.ics (officeholidays.com).
"""

import json
import os
import re
import sys
from datetime import date, datetime

_HOME = os.path.expanduser("~")
SETTINGS_PATH = os.path.join(_HOME, ".claude", "settings.json")
ICS_PATH = os.path.join(_HOME, ".claude", "south-korea-holidays.ics")

OPUS = "claude-opus-4-7"
SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5"


def load_holidays(ics_path: str) -> set[date]:
    """Parse DTSTART;VALUE=DATE lines from an ICS file."""
    holidays: set[date] = set()
    if not os.path.exists(ics_path):
        return holidays
    with open(ics_path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"DTSTART;VALUE=DATE:(\d{8})", line.strip())
            if m:
                holidays.add(datetime.strptime(m.group(1), "%Y%m%d").date())
    return holidays


def main():
    # Allow date override for testing: uv run switch_model.py 2026-05-01
    if len(sys.argv) > 1:
        today = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        today = date.today()
    holidays = load_holidays(ICS_PATH)
    weekday = today.weekday()  # Mon=0 … Sun=6

    if weekday == 5 or (today in holidays and weekday != 6):
        model = OPUS
        reason = "Saturday" if weekday == 5 else "holiday"
    else:
        model = SONNET
        reason = today.strftime("%A")

    with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
        settings = json.load(f)

    settings["model"] = model

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    print(f"Claude Code model set to: {model} ({reason})")


if __name__ == "__main__":
    main()
