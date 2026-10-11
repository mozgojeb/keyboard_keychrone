"""Windows tray-icon registry maintenance.

Windows 11 stores the "Other system tray icons" preferences under the current
user profile. During development or portable app updates, old PyInstaller paths
can leave duplicate disabled entries. These helpers are deliberately conservative
and only touch entries that look like Keyboard Companion.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from . import APP_NAME

_ROOT = r"Control Panel\NotifyIconSettings"
_OLD_TOOLTIP_HINTS = ("Keyboard Companion", "Keeb Battery Assistant")


@dataclass(frozen=True)
class TrayIconRecord:
    key_name: str
    executable_path: str
    initial_tooltip: str
    is_promoted: int | None

    @property
    def is_current_exe(self) -> bool:
        return _same_path(self.executable_path, current_executable_path())

    @property
    def is_promoted_bool(self) -> bool:
        return self.is_promoted == 1


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def current_executable_path() -> str:
    return str(Path(sys.executable))


def _same_path(a: str, b: str) -> bool:
    try:
        return str(Path(a)).casefold() == str(Path(b)).casefold()
    except (TypeError, ValueError):
        return False


def _looks_related(executable_path: str, tooltip: str) -> bool:
    exe_name = Path(executable_path).name.casefold() if executable_path else ""
    tooltip_text = tooltip or ""
    if exe_name == "keyboardcompanion.exe":
        return True
    if any(hint in tooltip_text for hint in _OLD_TOOLTIP_HINTS):
        return True
    # Early dev builds ran from python.exe/pythonw.exe but still exposed our
    # app tooltip; never delete arbitrary Python tray records.
    if exe_name in {"python.exe", "pythonw.exe"}:
        return any(hint in tooltip_text for hint in _OLD_TOOLTIP_HINTS)
    return APP_NAME in tooltip_text


def list_records() -> list[TrayIconRecord]:
    if not _is_windows():
        return []
    import winreg

    records: list[TrayIconRecord] = []
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _ROOT)
    except OSError:
        return []
    with root:
        index = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            try:
                with winreg.OpenKey(root, subkey_name) as subkey:
                    executable, _ = winreg.QueryValueEx(subkey, "ExecutablePath")
                    try:
                        tooltip, _ = winreg.QueryValueEx(subkey, "InitialTooltip")
                    except OSError:
                        tooltip = ""
                    try:
                        promoted, _ = winreg.QueryValueEx(subkey, "IsPromoted")
                    except OSError:
                        promoted = None
            except OSError:
                continue
            if _looks_related(str(executable), str(tooltip)):
                records.append(
                    TrayIconRecord(
                        key_name=subkey_name,
                        executable_path=str(executable),
                        initial_tooltip=str(tooltip),
                        is_promoted=int(promoted) if promoted is not None else None,
                    )
                )
    return records


def cleanup_old_records() -> int:
    """Delete stale Keyboard Companion tray records. Returns deleted count."""
    if not _is_windows():
        return 0
    import winreg

    deleted = 0
    current = current_executable_path()
    has_promoted_current = any(
        r.is_promoted_bool and _same_path(r.executable_path, current)
        for r in list_records()
    )
    for record in list_records():
        # Keep any promoted entry; Windows already considers it user-selected.
        # Also keep the current executable unless a promoted current duplicate
        # already exists, in which case an unpromoted current entry is stale.
        if record.is_promoted_bool:
            continue
        if _same_path(record.executable_path, current) and not has_promoted_current:
            continue
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{_ROOT}\\{record.key_name}")
            deleted += 1
        except OSError:
            pass
    return deleted


def current_is_promoted() -> bool:
    return any(r.is_current_exe and r.is_promoted_bool for r in list_records())


def promote_current_icon() -> bool:
    """Set current executable tray entry to always visible. Returns success."""
    if not _is_windows():
        return False
    import winreg

    changed = False
    for record in list_records():
        if not record.is_current_exe:
            continue
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                f"{_ROOT}\\{record.key_name}",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, "IsPromoted", 0, winreg.REG_DWORD, 1)
                changed = True
        except OSError:
            pass
    return changed or current_is_promoted()
