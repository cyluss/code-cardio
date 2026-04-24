# /// script
# requires-python = ">=3.10"
# ///
"""Register switch_model.py as a scheduled startup task.

Windows: creates schtasks entries (logon + hourly triggers).
macOS:   writes a LaunchAgent plist and loads it via launchctl.
Linux:   creates systemd user service + timer.
"""

import os
import subprocess
import sys

from switch_model import OPUS_START, OPUS_END

SCRIPT = os.path.join(os.path.expanduser("~"), "claude_home", "code-cardio", "switch_model.py")


def setup_windows():
    uv = os.path.join(os.environ["USERPROFILE"], ".cargo", "bin", "uv.exe")
    task_name = "ClaudeSwitchModel"

    for suffix, sc_args in [
        ("logon", ["onlogon"]),
        (str(OPUS_START), ["daily", "/st", f"{OPUS_START:02d}:00"]),
        (str(OPUS_END),   ["daily", "/st", f"{OPUS_END:02d}:00"]),
    ]:
        subprocess.run([
            "schtasks", "/create", "/f",
            "/tn", f"{task_name}-{suffix}",
            "/tr", f'"{uv}" run "{SCRIPT}"',
            "/sc", *sc_args,
        ], check=True)

    print(f"Scheduled tasks created: {task_name}-logon, {task_name}-{OPUS_START}, {task_name}-{OPUS_END}")


def setup_macos():
    uv = os.path.join(os.path.expanduser("~"), ".local", "bin", "uv")
    label = "com.claude.switch-model"
    agents_dir = os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents")
    plist_path = os.path.join(agents_dir, f"{label}.plist")

    os.makedirs(agents_dir, exist_ok=True)

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{uv}</string>
        <string>run</string>
        <string>{SCRIPT}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>{OPUS_START}</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
        <dict>
            <key>Hour</key>
            <integer>{OPUS_END}</integer>
            <key>Minute</key>
            <integer>0</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/claude-switch-model.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-switch-model.err</string>
</dict>
</plist>
"""
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist)

    subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
    subprocess.run(["launchctl", "load", "-w", plist_path], check=True)
    print(f"LaunchAgent loaded: {plist_path}")


def setup_linux():
    uv = os.path.join(os.path.expanduser("~"), ".local", "bin", "uv")
    units_dir = os.path.join(os.path.expanduser("~"), ".config", "systemd", "user")
    os.makedirs(units_dir, exist_ok=True)

    service_path = os.path.join(units_dir, "claude-switch-model.service")
    timer_path = os.path.join(units_dir, "claude-switch-model.timer")

    service = f"""[Unit]
Description=Switch Claude Code model based on day/holiday

[Service]
Type=oneshot
ExecStart={uv} run {SCRIPT}
StandardOutput=file:/tmp/claude-switch-model.log
StandardError=file:/tmp/claude-switch-model.err

[Install]
WantedBy=default.target
"""
    timer = f"""[Unit]
Description=Claude Code model switcher ({OPUS_START}:00 and {OPUS_END}:00)

[Timer]
OnCalendar=*-*-* {OPUS_START:02d}:00:00
OnCalendar=*-*-* {OPUS_END:02d}:00:00
Persistent=true
Unit=claude-switch-model.service

[Install]
WantedBy=timers.target
"""
    with open(service_path, "w", encoding="utf-8") as f:
        f.write(service)
    with open(timer_path, "w", encoding="utf-8") as f:
        f.write(timer)

    subprocess.run(["systemctl", "--user", "daemon-reload"])
    subprocess.run(["systemctl", "--user", "enable", "--now", "claude-switch-model.service"])
    subprocess.run(["systemctl", "--user", "enable", "--now", "claude-switch-model.timer"])
    print(f"systemd service and timer configured: {service_path}, {timer_path}")


def main():
    match sys.platform:
        case "win32":               setup_windows()
        case "darwin":              setup_macos()
        case p if p.startswith("linux"): setup_linux()
        case _:
            print(f"Unsupported platform: {sys.platform}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
