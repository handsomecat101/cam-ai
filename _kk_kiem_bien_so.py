# -*- coding: utf-8 -*-
"""Kiem chung bien_so.py va tu_chup.py - chay that tren crop that co san."""
import os
import sys
import time
import glob

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

# Console Windows mac dinh la cp1252 -> in chu co dau se crash
# (UnicodeEncodeError). Ep UTF-8 truoc khi in bat ky thu gi.
for _s in ("stdout", "stderr"):
    _luong = getattr(sys, _s, None)
    if _luong is not None:
        try:
            _luong.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

from bien_so import BoDocBienSo, chuan_hoa_bien_so, lam_sach

CROP_DIR = os.path.join(GOC, "_kiem_chung", "plate_thu", "crops")
OUT_DIR = os.path.join(GOC, "_kk_out", "ocr_thu")


def dong(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def test_chuan_hoa():
    dong("1. CHUAN HOA CHUOI BIEN SO (regex + sua loi OCR)")
    mau = [
        ("30A-12345", "dung chuan VN 2 hang"),
        ("30A12345", "khong dau gach"),
        ("30a-12345", "chu thuong"),
        ("51F 98765", "co khoang trang"),
        ("29B-54321", "dung chuan VN 2 hang"),
        ("O0A-12345", "O thay 0"),
        ("30A-1234", "chi 4 so"),
        ("ABC-XYZ", "khong phai bien so"),
        ("", "rong"),
    ]
    for s, ghi_chu in mau:
        try:
            kq = chuan_hoa_bien_so(s)
        except Exception as exc:
            kq = f"LOI: {type(exc).__name__}: {exc}"
        print(f"  {s!r:16s} -> {kq!r:16s}   ({ghi_chu})")


def test_ocr():
    dong("2. OCR THAT tren crop bien so co san")
    b = BoDocBienSo(nguong_tin_cay=0.3, thu_muc_luu=OUT_DIR)
    if not b.nap():
        print("  KHONG NAP DUOC RapidOCR - bo qua")
        return
    print("  nap duoc. id_bien_so =", getattr(b, "id_bien_so", None))
    print("  co the dung class 'plate' cua YOLO:",
          bool(getattr(b, "id_bien_so", None)))
    print()
    crops = sorted(glob.glob(os.path.join(CROP_DIR, "*_crop*.png")))
    if not crops:
        print("  KHONG CO crop nao")
        return
    tong_ms = []
    dung = 0
    for p in crops:
        import cv2
        img = cv2.imread(p)
        if img is None:
            print(f"  {os.path.basename(p):42s} DOC THAT BAI")
            continue
        t0 = time.perf_counter()
        try:
            kq = b.doc_vung(img, (0, 0, img.shape[1], img.shape[0]))
        except Exception as exc:
            kq = []
            print(f"  {os.path.basename(p):42s} LOI: {type(exc).__name__}: {exc}")
        ms = (time.perf_counter() - t0) * 1000
        tong_ms.append(ms)
        if kq:
            dung += 1
            chuoi = " | ".join(f"{k.chuoi!r} conf={k.tin_cay:.2f}" for k in kq)
        else:
            chuoi = "(khong doc duoc)"
        print(f"  {os.path.basename(p):42s} {ms:7.1f} ms  {chuoi}")
    if tong_ms:
        tb = sum(tong_ms) / len(tong_ms)
        print()
        print(f"  tong {len(tong_ms)} crop | trung binh {tb:.1f} ms/anh"
              f" | doc duoc {dung}/{len(tong_ms)}")


def test_tu_chup():
    dong("3. TU CHUP ANH SU KIEN")
    from tu_chup import TuChupAnh
    thu_muc = os.path.join(OUT_DIR, "su_kien")
    tc = TuChupAnh(thu_muc, nhoan_lai_giay=10.0, log=lambda d: None)
    print("  thu muc:", thu_muc)
    print("  co_the_chup('vua_toi') lan 1:", tc.co_the_chup("vua_toi"))
    import numpy as np
    anh = np.zeros((480, 640, 3), dtype=np.uint8)
    duong_dan = tc.chup(anh, loai_su_kien="vua_toi", so_nguoi=3)
    print("  chụp lần 1 ->", duong_dan)
    print("  co_the_chup('vua_toi') lan 2 (phải False do nghỉ 10s):",
          tc.co_the_chup("vua_toi"))
    duong_dan2 = tc.chup(anh, loai_su_kien="vua_toi", so_nguoi=3)
    print("  chụp lần 2 ->", duong_dan2, "(phải None)")
    duong_dan3 = tc.chup(anh, loai_su_kien="vuot_vung", so_nguoi=9)
    print("  chụp sự kiện khác ->", duong_dan3, "(phải có, vì khác loại)")
    csv = tc.ghi_csv()
    print("  CSV bảng kê:", csv)
    if csv and os.path.exists(csv):
        with open(csv, encoding="utf-8") as f:
            noi_dung = f.read()
        print("  noi dung CSV:")
        for dong_csv in noi_dung.splitlines():
            print("   ", dong_csv)
    print("  file anh da sinh:", os.listdir(thu_muc) if os.path.exists(thu_muc) else "(khong co)")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    test_chuan_hoa()
    test_ocr()
    test_tu_chup()
