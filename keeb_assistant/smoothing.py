"""Smoothing of the noisy battery percentage.

Li-po voltage sags under load and recovers at rest, so the raw percentage
jitters by a few points. We apply:

* an exponential moving average (EMA) on the percentage, and
* a hysteresis deadband on the *displayed* integer, so the shown value only
  moves when the smoothed estimate has drifted past a threshold (or, while
  charging, monotonically follows upward).
* a small anti-spike gate while on battery: sudden upward jumps have to persist
  for a few samples before entering the EMA.

This keeps the indicator stable without lying about big real changes.
"""

from __future__ import annotations


class BatterySmoother:
    def __init__(
        self,
        alpha: float = 0.3,
        deadband: float = 1.5,
        upward_spike_threshold: float = 3.0,
        upward_spike_confirmations: int = 8,
    ):
        # alpha: EMA weight for the newest sample (0..1). Lower = smoother/slower.
        self.alpha = max(0.01, min(1.0, alpha))
        self.deadband = max(0.0, deadband)
        self.upward_spike_threshold = max(0.0, upward_spike_threshold)
        self.upward_spike_confirmations = max(1, upward_spike_confirmations)
        self._ema: float | None = None
        self._displayed: int | None = None
        self._last_input: float | None = None
        self._pending_up: float | None = None
        self._pending_up_count = 0

    def reset(self) -> None:
        self._ema = None
        self._displayed = None
        self._last_input = None
        self._pending_up = None
        self._pending_up_count = 0

    def _filter_input(self, raw: float, charging: bool) -> float:
        if charging or self._last_input is None or self.upward_spike_threshold <= 0:
            self._pending_up = None
            self._pending_up_count = 0
            self._last_input = raw
            return raw

        # On battery, real SoC should not climb sharply. The K10 HE voltage logs
        # around 25-35% contain isolated upward jumps of 10+ points, so hold the
        # previous accepted input unless the higher value persists.
        if raw > self._last_input + self.upward_spike_threshold:
            if self._ema is not None and raw <= self._ema + self.upward_spike_threshold:
                self._pending_up = None
                self._pending_up_count = 0
                self._last_input = raw
                return raw
            if self._pending_up is not None and raw >= self._pending_up - 1.0:
                self._pending_up_count += 1
            else:
                self._pending_up = raw
                self._pending_up_count = 1

            if self._pending_up_count < self.upward_spike_confirmations:
                return self._last_input

        self._pending_up = None
        self._pending_up_count = 0
        self._last_input = raw
        return raw

    def update(self, raw_percentage: int, charging: bool = False) -> int:
        """Feed a raw percentage, get the value to display."""
        raw = float(max(0, min(100, raw_percentage)))
        raw = self._filter_input(raw, charging)

        if self._ema is None:
            self._ema = raw
        else:
            self._ema = self.alpha * raw + (1.0 - self.alpha) * self._ema

        if self._displayed is None:
            self._displayed = int(round(self._ema))
            return self._displayed

        # Snap to the extremes without waiting (0% and 100% are meaningful).
        if raw >= 100.0:
            self._displayed = 100
        elif raw <= 0.0:
            self._displayed = 0
        elif abs(self._ema - self._displayed) >= self.deadband:
            self._displayed = int(round(self._ema))

        return self._displayed

    @property
    def displayed(self) -> int | None:
        return self._displayed

    @property
    def ema(self) -> float | None:
        return self._ema
