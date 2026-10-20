# -*- coding: utf-8 -*-
"""Phong to 3x mot vung cua anh chup de kiem tra loi thi giac."""
import sys
from PIL import Image

src = sys.argv[1]
dst = sys.argv[2]
x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7])
im = Image.open(src)
crop = im.crop((x0, y0, x1, y1))
w, h = crop.size
crop = crop.resize((w * 3, h * 3), Image.LANCZOS)
crop.save(dst)
print(f"{dst} {crop.size}")
