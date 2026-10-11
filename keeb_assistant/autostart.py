"""Optional Windows auto-start via the per-user Run registry key.

The user controls this from the tray menu; nothing is enabled by default.
Works both when running as a frozen .exe and as a `python -m` script.

``is_enabled()`` is true only when the Run value matches this install *and*
the target exists. ``sync_from_config()`` refreshes or removes the Run entry
on app startup so renames, moves, and stale download paths do not leave a
checked UI with a broken logon command.
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import APP_ID

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _launch_command() -> str:
    """Command Windows should run at logon."""
    start_in_tray_arg = " --start-in-tray"
    if getattr(sys, "frozen", False):
        # Packaged exe (onedir): run the exe inside its install folder.
        return f'"{sys.executable}"{start_in_tray_arg}'
    # Dev mode: run with pythonw (no console window) -m keeb_assistant
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{runner}" -m keeb_assistant{start_in_tray_arg}'


def _normalize_command(command: str) -> str:
    return " ".join(command.split())


def _extract_exe_path(command: str) -> Path | None:
    """First token of a Run value (quoted exe path or bare path)."""
    text = command.strip()
    if not text:
        return None
    if text.startswith('"'):
        end = text.find('"', 1)
        if end > 1:
            return Path(text[1:end])
        return None
    token = text.split(None, 1)[0]
    return Path(token) if token else None


def _read_registry_command() -> str | None:
    if not _is_windows():
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_ID)
            return str(value) if value else None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _command_is_valid(stored: str) -> bool:
    """True when the Run value matches this install and the target exists."""
    if _normalize_command(stored) != _normalize_command(_launch_command()):
        return False
    exe = _extract_exe_path(stored)
    if exe is not None and not exe.is_file():
        return False
    return True


def _delete_registry_value() -> None:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, APP_ID)
    except FileNotFoundError:
        pass


def is_enabled() -> bool:
    stored = _read_registry_command()
    if not stored:
        return False
    return _command_is_valid(stored)


def set_enabled(enabled: bool) -> bool:
    """Enable/disable autostart. Returns the resulting state."""
    if not _is_windows():
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, _launch_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_ID)
                except FileNotFoundError:
                    pass
    except OSError:
        return is_enabled()
    return enabled


def sync_from_config(autostart_wanted: bool) -> bool:
    """Align the Run key with the user's preference; refresh path when enabled.

    When autostart is wanted, always rewrite the Run value so renames and new
    exe locations are picked up. When not wanted, remove a valid entry or drop
    a stale orphan left from an old path.
    """
    if autostart_wanted:
        return set_enabled(True)

    stored = _read_registry_command()
    if stored is None:
        return False
    if _command_is_valid(stored):
        return set_enabled(False)
    _delete_registry_value()
    return False
