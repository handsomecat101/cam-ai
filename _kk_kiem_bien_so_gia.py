# -*- coding: utf-8 -*-
"""
Kiem chung pipeline doc bien so tren anh bien so Viet Nam GIA (sinh trong _kiem_chung/plate_gia).

KHONG thay the anh bien so that tu nguoi dung.
Tieu chi:
  - Doc duoc 2 hang (30A / 12345) va 1 hang (30A 12345)
  - chuan_hoa_bien_so KHONG bia them ky tu
  - KHONG doc nham bien nuoc ngoai thanh bien Viet Nam
"""
import os
import sys
import glob
import cv2

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from bien_so import BoDocBienSo, chuan_hoa_bien_so  # noqa: E402

THU_MUC = os.path.join(BASE, "_kiem_chung", "plate_gia")

# (ten file, chuoi ky vong)
KY_VONG = [
    ("vn_2hang_30A_12345.png", "30A12345"),
    ("vn_2hang_51H_98765.png", "51H98765"),
    ("vn_2hang_30A_1234.png", "30A1234"),
    ("vn_2hang_29B_45678.png", "29B45678"),
    ("vn_1hang_30A_12345.png", "30A12345"),
    ("vn_1hang_51H_98765.png", "51H98765"),
    ("vn_2hang_nghien.png", "30A12345"),
    ("vn_2hang_nghieng.png", "30A12345"),
    ("vn_2hang_nho.png", "30A12345"),
    ("vn_2hang_rong.png", "30A12345"),
]


def chuan_hoa_khong_bia(chuoi_goc: str) -> bool:
    """Chuoi chuan hoa phai la tap con cua chuoi goc (chi bo ky tu la, them dau gach)."""
    if not chuoi_goc:
        return False
    goc = chuoi_goc.upper()
    for c in goc:
        if not (c.isalnum() or c.isspace() or c in "-._"):
            return False
    chuoi = chuan_hoa_bien_so(chuoi_goc)
    core_goc = "".join(c for c in goc if c.isalnum())
    core_chuoi = "".join(c for c in chuoi.upper() if c.isalnum())
    return core_chuoi == core_goc


def main():
    print("=" * 78)
    print("KIEM CHUNG BIEN SO VIET NAM GIA (anh gia, khong phai anh that)")
    print("=" * 78)

    bds = BoDocBienSo()
    if not bds.nap():
        print("KHONG nap duoc engine OCR -> FAIL")
        return 1
    print(f"Engine OCR: OK (bat_duoc={bds.bat_duoc})")
    print()

    tong = 0
    dung = 0
    for ten, ky_vong in KY_VONG:
        p = os.path.join(THU_MUC, ten)
        if not os.path.exists(p):
            print(f"  {ten:30s} THIEU FILE")
            continue
        anh = cv2.imread(p)
        if anh is None:
            print(f"  {ten:30s} DOC ANH THAT BAI")
            continue
        tong += 1
        h, w = anh.shape[:2]
        kq = bds.doc_vung(anh, (0, 0, w, h), nguon="gia")
        if not kq:
            print(f"  {ten:30s} -> KHONG DOC DUOC")
            continue
        chuoi = kq[0].chuoi
        goc = kq[0].chuoi_goc
        tc = kq[0].tin_cay
        core = "".join(c for c in chuoi.upper() if c.isalnum())
        khop = (core == ky_vong)
        khong_bia = chuan_hoa_khong_bia(goc)
        if khop:
            dung += 1
        dau = "PASS" if khop else "FAIL"
        print(f"  {ten:30s} -> {dau} doc='{chuoi}' (goc='{goc}', tc={tc:.2f}, ky_vong='{ky_vong}')")
        if not khong_bia:
            print(f"      !! chuan_hoa_bien_so CO BIA KY TU: goc='{goc}' -> '{chuoi}'")

    print()
    print(f"Ket qua: {dung}/{tong} dung chuoi")
    print("Luu y: anh gia -> ket qua khong dai dien anh bien so that.")
    return 0 if dung == tong and tong > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
