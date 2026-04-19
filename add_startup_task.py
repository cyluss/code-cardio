# /// script
# requires-python = ">=3.10"
# ///
"""Add switch_model.py as a Windows logon startup task via the Startup folder."""

import os

UV = os.path.join(os.environ["USERPROFILE"], ".cargo", "bin", "uv.exe")
SCRIPT = os.path.join(os.environ["USERPROFILE"], "claude_home", "code-cardio", "switch_model.py")
STARTUP_DIR = os.path.join(
    os.environ["APPDATA"],
    "Microsoft", "Windows", "Start Menu", "Programs", "Startup",
)
BAT = os.path.join(STARTUP_DIR, "switch-model.bat")

bat = f'@echo off\nstart "" /min "{UV}" run "{SCRIPT}"\n'

with open(BAT, "w", encoding="utf-8") as f:
    f.write(bat)

print(f"Startup task added: {BAT}")
