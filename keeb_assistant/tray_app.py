"""System-tray application wiring reader + smoothing + icon + i18n + config."""

from __future__ import annotations

import faulthandler
import os
import queue
import sys
import threading
import time
import traceback
import uuid
import webbrowser

import pystray
from pystray import Menu, MenuItem

from . import APP_ID, APP_NAME, autostart, battery_log, battery_model, ble_reader, i18n
from . import hid_reader, firmware_flash
from . import lighting_hid
from . import single_instance
from .config import Config
from .hid_reader import BatteryReader, BatteryReading
from .icon import make_icon
from .smoothing import BatterySmoother

STALE_AFTER = 20.0       # seconds without data before the reading is "old"
UI_TICK = 2.0            # seconds between tooltip refreshes
BLE_POLL = 15.0          # seconds between Windows BLE battery polls (when no HID)
TRANSPORT_BLUETOOTH = 2
LAUNCHER_URL = "https://launcher.keychron.com/"
FULL_CONFIRM_SECONDS = 30.0
TRAY_ICON_GUID = uuid.uuid5(uuid.NAMESPACE_DNS, f"{APP_ID}.TrayIcon")
POST_CHARGE_SETTLE_SECONDS = 8.0


class TrayApp:
    def __init__(self, *, start_in_tray: bool = False):
        self.start_in_tray = start_in_tray
        self.config = Config.load()
        effective_autostart = autostart.sync_from_config(
            bool(self.config.get("autostart", False))
        )
        if effective_autostart != bool(self.config.get("autostart", False)):
            self.config["autostart"] = effective_autostart
            self.config.save()
        i18n.set_language(self.config.get("language", i18n.DEFAULT_LANGUAGE))
        self.smoother = BatterySmoother(
            alpha=self.config["smoothing_alpha"],
            deadband=self.config["smoothing_deadband"],
        )

        self._lock = threading.Lock()
        # Serializes icon rendering + tray updates. make_icon() uses PIL/FreeType,
        # which is not thread-safe; _refresh_ui is called from several threads
        # (UI ticker, reader callback, status callback), so concurrent renders
        # would corrupt FreeType state and crash the process.
        self._render_lock = threading.Lock()
        self._latest: BatteryReading | None = None
        self._displayed_pct: int | None = None
        self._connected = False
        self._low_notified = False
        self._last_hid_ts = 0.0  # last time a cable/dongle raw-HID reading arrived
        self._full_candidate_since: float | None = None
        self._last_battery_voltage_mv: int | None = None
        self._post_charge_settle_until: float | None = None
        self._last_icon_key: tuple | None = None
        self._last_title: str | None = None
        # Cached tooltip device name. Resolving it can do HID enumeration or spawn
        # PowerShell, so it is computed only when the transport/model changes, and
        # only on the thread that produced the reading (which already owns the HID
        # devices) — never on the UI ticker, which would race the reader thread's
        # raw-HID I/O and crash the process (concurrent hidapi access on Windows).
        self._device_label: str | None = None
        self._device_label_key: tuple | None = None
        self._stop = threading.Event()
        self._exit_lock = threading.Lock()
        self._exit_requested = False
        self._shutdown_fast = False
        self._window_requests = queue.Queue()
        self._windows = {}

        self.icon = pystray.Icon(
            APP_ID,
            icon=make_icon(None, connected=False),
            title=f"{APP_NAME}\n• {i18n.t('tooltip_waiting')}",
            menu=self._build_menu(),
        )
        self.reader = BatteryReader(
            on_update=self._on_reading,
            on_status=self._on_status,
            pull_interval=float(self.config["pull_interval_sec"]),
        )
        from .lighting_overlay import LightingOverlay
        self.lighting_overlay = LightingOverlay(self.reader)
        self._lighting_lock = threading.Lock()
        from .lighting_schedule import LightingScheduler
        self.lighting_scheduler = LightingScheduler(self)
        from .monitor_shortcuts import MonitorShortcuts
        self.monitor_shortcuts = MonitorShortcuts()
        try:
            self.monitor_shortcuts.configure(self.config.get('monitor_shortcut',{}))
        except Exception as exc:
            self.monitor_shortcuts.status = str(exc)

    # -- menu --------------------------------------------------------------
    def _language_menu(self) -> Menu:
        items = []
        for code, label in i18n.available_languages():
            items.append(
                MenuItem(
                    label,
                    self._make_lang_setter(code),
                    checked=self._make_lang_checker(code),
                    radio=True,
                )
            )
        return Menu(*items)

    def _make_lang_setter(self, code):
        def _set(icon, item):
            self.set_language(code)
        return _set

    def _make_lang_checker(self, code):
        return lambda item: i18n.get_language() == code

    def _build_menu(self) -> Menu:
        # Intentionally no live values here: all battery info lives in the
        # tooltip. A static menu means update_menu() is only called on explicit
        # user actions, so the hover highlight never gets rebuilt mid-hover.
        return Menu(
            MenuItem(lambda item: i18n.t("menu_lighting"), self._open_lighting_tab),
            MenuItem(lambda item: i18n.t("menu_settings"), self._open_settings),
            MenuItem(lambda item: i18n.t("menu_open_launcher"), self._open_launcher),
            MenuItem(lambda item: i18n.t("menu_language"), self._language_menu()),
            MenuItem(
                lambda item: i18n.t("menu_autostart"),
                self._toggle_autostart,
                checked=lambda item: autostart.is_enabled(),
            ),
            MenuItem(
                lambda item: i18n.t("menu_notify"),
                self._toggle_notify,
                checked=lambda item: bool(self.config["notify_low_battery"]),
            ),
            MenuItem(lambda item: i18n.t("menu_flash_firmware"), self._open_firmware_tab),
            Menu.SEPARATOR,
            MenuItem(lambda item: i18n.t("menu_quit"), self._quit),
        )

    def _snapshot(self):
        """Return (reading, pct) only if data is present AND fresh, else (None, None).

        Stale data (no updates for STALE_AFTER, e.g. keyboard moved to a transport
        the app can't read like Bluetooth) is reported as 'Undetected', never as the
        last known value.
        """
        with self._lock:
            reading = self._latest
            pct = self._displayed_pct
            connected = self._connected
        if reading is None or not connected:
            return None, None
        if (time.time() - reading.timestamp) >= STALE_AFTER:
            return None, None
        return reading, pct

    def _tooltip_text(self) -> str:
        """Multi-line tray tooltip: app name + one bullet per field."""
        reading, pct = self._snapshot()
        if reading is None:
            return f"{APP_NAME}\n• {i18n.t('undetected')}"
        # Bullet layout, with the transport always in the same (last) slot:
        #   • <device name> (when known)
        #   • <pct>%
        #   • <charging>   (only when known — not available over the BLE mirror)
        #   • <transport>  ("Bluetooth" / "2.4 GHz" / "USB")
        # The device name is resolved elsewhere (cached) so this hot path, which
        # also runs on the UI ticker thread, never touches HID or spawns a process.
        with self._lock:
            device_label = self._device_label
        lines = [APP_NAME]
        if device_label:
            lines.append(f"• {i18n.t('tooltip_device_line', device=device_label)}")
        lines.append(f"• {pct}%")
        if reading.source != "windows":
            lines.append(f"• {reading.voltage_mv} mV")
            lines.append(f"• {i18n.t(f'charging_{reading.charging_code}')}")
        lines.append(f"• {reading.transport_name}")
        return "\n".join(lines)

    def _compute_device_label(self, reading: BatteryReading) -> str | None:
        """Resolve the connected keyboard's display name.

        May enumerate HID (cable/dongle) or spawn PowerShell (BLE name), so it is
        only ever called from the thread that produced the reading — the reader
        thread for HID, the BLE poller thread for Windows — never the UI ticker.
        """
        try:
            if reading.source == "windows":
                return ble_reader.read_bluetooth_device_name()
            model_name = hid_reader.MODEL_NAMES.get(getattr(reading, "model_id", 0) or 0)
            if model_name:
                return model_name
            if reading.transport == firmware_flash.TRANSPORT_USB:
                # Enumeration-only (no device open) → safe on the reader thread.
                return firmware_flash.cable_model_label()
            return hid_reader.best_device_label()
        except Exception:
            return None

    def _update_device_label(self, reading: BatteryReading) -> None:
        """Refresh the cached tooltip device name when the transport/model changes."""
        key = (reading.source, reading.transport, getattr(reading, "model_id", 0))
        with self._lock:
            if key == self._device_label_key:
                return
        label = self._compute_device_label(reading)
        with self._lock:
            self._device_label = label
            self._device_label_key = key

    # -- reader callbacks --------------------------------------------------
    def _on_status(self, connected: bool) -> None:
        if self._stop.is_set():
            return
        with self._lock:
            self._connected = connected
            if not connected:
                self.smoother.reset()
                self._displayed_pct = None
                self._full_candidate_since = None
                self._post_charge_settle_until = None
                # Force a re-resolve of the device name on the next reading.
                self._device_label_key = None
        self._refresh_ui()

    def _on_reading(self, reading: BatteryReading) -> None:
        if self._stop.is_set():
            return
        with self._lock:
            prev = self._latest
        # Switching source (HID cable/dongle <-> Windows BLE) can be a jump; start
        # the smoother fresh so we don't blend two different estimates.
        if prev is not None and prev.source != reading.source:
            self.smoother.reset()
            self._full_candidate_since = None
            self._last_battery_voltage_mv = None
            self._post_charge_settle_until = None
        if (
            prev is not None
            and prev.charging_code == battery_model.CHARGING_ACTIVE
            and reading.charging_code == battery_model.CHARGING_NONE
        ):
            self._post_charge_settle_until = reading.timestamp + POST_CHARGE_SETTLE_SECONDS
        # Charging compensation is applied to the value we *display* only; the
        # raw voltage/percentage are still logged below as ground truth.
        correction_enabled = bool(self.config.get("charge_correction", True))
        if reading.charging_code == battery_model.CHARGING_ACTIVE:
            correction_enabled = correction_enabled and battery_model.charging_voltage_is_inflated(
                reading.voltage_mv,
                self._last_battery_voltage_mv,
            )
        corrected = battery_model.corrected_percentage(
            reading.voltage_mv,
            reading.percentage,
            reading.charging_code,
            enabled=correction_enabled,
            offset_mv=int(self.config.get("charge_offset_mv", battery_model.DEFAULT_CHARGE_OFFSET_MV)),
        )
        post_charge_inflated = (
            reading.charging_code == battery_model.CHARGING_NONE
            and self._post_charge_settle_until is not None
            and reading.timestamp <= self._post_charge_settle_until
            and reading.voltage_mv >= battery_model.FULL_VOLTAGE_MV
            and reading.percentage >= battery_model.FULL_GUARD_MIN_RAW_PCT
        )
        if post_charge_inflated and self._displayed_pct is not None:
            corrected = self._displayed_pct
        if battery_model.is_full_charge_candidate(
            reading.voltage_mv,
            reading.percentage,
            reading.charging_code,
        ):
            if self._full_candidate_since is None:
                self._full_candidate_since = reading.timestamp
            if reading.timestamp - self._full_candidate_since >= FULL_CONFIRM_SECONDS:
                corrected = 100
        else:
            self._full_candidate_since = None
        smoothing_charging = (
            reading.charging_code == battery_model.CHARGING_ACTIVE
            or (corrected >= 100 and not post_charge_inflated)
        )
        displayed = self.smoother.update(corrected, charging=smoothing_charging)
        if (
            reading.charging_code == battery_model.CHARGING_NONE
            and reading.voltage_mv > 0
            and not post_charge_inflated
        ):
            self._last_battery_voltage_mv = reading.voltage_mv
        with self._lock:
            self._latest = reading
            self._displayed_pct = displayed
            self._connected = True
            if reading.source == "hid":
                self._last_hid_ts = reading.timestamp
        # Runs on the producing thread (reader for HID, BLE poller for windows),
        # and only does real work when the transport/model actually changes.
        if not self._shutdown_fast:
            self._update_device_label(reading)
        if self.config.get("battery_logging") and not self._shutdown_fast:
            battery_log.append(
                source=reading.source,
                transport=reading.transport_name,
                charging=reading.charging_code,
                voltage_mv=reading.voltage_mv,
                raw_pct=reading.percentage,
                displayed_pct=displayed,
                ema=self.smoother.ema,
            )
        if self._stop.is_set():
            return
        self._check_low_battery(displayed, reading.is_charging)
        self._refresh_ui()

    def _ble_poller(self) -> None:
        """When no cable/dongle HID data is flowing, mirror Windows' BLE battery."""
        if not ble_reader.is_supported():
            return
        # Small initial delay so HID (cable/dongle) gets first chance.
        if self._stop.wait(3.0):
            return
        while not self._stop.is_set():
            hid_active = (time.time() - self._last_hid_ts) < STALE_AFTER
            if not hid_active:
                pct = ble_reader.read_bluetooth_battery()
                if pct is not None:
                    self._on_reading(
                        BatteryReading(
                            percentage=pct,
                            voltage_mv=0,
                            charging=0,
                            transport=TRANSPORT_BLUETOOTH,
                            timestamp=time.time(),
                            source="windows",
                        )
                    )
            if self._stop.wait(BLE_POLL):
                break

    # -- ui ----------------------------------------------------------------
    def _refresh_ui(self) -> None:
        if self._stop.is_set() and self._shutdown_fast:
            return
        # Serialize the whole render: make_icon (PIL/FreeType) and the tray update
        # must never run on two threads at once.
        with self._render_lock:
            self._refresh_ui_locked()

    def _refresh_ui_locked(self) -> None:
        reading, pct = self._snapshot()
        if reading is None:
            # Stale/absent -> Undetected. Drop the smoother so a later reconnect
            # (possibly on another transport with a different level) starts clean.
            with self._lock:
                if self._displayed_pct is not None:
                    self.smoother.reset()
                    self._displayed_pct = None
            icon_key = (None, False, False)
        else:
            icon_key = (pct, reading.is_charging, True)
        title = self._tooltip_text()

        # On Windows, assigning icon.icon makes pystray serialize the PIL image
        # into an ICO through native encoders. Doing that every UI tick caused
        # rare native crashes, so only touch the icon when the rendered state
        # actually changed. The title is also skipped when identical.
        try:
            if icon_key != self._last_icon_key:
                self.icon.icon = make_icon(icon_key[0], charging=icon_key[1], connected=icon_key[2])
                self._last_icon_key = icon_key
            if title != self._last_title:
                self.icon.title = title
                self._last_title = title
        except Exception:
            pass

    def _check_low_battery(self, pct: int | None, charging: bool) -> None:
        if pct is None or not self.config["notify_low_battery"]:
            return
        threshold = int(self.config["low_battery_threshold"])
        if charging or pct > threshold + 5:
            self._low_notified = False
            return
        if pct <= threshold and not self._low_notified:
            self._low_notified = True
            try:
                self.icon.notify(
                    i18n.t("notify_low_body", pct=pct),
                    i18n.t("notify_low_title"),
                )
            except Exception:
                pass

    def _ui_ticker(self) -> None:
        while not self._stop.wait(UI_TICK):
            self._refresh_ui()

    # -- settings integration ---------------------------------------------
    def set_language(self, code: str) -> None:
        i18n.set_language(code)
        self.config["language"] = i18n.get_language()
        self.config.save()
        self._refresh_ui()
        self._force_menu_update()  # relabel all menu items in the new language

    def apply_settings(self) -> None:
        """Re-read config values that affect runtime behavior (from the window)."""
        i18n.set_language(self.config.get("language", i18n.DEFAULT_LANGUAGE))
        self.smoother.alpha = max(0.01, min(1.0, float(self.config["smoothing_alpha"])))
        self.smoother.deadband = max(0.0, float(self.config["smoothing_deadband"]))
        self.config.save()
        self._refresh_ui()

    def apply_lighting_profile(self, profile: dict) -> int:
        """Write one lighting profile through the reader-owned HID connection."""
        with self._lighting_lock:
            self.lighting_overlay.stop()
            count = lighting_hid.apply_profile(self.reader, profile)
            if not self._stop.is_set() and profile.get('keypress_effect', 'None') != 'None':
                self.lighting_overlay.start(profile)
            return count

    def turn_lighting_off(self) -> None:
        """Disable backlight while preserving saved per-key colours."""
        with self._lighting_lock:
            self.lighting_overlay.stop()
            lighting_hid.set_brightness(self.reader, 0)

    def _open_main_window(self, initial_tab: str = "settings") -> None:
        if not self._stop.is_set():
            self._window_requests.put(("main", initial_tab))

    def _open_settings(self, icon=None, item=None) -> None:
        self._open_main_window("settings")

    def _open_lighting_tab(self, icon=None, item=None) -> None:
        self._open_main_window("lighting")

    def _open_firmware_tab(self, icon=None, item=None) -> None:
        self._open_main_window("firmware")

    def _open_flash_wizard(self, icon=None, item=None) -> None:
        if not self._stop.is_set():
            self._window_requests.put(("flash", None))

    def _drain_window_requests(self) -> None:
        """Create and dispose every Tk window on the process main thread."""
        if self._stop.is_set():
            self._tk_root.quit()
            return
        while not self._window_requests.empty():
            kind, tab = self._window_requests.get_nowait()
            try:
                window = self._windows.get(kind)
                if window is None or not window.winfo_exists():
                    if kind == "main":
                        from .main_window import open_main_window
                        window = open_main_window(self, initial_tab=tab, parent=self._tk_root)
                    else:
                        from .flash_window import open_flash_wizard
                        window = open_flash_wizard(self, parent=self._tk_root)
                    self._windows[kind] = window
                elif kind == "main":
                    window.select_tab(tab)
                window.deiconify()
                window.lift()
                window.focus_force()
            except Exception:
                sys.excepthook(*sys.exc_info())
        self._tk_root.after(100, self._drain_window_requests)

    # -- menu actions ------------------------------------------------------
    def _toggle_autostart(self, icon, item) -> None:
        result = autostart.set_enabled(not autostart.is_enabled())
        self.config["autostart"] = result
        self.config.save()
        self._force_menu_update()

    def _toggle_notify(self, icon, item) -> None:
        self.config["notify_low_battery"] = not self.config["notify_low_battery"]
        self.config.save()
        self._force_menu_update()

    def _force_menu_update(self) -> None:
        """Rebuild the menu now (used after a click closes it, so no hover issue)."""
        try:
            self.icon.update_menu()
        except Exception:
            pass

    def _open_launcher(self, icon=None, item=None) -> None:
        if self._stop.is_set():
            return
        try:
            webbrowser.open(LAUNCHER_URL)
        except Exception:
            pass

    def _quit(self, icon, item) -> None:
        self.request_exit(reason="user", icon=icon)

    def request_exit(self, *, reason: str, fast: bool = False, icon=None) -> None:
        with self._exit_lock:
            if self._exit_requested:
                return
            self._exit_requested = True
            self._shutdown_fast = bool(fast)
        self._shutdown_log(f"exit requested: {reason} fast={fast}")
        self._stop.set()
        try:
            self.monitor_shortcuts.stop()
        except Exception:
            pass
        try:
            self.lighting_scheduler.stop()
        except Exception:
            pass
        try:
            if fast:
                self.lighting_overlay.stopped.set()
            else:
                self.lighting_overlay.stop()
        except Exception:
            pass
        try:
            self.reader.stop()
        except Exception:
            pass
        if fast:
            self._force_process_exit_later(1.5)
        try:
            (icon or self.icon).stop()
        except Exception as exc:
            self._shutdown_log(f"tray stop failed: {exc!r}")

    def _force_process_exit_later(self, delay_sec: float) -> None:
        def _exit_after_delay() -> None:
            time.sleep(delay_sec)
            self._shutdown_log("forcing process exit after shutdown grace period")
            try:
                if sys.platform.startswith("win"):
                    import ctypes

                    ctypes.windll.kernel32.ExitProcess(0)
                os._exit(0)
            except Exception:
                os._exit(0)

        threading.Thread(target=_exit_after_delay, daemon=True, name="ShutdownExit").start()

    def _shutdown_log(self, message: str) -> None:
        try:
            from .config import config_dir

            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            path = config_dir() / "shutdown_log.txt"
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(f"[{stamp}] {message}\n")
        except Exception:
            pass

    # -- lifecycle ---------------------------------------------------------
    def _install_windows_session_handlers(self) -> None:
        if not sys.platform.startswith("win"):
            return
        try:
            WM_QUERYENDSESSION = 0x0011
            WM_ENDSESSION = 0x0016

            def _on_query_end_session(wparam, lparam):
                self._shutdown_log("shutdown requested: WM_QUERYENDSESSION")
                return 1

            def _on_end_session(wparam, lparam):
                self._shutdown_log(f"shutdown confirmed: WM_ENDSESSION wParam={wparam}")
                if int(wparam):
                    threading.Thread(
                        target=lambda: self.request_exit(
                            reason="windows_shutdown", fast=True, icon=self.icon
                        ),
                        daemon=True,
                        name="WindowsShutdown",
                    ).start()
                return 0

            self.icon._message_handlers[WM_QUERYENDSESSION] = _on_query_end_session
            self.icon._message_handlers[WM_ENDSESSION] = _on_end_session
        except Exception as exc:
            self._shutdown_log(f"failed to install shutdown handlers: {exc!r}")

    def _install_doubleclick_handler(self) -> None:
        """Open Settings on a tray double-click.

        pystray's cross-platform API only exposes a single 'default' action, but
        on Windows the shell still delivers WM_LBUTTONDBLCLK to the icon's
        callback. We hook the win32 backend's notify dispatch to catch it and
        leave single-click unbound. No-op (and harmless) on other platforms or
        if pystray internals ever change.
        """
        if not sys.platform.startswith("win"):
            return
        try:
            from pystray._util import win32 as _w32

            WM_LBUTTONDBLCLK = 0x0203
            base = self.icon._on_notify

            def _on_notify(wparam, lparam):
                if lparam == WM_LBUTTONDBLCLK:
                    self._open_main_window("device")
                    return None
                return base(wparam, lparam)

            self.icon._message_handlers[_w32.WM_NOTIFY] = _on_notify
        except Exception:
            pass

    def _setup(self, icon) -> None:
        icon.visible = True
        self._install_doubleclick_handler()
        self._install_windows_session_handlers()
        self.reader.start()
        self.lighting_scheduler.start()
        threading.Thread(target=self._ui_ticker, daemon=True, name="UiTicker").start()
        threading.Thread(target=self._ble_poller, daemon=True, name="BlePoller").start()
        # A normal double-click on the exe should reveal the app, not only leave
        # a resident tray icon behind. The tray still remains the always-on agent.
        if not self.start_in_tray:
            self._open_main_window('monitor' if '--monitor' in sys.argv else 'lighting')

    def run(self) -> None:
        import tkinter as tk

        self._tk_root = tk.Tk()
        self._tk_root.withdraw()
        self._tk_root.report_callback_exception = sys.excepthook
        try:
            self.icon.run_detached(setup=self._setup)
            self._tk_root.after(100, self._drain_window_requests)
            self._tk_root.mainloop()
        finally:
            self.request_exit(reason="ui_closed")
            self._windows.clear()
            self._tk_root.destroy()


def _set_app_user_model_id() -> None:
    """Give the process a stable identity so Windows tracks the tray icon
    consistently (name + the 'always show' setting)."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{APP_ID}.Tray"
        )
    except Exception:
        pass


def _patch_pystray_stable_icon_guid() -> None:
    """Make Windows track this tray icon by a stable GUID, not by exe path.

    Windows' "Other system tray icons" list can create a fresh entry whenever a
    PyInstaller build is launched from a new folder/path. pystray's Win32 backend
    identifies icons with a runtime uID, so we add NIF_GUID to every
    Shell_NotifyIcon call. The GUID is deterministic from APP_ID and stable
    across builds.
    """
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        import pystray._win32 as pystray_win32
        from pystray._util import win32

        if getattr(pystray_win32.Icon, "_keyboard_companion_guid_patch", False):
            return

        guid = win32.NOTIFYICONDATAW.GUID()
        raw = TRAY_ICON_GUID.bytes_le
        guid.Data1 = int.from_bytes(raw[0:4], "little")
        guid.Data2 = int.from_bytes(raw[4:6], "little")
        guid.Data3 = int.from_bytes(raw[6:8], "little")
        guid.Data4[:] = raw[8:16]

        def _message(self, code, flags, **kwargs):
            win32.Shell_NotifyIcon(code, win32.NOTIFYICONDATAW(
                cbSize=ctypes.sizeof(win32.NOTIFYICONDATAW),
                hWnd=self._hwnd,
                uID=id(self),
                uFlags=flags | win32.NIF_GUID,
                guidItem=guid,
                **kwargs))

        pystray_win32.Icon._message = _message
        pystray_win32.Icon._keyboard_companion_guid_patch = True
    except Exception:
        # A failed patch must not prevent the tray from starting; AppUserModelID
        # still provides the best available fallback.
        pass


def _install_crash_logging() -> None:
    """Persist uncaught Python exceptions AND native faults to a consultable log.

    Writes to %APPDATA%\\KeyboardCompanion\\error_log.txt. faulthandler also
    catches hard crashes (e.g. an access violation from native HID code), which
    otherwise kill the tray with no trace, by dumping the Python stack at the
    point of the fault.
    """
    try:
        from .config import config_dir

        log_path = config_dir() / "error_log.txt"
        fh = open(log_path, "a", buffering=1, encoding="utf-8")  # noqa: SIM115
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        fh.write(f"\n=== session start {stamp} pid {os.getpid()} ===\n")
        faulthandler.enable(file=fh)

        def _excepthook(exc_type, exc, tb):
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f"[{ts}] uncaught {exc_type.__name__}: {exc}\n")
            traceback.print_exception(exc_type, exc, tb, file=fh)

        sys.excepthook = _excepthook

        def _thread_excepthook(args):
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            fh.write(f"[{ts}] uncaught in thread {args.thread.name}: {args.exc_value}\n")
            traceback.print_exception(
                args.exc_type, args.exc_value, args.exc_traceback, file=fh
            )

        threading.excepthook = _thread_excepthook
    except Exception:
        # Logging must never prevent the app from starting.
        pass


def _should_start_in_tray() -> bool:
    tray_args = {"--start-in-tray", "--tray", "--minimized"}
    return any(arg in tray_args for arg in sys.argv[1:])


def main() -> None:
    if not single_instance.try_acquire():
        sys.exit(0)
    _install_crash_logging()
    _set_app_user_model_id()
    _patch_pystray_stable_icon_guid()
    TrayApp(start_in_tray=_should_start_in_tray()).run()


if __name__ == "__main__":
    main()
