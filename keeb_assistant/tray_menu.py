"""Dark, keyboard accessible popup for the Windows tray icon."""
from __future__ import annotations

import tkinter as tk

from . import APP_NAME, autostart, i18n
from .theme import BG, CYAN, HEADER, LINE, MUTED, PANEL, SELECTED, TEXT, round_window


def show_tray_menu(app, parent):
    old = getattr(app, "_tray_popup", None)
    if old is not None and old.winfo_exists():
        old.destroy()
    popup = tk.Toplevel(parent)
    app._tray_popup = popup
    popup.overrideredirect(True)
    popup.attributes("-topmost", True)
    popup.configure(bg=LINE)
    panel = tk.Frame(popup, bg=HEADER, padx=9, pady=8)
    panel.pack(padx=1, pady=1)

    heading = tk.Frame(panel, bg=HEADER)
    heading.pack(fill="x", padx=8, pady=(4, 7))
    tk.Label(heading, text="K", bg=SELECTED, fg=CYAN,
             font=("Segoe UI", 12, "bold"), width=3).pack(side="left", padx=(0, 9))
    tk.Label(heading, text=APP_NAME, bg=HEADER, fg=TEXT,
             font=("Segoe UI", 10, "bold")).pack(side="left")
    tk.Frame(panel, bg=LINE, height=1).pack(fill="x", pady=(0, 6))

    def close():
        if popup.winfo_exists():
            popup.destroy()

    def invoke(callback):
        close()
        callback()

    def item(label, callback, *, checked=False, submenu=False):
        row = tk.Frame(panel, bg=HEADER, height=34, width=260, cursor="hand2")
        row.pack(fill="x")
        row.pack_propagate(False)
        marker = "✓" if checked else ""
        tk.Label(row, text=marker, bg=HEADER, fg=CYAN,
                 font=("Segoe UI", 10), width=2).pack(side="left", padx=(3, 4))
        text = tk.Label(row, text=label, bg=HEADER, fg=TEXT,
                        font=("Segoe UI", 10), anchor="w")
        text.pack(side="left", fill="both", expand=True)
        if submenu:
            tk.Label(row, text="›", bg=HEADER, fg=MUTED,
                     font=("Segoe UI", 13)).pack(side="right", padx=9)
        children = row.winfo_children()
        def hover(color):
            row.config(bg=color)
            for child in children:
                child.config(bg=color)
        for child in [row, *children]:
            child.bind("<Enter>", lambda _event: hover(PANEL))
            child.bind("<Leave>", lambda _event: hover(HEADER))
            child.bind("<Button-1>", lambda _event: callback() if submenu else invoke(callback))
        return row

    item(i18n.t("menu_lighting"), lambda: app._open_lighting_tab())
    item(i18n.t("menu_settings"), lambda: app._open_settings())
    item(i18n.t("menu_open_launcher"), lambda: app._open_launcher())

    languages = tk.Frame(panel, bg=HEADER)
    def toggle_languages():
        if languages.winfo_manager():
            languages.pack_forget()
        else:
            languages.pack(fill="x")
            position()
    item(i18n.t("menu_language"), toggle_languages, submenu=True)
    for code, label in i18n.available_languages():
        option = tk.Label(languages, text=("✓  " if i18n.get_language() == code else "    ") + label,
                          bg=HEADER, fg=MUTED, anchor="w", cursor="hand2",
                          font=("Segoe UI", 9), padx=37, pady=5)
        option.pack(fill="x")
        option.bind("<Enter>", lambda event: event.widget.config(bg=PANEL, fg=TEXT))
        option.bind("<Leave>", lambda event: event.widget.config(bg=HEADER, fg=MUTED))
        option.bind("<Button-1>", lambda _event, lang=code: invoke(
            lambda: app.set_language(lang)))

    item(i18n.t("menu_autostart"), lambda: app._toggle_autostart(app.icon, None),
         checked=autostart.is_enabled())
    item(i18n.t("menu_notify"), lambda: app._toggle_notify(app.icon, None),
         checked=bool(app.config["notify_low_battery"]))
    item(i18n.t("menu_flash_firmware"), lambda: app._open_firmware_tab())
    tk.Frame(panel, bg=LINE, height=1).pack(fill="x", pady=6)
    item(i18n.t("menu_quit"), lambda: app._quit(app.icon, None))

    def position():
        popup.update_idletasks()
        x, y = parent.winfo_pointerxy()
        screen_w, screen_h = popup.winfo_screenwidth(), popup.winfo_screenheight()
        x = max(2, min(x - 20, screen_w - popup.winfo_reqwidth() - 5))
        y = max(2, min(y - popup.winfo_reqheight() + 8,
                       screen_h - popup.winfo_reqheight() - 5))
        popup.geometry(f"+{x}+{y}")
        popup.after_idle(lambda: round_window(popup))

    position()
    popup.bind("<Escape>", lambda _event: close())
    popup.bind("<FocusOut>", lambda _event: popup.after(
        120, lambda: close() if popup.winfo_exists() and
        popup.focus_displayof() is None else None))
    popup.focus_force()
    return popup
