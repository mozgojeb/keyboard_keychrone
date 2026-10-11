"""Optional CSV logging of battery samples (diagnostics / future calibration).

Opt-in via the ``battery_logging`` config flag (default off). Each reading is
appended as one row to ``%APPDATA%/KeyboardCompanion/battery_log.csv``. A simple
size cap with a single ``.1`` backup keeps it from growing without bound.

The goal is to gather *real* data — especially voltage vs charging state across
charge/discharge cycles — so the charging-overestimate correction can later be
modelled on actual numbers instead of a guessed offset. It does NOT change
anything shown to the user.
"""

from __future__ import annotations

import csv
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import config_dir

LOG_FILENAME = "battery_log.csv"
MAX_BYTES = 5 * 1024 * 1024  # rotate to .1 past ~5 MB
HEADER = [
    "iso_time",
    "epoch",
    "source",
    "transport",
    "charging",
    "voltage_mv",
    "raw_pct",
    "displayed_pct",
    "ema",
]

_lock = threading.Lock()


def log_path() -> Path:
    return config_dir() / LOG_FILENAME


def _rotate_if_needed(path: Path) -> None:
    try:
        if path.exists() and path.stat().st_size >= MAX_BYTES:
            backup = path.with_name(path.name + ".1")
            try:
                if backup.exists():
                    backup.unlink()
            except OSError:
                pass
            path.replace(backup)
    except OSError:
        pass


def append(
    *,
    source: str,
    transport: str,
    charging: int,
    voltage_mv: int,
    raw_pct: int,
    displayed_pct: int | None,
    ema: float | None,
) -> None:
    """Append one sample row. Best-effort: never raises to the caller."""
    path = log_path()
    with _lock:
        try:
            _rotate_if_needed(path)
            is_new = not path.exists()
            with open(path, "a", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                if is_new:
                    writer.writerow(HEADER)
                now = time.time()
                writer.writerow(
                    [
                        datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds"),
                        f"{now:.3f}",
                        source,
                        transport,
                        charging,
                        voltage_mv,
                        raw_pct,
                        "" if displayed_pct is None else displayed_pct,
                        "" if ema is None else f"{ema:.2f}",
                    ]
                )
        except OSError:
            pass


def open_location() -> None:
    """Open the folder containing the log (so the user can grab the CSV)."""
    try:
        folder = str(config_dir())
        if sys.platform.startswith("win"):
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess

            subprocess.Popen(["open", folder])
        else:
            import subprocess

            subprocess.Popen(["xdg-open", folder])
    except Exception:
        pass
