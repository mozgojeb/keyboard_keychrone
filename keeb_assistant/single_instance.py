"""Ensure only one tray instance runs at a time (Windows named mutex)."""

from __future__ import annotations

import sys

from . import APP_ID

_ERROR_ALREADY_EXISTS = 183
_MUTEX_NAME = f"Local\\{APP_ID}.SingleInstance"
_handle: int | None = None


def try_acquire() -> bool:
    """Return True if this process is the sole instance; False if another holds it."""
    global _handle
    if not sys.platform.startswith("win"):
        return True
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        return True
    already = kernel32.GetLastError() == _ERROR_ALREADY_EXISTS
    if already:
        kernel32.CloseHandle(handle)
        return False
    _handle = handle
    return True
