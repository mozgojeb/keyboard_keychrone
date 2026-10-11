"""Keyboard Companion's custom EmblemaShot-style application window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk

from . import APP_NAME, __version__, i18n
from .config import Config
from .settings_window import build_settings_panel
from .lighting_editor import LightingEditor
from .monitor_panel import MonitorPanel
from .schedule_panel import SchedulePanel
from .theme import BG, CYAN, HEADER, LINE, MUTED, NAV, PANEL, SELECTED, TEXT
from .theme import ThemeButton, ThemeSwitch, apply_theme, dark_titlebar

TAB_IDS = ("device", "lighting", "settings", "firmware", "widget",
           "schedule", "monitor", "about")


def open_main_window(app, initial_tab: str = "settings", *, parent=None):
    root = tk.Toplevel(parent) if parent is not None else tk.Tk()
    apply_theme(root)
    root.title(APP_NAME)
    width = min(1460, max(900, root.winfo_screenwidth() - 100))
    height = min(1120, max(720, root.winfo_screenheight() - 100))
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.minsize(900, 700)

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
    version = tk.Label(header, text=f"v{__version__}", bg=HEADER, fg=MUTED,
                       font=("Segoe UI", 9))
    version.pack(side="right", padx=15)

    navigation = tk.Frame(border, bg=NAV, height=60)
    navigation.pack(fill="x")
    navigation.pack_propagate(False)
    nav_items = tk.Frame(navigation, bg=NAV)
    nav_items.pack(side="left", padx=12, pady=(9, 0))
    tk.Frame(border, bg=LINE, height=1).pack(fill="x")
    content = tk.Frame(border, bg=BG)
    content.pack(fill="both", expand=True, padx=36, pady=28)
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

    root.after(150, lambda: dark_titlebar(root))
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
        card = tk.Canvas(frame, bg=BG, height=122, highlightthickness=0,
                         borderwidth=0)
        card.grid(row=3, column=col, sticky="ew",
                  padx=(0, 13) if col < 2 else 0)
        card.create_text(21, 25, text=label, anchor="w", fill=MUTED,
                         font=("Segoe UI", 9))
        value = card.create_text(21, 79, text="--", anchor="w",
                                 fill=CYAN if key == "battery" else TEXT,
                                 font=("Segoe UI", 23, "bold"))
        def repaint(event, surface=card):
            width, height = max(1,event.width), max(1,event.height)
            image = Image.new("RGB", (width*3,height*3), BG)
            pen = ImageDraw.Draw(image)
            pen.rounded_rectangle((2,2,width*3-3,height*3-3),
                                  radius=13*3, fill=PANEL,
                                  outline="#344252", width=2)
            surface._card_photo = ImageTk.PhotoImage(
                image.resize((width,height),Image.Resampling.LANCZOS))
            if not surface.find_withtag("card_surface"):
                surface.create_image(0,0,anchor="nw",image=surface._card_photo,
                                     tags="card_surface")
                surface.tag_lower("card_surface")
            else:
                surface.itemconfigure("card_surface",image=surface._card_photo)
        card.bind("<Configure>", repaint)
        cards[key] = (card,value)

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
                cards[key][0].itemconfigure(cards[key][1], text=fmt(val))
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
    card_width, card_height = 390, 190
    card = tk.Canvas(frame, width=card_width, height=card_height,
                     bg=BG, highlightthickness=0, borderwidth=0)
    card.pack(anchor="w")
    image = Image.new("RGB", (card_width*3, card_height*3), BG)
    pen = ImageDraw.Draw(image)
    pen.rounded_rectangle((2, 2, card_width*3-3, card_height*3-3),
                          radius=19*3, fill=BG, outline="#798491", width=2)
    card._background = ImageTk.PhotoImage(
        image.resize((card_width, card_height), Image.Resampling.LANCZOS))
    card.create_image(0, 0, image=card._background, anchor="nw")
    device = card.create_text(24, 26, text="KEYBOARD COMPANION",
                              anchor="w", fill=CYAN, font=("Segoe UI", 9, "bold"))
    card.create_text(card_width-24, 26, text="×", anchor="e",
                     fill=MUTED, font=("Segoe UI", 16))
    percent = card.create_text(24, 96, text="--", anchor="w",
                               fill=TEXT, font=("Segoe UI", 34, "bold"))
    card.create_rectangle(271, 79, 360, 119, outline=MUTED, width=2)
    card.create_rectangle(361, 91, 368, 107, fill=MUTED, outline=MUTED)
    battery_fill = card.create_rectangle(276, 84, 276, 114, fill=CYAN, outline="")
    status = card.create_text(24, 155, text=i18n.t("undetected"),
                              anchor="w", fill=MUTED, font=("Segoe UI", 10))

    switch_row = tk.Frame(frame, bg=BG, width=390, height=96)
    switch_row.pack(anchor="w", pady=(26, 0))
    switch_row.pack_propagate(False)
    switch_row.grid_columnconfigure(0, weight=1)
    tk.Frame(switch_row, bg=LINE, height=1).grid(row=0, column=0, columnspan=2,
                                                  sticky="ew", pady=(0, 15))
    tk.Label(switch_row, text="Show on desktop", bg=BG, fg=TEXT,
             font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="w")
    hint = tk.Label(switch_row, text="Keep battery status visible while you work.",
                    bg=BG, fg=MUTED, font=("Segoe UI", 9))
    hint.grid(row=2, column=0, sticky="w", pady=(4, 0))
    widget_var = tk.BooleanVar(value=bool(app.config.get("widget_enabled")))

    def toggle_widget():
        enabled = bool(widget_var.get())
        if not app.set_widget_enabled(enabled):
            widget_var.set(False)
            hint.config(text="Widget could not be opened. Check the installation.")
        else:
            hint.config(text="Keep battery status visible while you work." if enabled
                        else "Desktop widget is off.")

    ThemeSwitch(switch_row, widget_var, command=toggle_widget).grid(
        row=1, column=1, rowspan=2, sticky="e", padx=(18, 0))

    def refresh():
        saved_enabled = bool(Config.load().get("widget_enabled"))
        if saved_enabled != bool(widget_var.get()):
            app.config["widget_enabled"] = saved_enabled
            widget_var.set(saved_enabled)
            hint.config(text="Keep battery status visible while you work." if saved_enabled
                        else "Desktop widget is off.")
        reading, pct = app._snapshot()
        card.itemconfigure(percent, text=f"{pct}%" if pct is not None else "--")
        card.itemconfigure(device, text=(getattr(app, "_device_label", None) or
                                         "KEYBOARD COMPANION").upper())
        if pct is not None:
            fill = max(0, min(100, int(pct)))
            card.coords(battery_fill, 276, 84, 276 + round(fill * 0.78), 114)
        else:
            card.coords(battery_fill, 276, 84, 276, 114)
        if reading:
            parts = [reading.transport_name]
            if reading.source != "windows":
                parts.insert(0, i18n.t(f"charging_{reading.charging_code}"))
                if reading.voltage_mv > 0:
                    parts.append(f"{reading.voltage_mv:,} mV")
            card.itemconfigure(status, text="  •  ".join(parts))
        else:
            card.itemconfigure(status, text=i18n.t("undetected"))
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
