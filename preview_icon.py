"""Render sample tray icons into a single preview PNG (assets/preview.png)."""
from pathlib import Path

from PIL import Image

from keeb_assistant.icon import make_icon

samples = [
    ("67", make_icon(67, charging=False, connected=True)),
    ("67chg", make_icon(67, charging=True, connected=True)),
    ("100", make_icon(100, charging=False, connected=True)),
    ("9", make_icon(9, charging=False, connected=True)),
    ("none", make_icon(None, connected=False)),
]

pad = 8
cell = 64
sheet = Image.new("RGBA", (len(samples) * (cell + pad) + pad, cell + 2 * pad), (40, 40, 40, 255))
x = pad
for _, im in samples:
    sheet.alpha_composite(im, (x, pad))
    x += cell + pad

# Also a downscaled row (~22px) to simulate the real tray size.
small = Image.new("RGBA", (sheet.width, 22 + 2 * pad), (40, 40, 40, 255))
x = pad
for _, im in samples:
    s = im.resize((22, 22), Image.LANCZOS)
    small.alpha_composite(s, (x, pad))
    x += cell + pad

out = Image.new("RGBA", (sheet.width, sheet.height + small.height), (40, 40, 40, 255))
out.alpha_composite(sheet, (0, 0))
out.alpha_composite(small, (0, sheet.height))

dest = Path(__file__).parent / "assets" / "preview.png"
dest.parent.mkdir(parents=True, exist_ok=True)
out.convert("RGB").save(dest)
print(f"wrote {dest}")
