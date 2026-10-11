"""Keyboard Companion's custom EmblemaShot-style application window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import APP_NAME, __version__, i18n
from .settings_window import build_settings_panel
from .lighting_editor import LightingEditor
from .monitor_panel import MonitorPanel
from .schedule_panel import SchedulePanel
from .theme import BG, CYAN, HEADER, LINE, MUTED, NAV, PANEL, SELECTED, TEXT
from .theme import ThemeButton, apply_theme, round_window

TAB_IDS = ("device", "lighting", "settings", "firmware", "widget",
           "schedule", "monitor", "about")


def open_main_window(app, initial_tab: str = "settings", *, parent=None):
    root = tk.Toplevel(parent) if parent is not None else tk.Tk()
    apply_theme(root)
    root.title(APP_NAME)
    width = min(1460, max(900, root.winfo_screenwidth() - 100))
    height = min(1040, max(720, root.winfo_screenheight() - 100))
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.overrideredirect(True)
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    border = tk.Frame(root, bg=BG, highlightbackground="#798491", highlightthickness=1)
    border.pack(fill="both", expand=True)
    header = tk.Frame(border, bg=HEADER, height=54)
    header.pack(fill="x")
    header.pack_propagate(False)
    mark = tk.Label(header, text="K", bg=SELECTED, fg=CYAN,
                    font=("Segoe UI", 17, "bold"), width=3)
    mark.pack(side="left", padx=(18, 10), pady=8)
    title = tk.Label(header, text=APP_NAME, bg=HEADER, fg=TEXT,
                     font=("Segoe UI", 12, "bold"))
    title.pack(side="left")
    close = tk.Button(header, text="×", bg=HEADER, fg=TEXT,
                      activebackground="#542b35", activeforeground=TEXT,
                      font=("Segoe UI", 18), bd=0, highlightthickness=0,
                      width=3, command=root.destroy)
    close.pack(side="right", fill="y")
    maximize = tk.Button(header, text="□", bg=HEADER, fg=MUTED,
                         activebackground=PANEL, activeforeground=TEXT,
                         font=("Segoe UI", 14), bd=0, highlightthickness=0, width=3)
    maximize.pack(side="right", fill="y")
    minimize = tk.Button(header, text="−", bg=HEADER, fg=MUTED,
                         activebackground=PANEL, activeforeground=TEXT,
                         font=("Segoe UI", 16), bd=0, highlightthickness=0, width=3)
    minimize.pack(side="right", fill="y")
    version = tk.Label(header, text=f"v{__version__} · EmblemaShot theme", bg=HEADER, fg=MUTED,
                       font=("Segoe UI", 9))
    version.pack(side="right", padx=15)

    navigation = tk.Frame(border, bg=NAV, height=60)
    navigation.pack(fill="x")
    navigation.pack_propagate(False)
    nav_items = tk.Frame(navigation, bg=NAV)
    nav_items.pack(side="left", padx=12, pady=(9, 0))
    tk.Frame(border, bg=LINE, height=1).pack(fill="x")
    content = tk.Frame(border, bg=BG)
    content.pack(fill="both", expand=True, padx=23, pady=20)
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(0, weight=1)

    device = _build_device_tab(content, app)
    lighting = LightingEditor(content, app)
    schedule = SchedulePanel(content, app)
    monitor = MonitorPanel(content, app)
    firmware = _build_firmware_tab(content, app)
    settings = build_settings_panel(content, app, on_close=root.destroy, title_callback=root.title)
    widget = _build_widget_tab(content, app)
    about = _build_about_tab(content)

    tabs = {
        "device": device,
        "lighting": lighting,
        "settings": settings,
        "firmware": firmware,
        "widget": widget,
        "schedule": schedule,
        "monitor": monitor,
        "about": about,
    }
    labels = {
        "device": i18n.t("main_tab_device"), "lighting": i18n.t("main_tab_lighting"),
        "settings": i18n.t("main_tab_settings"), "firmware": i18n.t("main_tab_firmware"),
        "widget": "Battery widget", "schedule": "Schedule", "monitor": "Monitor",
        "about": i18n.t("main_tab_about"),
    }
    buttons = {}
    for key, label in labels.items():
        button = ThemeButton(nav_items, label, lambda k=key: select_tab(k),
                             variant="nav", width=max(105, len(label) * 10 + 31), height=44)
        button.pack(side="left", padx=2)
        buttons[key] = button
    for panel in tabs.values():
        panel.grid(row=0, column=0, sticky="nsew")

    def select_tab(key):
        key = key if key in tabs else "settings"
        tabs[key].tkraise()
        for name, button in buttons.items():
            button.set_selected(name == key)
        root.active_tab = key

    root.select_tab = select_tab
    select_tab(initial_tab)

    drag = {}
    def drag_start(event):
        if getattr(root, "maximized", False):
            return
        drag["x"] = event.x_root - root.winfo_x()
        drag["y"] = event.y_root - root.winfo_y()

    def drag_move(event):
        if "x" in drag and not getattr(root, "maximized", False):
            root.geometry(f"+{event.x_root - drag['x']}+{event.y_root - drag['y']}")

    for surface in (header, mark, title, version):
        surface.bind("<ButtonPress-1>", drag_start)
        surface.bind("<B1-Motion>", drag_move)

    def minimize_window():
        root.overrideredirect(False)
        root.iconify()

    def restore_from_minimize(event):
        if event.widget is not root:
            return
        if root.state() == "normal":
            root.overrideredirect(True)
            root.after_idle(lambda: round_window(root))

    def toggle_maximize():
        if getattr(root, "maximized", False):
            root.geometry(root.normal_geometry)
            root.maximized = False
            maximize.configure(text="□")
        else:
            root.normal_geometry = root.geometry()
            work_width = root.winfo_screenwidth()
            work_height = root.winfo_screenheight() - 48
            root.geometry(f"{work_width}x{work_height}+0+0")
            root.maximized = True
            maximize.configure(text="❐")
        root.after_idle(lambda: round_window(root))

    minimize.configure(command=minimize_window)
    maximize.configure(command=toggle_maximize)
    root.bind("<Map>", restore_from_minimize, add="+")
    root.bind("<Alt-F4>", lambda _e: root.destroy())
    root.after_idle(lambda: round_window(root))
    root.update_idletasks()
    if parent is None:
        root.mainloop()
    return root


def _build_device_tab(parent, app):
    frame = tk.Frame(parent, bg=BG)
    frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="cards")
    tk.Label(frame, text="DEVICE STATUS", bg=BG, fg=CYAN,
             font=("Segoe UI", 9, "bold")).grid(
                 row=0, column=0, columnspan=3, sticky="w", pady=(15, 7))
    title = tk.Label(frame, text=i18n.t("device_tab_title"), bg=BG, fg=TEXT,
                     font=("Segoe UI", 23, "bold"))
    title.grid(row=1, column=0, columnspan=3, sticky="w")
    tk.Label(frame, text="Battery and connection information at a glance.",
             bg=BG, fg=MUTED, font=("Segoe UI", 11)).grid(
                 row=2, column=0, columnspan=3, sticky="w", pady=(4, 27))

    cards = {}
    for col, (key, label) in enumerate((
        ("battery", "Battery level"), ("connection", "Connection"),
        ("mode", "Charging"),
    )):
        card = tk.Frame(frame, bg=PANEL, highlightbackground="#344252",
                        highlightthickness=1, height=112)
        card.grid(row=3, column=col, sticky="ew",
                  padx=(0, 13) if col < 2 else 0)
        card.grid_propagate(False)
        tk.Label(card, text=label, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(17, 0))
        value = tk.Label(card, text="--", bg=PANEL,
                         fg=CYAN if key == "battery" else TEXT,
                         font=("Segoe UI", 23, "bold"))
        value.pack(anchor="w", padx=20, pady=(5, 0))
        cards[key] = value

    tk.Label(frame, text="Device details", bg=BG, fg=TEXT,
             font=("Segoe UI", 12, "bold")).grid(
                 row=4, column=0, columnspan=3, sticky="w", pady=(27, 11))
    values = {}
    for index, (key, label_key) in enumerate((
        ("model", "device_field_model"), ("voltage", "device_field_voltage"),
        ("source", "device_field_source"),
    )):
        row = tk.Frame(frame, bg=BG, height=48)
        row.grid(row=5 + index, column=0, columnspan=3, sticky="ew")
        row.grid_propagate(False)
        tk.Label(row, text=i18n.t(label_key), bg=BG, fg=MUTED,
                 font=("Segoe UI", 10)).pack(side="left")
        val = tk.Label(row, text="--", bg=BG, fg=TEXT,
                       font=("Segoe UI", 10))
        val.pack(side="right")
        tk.Frame(frame, bg=LINE, height=1).grid(
            row=5 + index, column=0, columnspan=3, sticky="sew")
        values[key] = val

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
        title.config(text=fmt(data["model"]) if reading else i18n.t("device_tab_title"))
        for key, val in data.items():
            if key in values:
                values[key].config(text=fmt(val))
            if key in cards:
                cards[key].config(text=fmt(val))
        try:
            frame.after(1000, refresh)
        except tk.TclError:
            pass

    refresh()
    return frame


def _build_widget_tab(parent, app):
    frame = tk.Frame(parent, bg=BG)
    tk.Label(frame, text="DESKTOP WIDGET", bg=BG, fg=CYAN,
             font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(15, 8))
    tk.Label(frame, text="Battery at a glance", bg=BG, fg=TEXT,
             font=("Segoe UI", 23, "bold")).pack(anchor="w")
    tk.Label(frame, text="The desktop widget shares the palette with the app.",
             bg=BG, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w", pady=(4, 28))
    card = tk.Frame(frame, bg=BG, highlightbackground="#798491",
                    highlightthickness=1, width=280, height=145)
    card.pack(anchor="w")
    card.pack_propagate(False)
    tk.Label(card, text="KEYBOARD COMPANION", bg=BG, fg=CYAN,
             font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(15, 4))
    percent = tk.Label(card, text="--", bg=BG, fg=TEXT,
                       font=("Segoe UI", 27, "bold"))
    percent.pack(anchor="w", padx=18)
    status = tk.Label(card, text=i18n.t("undetected"), bg=BG, fg=MUTED,
                      font=("Segoe UI", 9))
    status.pack(anchor="w", padx=18, pady=(2, 0))

    def refresh():
        reading, pct = app._snapshot()
        percent.config(text=f"{pct}%" if pct is not None else "--")
        status.config(text=reading.transport_name if reading else i18n.t("undetected"))
        try:
            frame.after(1500, refresh)
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
