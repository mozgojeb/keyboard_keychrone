"""Open the Lighting tab without starting the tray service."""

from __future__ import annotations

from threading import RLock

from keeb_assistant.config import Config
from keeb_assistant.main_window import open_main_window


class PreviewApp:
    def __init__(self):
        self.config = Config.load()
        self._lock = RLock()
        self._device_label = "Keychron K10 HE"

    def _snapshot(self):
        return None, None

    def _open_flash_wizard(self):
        return None


if __name__ == "__main__":
    open_main_window(PreviewApp(), initial_tab="lighting")
