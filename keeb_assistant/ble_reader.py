"""Bluetooth battery via Windows (mirror of what the OS already knows).

When the keyboard is connected over Bluetooth LE, its vendor raw-HID interface
is NOT exposed (only standard HID + the BLE Battery Service). Rather than
opening our own GATT connection (which can clash with the OS holding the HID
link), we simply read the battery level Windows already cached as a device
property: DEVPKEY_Bluetooth_Battery = {104EA319-6EE2-4701-BD47-8DDBF425BBE5},2.

CRUCIAL: that battery value is *cached*. Windows keeps a paired BLE device
"present" (with its last-known battery) for a while after it disconnects, so
`-PresentOnly` alone is NOT enough — it would mirror a stale percentage for a
keyboard that is actually off/away. We therefore also require the device to be
*actively connected* via the Bluetooth connection-status property
{83DA6326-97A6-4088-9453-A1923F573B29},15 (True only while connected; confirmed
on the K10 HE BTHLE node). If it is not connected we return None, so the tray
falls back to "Undetected" instead of showing a phantom Bluetooth reading.

This is read via PowerShell's Get-PnpDeviceProperty, matching the keyboard by
friendly name. No extra Python dependency required.
"""

from __future__ import annotations

import re
import subprocess
import sys

# Devices whose friendly name matches this are considered "our" keyboard(s).
NAME_PATTERN = "Keychron|K10|Lemokey"

_BATTERY_KEY = "{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2"
# Bluetooth "is connected" flag (True only while the device is actively connected).
_CONNECTED_KEY = "{83DA6326-97A6-4088-9453-A1923F573B29} 15"

_PS_BATTERY_SCRIPT = (
    "$ErrorActionPreference='SilentlyContinue';"
    f"$bat='{_BATTERY_KEY}';"
    f"$conn='{_CONNECTED_KEY}';"
    f"Get-PnpDevice -PresentOnly | Where-Object {{ $_.FriendlyName -match '{NAME_PATTERN}' }} | "
    "ForEach-Object {"
    " $c = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName $conn).Data;"
    " if ($c -eq $true) {"
    "  $b = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName $bat).Data;"
    "  if ($b -ne $null) { Write-Output $b }"
    " }"
    "}"
)

_PS_NAME_SCRIPT = (
    "$ErrorActionPreference='SilentlyContinue';"
    f"$conn='{_CONNECTED_KEY}';"
    f"Get-PnpDevice -PresentOnly | Where-Object {{ $_.FriendlyName -match '{NAME_PATTERN}' }} | "
    "ForEach-Object {"
    " $c = (Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName $conn).Data;"
    " if ($c -eq $true) { Write-Output $_.FriendlyName }"
    " }"
)

_CREATE_NO_WINDOW = 0x08000000


def is_supported() -> bool:
    return sys.platform.startswith("win")


def read_bluetooth_battery() -> int | None:
    """Return the BLE battery percentage Windows reports, or None."""
    if not is_supported():
        return None
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_BATTERY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    for token in re.findall(r"\d+", proc.stdout or ""):
        value = int(token)
        if 0 <= value <= 100:
            return value
    return None


def read_bluetooth_device_name() -> str | None:
    """Return the friendly name of a connected BLE keyboard, or None."""
    if not is_supported():
        return None
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_NAME_SCRIPT],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    # The script prints one FriendlyName per connected matching node (usually
    # exactly one, e.g. "Keychron K10 HE"); take the first non-empty line.
    for line in (proc.stdout or "").splitlines():
        name = line.strip()
        if name:
            return name
    return None
