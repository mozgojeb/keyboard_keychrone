"""EmblemaShot-inspired colours for Keyboard Companion's Tk windows."""

from tkinter import ttk

BG = "#0d1017"
NAV = "#090c12"
PANEL = "#151b25"
FIELD = "#191d25"
TEXT = "#f4f7ff"
MUTED = "#bfc9da"
LINE = "#343b47"
CYAN = "#27c8ee"


def apply_theme(root):
    """Style the existing ttk controls without changing keyboard behaviour."""
    root.configure(background=BG)
    root.option_add("*Font", "{Segoe UI} 10")
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", "#143d49")
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("TButton", background=FIELD, foreground=TEXT,
                    bordercolor="#798491", lightcolor=FIELD, darkcolor=FIELD,
                    focuscolor=CYAN, relief="flat", padding=(14, 8))
    style.map("TButton", background=[("disabled", "#252b35"),
                                      ("pressed", "#143d49"), ("active", "#2c3542")],
              foreground=[("disabled", "#798491"), ("active", TEXT)])
    style.configure("TCheckbutton", background=BG, foreground=TEXT, padding=4)
    style.map("TCheckbutton", background=[("active", BG)], foreground=[("active", TEXT)])
    for widget in ("TEntry", "TSpinbox", "TCombobox"):
        style.configure(widget, fieldbackground=FIELD, background=FIELD,
                        foreground=TEXT, insertcolor=TEXT, arrowcolor=TEXT,
                        bordercolor="#67707d", lightcolor=FIELD, darkcolor=FIELD,
                        padding=5)
        style.map(widget, fieldbackground=[("readonly", FIELD), ("disabled", "#252b35")],
                  foreground=[("readonly", TEXT), ("disabled", "#798491")])
    style.configure("TScale", background=BG, troughcolor=FIELD, bordercolor=BG,
                    lightcolor=BG, darkcolor=BG)
    style.configure("TProgressbar", background=CYAN, troughcolor=FIELD,
                    bordercolor=LINE, lightcolor=CYAN, darkcolor=CYAN)
    style.configure("TSeparator", background=LINE)
    style.configure("TNotebook", background=NAV, borderwidth=0, tabmargins=(8, 8, 8, 0))
    style.configure("TNotebook.Tab", background=FIELD, foreground=MUTED,
                    bordercolor=LINE, lightcolor=FIELD, darkcolor=FIELD,
                    padding=(15, 10), font=("Segoe UI", 10))
    style.map("TNotebook.Tab", background=[("selected", "#143d49"),
                                            ("active", "#171e28")],
              foreground=[("selected", TEXT), ("active", TEXT)],
              lightcolor=[("selected", CYAN)], bordercolor=[("selected", CYAN)])
