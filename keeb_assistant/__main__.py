"""Entry point: `python -m keeb_assistant`.

Supports a small CLI for quick checks in addition to the tray app:
  python -m keeb_assistant            -> launch the tray app
  python -m keeb_assistant --start-in-tray -> launch without opening the GUI
  python -m keeb_assistant --once     -> print one reading and exit
"""

from __future__ import annotations

import sys


def _cli_once() -> int:
    from . import i18n
    from .config import Config
    from .hid_reader import read_once

    i18n.set_language(Config.load().get("language", i18n.DEFAULT_LANGUAGE))

    reading = read_once(timeout=5.0)
    if reading is None:
        print(i18n.t("cli_no_data"))
        return 1
    print(
        i18n.t(
            "cli_line",
            pct=reading.percentage,
            mv=reading.voltage_mv,
            charging=i18n.t(f"charging_{reading.charging_code}"),
            transport=reading.transport_name,
        )
    )
    return 0


def main() -> None:
    if "--once" in sys.argv:
        # Console may be cp1252 on Windows; allow non-Latin output (e.g. 中文).
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        sys.exit(_cli_once())
    from .tray_app import main as tray_main

    tray_main()


if __name__ == "__main__":
    main()
