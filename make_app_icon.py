"""Generate assets/app.ico (a clean battery glyph) for the exe and tray identity.

Run once: python make_app_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "assets" / "app.ico"


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64.0
    outline = (235, 235, 235, 255)
    green = (90, 200, 120, 255)

    body = (6 * s, 18 * s, 52 * s, 46 * s)
    d.rounded_rectangle(body, radius=int(6 * s), outline=outline, width=max(2, int(3 * s)))
    d.rounded_rectangle((52 * s, 26 * s, 58 * s, 38 * s), radius=int(2 * s), fill=outline)
    # ~80% fill
    d.rounded_rectangle((10 * s, 22 * s, 42 * s, 42 * s), radius=int(3 * s), fill=green)
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base = draw(256)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(OUT, format="ICO", sizes=sizes)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
