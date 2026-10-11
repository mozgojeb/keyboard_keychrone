"""Shared EmblemaShot-style surfaces and controls for Keyboard Companion."""

import ctypes
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

BG = "#0d1017"
NAV = "#090c12"
PANEL = "#151b25"
FIELD = "#191d25"
TEXT = "#f4f7ff"
MUTED = "#bfc9da"
LINE = "#343b47"
CYAN = "#27c8ee"
HEADER = "#11151c"
SELECTED = "#143d49"


def enable_dpi_awareness():
    """Ask Windows for crisp text before the first Tk window is created."""
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass


def round_window(window):
    """Clip the custom window corners to match EmblemaShot on Windows."""
    if not sys.platform.startswith("win"):
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        width, height = window.winfo_width(), window.winfo_height()
        region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, 26, 26)
        if region and not ctypes.windll.user32.SetWindowRgn(hwnd, region, True):
            ctypes.windll.gdi32.DeleteObject(region)
    except (AttributeError, OSError, tk.TclError):
        pass


def dark_titlebar(window):
    """Use Windows' real, accessible title bar in dark mode."""
    if not sys.platform.startswith("win"):
        return
    try:
        user32 = ctypes.windll.user32
        user32.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user32.GetAncestor.restype = ctypes.c_void_p
        hwnd = user32.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
        enabled = ctypes.c_int(1)
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = (
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint)
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        for attribute in (20, 19):
            if dwm.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(enabled),
                                         ctypes.sizeof(enabled)) == 0:
                break
        caption = ctypes.c_uint(0x001C1511)
        caption_text = ctypes.c_uint(0x00FFF7F4)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption),
                                  ctypes.sizeof(caption))
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(caption_text),
                                  ctypes.sizeof(caption_text))
    except (AttributeError, OSError, tk.TclError):
        pass


def present_window(window):
    """Restore and activate the normal app window from a tray action."""
    window.deiconify()
    window.lift()
    window.update_idletasks()
    if sys.platform.startswith("win"):
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        except (AttributeError, OSError, tk.TclError):
            pass
    window.focus_force()


class ThemeButton(tk.Canvas):
    """Antialiased, keyboard-accessible button for the app shell and actions."""

    def __init__(self, parent, text, command, *, variant="secondary", width=None, height=42):
        self.label = text
        self.command = command
        self.variant = variant
        self.hover = False
        self.selected = False
        self.font = tkfont.Font(family="Segoe UI", size=10,
                                weight="bold" if variant == "primary" else "normal")
        width = width or max(92, self.font.measure(text) + 32)
        self.background = parent.cget("bg")
        super().__init__(parent, width=width, height=height, bg=self.background,
                         highlightthickness=0, borderwidth=0, cursor="hand2", takefocus=1)
        self.bind("<Enter>", lambda _e: self._hover(True))
        self.bind("<Leave>", lambda _e: self._hover(False))
        self.bind("<Button-1>", lambda _e: self._activate())
        self.bind("<Return>", lambda _e: self._activate())
        self.bind("<space>", lambda _e: self._activate())
        self._paint()

    def _hover(self, value):
        self.hover = value
        self._paint()

    def _activate(self):
        self.focus_set()
        self.command()

    def set_selected(self, value):
        self.selected = value
        self._paint()

    def _paint(self):
        width, height = int(self.cget("width")), int(self.cget("height"))
        scale = 3
        image = Image.new("RGB", (width * scale, height * scale), self.background)
        pen = ImageDraw.Draw(image)
        if self.variant == "primary":
            fill, outline, ink = ("#54d8f4" if self.hover else CYAN), CYAN, "#07151b"
        elif self.variant == "nav":
            fill = SELECTED if self.selected else "#171e28" if self.hover else NAV
            outline, ink = (CYAN if self.selected else fill), (TEXT if self.selected or self.hover else MUTED)
        else:
            fill, outline, ink = ("#2c3542" if self.hover else FIELD), "#798491", TEXT
        pen.rounded_rectangle((2, 2, width * scale - 3, height * scale - 3),
                              radius=11 * scale, fill=fill, outline=outline, width=2)
        self._photo = ImageTk.PhotoImage(image.resize((width, height), Image.Resampling.LANCZOS))
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._photo)
        self.create_text(width // 2, height // 2, text=self.label, fill=ink, font=self.font)


class ThemeSwitch(tk.Canvas):
    """Toggle with the cyan on state used in the EmblemaShot settings UI."""

    def __init__(self, parent, variable, command=None):
        self.variable = variable
        self.command = command
        super().__init__(parent, width=52, height=30, bg=parent.cget("bg"),
                         highlightthickness=0, borderwidth=0, cursor="hand2", takefocus=1)
        self.bind("<Button-1>", lambda _e: self._toggle())
        self.bind("<Return>", lambda _e: self._toggle())
        self.bind("<space>", lambda _e: self._toggle())
        variable.trace_add("write", lambda *_: self._paint())
        self._paint()

    def _toggle(self):
        self.variable.set(not self.variable.get())
        self.focus_set()
        if self.command is not None:
            self.command()

    def _paint(self):
        image = Image.new("RGB", (156, 90), self.cget("bg"))
        pen = ImageDraw.Draw(image)
        enabled = bool(self.variable.get())
        pen.rounded_rectangle((3, 9, 153, 81), radius=36,
                              fill=CYAN if enabled else "#424c5b")
        x = 84 if enabled else 12
        pen.ellipse((x, 15, x + 60, 75), fill="#071a24" if enabled else "#edf2f8")
        self._photo = ImageTk.PhotoImage(image.resize((52, 30), Image.Resampling.LANCZOS))
        self.delete("all")
        self.create_image(0, 0, anchor="nw", image=self._photo)


def apply_theme(root):
    """Style the existing ttk controls without changing keyboard behaviour."""
    root.configure(background=BG)
    root.option_add("*Font", "{Segoe UI} 10")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family="Segoe UI", size=10)
        except tk.TclError:
            pass
    root.option_add("*Listbox.background", FIELD)
    root.option_add("*Listbox.foreground", TEXT)
    root.option_add("*Listbox.selectBackground", SELECTED)
    root.option_add("*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", "#143d49")
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("TButton", font=("Segoe UI", 10))
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
