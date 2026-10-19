# -*- coding: utf-8 -*-
"""Zoom vung chu can kiem: ghi chu trong nhom 'Tu chup anh khi co su kien'."""
import os
import sys
import cv2

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "_kk_out", "v3_3_bien_so_tu_chup.png")
OUT = os.path.join(BASE, "_kk_out")

img = cv2.imread(SRC)
if img is None:
    print("khong doc duoc anh:", SRC)
    sys.exit(1)
print("anh goc:", img.shape)

# Toa do tu quan sat truc tiep tren anh 1620x1080
vung = [
    ("zoom_ghi_chu.png", (40, 380, 310, 460)),      # khoi ghi chu trong nhom tu chup
    ("zoom_thu_muc.png", (40, 235, 310, 300)),      # o thu muc luu anh
    ("zoom_nhanh.png", (40, 300, 310, 380)),        # nhan giu giua 2 lan
]
for ten, (x1, y1, x2, y2) in vung:
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(img.shape[1], x2); y2 = min(img.shape[0], y2)
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        print("vung rong:", ten)
        continue
    big = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    p = os.path.join(OUT, ten)
    cv2.imwrite(p, big)
    print(f"  {ten}: {crop.shape} -> x4 {big.shape}")
