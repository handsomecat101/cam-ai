# -*- coding: utf-8 -*-
"""Kiem chung: crop nho co can phong to truoc khi OCR khong?"""
import glob
import os
import sys
import time

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

import cv2
import numpy as np

from bien_so import BoDocBienSo, chuan_hoa_bien_so

CROP_DIR = os.path.join(GOC, "_kiem_chung", "plate_thu", "crops")


def phong_to(anh, lan):
    """Phong to gan bang cu bien so (x2/x3/x4) - giong cach _kk_phong_to_bien_so.py."""
    if lan <= 1:
        return anh
    h, w = anh.shape[:2]
    # canh chieu theo chieu rong, toi da 1200px
    he = int(h * lan)
    rong = int(w * lan)
    if rong > 1200:
        lan = 1200 / w
        he = int(h * lan)
        rong = 1200
    return cv2.resize(anh, (rong, he), interpolation=cv2.INTER_CUBIC)


def main():
    b = BoDocBienSo(nguong_tin_cay=0.3, thu_muc_luu="")
    if not b.nap():
        print("khong nap duoc OCR")
        return

    crops = [p for p in sorted(glob.glob(os.path.join(CROP_DIR, "*_crop*.png")))
             if not p.endswith("_crop_A.png")]
    print(f"{'file':38s} {'size':12s} " + " ".join(f"x{l:<2d}" for l in (1, 2, 3, 4, 6)))
    print("-" * 100)
    for p in crops:
        img = cv2.imread(p)
        if img is None:
            continue
        h, w = img.shape[:2]
        o = os.path.basename(p).replace("_crop", "").replace(".png", "")
        ket_qua = []
        for lan in (1, 2, 3, 4, 6):
            a = phong_to(img, lan)
            t0 = time.perf_counter()
            try:
                kq = b.doc_vung(a, (0, 0, a.shape[1], a.shape[0]))
            except Exception as exc:
                ket_qua.append(f"ERR({type(exc).__name__})")
                continue
            ms = (time.perf_counter() - t0) * 1000
            if kq:
                ket_qua.append(f"{kq[0].chuoi} {ms:.0f}ms")
            else:
                ket_qua.append(f"- {ms:.0f}ms")
        print(f"{o:38s} {w}x{h:<6d} " + " | ".join(ket_qua))


if __name__ == "__main__":
    main()
