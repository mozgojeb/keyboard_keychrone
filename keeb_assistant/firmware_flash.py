"""Firmware flash helpers (Windows): cable detection, dfu-util, STM32 DFU."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

try:
    import hid  # type: ignore
except ImportError:
    hid = None

from .config import config_dir
from .hid_reader import (
    KC_GET_BATTERY,
    KC_GET_FIRMWARE_VERSION,
    RAW_USAGE,
    RAW_USAGE_PAGE,
    REPORT_SIZE,
    VENDOR_ID,
    _parse_report,
)

FlashProgressCallback = Callable[[str, str | None, int | None], None]

@dataclass(frozen=True)
class CableKeyboard:
    model: str
    layout: str


# Supported Keychron HE direct USB (Cable) PIDs, not the 2.4 GHz dongle (0xD030).
# These IDs must match the keyboard.json for each layout in the flashed firmware.
# This is whatever the *flashed firmware* advertises, not read from the keycaps.
CABLE_KEYBOARDS: dict[int, CableKeyboard] = {
    0x0EA0: CableKeyboard("Keychron K10 HE", "ANSI"),
    0x0EA1: CableKeyboard("Keychron K10 HE", "ISO"),
    0x0B10: CableKeyboard("Keychron Q1 HE", "ANSI Knob"),
    0x0B11: CableKeyboard("Keychron Q1 HE", "ISO Knob"),
    0x0B12: CableKeyboard("Keychron Q1 HE", "JIS Knob"),
}
CABLE_KEYBOARD_PIDS = frozenset(CABLE_KEYBOARDS)
TRANSPORT_USB = 1

DFU_USB_ID = "0483:df11"
DFU_ALT = "0"
DFU_ADDRESS = "0x08000000:leave"

QMK_TOOLBOX_RELEASES_URL = "https://github.com/qmk/qmk_toolbox/releases"
QMK_FLASHING_DOCS_URL = "https://docs.qmk.fm/#/newbs_flashing"

_DFU_UTIL_CANDIDATES = (
    # PyInstaller onedir places bundled binaries under sys._MEIPASS.
    Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "dfu-util.exe",
    # Source checkout fallback.
    Path(__file__).resolve().parent.parent / "vendor" / "qmk_flashutils" / "dfu-util.exe",
    Path(r"C:\QMK_MSYS\opt\qmk\bin\dfu-util.exe"),
    Path(r"C:\QMK_MSYS\usr\bin\dfu-util.exe"),
)


def _flash_log_path() -> Path:
    """Location for dfu-util debug logs."""
    return config_dir() / "flash_log.txt"


def _append_flash_log(message: str) -> None:
    """Best-effort append to the flash debug log."""
    try:
        path = _flash_log_path()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"[{timestamp}] {message}\n")
    except OSError:
        # Logging must never break flashing.
        pass


def find_dfu_util() -> Path | None:
    """Return path to dfu-util if available."""
    found = shutil.which("dfu-util")
    if found:
        return Path(found)
    for candidate in _DFU_UTIL_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _hid_entries() -> list[dict]:
    if hid is None:
        return []
    try:
        return list(hid.enumerate(VENDOR_ID, 0))
    except Exception:
        return []


def cable_hid_paths() -> list[bytes]:
    """Open paths for Keychron raw HID on the keyboard's USB cable interface."""
    paths: list[bytes] = []
    for info in _hid_entries():
        if info.get("usage_page") != RAW_USAGE_PAGE or info.get("usage") != RAW_USAGE:
            continue
        if info.get("product_id") not in CABLE_KEYBOARD_PIDS:
            continue
        path = info.get("path")
        if path:
            paths.append(path)
    return paths


def is_cable_keyboard_connected(*, verify_transport: bool = True) -> bool:
    """True when a supported Keychron HE is on USB Cable (keyboard PID, not dongle)."""
    paths = cable_hid_paths()
    if not paths:
        return False
    if not verify_transport:
        return True
    return _verify_usb_transport(paths[0])


def _normalize_response(resp: list[int] | bytes | None, cmd: int) -> bytes | None:
    if not resp:
        return None
    data = bytes(resp)
    if data[0] == cmd:
        return data
    if len(data) > 1 and data[1] == cmd:
        return data[1:]
    return None


def _raw_hid_command(path: bytes, cmd: int, *, timeout_ms: int = 800) -> bytes | None:
    if hid is None:
        return None
    dev = None
    try:
        dev = hid.device()
        dev.open_path(path)
        dev.set_nonblocking(False)
        report = bytes([0x00, cmd] + [0x00] * REPORT_SIZE)
        dev.write(report)
        resp = dev.read(REPORT_SIZE, timeout_ms=timeout_ms)
        return _normalize_response(resp, cmd)
    except OSError:
        return None
    finally:
        if dev is not None:
            try:
                dev.close()
            except OSError:
                pass


def read_firmware_version() -> str | None:
    """Return the keyboard's QMK version string (Cable / raw HID), or None."""
    paths = cable_hid_paths()
    if not paths:
        return None
    resp = _raw_hid_command(paths[0], KC_GET_FIRMWARE_VERSION)
    if not resp or len(resp) < 3:
        return None
    payload = bytes(resp[1:]).split(b"\x00", 1)[0]
    text = payload.decode("ascii", errors="replace").strip()
    if not text or text[0] != "v":
        return None
    return text


def cable_device_info() -> tuple[str | None, str | None, int | None, str | None]:
    """Return (model, usb_layout, pid, firmware version) for a cable-connected keyboard."""
    for info in _hid_entries():
        if info.get("usage_page") != RAW_USAGE_PAGE or info.get("usage") != RAW_USAGE:
            continue
        pid = info.get("product_id")
        if pid not in CABLE_KEYBOARD_PIDS:
            continue
        path = info.get("path")
        keyboard = CABLE_KEYBOARDS.get(pid)
        layout = keyboard.layout if keyboard else None
        model = keyboard.model if keyboard else None
        if model is None:
            product = (info.get("product_string") or "").strip()
            manufacturer = (info.get("manufacturer_string") or "").strip()
            if product and manufacturer:
                model = f"{manufacturer} {product}"
            elif product:
                model = product
            else:
                model = f"Keychron (PID 0x{pid:04X})"
        fw = read_firmware_version() if path else None
        return model, layout, pid, fw
    return None, None, None, None


def cable_model_label() -> str | None:
    """Cable keyboard model name from HID enumeration only (no device open).

    Safe to call from any thread: it never opens the device or does raw-HID I/O,
    so it cannot race with the BatteryReader thread (concurrent hidapi access on
    the same device crashes the process on Windows). Used for the tray tooltip.
    """
    for info in _hid_entries():
        if info.get("usage_page") != RAW_USAGE_PAGE or info.get("usage") != RAW_USAGE:
            continue
        pid = info.get("product_id")
        if pid not in CABLE_KEYBOARD_PIDS:
            continue
        keyboard = CABLE_KEYBOARDS.get(pid)
        if keyboard:
            return keyboard.model
        product = (info.get("product_string") or "").strip()
        manufacturer = (info.get("manufacturer_string") or "").strip()
        if product and manufacturer:
            return f"{manufacturer} {product}"
        if product:
            return product
        return f"Keychron (PID 0x{pid:04X})"
    return None


def _verify_usb_transport(path: bytes) -> bool:
    """Send KC_GET_BATTERY once; require transport byte USB (proof of Cable mode)."""
    if hid is None:
        return True
    dev = None
    try:
        dev = hid.device()
        dev.open_path(path)
        dev.set_nonblocking(False)
        report = bytes([0x00, KC_GET_BATTERY] + [0x00] * REPORT_SIZE)
        dev.write(report)
        resp = dev.read(REPORT_SIZE, timeout_ms=800)
        reading = _parse_report(resp)
        return reading is not None and reading.transport == TRANSPORT_USB
    except OSError:
        return False
    finally:
        if dev is not None:
            try:
                dev.close()
            except OSError:
                pass


def dfu_util_list_text() -> str:
    exe = find_dfu_util()
    if exe is None:
        return ""
    try:
        proc = subprocess.run(
            [str(exe), "-l"],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_subprocess_no_window(),
        )
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return ""


def is_dfu_bootloader_present() -> bool:
    text = dfu_util_list_text().lower()
    return DFU_USB_ID.lower() in text


def dfu_bootloader_label() -> str | None:
    """Human-readable DFU device name when the STM32 bootloader is visible."""
    if not is_dfu_bootloader_present():
        return None
    text = dfu_util_list_text()
    for line in text.splitlines():
        low = line.lower()
        if DFU_USB_ID.lower() in low and "dfu" in low:
            return f"STM32 DFU Bootloader ({DFU_USB_ID})"
    return f"STM32 DFU Bootloader ({DFU_USB_ID})"


def connected_device_label() -> str | None:
    """Best-effort label for what USB currently exposes (DFU or keyboard)."""
    dfu = dfu_bootloader_label()
    if dfu:
        return dfu
    # cable_device_info returns (model, layout, pid, firmware_version)
    name, _, _, _ = cable_device_info()
    if name:
        return name
    return None


def check_flash_prerequisites() -> tuple[bool, str]:
    """Return (ready, reason_code) before showing the file picker.

    reason_code is an i18n key suffix ``flash_err_*`` or empty when ready.
    """
    if sys.platform != "win32":
        return False, "platform"
    if hid is None:
        return False, "hidapi"
    if find_dfu_util() is None:
        return False, "dfu_util"
    listing = dfu_util_list_text()
    if not listing:
        return False, "dfu_list"
    low = listing.lower()
    if "cannot open usb device" in low or "no dfu capable" in low:
        # dfu-util runs but USB stack / driver may be wrong (still allow retry at flash time).
        pass
    return True, ""


_DFU_PERCENT_RE = re.compile(r"(\d+)\s*%")


def _parse_dfu_progress_line(line: str) -> tuple[int | None, str | None]:
    """Extract percent and a short detail snippet from a dfu-util status line."""
    pct_match = _DFU_PERCENT_RE.search(line)
    pct = int(pct_match.group(1)) if pct_match else None
    if pct is not None and (pct < 0 or pct > 100):
        pct = None
    detail = line.strip() if line.strip() else None
    return pct, detail


def flash_firmware(
    bin_path: Path,
    *,
    timeout_bootloader: float = 180.0,
    on_progress: FlashProgressCallback | None = None,
    should_abort: Callable[[], bool] | None = None,
) -> tuple[bool, str]:
    """Wait for STM32 DFU, then flash. Returns (success, message_code)."""
    exe = find_dfu_util()
    if exe is None:
        return False, "dfu_util"
    if not bin_path.is_file():
        return False, "missing_file"

    def report(phase: str, detail: str | None = None, percent: int | None = None) -> None:
        if on_progress is not None:
            on_progress(phase, detail, percent)

    _append_flash_log(f"Starting flash: bin={bin_path}")

    report("wait_bootloader")
    deadline = time.monotonic() + timeout_bootloader
    while time.monotonic() < deadline:
        if should_abort and should_abort():
            return False, "cancelled"
        if is_dfu_bootloader_present():
            break
        time.sleep(0.5)
    else:
        _append_flash_log("Bootloader timeout waiting for DFU device")
        return False, "bootloader_timeout"

    report("bootloader_found")
    cmd = [
        str(exe),
        "-a",
        DFU_ALT,
        "-d",
        DFU_USB_ID,
        "-s",
        DFU_ADDRESS,
        "-D",
        str(bin_path),
    ]
    flags = _subprocess_no_window()
    _append_flash_log(f"DFU command: {' '.join(cmd)}")
    report("writing", None, 0)
    try:
        # Stream dfu-util output so progress can be updated while it runs,
        # instead of parsing everything only after the process exits.
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=flags,
        )
    except OSError as exc:
        _append_flash_log(f"dfu-util spawn failed: {exc!r}")
        return False, "flash_failed"

    combined_lines: list[str] = []
    last_pct = 0
    try:
        assert proc.stdout is not None
        for raw_line in proc.stdout:
            combined_lines.append(raw_line)
            # dfu-util often uses carriage returns for progress; normalise.
            for line in raw_line.replace("\r", "\n").splitlines():
                if not line:
                    continue
                _append_flash_log(f"  {line}")
                pct, detail = _parse_dfu_progress_line(line)
                if pct is not None and pct != last_pct:
                    last_pct = pct
                    _append_flash_log(f"parsed progress: pct={pct}, detail={detail!r}")
                    report("writing", detail, pct)
        proc.wait(timeout=180)
    except subprocess.TimeoutExpired:
        _append_flash_log("dfu-util timeout while flashing")
        try:
            proc.kill()
        except OSError:
            pass
        return False, "flash_failed"

    combined = "".join(combined_lines)
    _append_flash_log(f"dfu-util returncode={proc.returncode}")

    if proc.returncode != 0:
        err = combined.strip()
        if "cannot open" in err.lower() or "permission" in err.lower():
            _append_flash_log("Classifying error as 'driver'")
            return False, "driver"
        _append_flash_log("Classifying error as 'flash_failed'")
        return False, "flash_failed"
    report("done", None, 100)
    _append_flash_log("Flash completed successfully")
    return True, ""


def _subprocess_no_window() -> int:
    if sys.platform != "win32":
        return 0
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)
