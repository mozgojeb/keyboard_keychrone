"""Generate the K10 HE ISO map from Keychron's 2025q3 GPLv2 firmware."""
import json
from pathlib import Path
import re

base = Path(__file__).parent
source = (base / 'iso.c').read_text()
matrix_block = source.split('// Key Matrix to LED Index')[1].split('// LED Index to Physical Position')[0]
matrix = [[None if n == '__' else int(n) for n in re.findall(r'\b\d+\b|__', row)]
          for row in re.findall(r'\{([^{}]+)\}', matrix_block)]
labels = [
    ['Esc'] + [f'F{i}' for i in range(1,13)] + ['PrtSc','ScrLk','Pause'],
    ['`'] + list('1234567890') + ['-','=','Backspace','Ins','Home','PgUp','Num','/','*','-'],
    ['Tab'] + list('QWERTYUIOP') + ['[',']','Enter','Del','End','PgDn','7','8','9','+'],
    ['Caps'] + list('ASDFGHJKL') + [';',"'",'#','4','5','6'],
    ['Shift','\\'] + list('ZXCVBNM') + [',','.','/','Shift','↑','1','2','3','Enter'],
    ['Ctrl','Win','Alt','Space','Alt','Fn','Menu','Ctrl','←','↓','→','0','.'],
]
flat = sum(labels, [])
assert len(flat) == 105
keys = []
for key in json.loads((base/'keyboard.json').read_text())['layouts']['LAYOUT_105_iso']['layout']:
    row, col = key['matrix']
    led = matrix[row][col]
    assert led is not None
    keys.append(dict(led=led, label=flat[led], row=row, col=col,
                     x=key['x'], y=key['y'], w=key.get('w',1), h=key.get('h',1)))
keys.sort(key=lambda key: key['led'])
assert [k['led'] for k in keys] == list(range(105))
header = '''"""K10 HE ISO key geometry and LED map.

Derived from Keychron qmk_firmware, branch 2025q3:
keyboards/keychron/k10_he/iso/{keyboard.json,iso.c}.
Copyright 2025 Keychron. GPL-2.0-or-later; see LICENSE.
Regenerate with reference/generate_layout.py.
"""

LAYOUT_ID = "k10_he_iso"
KEYS = [
'''
(base.parent/'keeb_assistant'/'keyboard_layout.py').write_text(
    header + ''.join('    '+repr(key)+',\n' for key in keys) + ']\n', encoding='utf-8')
