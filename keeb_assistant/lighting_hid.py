"""Keychron RGB profile writer over the documented 0xA8 raw-HID protocol."""

from __future__ import annotations

import colorsys
from .keyboard_layout import KEYS

KC_GET_SUPPORT_FEATURE = 0xA2
KC_KEYCHRON_RGB = 0xA8
FEATURE_KEYCHRON_RGB = 0x0080

RGB_SAVE = 0x02
RGB_GET_LED_COUNT = 0x05
PER_KEY_RGB_SET_TYPE = 0x08
PER_KEY_RGB_SET_COLOR = 0x0A
RGB_GET_LED_IDX = 0x06
VIA_SET = 0x07
VIA_GET = 0x08
VIA_SAVE = 0x09
RGB_CHANNEL = 3
K10_HE_PER_KEY_MODE = 23

EFFECT_IDS = {
    "Static": 0,
    "Breathing": 1,
    "Reactive": 2,
    "Splash": 4,
}


class LightingError(RuntimeError):
    pass


def _rgb_to_hsv(hex_color: str, brightness: int) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    hue, saturation, _ = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    level = max(0, min(100, int(brightness))) / 100
    return round(hue * 255) % 256, round(saturation * 255), round(level * 255)


def _request(reader, payload: bytes, *, subcommand: int | None = None, timeout: float = 0.8) -> bytes:
    response = reader.request(
        payload,
        expected_command=payload[0],
        expected_subcommand=subcommand,
        timeout=timeout,
        target_pid=0x0EA1,
    )
    if response is None:
        raise LightingError("Keyboard did not answer. Switch it to Cable mode and retry.")
    return response


def apply_profile(reader, profile: dict) -> int:
    """Apply profile to every addressable LED and persist it in keyboard EEPROM."""
    features = _request(reader, bytes([KC_GET_SUPPORT_FEATURE]))
    if len(features) < 4 or not ((features[2] | (features[3] << 8)) & FEATURE_KEYCHRON_RGB):
        raise LightingError("Connected firmware does not advertise Keychron RGB control.")

    count_response = _request(
        reader,
        bytes([KC_KEYCHRON_RGB, RGB_GET_LED_COUNT]),
        subcommand=RGB_GET_LED_COUNT,
    )
    if len(count_response) < 4 or count_response[2] != 0:
        raise LightingError("Keyboard rejected LED discovery.")
    led_count = count_response[3]
    if not 1 <= led_count <= 200:
        raise LightingError(f"Keyboard returned invalid LED count: {led_count}.")

    if led_count != len(KEYS):
        raise LightingError('This editor requires the K10 HE ISO 105-key layout.')
    # Confirm the matrix before any write; other models can have 105 LEDs too.
    for row in range(6):
        row_keys = [key for key in KEYS if key['row'] == row]
        mask = sum(1 << key['col'] for key in row_keys)
        response = _request(reader, bytes([KC_KEYCHRON_RGB, RGB_GET_LED_IDX, row]) +
                            mask.to_bytes(3, 'little'), subcommand=RGB_GET_LED_IDX)
        if len(response) < 24 or response[2] != 0 or any(
            response[3 + key['col']] != key['led'] for key in row_keys
        ):
            raise LightingError('Connected keyboard LED map does not match K10 HE ISO.')

    effect_id = EFFECT_IDS.get(profile.get("effect"), EFFECT_IDS["Static"])
    response = _request(
        reader,
        bytes([KC_KEYCHRON_RGB, PER_KEY_RGB_SET_TYPE, effect_id]),
        subcommand=PER_KEY_RGB_SET_TYPE,
    )
    if len(response) < 3 or response[2] != 0:
        raise LightingError("Keyboard rejected lighting effect.")

    primary = _rgb_to_hsv(profile["color"], profile["brightness"])
    accent = _rgb_to_hsv(profile["accent"], profile["brightness"])
    for index in range(led_count):
        custom_color = profile.get('key_colors', {}).get(str(index))
        hue, saturation, value = (_rgb_to_hsv(custom_color, profile['brightness'])
                                  if custom_color else (primary if index % 5 < 3 else accent))
        response = _request(
            reader,
            bytes([
                KC_KEYCHRON_RGB,
                PER_KEY_RGB_SET_COLOR,
                index,
                1,
                hue,
                saturation,
                value,
            ]),
            subcommand=PER_KEY_RGB_SET_COLOR,
        )
        if len(response) < 3 or response[2] != 0:
            raise LightingError(f"Keyboard rejected LED {index}.")

    # Keychron's custom solid effect uses the global value, not per-LED HSV.v.
    for value_id, value in ((2, K10_HE_PER_KEY_MODE),
                            (1, round(profile['brightness'] * 255 / 100)),
                            (3, round(profile.get('speed', 50) * 255 / 100))):
        payload = bytes([VIA_SET, RGB_CHANNEL, value_id, value])
        response = _request(reader, payload, subcommand=RGB_CHANNEL)
        if response[:4] != payload:
            raise LightingError('Keyboard rejected custom lighting mode or brightness.')
        response = _request(reader, bytes([VIA_GET, RGB_CHANNEL, value_id]), subcommand=RGB_CHANNEL)
        if len(response) < 4 or response[2] != value_id or abs(response[3] - value) > (2 if value_id == 1 else 0):
            raise LightingError('Keyboard did not confirm the lighting settings.')

    response = _request(
        reader,
        bytes([KC_KEYCHRON_RGB, RGB_SAVE]),
        subcommand=RGB_SAVE,
        timeout=1.5,
    )
    if len(response) < 3 or response[2] != 0:
        raise LightingError("Keyboard changed lighting but could not save it.")
    response = _request(reader, bytes([VIA_SAVE, RGB_CHANNEL]), subcommand=RGB_CHANNEL)
    if response[:2] != bytes([VIA_SAVE, RGB_CHANNEL]):
        raise LightingError('Colours saved, but the keyboard could not save custom lighting mode.')
    return led_count


def set_brightness(reader, brightness: int) -> None:
    """Set global backlight brightness without rewriting every key colour."""
    value = round(max(0, min(100, int(brightness))) * 255 / 100)
    payload = bytes([VIA_SET, RGB_CHANNEL, 1, value])
    response = _request(reader, payload, subcommand=RGB_CHANNEL)
    if response[:4] != payload:
        raise LightingError("Keyboard rejected backlight brightness.")
    response = _request(reader, bytes([VIA_GET, RGB_CHANNEL, 1]), subcommand=RGB_CHANNEL)
    if len(response) < 4 or response[2] != 1 or abs(response[3] - value) > 2:
        raise LightingError("Keyboard did not confirm backlight brightness.")
    response = _request(reader, bytes([VIA_SAVE, RGB_CHANNEL]), subcommand=RGB_CHANNEL)
    if response[:2] != bytes([VIA_SAVE, RGB_CHANNEL]):
        raise LightingError("Backlight changed but could not be saved.")
