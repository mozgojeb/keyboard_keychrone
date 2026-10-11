"""Lighting profile model and normalization helpers."""

from __future__ import annotations

from copy import deepcopy
import re

from .config import DEFAULTS

EFFECTS = ("Static", "Breathing", "Reactive", "Splash")
KEYPRESS_EFFECTS = ("None", "Reactive", "Splash")
_EFFECT_ALIASES = {"Wave": "Breathing", "Ripple": "Splash", "Breathe": "Breathing"}
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalize_profile(profile: dict | None, fallback_name: str = "New profile") -> dict:
    source = profile if isinstance(profile, dict) else {}
    name = str(source.get("name") or fallback_name).strip()[:32] or fallback_name
    effect = str(source.get("effect") or "Static")
    effect = _EFFECT_ALIASES.get(effect, effect)
    if effect not in EFFECTS:
        effect = "Static"
    keypress = source.get('keypress_effect', 'None')
    if keypress not in KEYPRESS_EFFECTS:
        keypress = 'None'
    if keypress != 'None':
        effect = 'Static'

    def color(key: str, default: str) -> str:
        value = str(source.get(key) or default).upper()
        return value if _HEX_COLOR.fullmatch(value) else default

    def bounded_int(key: str, default: int) -> int:
        try:
            value = int(source.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(0, min(100, value))

    key_colors = {}
    raw_colors = source.get('key_colors', {})
    if isinstance(raw_colors, dict):
        for index, value in raw_colors.items():
            try:
                led = int(index)
            except (TypeError, ValueError):
                continue
            value = str(value).upper()
            if 0 <= led < 105 and _HEX_COLOR.fullmatch(value):
                key_colors[str(led)] = value

    return {
        "name": name,
        "effect": effect,
        "color": color("color", "#18D9FF"),
        "accent": color("accent", "#7C5CFF"),
        "brightness": bounded_int("brightness", 80),
        "speed": bounded_int("speed", 50),
        "layout": "k10_he_iso",
        "key_colors": key_colors,
        "keypress_effect": keypress,
        "keypress_color": color('keypress_color', '#FF6030'),
        "keypress_duration": max(200, min(3000, _duration(source.get('keypress_duration', 1200)))),
    }


def _duration(value):
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return 1200


def load_profiles(config) -> list[dict]:
    raw = config.get("lighting_profiles", [])
    profiles = [normalize_profile(item) for item in raw if isinstance(item, dict)]
    if not profiles:
        profiles = deepcopy(DEFAULTS["lighting_profiles"])
    return profiles


def save_profiles(config, profiles: list[dict], active_name: str) -> None:
    normalized = [normalize_profile(item) for item in profiles]
    config["lighting_profiles"] = normalized
    config["active_lighting_profile"] = active_name
    config.save()
