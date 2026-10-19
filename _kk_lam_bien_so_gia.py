# -*- coding: utf-8 -*-
"""
Tao anh bien so xe Viet Nam gia (khong phai anh that) de kiem chung pipeline OCR.

Muc dich: chung minh pipeline doc duoc 2 hang (30A / 12345) va 1 hang.
KHONG thay the anh bien so that tu nguoi dung.
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_kiem_chung", "plate_gia")
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
os.makedirs(OUT, exist_ok=True)


def ve_bien(hang_tren, hang_duoi, ten_file, w=520, h=110, xu_nghieng=0.0, nhe=0.0, scale=1.0):
    """Ve 1 bien so trang nen, chu den. hang_duoi rong -> bien 1 hang."""
    img = Image.new("RGB", (w, h), (250, 250, 248))
    d = ImageDraw.Draw(img)
    # Vien bien
    d.rectangle([3, 3, w - 4, h - 4], outline=(20, 20, 20), width=4)

    def ve_chu(text, y, size, khoang_cach=1.0):
        f = ImageFont.truetype(FONT_BOLD, size)
        # do rong chu
        w_chu = 0
        for ch in text:
            w_chu += d.textlength(ch, font=f)
        w_chu = int(w_chu * khoang_cach)
        x = (w - w_chu) // 2
        for ch in text:
            cw = int(d.textlength(ch, font=f) * khoang_cach)
            d.text((x, y), ch, font=f, fill=(10, 10, 10))
            x += cw

    if hang_duoi:
        size = int((h - 20) / 2.4)
        ve_chu(hang_tren, 12, size)
        ve_chu(hang_duoi, 12 + int(size * 1.25), size)
    else:
        size = int((h - 24) / 1.3)
        ve_chu(hang_tren, (h - size) // 2 - 4, size)

    arr = np.array(img)
    if xu_nghieng != 0.0:
        # Ve tren canvas RONG HON roi cat theo bbox noi dung thuc te:
        # neu xoay truc tiep tren canvas thi bien se bi cat mat chan so
        # (khong phai loi OCR).
        h2, w2 = arr.shape[:2]
        pad = int(max(h2, w2) * 0.5)
        big = cv2.copyMakeBorder(arr, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(250, 250, 248))
        hb, wb = big.shape[:2]
        M = cv2.getRotationMatrix2D((wb / 2, hb / 2), xu_nghieng, 1.0)
        big = cv2.warpAffine(big, M, (wb, hb), borderValue=(250, 250, 248))
        # Tim bbox phan khac nen (nen = mau goc, khac 2 pixel)
        nen = np.array([250, 250, 248], dtype=np.int16)
        khac = np.abs(big.astype(np.int16) - nen).max(axis=2) > 2
        ys, xs = np.where(khac)
        if len(xs) > 0:
            m = 6
            x0 = max(0, int(xs.min()) - m)
            x1 = min(wb, int(xs.max()) + m)
            y0 = max(0, int(ys.min()) - m)
            y1 = min(hb, int(ys.max()) + m)
            big = big[y0:y1, x0:x1]
        arr = big
    if nhe > 0:
        rng = np.random.default_rng(7)
        noise = rng.normal(0, nhe, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    if scale != 1.0:
        arr = cv2.resize(arr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    p = os.path.join(OUT, ten_file)
    cv2.imwrite(p, cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    return p, arr.shape


def main():
    print("=== Tao anh bien so gia (test noi bo) ===")
    cases = [
        # (hang tren, hang duoi, ten, kwargs)
        ("30A", "12345", "vn_2hang_30A_12345.png", {}),
        ("51H", "98765", "vn_2hang_51H_98765.png", {}),
        ("30A", "1234", "vn_2hang_30A_1234.png", {}),
        ("29B", "45678", "vn_2hang_29B_45678.png", {}),
        ("30A 12345", "", "vn_1hang_30A_12345.png", {}),
        ("51H 98765", "", "vn_1hang_51H_98765.png", {}),
        ("30A", "12345", "vn_2hang_nghien.png", {"nhe": 14}),
        ("30A", "12345", "vn_2hang_nghieng.png", {"xu_nghieng": 6.0}),
        ("30A", "12345", "vn_2hang_nho.png", {"scale": 0.42}),
        ("30A", "12345", "vn_2hang_rong.png", {"scale": 1.6}),
    ]
    for ht, hd, ten, kw in cases:
        p, shp = ve_bien(ht, hd, ten, **kw)
        print(f"  {ten:32s} shape={shp}  -> {os.path.basename(p)}")
    print(f"\nLuu tai: {OUT}")
    print("Luu y: anh gia, KHONG phai anh bien so that.")


if __name__ == "__main__":
    main()
