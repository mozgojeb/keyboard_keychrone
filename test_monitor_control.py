from contextlib import contextmanager
import ctypes
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from keeb_assistant.monitor_control import MonitorControl,MonitorError,input_codes
from keeb_assistant.monitor_shortcuts import MonitorShortcuts,parse_shortcut


class MonitorTests(unittest.TestCase):
    def test_advertised_input_codes(self):
        caps = '(vcp(10 12 60(11 12 0F 10) 62) mccs_ver(2.0))'
        self.assertEqual(input_codes(caps),[17,18,15,16])
        self.assertEqual(input_codes('(vcp(10 60))'),[])

    def test_ctrl_insert_and_invalid_shortcuts(self):
        self.assertEqual(parse_shortcut('CTRL+Ins'),(0x4002,0x2D))
        self.assertEqual(parse_shortcut('Ctrl+Insert'),(0x4002,0x2D))
        for invalid in ['F','A','Ctrl+','Ctrl+Fn','Insert']:
            with self.assertRaises(MonitorError): parse_shortcut(invalid)

    def backend(self,current=15):
        backend = MonitorControl.__new__(MonitorControl)
        backend.api = SimpleNamespace(SetVCPFeature=Mock(return_value=True))
        backend.current = Mock(return_value=current)
        @contextmanager
        def physical():
            yield [dict(id='chosen',handle=123),dict(id='other',handle=456)]
        backend.physical_monitors = physical
        return backend

    def test_toggle_targets_only_saved_monitor_and_opposite_input(self):
        backend = self.backend()
        self.assertEqual(backend.toggle('chosen',16,15),16)
        backend.api.SetVCPFeature.assert_called_once_with(123,0x60,16)
        backend.current.return_value = 16
        self.assertEqual(backend.toggle('chosen',16,15),15)
        backend.api.SetVCPFeature.assert_called_with(123,0x60,15)

    def test_missing_monitor_and_failed_read_do_not_send_commands(self):
        backend = self.backend()
        with self.assertRaises(MonitorError): backend.toggle('absent',16,15)
        backend.current.side_effect = MonitorError('unavailable')
        with self.assertRaises(MonitorError): backend.toggle('chosen',16,15)
        backend.api.SetVCPFeature.assert_not_called()

    def test_hotkey_registration_dispatch_conflict_and_shutdown(self):
        backend = SimpleNamespace(toggle=Mock(return_value=16))
        service = MonitorShortcuts(backend)
        rival = MonitorShortcuts(backend)
        settings = dict(enabled=True,monitor_id='chosen',first=16,second=15,shortcut='Ctrl+Alt+Shift+F24')
        try:
            service.configure(settings)
            with self.assertRaises(MonitorError): rival.configure(settings)
            self.assertEqual(service.settings,settings)
            ctypes.windll.user32.PostThreadMessageW(service.thread_id,0x312,1,0)
            deadline = time.monotonic()+2
            while not backend.toggle.called and time.monotonic()<deadline: time.sleep(.01)
            backend.toggle.assert_called_once_with('chosen',16,15)
            service.configure(dict(settings,enabled=False))
            rival.configure(settings)
        finally:
            service.stop()
            rival.stop()
        self.assertFalse(service.thread.is_alive())
        self.assertFalse(rival.thread.is_alive())


if __name__=='__main__': unittest.main()
