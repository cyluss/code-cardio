# /// script
# requires-python = ">=3.10"
# ///
"""Add switch_model.py as a logon startup task.

Windows: writes to the Startup folder (no admin required).
macOS:   writes a LaunchAgent plist and loads it via launchctl.
"""

import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.expanduser("~"), "claude_home", "code-cardio", "switch_model.py")


def setup_windows():
    uv = os.path.join(os.environ["USERPROFILE"], ".cargo", "bin", "uv.exe")
    startup_dir = os.path.join(
        os.environ["APPDATA"],
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
    )
    bat = os.path.join(startup_dir, "switch-model.bat")
    with open(bat, "w", encoding="utf-8") as f:
        f.write(f'@echo off\nstart "" /min "{uv}" run "{SCRIPT}"\n')
    print(f"Startup task added: {bat}")


def setup_macos():
    uv = os.path.join(os.path.expanduser("~"), "bin", "uv")
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
    <key>StandardOutPath</key>
    <string>/tmp/claude-switch-model.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-switch-model.err</string>
</dict>
</plist>
"""
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist)

    # Unload first in case it was already registered
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

[Install]
WantedBy=default.target
"""
    timer = """[Unit]
Description=Daily Claude Code model switcher

[Timer]
OnCalendar=daily
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


if sys.platform == "win32":
    setup_windows()
elif sys.platform == "darwin":
    setup_macos()
elif sys.platform.startswith("linux"):
    setup_linux()
else:
    print(f"Unsupported platform: {sys.platform}", file=sys.stderr)
    sys.exit(1)
