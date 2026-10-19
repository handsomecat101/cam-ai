# -*- coding: utf-8 -*-
"""Coordinator: phong to mot vung cua anh chup de kiem tra chi tiot bang mat.

Dung: .venv\\Scripts\\python.exe -W ignore _kk_zoom_v3.py <ten> <x> <y> <w> <h> [cuong]
"""
import os
import sys

from PIL import Image

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(APP_DIR, "_kk_out")


def main():
    if len(sys.argv) < 6:
        print("Dung: _kk_zoom_v3.py <anh> <x> <y> <w> <h> [cuong]")
        return 1
    ten = sys.argv[1]
    x, y, w, h = (int(v) for v in sys.argv[2:6])
    cuong = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
    duong = os.path.join(OUT, f"{ten}.png")
    if not os.path.exists(duong):
        duong = os.path.join(APP_DIR, "_kk_out", f"{ten}.png")
    img = Image.open(duong)
    vung = img.crop((x, y, x + w, y + h)).convert("RGB")
    vung = vung.resize((int(vung.width * cuong), int(vung.height * cuong)),
                       Image.LANCZOS)
    ra = os.path.join(OUT, f"zoom_{ten}.png")
    vung.save(ra)
    print(f"  [zoom] {ra} ({vung.size[0]}x{vung.size[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
