# /// script
# requires-python = ">=3.10"
# ///
"""Format `toktrack daily --json` as per-SKU daily cost and token tables."""

import json
import os
import subprocess
import sys
from datetime import datetime
from itertools import groupby

TOKTRACK = os.path.expanduser("~/bin/toktrack.exe")
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "thinking_tokens",
)


def model_tokens(m: dict) -> int:
    return sum(int(m.get(f, 0) or 0) for f in TOKEN_FIELDS)


def _detect_iana() -> str:
    tz_env = os.environ.get("TZ", "").strip()
    if tz_env and "/" in tz_env:
        return tz_env
    try:
        with open("/etc/timezone", "r", encoding="utf-8") as f:
            name = f.read().strip()
            if name:
                return name
    except OSError:
        pass
    link = "/etc/localtime"
    try:
        if os.path.islink(link):
            target = os.readlink(link)
            marker = "/zoneinfo/"
            if marker in target:
                return target.split(marker, 1)[1]
    except OSError:
        pass
    if sys.platform == "win32":
        try:
            import winreg  # type: ignore[import-not-found]

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "TimeZoneKeyName")
                if value:
                    return str(value)
        except (ImportError, OSError):
            pass
    return ""


def local_timezone_label() -> str:
    now = datetime.now().astimezone()
    abbrev = now.tzname() or ""
    offset = now.strftime("%z")
    if offset:
        offset = f"{offset[:3]}:{offset[3:]}"
    iana = _detect_iana()
    parts = [p for p in (iana, abbrev, f"UTC{offset}" if offset else "") if p]
    return " ".join(parts) if parts else "local"


def humanize(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def build_table(data, skus, col_w, value_fn, fmt_cell, fmt_total):
    header = f"{'date':<12}" + "".join(f"{s:>{col_w}}" for s in skus) + f"{'TOTAL':>{col_w}}"
    sep = "-" * len(header)
    lines = [header, sep]
    sku_totals = {s: 0 for s in skus}
    grand = 0

    for month, month_days in groupby(data, key=lambda d: d["date"][:7]):
        month_sku = {s: 0 for s in skus}
        month_total = 0
        for d in month_days:
            row = f"{d['date']:<12}"
            day_total = 0
            for s in skus:
                v = value_fn(s, d.get("models", {}).get(s, {}) or {}, d)
                month_sku[s] += v
                day_total += v
                row += fmt_cell(v)
            month_total += day_total
            row += fmt_total(day_total)
            lines.append(row)
        for s in skus:
            sku_totals[s] += month_sku[s]
        grand += month_total
        lines.append(
            f"{month + ' sub':<12}"
            + "".join(fmt_cell(month_sku[s]) for s in skus)
            + fmt_total(month_total)
        )
        lines.append(sep)

    lines.append(
        f"{'TOTAL':<12}"
        + "".join(fmt_cell(sku_totals[s]) for s in skus)
        + fmt_total(grand)
    )
    return lines


def main() -> int:
    result = subprocess.run(
        [TOKTRACK, "daily", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = sorted(json.loads(result.stdout), key=lambda d: d["date"])
    if not data:
        print("no data")
        return 0

    skus = sorted({m for d in data for m in d.get("models", {})})
    col_w = max([len(s) for s in skus] + [10]) + 2

    cost_lines = build_table(
        data,
        skus,
        col_w,
        value_fn=lambda s, m, d: m.get("cost_usd", 0.0),
        fmt_cell=lambda v: f"${v:>{col_w - 1}.2f}",
        fmt_total=lambda v: f"${v:>{col_w - 1}.2f}",
    )
    token_lines = build_table(
        data,
        skus,
        col_w,
        value_fn=lambda s, m, d: model_tokens(m),
        fmt_cell=lambda v: f"{humanize(v):>{col_w}}",
        fmt_total=lambda v: f"{humanize(v):>{col_w}}",
    )

    tz = local_timezone_label()
    print(f"note: dates are in your local timezone ({tz})")
    print()
    print("=== COST (USD) ===")
    print("\n".join(cost_lines))
    print()
    print("=== TOKENS (input + output + cache + thinking) ===")
    print("\n".join(token_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
