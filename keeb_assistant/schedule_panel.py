"""Tk editor for weekly keyboard backlight schedules."""

from __future__ import annotations

from copy import deepcopy
import tkinter as tk
from tkinter import messagebox, ttk

from .lighting_profiles import load_profiles
from .lighting_schedule import TIME_RE, load_schedules, normalize_schedule

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


class SchedulePanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.schedules = load_schedules(app.config)
        if not self.schedules:
            self.schedules = [normalize_schedule({"name": "Evening", "days": range(7)})]
        self.index = 0
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Backlight schedules", font=("", 14, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        left = ttk.Frame(self)
        left.grid(row=1, column=0, sticky="ns", padx=(0, 20))
        self.listbox = tk.Listbox(left, width=22, height=16, exportselection=False)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.switch)
        ttk.Button(left, text="New schedule", command=self.add).pack(fill="x", pady=(8, 0))
        ttk.Button(left, text="Duplicate", command=self.duplicate).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="Delete", command=self.delete).pack(fill="x", pady=(6, 0))

        form = ttk.Frame(self)
        form.grid(row=1, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)
        self.master_enabled = tk.BooleanVar(value=bool(app.config.get("lighting_scheduler_enabled", False)))
        self.enabled = tk.BooleanVar()
        self.name = tk.StringVar()
        self.on_time = tk.StringVar()
        self.off_time = tk.StringVar()
        self.profile = tk.StringVar()
        self.days = [tk.BooleanVar() for _ in DAY_NAMES]

        ttk.Checkbutton(form, text="Enable automatic backlight scheduling",
                        variable=self.master_enabled).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        ttk.Label(form, text="Schedule name", width=17).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.name).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Checkbutton(form, text="This schedule is enabled", variable=self.enabled).grid(
            row=2, column=1, sticky="w", pady=4)
        ttk.Label(form, text="Days").grid(row=3, column=0, sticky="nw", pady=4)
        days_frame = ttk.Frame(form)
        days_frame.grid(row=3, column=1, sticky="w", pady=4)
        for index, label in enumerate(DAY_NAMES):
            ttk.Checkbutton(days_frame, text=label, variable=self.days[index]).pack(side="left", padx=(0, 7))
        ttk.Label(form, text="Backlight on").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.on_time, width=9).grid(row=4, column=1, sticky="w", pady=4)
        ttk.Label(form, text="Backlight off").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.off_time, width=9).grid(row=5, column=1, sticky="w", pady=4)
        ttk.Label(form, text="Lighting profile").grid(row=6, column=0, sticky="w", pady=4)
        self.profile_combo = ttk.Combobox(form, textvariable=self.profile, state="readonly",
                                          values=[p["name"] for p in load_profiles(app.config)])
        self.profile_combo.grid(row=6, column=1, sticky="ew", pady=4)
        ttk.Label(form, text="Use 24-hour times (HH:MM). Overnight ranges are supported.",
                  foreground="#bfc9da").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 12))
        actions = ttk.Frame(form)
        actions.grid(row=8, column=0, columnspan=2, sticky="w")
        ttk.Button(actions, text="Save schedules", command=self.save).pack(side="left")
        ttk.Button(actions, text="Apply schedule now", command=self.apply_now).pack(side="left", padx=8)
        self.status = tk.StringVar()
        ttk.Label(form, textvariable=self.status, wraplength=650).grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.load()
        self.poll_job = self.after(500, self.poll)
        self.bind("<Destroy>", self.on_destroy, add="+")

    def on_destroy(self, event):
        if event.widget is self:
            self.after_cancel(self.poll_job)

    def capture(self) -> bool:
        on_time = self.on_time.get().strip()
        off_time = self.off_time.get().strip()
        if not TIME_RE.fullmatch(on_time) or not TIME_RE.fullmatch(off_time):
            self.status.set("Enter times as HH:MM, from 00:00 to 23:59.")
            return False
        if on_time == off_time:
            self.status.set("On and off times must differ.")
            return False
        chosen_days = [index for index, value in enumerate(self.days) if value.get()]
        if not chosen_days:
            self.status.set("Select at least one day.")
            return False
        profile = self.profile.get()
        if profile not in self.profile_combo.cget("values"):
            self.status.set("Select an existing lighting profile.")
            return False
        self.schedules[self.index] = normalize_schedule({
            "name": self.name.get(), "enabled": self.enabled.get(), "days": chosen_days,
            "on_time": on_time, "off_time": off_time, "profile": profile,
        })
        return True

    def load(self):
        rule = self.schedules[self.index]
        self.name.set(rule["name"])
        self.enabled.set(rule["enabled"])
        self.on_time.set(rule["on_time"])
        self.off_time.set(rule["off_time"])
        profiles = [p["name"] for p in load_profiles(self.app.config)]
        self.profile_combo.configure(values=profiles)
        self.profile.set(rule["profile"] if rule["profile"] in profiles else profiles[0])
        for index, value in enumerate(self.days):
            value.set(index in rule["days"])
        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for rule in self.schedules:
            self.listbox.insert(tk.END, rule["name"])
        self.listbox.selection_set(self.index)

    def switch(self, event=None):
        selection = self.listbox.curselection()
        if selection and selection[0] != self.index:
            if not self.capture():
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(self.index)
                return
            self.index = selection[0]
            self.load()

    def add(self):
        if not self.capture():
            return
        profiles = self.profile_combo.cget("values")
        self.schedules.append(normalize_schedule({"name": f"Schedule {len(self.schedules) + 1}",
                                                   "days": range(7), "profile": profiles[0]}))
        self.index = len(self.schedules) - 1
        self.load()

    def duplicate(self):
        if not self.capture():
            return
        rule = deepcopy(self.schedules[self.index])
        rule["name"] = rule["name"][:27] + " copy"
        self.schedules.append(rule)
        self.index = len(self.schedules) - 1
        self.load()

    def delete(self):
        if len(self.schedules) == 1:
            self.status.set("Keep at least one schedule.")
            return
        if messagebox.askyesno("Delete schedule", f"Delete {self.schedules[self.index]['name']}?", parent=self):
            self.schedules.pop(self.index)
            self.index = min(self.index, len(self.schedules) - 1)
            self.load()

    def save(self):
        if not self.capture():
            return False
        self.app.config["lighting_scheduler_enabled"] = self.master_enabled.get()
        self.app.config["lighting_schedules"] = deepcopy(self.schedules)
        self.app.config.save()
        scheduler = getattr(self.app, "lighting_scheduler", None)
        if scheduler:
            scheduler.reload()
        self.refresh_list()
        self.status.set("Schedules saved. Keep Keyboard Companion running; Cable mode is required.")
        return True

    def apply_now(self):
        if self.save():
            scheduler = getattr(self.app, "lighting_scheduler", None)
            if scheduler:
                scheduler.evaluate_now()
                self.status.set("Schedule queued for immediate evaluation.")

    def poll(self):
        scheduler = getattr(self.app, "lighting_scheduler", None)
        if scheduler and scheduler.status:
            self.status.set(scheduler.status)
        self.poll_job = self.after(500, self.poll)
