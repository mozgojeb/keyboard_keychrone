"""Main multi-tab Keyboard Companion window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import APP_NAME, __version__, i18n
from .settings_window import build_settings_panel
from .lighting_editor import LightingEditor
from .monitor_panel import MonitorPanel
from .schedule_panel import SchedulePanel
from .theme import apply_theme, MUTED

TAB_IDS = ("device", "lighting", "schedule", "monitor", "firmware", "settings", "about")


def open_main_window(app, initial_tab: str = "settings", *, parent=None):
    root = tk.Toplevel(parent) if parent is not None else tk.Tk()
    apply_theme(root)
    root.title(APP_NAME)
    root.geometry("1180x880")
    root.minsize(1040, 820)
    root.resizable(True, True)
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    notebook = ttk.Notebook(root)
    notebook.grid(row=0, column=0, sticky="nsew")

    device = _build_device_tab(notebook, app)
    lighting = LightingEditor(notebook, app)
    schedule = SchedulePanel(notebook, app)
    monitor = MonitorPanel(notebook, app)
    firmware = _build_firmware_tab(notebook, app)
    settings = build_settings_panel(notebook, app, on_close=root.destroy, title_callback=root.title)
    about = _build_about_tab(notebook)

    tabs = {
        "device": device,
        "lighting": lighting,
        "schedule": schedule,
        "monitor": monitor,
        "firmware": firmware,
        "settings": settings,
        "about": about,
    }
    notebook.add(device, text=i18n.t("main_tab_device"))
    notebook.add(lighting, text=i18n.t("main_tab_lighting"))
    notebook.add(schedule, text="Schedule")
    notebook.add(monitor, text='Monitor')
    notebook.add(firmware, text=i18n.t("main_tab_firmware"))
    notebook.add(settings, text=i18n.t("main_tab_settings"))
    notebook.add(about, text=i18n.t("main_tab_about"))

    if initial_tab in tabs:
        notebook.select(tabs[initial_tab])
    root.select_tab = lambda tab: notebook.select(tabs.get(tab, settings))

    def on_close() -> None:
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.update_idletasks()
    if parent is None:
        root.mainloop()
    return root


def _build_device_tab(parent, app):
    frame = ttk.Frame(parent, padding=16)
    title = ttk.Label(frame, text=i18n.t("device_tab_title"), font=("", 11, "bold"))
    title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

    fields = [
        ("model", "device_field_model"),
        ("battery", "device_field_battery"),
        ("voltage", "device_field_voltage"),
        ("mode", "device_field_mode"),
        ("connection", "device_field_connection"),
        ("source", "device_field_source"),
    ]
    labels = {}
    values = {}
    for row, (key, label_key) in enumerate(fields, start=1):
        lbl = ttk.Label(frame, text=i18n.t(label_key), foreground=MUTED)
        val = ttk.Label(frame, text="--", width=28)
        lbl.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 18))
        val.grid(row=row, column=1, sticky="w", pady=4)
        labels[key] = lbl
        values[key] = val

    note = ttk.Label(
        frame,
        text=i18n.t("device_tab_note"),
        foreground=MUTED,
        wraplength=420,
    )
    note.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def fmt(value) -> str:
        if value is None or value == "":
            return "--"
        return str(value)

    def refresh() -> None:
        reading, pct = app._snapshot()
        if reading is None:
            data = {
                "model": i18n.t("undetected"),
                "battery": "--",
                "voltage": "--",
                "mode": "--",
                "connection": "--",
                "source": "--",
            }
        else:
            with app._lock:
                device_label = app._device_label
            data = {
                "model": device_label or "--",
                "battery": f"{pct}%" if pct is not None else "--",
                "voltage": f"{reading.voltage_mv} mV" if reading.voltage_mv > 0 else "--",
                "mode": (
                    i18n.t(f"charging_{reading.charging_code}")
                    if reading.source != "windows"
                    else "--"
                ),
                "connection": reading.transport_name,
                "source": "Windows BLE mirror" if reading.source == "windows" else "Raw HID",
            }
        for key, val in data.items():
            values[key].config(text=fmt(val))
        try:
            frame.after(1000, refresh)
        except tk.TclError:
            pass

    refresh()
    return frame


def _build_about_tab(parent):
    frame = ttk.Frame(parent, padding=16)
    title = ttk.Label(frame, text=APP_NAME, font=("", 14, "bold"))
    version = ttk.Label(frame, text=i18n.t("about_version", version=__version__))
    body = ttk.Label(
        frame,
        text=i18n.t("about_body"),
        wraplength=420,
        foreground=MUTED,
    )
    title.grid(row=0, column=0, sticky="w")
    version.grid(row=1, column=0, sticky="w", pady=(6, 0))
    body.grid(row=2, column=0, sticky="w", pady=(12, 0))
    return frame


def _build_firmware_tab(parent, app):
    frame = ttk.Frame(parent, padding=16)
    title = ttk.Label(frame, text=i18n.t("firmware_tab_title"), font=("", 11, "bold"))
    body = ttk.Label(
        frame,
        text=i18n.t("firmware_tab_body"),
        wraplength=420,
        foreground=MUTED,
    )
    btn = ttk.Button(
        frame,
        text=i18n.t("firmware_tab_open_wizard"),
        command=lambda: _open_flash_wizard_from_main(frame, app),
    )
    title.grid(row=0, column=0, sticky="w")
    body.grid(row=1, column=0, sticky="w", pady=(8, 12))
    btn.grid(row=2, column=0, sticky="w")
    return frame


def _open_flash_wizard_from_main(frame, app) -> None:
    # Tk on Windows is fragile with multiple Tk roots in different threads.
    # Close the main window before launching the dedicated flash wizard.
    try:
        frame.winfo_toplevel().destroy()
    except tk.TclError:
        pass
    app._open_flash_wizard()
