"""Host-side battery percentage model (charging compensation).

The keyboard derives its percentage from the *instantaneous* battery voltage.
While charging, the terminal voltage is inflated (IR rise during constant
current + the charger holding it high in constant voltage), so that percentage
overestimates the true resting state of charge.

Measured on a real K10 HE, the voltage inflation is not constant: it can be
~170-180 mV around raw 50%, ~120 mV around raw 76%, then taper to ~90 mV near
raw 95-96% once the charger is holding the cell close to the CV plateau. So
while *actively* charging we subtract an adaptive voltage offset before mapping
to %, which approximates the open-circuit (resting) voltage.

Only the value shown to the user is affected. The raw voltage/percentage that
the logger writes to the CSV are left untouched, so calibration data stays a
clean ground truth and the offset can be refined later from real samples.
"""

from __future__ import annotations

# Mirror the firmware thresholds (keychron/common/wireless/battery.{c,h}).
FULL_VOLTAGE_MV = 4100
EMPTY_VOLTAGE_MV = 3500
SHUTDOWN_VOLTAGE_MV = 3300

# Charge state (report byte 4): 0 = on battery, 1 = charging, 2 = full.
CHARGING_NONE = 0
CHARGING_ACTIVE = 1
CHARGING_FULL = 2

# Empirical starting point from early CSVs. Later low-SoC attach/unplug logs
# showed the charging voltage can be inflated by ~170-180 mV around raw 50%.
DEFAULT_CHARGE_OFFSET_MV = 120
MAX_ADAPTIVE_CHARGE_OFFSET_MV = 180
CHARGE_INFLATION_MIN_MV = 60

# A "full" charge state from the firmware can flicker briefly at non-full
# voltages, so never trust charging==2 alone. The tray layer also requires this
# condition to persist before snapping the user-visible value to 100%.
FULL_GUARD_MIN_MV = 4050
FULL_GUARD_MIN_RAW_PCT = 95


def voltage_to_percentage(mv: int) -> int:
    """Replicate the firmware's piecewise voltage -> percentage mapping."""
    if mv >= FULL_VOLTAGE_MV:
        return 100
    if mv > EMPTY_VOLTAGE_MV:
        span = FULL_VOLTAGE_MV - EMPTY_VOLTAGE_MV
        return int(round((mv - EMPTY_VOLTAGE_MV) * 80 / span + 20))
    if mv > SHUTDOWN_VOLTAGE_MV:
        span = EMPTY_VOLTAGE_MV - SHUTDOWN_VOLTAGE_MV
        return int(round((mv - SHUTDOWN_VOLTAGE_MV) * 20 / span))
    return 0


def corrected_percentage(
    voltage_mv: int,
    raw_percentage: int,
    charging: int,
    *,
    enabled: bool = True,
    offset_mv: int = DEFAULT_CHARGE_OFFSET_MV,
) -> int:
    """Return a charging-compensated percentage for *display only*.

    Falls back to the keyboard's own percentage when:
    * correction is disabled,
    * not actively charging (on battery, or already full), or
    * no voltage is available (e.g. the Windows/BLE mirror sends voltage_mv=0).

    The correction can only lower the charging reading toward its resting value,
    never raise it above what the keyboard reports.
    """
    if not enabled or charging != CHARGING_ACTIVE or voltage_mv <= 0:
        return raw_percentage
    adjusted = voltage_to_percentage(
        max(0, voltage_mv - adaptive_charge_offset(voltage_mv, raw_percentage, offset_mv))
    )
    return min(adjusted, raw_percentage)


def adaptive_charge_offset(
    voltage_mv: int,
    raw_percentage: int,
    base_offset_mv: int = DEFAULT_CHARGE_OFFSET_MV,
) -> int:
    """Return the voltage offset to subtract while actively charging.

    Recent logs show low-SoC charging around raw 48-51% relaxes to ~25% after
    unplug, requiring ~170-180 mV. High-SoC logs show raw 95-96% at ~4070 mV
    relaxes to raw 83-84% at ~3980 mV, so the high plateau needs only ~90 mV.
    Keep the user's configured value as a lower bound in the low/mid range, but
    allow the high plateau to taper below it.
    """
    base = max(0, int(base_offset_mv))
    if raw_percentage >= 95 and voltage_mv >= 4050:
        target = 90
        return min(MAX_ADAPTIVE_CHARGE_OFFSET_MV, target)
    if raw_percentage >= 90 and voltage_mv >= 4020:
        raw_factor = min(1.0, max(0.0, (raw_percentage - 90) / 5.0))
        voltage_factor = min(1.0, max(0.0, (voltage_mv - 4020) / 30.0))
        target = int(round(120 - 30 * max(raw_factor, voltage_factor)))
        return min(MAX_ADAPTIVE_CHARGE_OFFSET_MV, max(90, target))
    if raw_percentage <= 55:
        target = 175
    elif raw_percentage <= 75:
        # 55% -> 175 mV, 75% -> 155 mV
        target = 175 - int(round((raw_percentage - 55) * 20 / 20))
    else:
        # 75% -> 155 mV, 90% -> 120 mV. This bridges the mid-SoC correction
        # into the high-SoC taper without pulling raw 95-96% down to the 70s.
        target = 155 - int(round(min(15, raw_percentage - 75) * 35 / 15))
    return min(MAX_ADAPTIVE_CHARGE_OFFSET_MV, max(base, target))


def charging_voltage_is_inflated(current_mv: int, previous_battery_mv: int | None) -> bool:
    """True once charging voltage has actually risen above the battery baseline."""
    if previous_battery_mv is None or previous_battery_mv <= 0:
        return True
    return current_mv >= previous_battery_mv + CHARGE_INFLATION_MIN_MV


def is_full_charge_candidate(voltage_mv: int, raw_percentage: int, charging: int) -> bool:
    """Return True only for credible, high-voltage full-charge reports."""
    return (
        charging == CHARGING_FULL
        and voltage_mv >= FULL_GUARD_MIN_MV
        and raw_percentage >= FULL_GUARD_MIN_RAW_PCT
    )
