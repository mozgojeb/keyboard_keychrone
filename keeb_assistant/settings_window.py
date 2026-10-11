"""Small Tk settings window, opened from the tray menu.

The application embeds this panel in its main-thread Tk window. Tkinter is
bundled with CPython.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import APP_NAME, __version__, autostart, battery_log, i18n, tray_registry
from .theme import apply_theme, MUTED


def build_settings_panel(parent, app, *, on_close=None, title_callback=None):
    cfg = app.config

    frame = ttk.Frame(parent, padding=16)

    lang_codes = [code for code, _ in i18n.available_languages()]
    lang_labels = [label for _, label in i18n.available_languages()]

    lang_var = tk.StringVar(value=i18n.language_label(i18n.get_language()))
    notify_var = tk.BooleanVar(value=bool(cfg["notify_low_battery"]))
    threshold_var = tk.IntVar(value=int(cfg["low_battery_threshold"]))
    alpha_var = tk.DoubleVar(value=float(cfg["smoothing_alpha"]))
    autostart_var = tk.BooleanVar(value=autostart.is_enabled())
    correction_var = tk.BooleanVar(value=bool(cfg.get("charge_correction", True)))
    logging_var = tk.BooleanVar(value=bool(cfg.get("battery_logging")))

    # Keep references so we can re-translate labels live on language change.
    lbl_language = ttk.Label(frame)
    lbl_threshold = ttk.Label(frame)
    chk_notify = ttk.Checkbutton(frame, variable=notify_var)
    lbl_smoothing = ttk.Label(frame)
    chk_autostart = ttk.Checkbutton(frame, variable=autostart_var)
    chk_correction = ttk.Checkbutton(frame, variable=correction_var)
    chk_logging = ttk.Checkbutton(frame, variable=logging_var)
    btn_open_log = ttk.Button(frame, command=battery_log.open_location)
    tray_tools_sep = ttk.Separator(frame, orient="horizontal")
    lbl_tray_tools = ttk.Label(frame, foreground=MUTED, wraplength=320)
    btn_clean_tray = ttk.Button(frame)
    btn_promote_tray = ttk.Button(frame)
    lbl_note = ttk.Label(frame, foreground=MUTED, wraplength=320)
    lbl_version = ttk.Label(frame, foreground=MUTED, text=f"{APP_NAME}  v{__version__}")
    btn_save = ttk.Button(frame)
    btn_close = ttk.Button(frame)

    def retranslate() -> None:
        if title_callback:
            title_callback(APP_NAME)
        lbl_language.config(text=i18n.t("settings_language"))
        lbl_threshold.config(text=i18n.t("settings_threshold"))
        chk_notify.config(text=i18n.t("settings_notify"))
        lbl_smoothing.config(text=i18n.t("settings_smoothing"))
        chk_autostart.config(text=i18n.t("settings_autostart"))
        chk_correction.config(text=i18n.t("settings_charge_correction"))
        chk_logging.config(text=i18n.t("settings_logging"))
        btn_open_log.config(text=i18n.t("settings_open_log"))
        lbl_tray_tools.config(text=i18n.t("settings_tray_tools"))
        btn_clean_tray.config(text=i18n.t("settings_clean_tray_records"))
        btn_promote_tray.config(text=i18n.t("settings_promote_tray_icon"))
        lbl_note.config(text=i18n.t("settings_note"))
        btn_save.config(text=i18n.t("settings_save"))
        btn_close.config(text=i18n.t("settings_close"))

    def on_language_changed(event=None) -> None:
        try:
            idx = lang_labels.index(lang_var.get())
        except ValueError:
            return
        app.set_language(lang_codes[idx])
        retranslate()

    combo = ttk.Combobox(
        frame, textvariable=lang_var, values=lang_labels, state="readonly", width=18
    )
    combo.bind("<<ComboboxSelected>>", on_language_changed)

    spin = ttk.Spinbox(frame, from_=1, to=99, textvariable=threshold_var, width=6)
    scale = ttk.Scale(frame, from_=0.05, to=1.0, variable=alpha_var, orient="horizontal", length=200)

    def on_save() -> None:
        cfg["notify_low_battery"] = bool(notify_var.get())
        try:
            cfg["low_battery_threshold"] = int(threshold_var.get())
        except (tk.TclError, ValueError):
            pass
        cfg["smoothing_alpha"] = round(float(alpha_var.get()), 2)
        cfg["autostart"] = autostart.set_enabled(bool(autostart_var.get()))
        cfg["charge_correction"] = bool(correction_var.get())
        cfg["battery_logging"] = bool(logging_var.get())
        app.apply_settings()
        (on_close or frame.winfo_toplevel().destroy)()

    def on_clean_tray_records() -> None:
        deleted = tray_registry.cleanup_old_records()
        messagebox.showinfo(
            APP_NAME,
            i18n.t("settings_clean_tray_done", count=deleted),
            parent=frame.winfo_toplevel(),
        )

    def on_promote_tray_icon() -> None:
        ok = tray_registry.promote_current_icon()
        key = "settings_promote_tray_done" if ok else "settings_promote_tray_failed"
        messagebox.showinfo(APP_NAME, i18n.t(key), parent=frame.winfo_toplevel())

    btn_save.config(command=on_save)
    btn_close.config(command=on_close or frame.winfo_toplevel().destroy)
    btn_clean_tray.config(command=on_clean_tray_records)
    btn_promote_tray.config(command=on_promote_tray_icon)

    # Layout.
    lbl_language.grid(row=0, column=0, sticky="w", pady=4)
    combo.grid(row=0, column=1, sticky="e", pady=4)
    lbl_threshold.grid(row=1, column=0, sticky="w", pady=4)
    spin.grid(row=1, column=1, sticky="e", pady=4)
    chk_notify.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
    lbl_smoothing.grid(row=3, column=0, sticky="w", pady=4)
    scale.grid(row=3, column=1, sticky="e", pady=4)
    chk_autostart.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
    chk_correction.grid(row=5, column=0, columnspan=2, sticky="w", pady=4)
    chk_logging.grid(row=6, column=0, sticky="w", pady=4)
    btn_open_log.grid(row=6, column=1, sticky="e", pady=4)
    tray_tools_sep.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 8))
    lbl_tray_tools.grid(row=8, column=0, columnspan=2, sticky="w", pady=(0, 4))
    btn_clean_tray.grid(row=9, column=0, columnspan=2, sticky="ew", pady=3)
    btn_promote_tray.grid(row=10, column=0, columnspan=2, sticky="ew", pady=3)
    lbl_note.grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 8))
    btn_save.grid(row=12, column=0, sticky="w", pady=(4, 0))
    btn_close.grid(row=12, column=1, sticky="e", pady=(4, 0))
    lbl_version.grid(row=13, column=0, columnspan=2, sticky="w", pady=(12, 0))

    retranslate()
    frame.retranslate = retranslate  # type: ignore[attr-defined]
    return frame


def open_settings(app) -> None:
    root = tk.Tk()
    apply_theme(root)
    root.title(APP_NAME)
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    frame = build_settings_panel(root, app, on_close=root.destroy, title_callback=root.title)
    frame.grid(row=0, column=0, sticky="nsew")

    root.update_idletasks()
    root.mainloop()
