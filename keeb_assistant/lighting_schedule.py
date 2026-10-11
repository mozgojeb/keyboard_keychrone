"""Weekly backlight scheduling and background application service."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
import threading

from .lighting_profiles import load_profiles

TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def normalize_schedule(schedule: dict | None, fallback_name: str = "Schedule") -> dict:
    source = schedule if isinstance(schedule, dict) else {}
    days = []
    for value in source.get("days", []):
        try:
            day = int(value)
        except (TypeError, ValueError):
            continue
        if 0 <= day <= 6 and day not in days:
            days.append(day)
    on_time = str(source.get("on_time", "18:00"))
    off_time = str(source.get("off_time", "23:00"))
    return {
        "name": str(source.get("name") or fallback_name).strip()[:32] or fallback_name,
        "enabled": bool(source.get("enabled", True)),
        "days": sorted(days),
        "on_time": on_time if TIME_RE.fullmatch(on_time) else "18:00",
        "off_time": off_time if TIME_RE.fullmatch(off_time) else "23:00",
        "profile": str(source.get("profile") or "").strip()[:32],
    }


def load_schedules(config) -> list[dict]:
    raw = config.get("lighting_schedules", [])
    return [normalize_schedule(item, f"Schedule {index + 1}")
            for index, item in enumerate(raw) if isinstance(item, dict)]


def active_schedule(schedules: list[dict], now: datetime) -> dict | None:
    """Return first active rule. Days identify days when its on-time occurs."""
    minute = now.hour * 60 + now.minute
    today = now.weekday()
    yesterday = (today - 1) % 7
    for raw in schedules:
        rule = normalize_schedule(raw)
        if not rule["enabled"] or not rule["days"]:
            continue
        start_h, start_m = (int(part) for part in rule["on_time"].split(":"))
        end_h, end_m = (int(part) for part in rule["off_time"].split(":"))
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start == end:
            continue
        if start < end:
            inside = today in rule["days"] and start <= minute < end
        else:
            inside = ((today in rule["days"] and minute >= start) or
                      (yesterday in rule["days"] and minute < end))
        if inside:
            return rule
    return None


class LightingScheduler:
    def __init__(self, app, interval: float = 30.0):
        self.app = app
        self.interval = interval
        self.status = "Scheduler disabled."
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._applied = None
        self._thread = threading.Thread(target=self._run, daemon=True, name="LightingScheduler")

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def reload(self) -> None:
        self._applied = None
        self._wake.set()

    def evaluate_now(self) -> None:
        self.reload()

    def _profile(self, name: str) -> dict:
        profiles = load_profiles(self.app.config)
        return deepcopy(next((profile for profile in profiles if profile["name"] == name), profiles[0]))

    def _run(self) -> None:
        while not self._stop.is_set():
            enabled = bool(self.app.config.get("lighting_scheduler_enabled", False))
            if not enabled:
                self.status = "Scheduler disabled."
                self._applied = None
            else:
                rule = active_schedule(load_schedules(self.app.config), datetime.now())
                desired = ("on", rule["profile"]) if rule else ("off",)
                if desired != self._applied:
                    try:
                        if rule:
                            profile = self._profile(rule["profile"])
                            self.app.apply_lighting_profile(profile)
                            self.status = f"Backlight on · {rule['name']} · {profile['name']}"
                        else:
                            self.app.turn_lighting_off()
                            self.status = "Backlight off · outside scheduled hours"
                        self._applied = desired
                    except Exception as exc:
                        self.status = f"Waiting to apply schedule: {exc}"
            self._wake.wait(self.interval)
            self._wake.clear()
