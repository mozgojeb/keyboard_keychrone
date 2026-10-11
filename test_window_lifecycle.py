"""Regression check for tray requests and repeated Tk window lifetimes."""
import gc
import queue
import threading
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from keeb_assistant.config import Config
from keeb_assistant.tray_app import TrayApp
from keeb_assistant.tray_menu import show_tray_menu


class WindowLifecycleTest(unittest.TestCase):
    def test_tray_settings_click_requests_main_window(self):
        app = TrayApp.__new__(TrayApp)
        app.config = Config()
        app.icon = Mock()
        app._stop = threading.Event()
        app._window_requests = queue.Queue()
        app._windows = {}
        app._snapshot = lambda: (None, None)
        app._tk_root = tk.Tk()
        app._tk_root.withdraw()
        try:
            popup = show_tray_menu(app, app._tk_root)
            app._tk_root.update()
            panel = popup.winfo_children()[0]
            rows = [child for child in panel.winfo_children()
                    if child.winfo_class() == "Frame"]
            # The first row is the heading and the next actionable rows are
            # Lighting and Settings.
            rows[3].winfo_children()[1].event_generate("<Button-1>")
            app._tk_root.update()
            self.assertEqual(app._window_requests.get_nowait(), ("main", "settings"))
        finally:
            app._windows.clear()
            app._tk_root.destroy()

    def test_worker_requests_reuse_and_reopen_main_thread_windows(self):
        app = TrayApp.__new__(TrayApp)
        app.config = Config()
        app._stop = threading.Event()
        app._window_requests = queue.Queue()
        app._windows = {}
        app._snapshot = lambda: (None, None)
        app._tk_root = tk.Tk()
        app._tk_root.withdraw()
        errors = []
        app._tk_root.report_callback_exception = lambda *args: errors.append(args)

        def request(tab):
            worker = threading.Thread(target=lambda: app._open_main_window(tab))
            worker.start()
            worker.join()
            app._drain_window_requests()
            app._tk_root.update()

        try:
            with patch('sys.excepthook', side_effect=lambda *args: errors.append(args)):
                for _ in range(8):
                    request('lighting')
                    window = app._windows['main']
                    self.assertTrue(window.winfo_viewable())
                    request('settings')
                    self.assertIs(window, app._windows['main'])
                    window.destroy()
                    gc.collect()
                request('device')
                app._stop.set()
                app._open_main_window('lighting')
                self.assertTrue(app._window_requests.empty())
                self.assertEqual(errors, [])
        finally:
            app._windows.clear()
            app._tk_root.destroy()
            gc.collect()


if __name__ == '__main__':
    unittest.main()
