"""Launch the optional desktop battery widget from the installed app."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def widget_script() -> Path:
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return bundle / "KeyboardBatteryWidget.ps1"


def show_widget() -> bool:
    script = widget_script()
    if not sys.platform.startswith("win") or not script.is_file():
        return False
    try:
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
             "-WindowStyle", "Hidden", "-File", str(script)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except OSError:
        return False
