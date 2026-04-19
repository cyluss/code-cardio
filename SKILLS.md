# Claude Code Cost Management Skill

## Overview

Automatically optimize Claude Code costs by switching models based on day-of-week and holidays,
with cross-platform startup automation (Windows, macOS, Rocky 9) and daily cost reporting.
Problem: Claude models have vastly different unit costs ($0.0004–$0.150 per M input tokens).
Solution: Deep work (weekends) → Opus; routine tasks (weekdays) → Sonnet; cooldown (Sundays) → Haiku.
Tools: `switch_model.py` (scheduler), `add_startup_task.py` (platform launcher), `toktrack_daily_sku.py` (cost tracking).

---

## Model Strategy

| Day / Condition | Model | Cost/Speed | Use Case |
|---|---|---|---|
| Saturday or holiday | Opus 4.7 | Expensive, best reasoning | Deep design, refactoring, complex problems |
| Sunday | Haiku 4.5 | Cheapest, fastest | Light exploration, cooldown, low-priority tasks |
| Monday–Friday | Sonnet 4.6 | Balanced | Routine scripting, debugging, quick fixes |

**Holiday detection**: Reads `~/.claude/south-korea-holidays.ics` (ICS format, auto-updated from officeholidays.com).
**Custom holidays**: Add `VEVENT` blocks to the ICS file before `END:VCALENDAR` (e.g., election day).

---

## Implementation Guide

### Prerequisites

- **Python 3.10+** — runs the scripts
- **[uv](https://github.com/astral-sh/uv)** — PEP 723 script runner; install via `curl -L | sh` or package manager
- **[toktrack](https://github.com/mag123c/toktrack)** — Claude Code metrics collector (optional, for cost reports)
- **Holiday ICS file** — download from officeholidays.com (setup below)

### Step 1: Download holidays ICS

```bash
curl -L -o ~/.claude/south-korea-holidays.ics \
  https://www.officeholidays.com/ics/south-korea
```

(Replace `south-korea` with your country code if needed.)

### Step 2: Register startup task

Registers `switch_model.py` to run on login (Windows Startup folder, macOS LaunchAgent, or Rocky 9 systemd).

```bash
uv run add_startup_task.py
```

No admin required on any platform.

### Step 3: Install toktrack (optional, for /cost-check)

Download the binary for your platform:

**macOS (Apple Silicon)**
```bash
curl -L -o ~/bin/toktrack \
  https://github.com/mag123c/toktrack/releases/download/v2.4.0/toktrack-darwin-arm64
chmod +x ~/bin/toktrack
xattr -d com.apple.quarantine ~/bin/toktrack
```

**macOS (Intel)**
```bash
curl -L -o ~/bin/toktrack \
  https://github.com/mag123c/toktrack/releases/download/v2.4.0/toktrack-darwin-x64
chmod +x ~/bin/toktrack
xattr -d com.apple.quarantine ~/bin/toktrack
```

**Windows**
```bash
curl -L -o ~/bin/toktrack.exe \
  https://github.com/mag123c/toktrack/releases/download/v2.4.0/toktrack-win32-x64.exe
```

### Step 4: Verify setup

Test manual model switching:
```bash
uv run switch_model.py          # Switch for today
uv run switch_model.py 2026-05-01  # Test for a specific date (Saturday)
```

Check the model was updated:
```bash
cat ~/.claude/settings.json | grep model
```

(Optional) View cost report:
```bash
uv run toktrack_daily_sku.py
```

---

## Platform Setup Reference

### Windows

**Location**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\switch-model.bat`

**uv location**: `%USERPROFILE%\.cargo\bin\uv.exe` (auto-detected)

**Behavior**: Runs on logon, hides window, no admin needed.

**Logs**: (none; runs silently)

---

### macOS

**Location**: `~/Library/LaunchAgents/com.claude.switch-model.plist`

**uv location**: `~/bin/uv` (hardcoded; adjust `setup_macos()` if different)

**Behavior**: Runs at login via launchd, no admin needed.

**Logs**: `tail /tmp/claude-switch-model.log` or `launchctl list | grep switch-model`

**Manual reload**:
```bash
launchctl unload ~/Library/LaunchAgents/com.claude.switch-model.plist
launchctl load -w ~/Library/LaunchAgents/com.claude.switch-model.plist
```

---

### Rocky 9 / systemd Linux

**Locations**:
- Service: `~/.config/systemd/user/claude-switch-model.service`
- Timer: `~/.config/systemd/user/claude-switch-model.timer`

**uv location**: `~/.local/bin/uv` (curl installer default; adjust `setup_linux()` if different)

**Behavior**:
- Service runs at login (`WantedBy=default.target`)
- Timer runs daily at midnight, catches up if missed (`OnCalendar=daily`, `Persistent=true`)

**Logs**:
```bash
tail /tmp/claude-switch-model.log
tail /tmp/claude-switch-model.err
journalctl --user-unit=claude-switch-model.service -n 20
```

**Manual trigger**:
```bash
systemctl --user start claude-switch-model.service
systemctl --user list-timers
```

---

## Skill Prompts (Claude Code Integration)

Paste these into your CLAUDE.md or invoke directly from the CLI.

### `/cost-check`

Run `uv run toktrack_daily_sku.py` and provide a monthly summary:
- Total spend by model
- Day-over-day cost trend (spike days, average day)
- Top 3 most expensive days
- **Highlight switching misses**: dates where Opus was used but the strategy expected Sonnet/Haiku (indicates the scheduler didn't run or a manual model override happened)

---

### `/model-status`

1. Read `~/.claude/settings.json` and report the current configured model
2. Calculate today's expected model: Saturday or holiday → Opus 4.7; Sunday → Haiku 4.5; else Sonnet 4.6
3. If current ≠ expected, explain why and offer to run `uv run switch_model.py` to fix

---

### `/switching-miss-check`

1. Run `uv run toktrack_daily_sku.py` or call `toktrack daily --json`
2. For each day in the past 30 days, determine the expected model (strategy), then identify which model actually incurred the most cost that day
3. List misses (date, expected model, actual model, % cost overage vs. expected model's rate)
4. Suggest whether to: disable the switching script (run it manually instead), check if the ICS file is stale, or investigate why the scheduler missed a run

---

### `/monthly-budget`

Given a target budget (e.g., "$500/month"):
1. Estimate tokens available at each model's rate (input cost per million tokens)
2. Show allocations: "At $500/mo with 60% Sonnet, 30% Opus, 10% Haiku, you can spend X tokens/month"
3. Compare to this month's actual usage; flag if overage is likely

---

## Tuning Notes

- **Timer persistence** (Rocky 9): `Persistent=true` ensures the daily timer fires immediately if the system was off at midnight. Good for sporadic use; disable if you want strict midnight-only runs.
- **Holiday ICS updates**: officeholidays.com updates monthly. Re-download occasionally or automate with a cron job.
- **Manual holiday entries**: For non-recurring holidays (e.g., special elections), add entries directly to the ICS file:
  ```ini
  BEGIN:VEVENT
  DTSTART;VALUE=DATE:20260603
  DTEND;VALUE=DATE:20260604
  SUMMARY:Local Election Day
  END:VEVENT
  ```
- **Model retirement**: `toktrack` tracks exact model IDs. If Claude retires a model (e.g., Opus 4.6 → 4.7), update the model constants in `switch_model.py` and check `toktrack_daily_sku.py` output for stale SKUs.
- **Timezone**: Cost reports use your local timezone. `toktrack` logs in UTC; `switch_model.py` uses the OS date.

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Model not switching | Run `uv run switch_model.py` manually. Check `~/.claude/south-korea-holidays.ics` exists. Verify startup task registered (Windows Startup folder, `launchctl list`, `systemctl --user list-timers`). |
| Incorrect model (expected Sonnet, got Opus) | Holiday detection: check date in ICS file. Manual override: reload settings.json. |
| Cost spikes | Run `/switching-miss-check` to identify which model was used. Compare to expected model via `/model-status`. |
| No toktrack output | Install binary correctly. Check path: `~/bin/toktrack` (macOS) or `~/.local/bin/toktrack` (Linux). Verify toktrack executable: `toktrack daily --json` directly. |

