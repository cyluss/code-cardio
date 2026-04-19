# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: code-cardio — Claude Code Cost Management

Auto-switches Claude Code models (Opus/Sonnet/Haiku) based on day-of-week + Korean holidays,
with cross-platform startup automation and daily cost tracking.

---

## Commands

All scripts use PEP 723 inline script metadata and run via `uv`:

```bash
# Test model switching for today
uv run switch_model.py

# Test for a specific date (e.g., check Saturday logic)
uv run switch_model.py 2026-05-01

# Register the model switcher as a logon/login startup task
# (auto-detects platform: Windows .bat, macOS LaunchAgent, Rocky 9 systemd)
uv run add_startup_task.py

# Show daily cost + token usage by model (requires toktrack binary installed)
uv run toktrack_daily_sku.py

# Download holiday ICS from officeholidays.com
curl -L -o ~/.claude/south-korea-holidays.ics \
  https://www.officeholidays.com/ics/south-korea
```

---

## Architecture Overview

### Three Independent Scripts

**1. `switch_model.py` — Model Switcher**
- **Input**: Today's date, holidays ICS file at `~/.claude/south-korea-holidays.ics`
- **Logic**: 
  - Saturday OR holiday → Opus 4.7 (deep work)
  - Sunday → Haiku 4.5 (cooldown)
  - Else → Sonnet 4.6 (routine)
- **Output**: Updates `~/.claude/settings.json` with the model key
- **Execution**: Runs at login (platform-specific startup)

**2. `add_startup_task.py` — Cross-Platform Launcher Registration**
- **Logic**: Detects OS and writes the appropriate startup unit
- **Platform handlers**:
  - Windows: Creates `.bat` in Startup folder; hardcodes uv path at `%USERPROFILE%\.cargo\bin\uv.exe`
  - macOS: Creates LaunchAgent plist; assumes uv at `~/bin/uv`
  - Rocky 9/systemd: Creates systemd user `.service` and `.timer` files; assumes uv at `~/.local/bin/uv`
- **Idempotent**: Re-running overwrites and re-registers the startup unit

**3. `toktrack_daily_sku.py` — Cost Reporter**
- **Input**: `toktrack daily --json` (Claude Code metrics)
- **Logic**: Groups daily usage by SKU (model), calculates costs, formats as human-readable tables
- **Output**: Dual tables (cost in USD, tokens by type: input/output/cache/thinking)
- **Timezone**: Auto-detects local timezone and labels dates accordingly

### Data Flow

```
User logs in
  ↓
Startup task runs switch_model.py
  ↓
Reads ~/.claude/south-korea-holidays.ics
  ↓
Calculates expected model for today
  ↓
Updates ~/.claude/settings.json (model key)
  ↓
Claude Code reads settings.json on startup → uses new model
```

Separately, toktrack collects Claude Code usage → user can run toktrack_daily_sku.py to review costs and identify switching misses.

---

## Platform-Specific Details

### Windows

- **uv path**: `%USERPROFILE%\.cargo\bin\uv.exe` (auto-detected from `.cargo/bin/`)
- **startup file**: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\switch-model.bat`
- **Encoding**: Windows Korean locale defaults to cp949. Always use `encoding='utf-8'` in `open()`, `Path.read_text()`, etc. or set `PYTHONIOENCODING=utf-8`.
- **Dev Drive optimization** (from CLAUDE.md context): Keep repo on Dev Drive (D:) for fast Windows access; set `UV_PROJECT_ENVIRONMENT=~/.venvs/<project>` to keep dependency trees on WSL 2 ext4 for fast Linux toolchain access.

### macOS

- **uv path**: `~/bin/uv` (hardcoded in `setup_macos()`)
- **startup file**: `~/Library/LaunchAgents/com.claude.switch-model.plist`
- **launchd concepts**: Equivalent to systemd on Linux; see README.md table for launchd ↔ systemd mappings
- **Logs**: `tail /tmp/claude-switch-model.log` (plist captures stdout/stderr to files)

### Rocky 9 / systemd Linux

- **uv path**: `~/.local/bin/uv` (curl installer default)
- **startup units**: `~/.config/systemd/user/claude-switch-model.{service,timer}`
  - Service: `Type=oneshot`, runs once per login (`WantedBy=default.target`)
  - Timer: `OnCalendar=daily`, `Persistent=true` (fires daily, catches up if missed)
- **Logs**: Both file (`/tmp/claude-switch-model.{log,err}`) and journal (`journalctl --user-unit=...`)
- **Activation**: `systemctl --user enable --now`

---

## Key Files & Responsibilities

| File | Purpose | Key Logic |
|------|---------|-----------|
| `switch_model.py` | Model selection | `weekday == 5` (Sat) or `today in holidays` → Opus; `weekday == 6` (Sun) → Haiku; else Sonnet |
| `add_startup_task.py` | Startup registration | Platform dispatch via `sys.platform` check; writes unit files with uv + SCRIPT paths |
| `toktrack_daily_sku.py` | Cost reporting | Parses toktrack JSON, groups by SKU, builds dual tables (cost + tokens) |
| README.md | User documentation | Setup instructions per platform, holidays ICS source, toktrack binary downloads |
| SKILLS.md | Skill extraction | Full implementation guide + Claude skill prompts (`/cost-check`, `/model-status`, etc.) |

---

## Critical Gotchas

1. **ICS file required** — `switch_model.py` silently returns empty set if `~/.claude/south-korea-holidays.ics` is missing; holidays won't be detected.

2. **uv paths are hardcoded per platform** — If user installs uv to a non-standard location (e.g., `~/custom/bin/uv`), the startup task will fail. User must edit the `setup_*()` function.

3. **settings.json encoding on Windows Korean** — On Korean Windows (cp949 locale), reading/writing settings.json without `encoding='utf-8-sig'` can cause `UnicodeDecodeError`. Current code handles this correctly; preserve when editing.

4. **toktrack binary separate** — The tool is not bundled; user must download the binary from releases and place it at `~/bin/toktrack` (or `~/.local/bin/` on Linux).

5. **Startup task idempotency** — Re-running `add_startup_task.py` overwrites the previous unit file. On macOS, this unloads then reloads the plist; on Rocky 9, this runs `daemon-reload`. Safe to re-run, but watch for error output if user is testing rapid changes.

6. **Model constants hardcoded** — Model IDs (OPUS, SONNET, HAIKU) are module-level constants. If Claude retires a model ID, update all three scripts.

---

## Extensibility Notes

- **Adding a new platform**: Add a `setup_<platform>()` function in `add_startup_task.py` and a new branch in the platform dispatch. Follow the existing pattern: create unit files, run activation commands.
- **Changing holiday source**: Swap the ICS URL or file format. The parser looks for `DTSTART;VALUE=DATE:YYYYMMDD` lines; as long as input matches this, it works.
- **Custom model strategy**: Edit the decision logic in `switch_model.py` main(). Currently day-of-week + holiday; could add special rules (e.g., "month > 6 → Sonnet") or integrate external calendar/budget APIs.
- **Cost thresholds**: `toktrack_daily_sku.py` could add alerts (e.g., "exceeded daily budget by 20%") by extending the table-building logic.

---

## References

- **README.md** — User-facing setup guide, background, dependencies
- **SKILLS.md** — Skill prompts and implementation guide for cost analysis on-demand
- **Context** — This codebase targets Korean holidays; main branch is in Korean (README, comments). Consider translating if expanding to international users.
