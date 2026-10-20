# -*- coding: utf-8 -*-
"""
CamAI - Tao file icon app tu anh AI (Nano Banana Pro).

Viet lai anh AI 1K ve thanh icon vuong, cat phan nen thua, can chinh duong vien
va tao day du kich thuoc Windows: PNG 512 + ICO nhieu kich thuoc.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_lam_icon_app.py <anh_nguon.png>

Mac dinh neu khong truyen: doc tu _kk_out\\icon\\camai-icon-var-d.png
Ket qua ghi vao assets\\camai.png va assets\\camai.ico
"""

from __future__ import annotations

import os
import sys

from PIL import Image

APP_DIR = os.path.dirname(os.path.abspath(__file__))
THU_MUC_ASSETS = os.path.join(APP_DIR, "assets")
MAC_DINH_NGUON = os.path.join(APP_DIR, "_kk_out", "icon", "camai-icon-var-d.png")

KICH_THUOC_PNG = 512
KICH_THUOC_ICO = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                  (128, 128), (256, 256)]
CANH_VI = 0.06          # vien trong (6%) o moi canh


def mau_nen(anh: Image.Image) -> tuple:
    """Lay mau nen tu 4 goc anh (gia su nen phang)."""
    w, h = anh.size
    goc = [anh.getpixel((0, 0)), anh.getpixel((w - 1, 0)),
           anh.getpixel((0, h - 1)), anh.getpixel((w - 1, h - 1))]
    return goc[0]


def cat_noi_dung(anh: Image.Image, mau_bg) -> Image.Image:
    """Cat vung khac mau nen, giu vien 2%."""
    rgb = anh.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    nguong = 26
    xs, ys = [], []
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b = px[x, y]
        # vong lap nhanh hon de nhanh
    bang = rgb.load()
    for y in range(h):
        for x in range(w):
            r, g, b = bang[x, y]
            if abs(r - mau_bg[0]) + abs(g - mau_bg[1]) + abs(b - mau_bg[2]) > nguong:
                xs.append(x)
                ys.append(y)
    if not xs:
        return rgb
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    canh = int(0.02 * max(x1 - x0, y1 - y0))
    x0 = max(0, x0 - canh)
    y0 = max(0, y0 - canh)
    x1 = min(w - 1, x1 + canh)
    y1 = min(h - 1, y1 + canh)
    return rgb.crop((x0, y0, x1 + 1, y1 + 1))


def canh_vuong(anh: Image.Image, canh_px: int, mau_bg) -> Image.Image:
    """Canh vuong + nen, noi dung canh giua."""
    w, h = anh.size
    c = max(w, h)
    nen = Image.new("RGB", (c, c), mau_bg)
    nen.paste(anh, ((c - w) // 2, (c - h) // 2))
    return nen


def chay(duong_dan_nguon: str) -> int:
    if not os.path.isfile(duong_dan_nguon):
        print(f"LOI: khong tim thay anh nguon: {duong_dan_nguon}")
        return 2
    os.makedirs(THU_MUC_ASSETS, exist_ok=True)

    goc = Image.open(duong_dan_nguon).convert("RGB")
    print(f"anh nguon : {duong_dan_nguon} {goc.size}")

    mau_bg = mau_nen(goc)
    print(f"mau nen   : {mau_bg}")

    noi_dung = cat_noi_dung(goc, mau_bg)
    print(f"cat       : {noi_dung.size}")

    canh = int(CANH_VI * max(noi_dung.size))
    khung = Image.new("RGB", (noi_dung.size[0] + 2 * canh, noi_dung.size[1] + 2 * canh),
                      mau_bg)
    khung.paste(noi_dung, (canh, canh))
    vuong = canh_vuong(khung, canh, mau_bg)
    print(f"canh vuong: {vuong.size} (vien {canh}px)")

    duong_png = os.path.join(THU_MUC_ASSETS, "camai.png")
    vuong.resize((KICH_THUOC_PNG, KICH_THUOC_PNG), Image.LANCZOS).save(duong_png)
    print(f"da luu    : {duong_png}")

    duong_ico = os.path.join(THU_MUC_ASSETS, "camai.ico")
    vuong.save(duong_ico, format="ICO",
               sizes=[(s, s) for s, _ in KICH_THUOC_ICO])
    print(f"da luu    : {duong_ico}")

    # Ban kiem tra nhanh: xem cac kich thuoc nho co con khong
    for s, _ in KICH_THUOC_ICO:
        thu = vuong.resize((s, s), Image.LANCZOS)
        mau = thu.convert("RGB").getcolors(maxcolors=100000)
        print(f"  {s:>3}px -> so mau = {len(mau) if mau else '>100000'}")
    return 0


if __name__ == "__main__":
    nguon = sys.argv[1] if len(sys.argv) > 1 else MAC_DINH_NGUON
    sys.exit(chay(nguon))
