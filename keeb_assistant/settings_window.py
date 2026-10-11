"""Settings panel styled to match the EmblemaShot mockup."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from . import APP_NAME, autostart, battery_log, i18n, tray_registry
from .theme import BG, CYAN, LINE, MUTED, TEXT, ThemeButton, ThemeSwitch, apply_theme


def build_settings_panel(parent, app, *, on_close=None, title_callback=None):
    cfg = app.config
    frame = tk.Frame(parent, bg=BG)
    frame.grid_columnconfigure(0, weight=1)
    languages = i18n.available_languages()
    lang_codes = [code for code, _ in languages]
    lang_labels = [label for _, label in languages]
    lang_var = tk.StringVar(value=i18n.language_label(i18n.get_language()))
    notify_var = tk.BooleanVar(value=bool(cfg["notify_low_battery"]))
    threshold_var = tk.IntVar(value=int(cfg["low_battery_threshold"]))
    alpha_var = tk.DoubleVar(value=float(cfg["smoothing_alpha"]))
    autostart_var = tk.BooleanVar(value=autostart.is_enabled())
    correction_var = tk.BooleanVar(value=bool(cfg.get("charge_correction", True)))
    logging_var = tk.BooleanVar(value=bool(cfg.get("battery_logging")))

    tk.Label(frame, text="PREFERENCES", bg=BG, fg=CYAN,
             font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(10, 8))
    heading = tk.Label(frame, bg=BG, fg=TEXT, font=("Segoe UI", 23, "bold"))
    heading.grid(row=1, column=0, sticky="w")
    tk.Label(frame, text="Dark surfaces, clear fields, and cyan active controls.",
             bg=BG, fg=MUTED, font=("Segoe UI", 11)).grid(
                 row=2, column=0, sticky="w", pady=(4, 24))
    body = tk.Frame(frame, bg=BG)
    body.grid(row=3, column=0, sticky="ew")
    body.grid_columnconfigure(0, weight=1)

    def row(index, description, control_factory):
        holder = tk.Frame(body, bg=BG, height=68)
        holder.grid(row=index * 2, column=0, sticky="ew")
        holder.grid_propagate(False)
        holder.grid_columnconfigure(0, weight=1)
        label = tk.Label(holder, bg=BG, fg=TEXT, font=("Segoe UI", 11, "bold"))
        label.grid(row=0, column=0, sticky="w", pady=(8, 0))
        tk.Label(holder, text=description, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")
        control = control_factory(holder)
        control.grid(row=0, column=1, rowspan=2, sticky="e", padx=(20, 0))
        tk.Frame(body, bg=LINE, height=1).grid(row=index * 2 + 1, column=0, sticky="ew")
        return label, control

    def on_language_changed(_event=None):
        try:
            code = lang_codes[lang_labels.index(lang_var.get())]
        except ValueError:
            return
        app.set_language(code)
        retranslate()

    lbl_language, combo = row(
        0, "Choose the language used throughout the app.",
        lambda holder: ttk.Combobox(holder, textvariable=lang_var, values=lang_labels,
                                    state="readonly", width=18))
    combo.bind("<<ComboboxSelected>>", on_language_changed)
    lbl_notify, _ = row(1, "Show a notification when the battery runs low.",
                        lambda holder: ThemeSwitch(holder, notify_var))
    lbl_logging, _ = row(2, "Keep the desktop widget up to date.",
                         lambda holder: ThemeSwitch(holder, logging_var))
    lbl_autostart, _ = row(3, "Launch Keyboard Companion at sign-in.",
                           lambda holder: ThemeSwitch(holder, autostart_var))

    actions = tk.Frame(frame, bg=BG)
    actions.grid(row=4, column=0, sticky="w", pady=(26, 9))
    advanced = tk.Frame(frame, bg=BG)
    advanced.grid(row=5, column=0, sticky="ew", pady=(6, 0))
    tk.Frame(advanced, bg=LINE, height=1).grid(
        row=0, column=0, columnspan=4, sticky="ew", pady=(0, 13))
    tk.Label(advanced, text="ADVANCED", bg=BG, fg=CYAN,
             font=("Segoe UI", 9, "bold")).grid(
                 row=1, column=0, columnspan=4, sticky="w", pady=(0, 8))
    lbl_threshold = tk.Label(advanced, bg=BG, fg=TEXT)
    lbl_threshold.grid(row=2, column=0, sticky="w", padx=(0, 15), pady=3)
    ttk.Spinbox(advanced, from_=1, to=99, textvariable=threshold_var,
                width=6).grid(row=2, column=1, sticky="w", pady=3)
    lbl_smoothing = tk.Label(advanced, bg=BG, fg=TEXT)
    lbl_smoothing.grid(row=3, column=0, sticky="w", pady=3)
    ttk.Scale(advanced, from_=0.05, to=1.0, variable=alpha_var,
              orient="horizontal", length=160).grid(row=3, column=1, sticky="w", pady=3)
    correction = ttk.Checkbutton(advanced, variable=correction_var)
    correction.grid(row=4, column=0, columnspan=3, sticky="w", pady=3)
    btn_log = ttk.Button(advanced, command=battery_log.open_location)
    btn_log.grid(row=5, column=0, sticky="w", pady=(9, 0), padx=(0, 8))
    btn_clean = ttk.Button(advanced)
    btn_clean.grid(row=5, column=1, sticky="w", pady=(9, 0), padx=(0, 8))
    btn_promote = ttk.Button(advanced)
    btn_promote.grid(row=5, column=2, sticky="w", pady=(9, 0))
    note = tk.Label(advanced, bg=BG, fg=MUTED, wraplength=770, justify="left")
    note.grid(row=6, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def on_save():
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

    def on_clean():
        deleted = tray_registry.cleanup_old_records()
        messagebox.showinfo(APP_NAME, i18n.t("settings_clean_tray_done", count=deleted),
                            parent=frame.winfo_toplevel())

    def on_promote():
        ok = tray_registry.promote_current_icon()
        key = "settings_promote_tray_done" if ok else "settings_promote_tray_failed"
        messagebox.showinfo(APP_NAME, i18n.t(key), parent=frame.winfo_toplevel())

    btn_clean.configure(command=on_clean)
    btn_promote.configure(command=on_promote)
    save = ThemeButton(actions, "Save settings", on_save, variant="primary", width=150)
    save.pack(side="left", padx=(0, 8))
    close = ThemeButton(actions, "Close", on_close or frame.winfo_toplevel().destroy,
                        width=90)
    close.pack(side="left")

    def retranslate():
        if title_callback:
            title_callback(APP_NAME)
        heading.config(text=i18n.t("main_tab_settings"))
        for label, key in (
            (lbl_language, "settings_language"), (lbl_notify, "settings_notify"),
            (lbl_logging, "settings_logging"), (lbl_autostart, "settings_autostart"),
            (lbl_threshold, "settings_threshold"), (lbl_smoothing, "settings_smoothing"),
            (correction, "settings_charge_correction"), (btn_log, "settings_open_log"),
            (btn_clean, "settings_clean_tray_records"),
            (btn_promote, "settings_promote_tray_icon"), (note, "settings_note"),
        ):
            label.config(text=i18n.t(key))
        save.label = i18n.t("settings_save")
        save._paint()
        close.label = i18n.t("settings_close")
        close._paint()

    retranslate()
    frame.retranslate = retranslate
    return frame


def open_settings(app) -> None:
    root = tk.Tk()
    apply_theme(root)
    root.title(APP_NAME)
    root.geometry("850x750")
    build_settings_panel(root, app, on_close=root.destroy,
                         title_callback=root.title).pack(fill="both", expand=True, padx=25, pady=20)
    root.mainloop()
