"""Overlay compositing, transient wire writes, and device-filter checks."""
import threading
import time
import unittest
from unittest.mock import Mock
from keeb_assistant.hid_reader import BatteryReader, _HidRequest
from keeb_assistant.keypress_input import key_led, KeypressInput
from keeb_assistant.lighting_profiles import normalize_profile
from keeb_assistant.lighting_overlay import render_frame, base_colors, write_frame, LightingOverlay
from test_per_key_lighting import FakeKeyboard


class OverlayTests(unittest.TestCase):
    def profile(self, **changes):
        return normalize_profile(dict(color='#0000FF',accent='#0000FF',
                                      keypress_effect='Splash',keypress_color='#FFFFFF',
                                      keypress_duration=1200,**changes))

    def test_static_base_survives_splash_and_returns_exactly_after_fade(self):
        p = self.profile()
        base = base_colors(p)
        self.assertEqual(render_frame(p,[],10),base)
        frame = render_frame(p,[(59,10)],10)
        self.assertEqual(frame[59],'#FFFFFF')
        self.assertEqual(frame[104],base[104])
        ring = render_frame(p,[(59,10)],10.3)
        self.assertNotEqual(ring,base)
        self.assertEqual(render_frame(p,[(59,10)],12),base)

    def test_reactive_only_changes_pressed_key(self):
        p = self.profile()
        p['keypress_effect'] = 'Reactive'
        frame = render_frame(p,[(39,2)],2.1)
        changed = [i for i,(a,b) in enumerate(zip(frame,base_colors(p))) if a!=b]
        self.assertEqual(changed,[39])

    def test_only_matching_device_key_down_events_trigger(self):
        name = 'HID#VID_3434&PID_0EA1&MI_00'
        self.assertEqual(key_led(name,30,0),59)
        self.assertEqual(key_led(name,41,0),16)
        self.assertEqual(key_led(name,28,0),50)
        self.assertEqual(key_led(name,28,2),91)
        self.assertIsNone(key_led(name,30,1))
        self.assertIsNone(key_led('HID#VID_1234&PID_0EA1',30,0))

    def test_frame_packets_fit_report_and_never_write_eeprom(self):
        reader = FakeKeyboard()
        base = base_colors(self.profile())
        write_frame(reader,base)
        self.assertEqual(len(reader.sent),12)
        self.assertTrue(all(p[:2] == bytes([0xA8,10]) and len(p)<=32 for p in reader.sent))
        reader.sent.clear()
        write_frame(reader,base,base)
        self.assertEqual(reader.sent,[])

    def test_normalization_preserves_overlay_and_enforces_static_base(self):
        p = self.profile(effect='Breathing')
        self.assertEqual(p['effect'],'Static')
        self.assertEqual(normalize_profile(p),p)

    def test_worker_stop_restores_base(self):
        class Listener:
            def __init__(self, callback): self.callback = callback
            def start(self): pass
            def stop(self): pass
        reader = FakeKeyboard()
        engine = LightingOverlay(reader,Listener)
        engine.start(self.profile())
        engine.hit(59)
        deadline = time.monotonic()+2
        while not reader.sent and time.monotonic()<deadline:
            time.sleep(.01)
        engine.stop()
        self.assertFalse(engine.thread.is_alive())
        self.assertTrue(reader.sent)
        restored = reader.sent[-12:]
        self.assertEqual([p[2] for p in restored],list(range(0,105,9)))
        self.assertTrue(all(p[:2] == bytes([0xA8,10]) for p in reader.sent))

    def test_native_listener_starts_and_stops_without_keyboard_input(self):
        listener = KeypressInput(lambda led: None)
        listener.start()
        try:
            self.assertTrue(listener.thread.is_alive())
        finally:
            listener.stop()
        self.assertFalse(listener.thread.is_alive())

    def test_lighting_request_ignores_receiver_when_usb_is_connected(self):
        reader = BatteryReader(lambda reading: None)
        usb, receiver = Mock(), Mock()
        usb.read.return_value = [0xA8,10,0]+[0]*29
        reader._devices = {b'HID#VID_3434&PID_0EA1&MI_01':usb}
        reader._bridge_devices = {b'HID#VID_3434&PID_D030':receiver}
        request = _HidRequest(bytes([0xA8,10,0,1,0,0,255]),0xA8,10,.2,threading.Event(),target_pid=0x0EA1)
        reader._perform_request(request)
        self.assertTrue(request.done.is_set())
        self.assertIsNotNone(request.response)
        usb.write.assert_called_once()
        receiver.write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
