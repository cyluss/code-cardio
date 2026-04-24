# /// script
# requires-python = ">=3.10"
# ///
"""Set Claude Code model based on day of week, hour, and Korean public holidays.

Saturday or weekday holiday 10–19 = Opus (deep work),
everything else = Sonnet (routine).
Holidays sourced from south-korea-holidays.ics (officeholidays.com).
"""

import json
import os
import re
import sys
from datetime import date, datetime

# --- Paths ---

_HOME = os.path.expanduser("~")
SETTINGS_PATH = os.path.join(_HOME, ".claude", "settings.json")
ICS_PATH = os.path.join(_HOME, ".claude", "south-korea-holidays.ics")

# --- Models ---

OPUS = "claude-opus-4-7"
SONNET = "claude-sonnet-4-6"

OPUS_START = 10
OPUS_END = 19

# --- Input: ICS parsing ---


def load_holidays(ics_path: str) -> set[date]:
    holidays: set[date] = set()
    if not os.path.exists(ics_path):
        return holidays
    with open(ics_path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"DTSTART;VALUE=DATE:(\d{8})", line.strip())
            if m:
                holidays.add(datetime.strptime(m.group(1), "%Y%m%d").date())
    return holidays


# --- Logic: model selection (MECE) ---


def _day_type(today: date, holidays: set[date]) -> str:
    weekday = today.weekday()
    match weekday:
        case 6:                                         return "sunday"
        case 5:                                         return "saturday"
        case _ if today in holidays:                    return "weekday_holiday"
        case _:                                         return "weekday"


def pick_model(now: datetime, holidays: set[date]) -> tuple[str, str]:
    in_hours = OPUS_START <= now.hour < OPUS_END
    day = _day_type(now.date(), holidays)

    match (day, in_hours):
        case ("saturday",        True):     return OPUS,   "Saturday"
        case ("saturday",        False):    return SONNET, "Saturday"
        case ("weekday_holiday", True):     return OPUS,   "holiday"
        case ("weekday_holiday", False):    return SONNET, now.date().strftime("%A")
        case ("sunday",          _):        return SONNET, "Sunday"
        case ("weekday",         _):        return SONNET, now.date().strftime("%A")
        case _:                             raise ValueError(f"unexpected: {day!r}")


# --- Output: settings.json ---


def apply_model(model: str, reason: str) -> None:
    with open(SETTINGS_PATH, "r", encoding="utf-8-sig") as f:
        settings = json.load(f)

    settings["model"] = model

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

    print(f"Claude Code model set to: {model} ({reason})")


# --- Entry point ---


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        now = datetime.strptime(arg, "%Y-%m-%d %H:%M") if " " in arg else datetime.strptime(arg, "%Y-%m-%d")
    else:
        now = datetime.now()

    holidays = load_holidays(ICS_PATH)
    model, reason = pick_model(now, holidays)
    apply_model(model, reason)


if __name__ == "__main__":
    main()
