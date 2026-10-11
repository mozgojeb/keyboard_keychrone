"""Per-key colour persistence, layout, UI selection, and wire protocol checks."""
from copy import deepcopy
from types import SimpleNamespace
import tkinter as tk
import unittest
from unittest.mock import Mock

from keeb_assistant.config import Config
from keeb_assistant.keyboard_layout import KEYS
from keeb_assistant.lighting_editor import LightingEditor, section_keys
from keeb_assistant.lighting_profiles import normalize_profile, load_profiles
from keeb_assistant.lighting_hid import apply_profile, LightingError


class FakeKeyboard:
    def __init__(self):
        self.sent = []
        self.values = {}
        self.led_count = 105

    def request(self, payload, **kwargs):
        self.sent.append(payload)
        result = bytearray(32)
        result[:len(payload)] = payload
        if payload[0] == 0xA2:
            result[2] = 0x80
        elif payload[:2] == bytes([0xA8,5]):
            result[2:4] = bytes([0,self.led_count])
        elif payload[:2] == bytes([0xA8,6]):
            row = payload[2]
            result[2] = 0
            result[3:24] = bytes([255])*21
            for key in KEYS:
                if key['row'] == row:
                    result[3+key['col']] = key['led']
        elif payload[0] == 0xA8:
            result[2] = 0
        elif payload[0] == 7:
            self.values[payload[2]] = payload[3]
        elif payload[0] == 8:
            result[3] = self.values[payload[2]]
        return bytes(result)


class PerKeyTests(unittest.TestCase):
    def test_white_section_and_other_colours_survive_save_reload(self):
        config = Config()
        config.save = Mock()
        root = tk.Tk()
        root.geometry('1180x790')
        root.withdraw()
        app = SimpleNamespace(config=config)
        editor = LightingEditor(root,app)
        editor.pack(fill='both',expand=True)
        root.update_idletasks()
        try:
            editor.select_section('All')
            editor.paint_color.set('#FF0000')
            editor.paint()
            editor.select_section('Numpad')
            editor.paint_color.set('#FFFFFF')
            editor.paint()
            self.assertEqual(len(editor.selected),17)
            editor.save()
            saved = load_profiles(config)[editor.index]
            for key in KEYS:
                self.assertEqual(saved['key_colors'][str(key['led'])],
                                 '#FFFFFF' if key['led'] in section_keys('Numpad') else '#FF0000')
            before = deepcopy(saved)
            editor.duplicate()
            editor.select_section('WASD')
            editor.paint_color.set('#00FF00')
            editor.paint()
            editor.save()
            self.assertEqual(load_profiles(config)[0],before)
            # Clicking a wide space bar selects only its actual LED.
            a,b,c,d = editor.boxes[95]
            editor.press(SimpleNamespace(x=(a+c)/2,y=(b+d)/2,state=0))
            self.assertEqual(editor.selected,{95})
            a,b,c,d = editor.boxes[50]
            editor.press(SimpleNamespace(x=(a+c)/2,y=(b+d)/2,state=4))
            self.assertEqual(editor.selected,{50,95})
        finally:
            root.destroy()

    def test_wire_preserves_selected_white_and_activates_custom_mode(self):
        reader = FakeKeyboard()
        profile = normalize_profile({'color':'#FF0000','accent':'#FF0000',
                                    'key_colors':{str(k):'#FFFFFF' for k in section_keys('Numpad')}})
        self.assertEqual(apply_profile(reader,profile),105)
        writes = [p for p in reader.sent if p[:2] == bytes([0xA8,10])]
        self.assertEqual(len(writes),105)
        for p in writes:
            self.assertEqual(p[5],0 if p[2] in section_keys('Numpad') else 255)
        self.assertIn(bytes([7,3,2,23]),reader.sent)
        self.assertEqual(reader.sent[-1],bytes([9,3]))

    def test_wrong_layout_stops_before_any_write(self):
        reader = FakeKeyboard()
        reader.led_count = 104
        with self.assertRaises(LightingError):
            apply_profile(reader,normalize_profile({}))
        self.assertFalse(any(p[0] == 7 or p[:2] == bytes([0xA8,10]) for p in reader.sent))

    def test_normalization_rejects_bad_colour_and_out_of_range_keys(self):
        profile = normalize_profile({'key_colors':{'0':'#ffffff','105':'#FF0000','bad':'#FFFFFF','1':'oops'}})
        self.assertEqual(profile['key_colors'],{'0':'#FFFFFF'})


if __name__ == '__main__':
    unittest.main()
