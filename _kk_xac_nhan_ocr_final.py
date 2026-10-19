"""Coordinator tu kiem chung RapidOCR chi-doc tren crop bien SAI DA.

Dung dung API dung: khoi tao RapidOCR(use_text_det=False, use_angle_cls=False).
Kiem chung lai so do thoi gian de quyet dinh nen dung OCR nao cho live view.

Chay: .venv\Scripts\python.exe -W ignore _kk_xac_nhan_ocr_final.py
"""

import sys
import time
from pathlib import Path

import cv2
from rapidocr_onnxruntime import RapidOCR

THU_MUC = Path("_kiem_chung") / "plate_thu" / "crops"

# Crop da xac nhan bang mat la that, kem chuoi bien expected
MAU_THAT = [
    ("bien-so-trong_crop_C.png", "POLIZIAM7318"),
    ("bien-so-ra-cong_crop_C.png", "SZ62144"),
    ("xe-chay-duong-1-lan_crop_C.png", "MSWL345"),
]

# Crop bi CHON SAI vung - phai ra ket qua rong
MAU_SAI = [
    ("bien-so-gan_crop_C.png", None),
    ("xe-dap-tuyen-pho_crop.png", None),
]

SO_LAN = 5


def chuan_hoa(text):
    giu = [c for c in text if c.isalnum()]
    return "".join(giu).upper()


def do_mot(ocr, anh):
    t0 = time.perf_counter()
    kq, _ = ocr(anh)
    return (time.perf_counter() - t0) * 1000.0, kq


def lay_chuoi(kq):
    if not kq:
        return ""
    if isinstance(kq, list) and kq and isinstance(kq[0], (list, tuple)):
        return " ".join(str(phan[1]) for phan in kq)
    return str(kq)


def main():
    print("=== KIEM CHUNG RAPIDOCR CHI DOC (API DUNG) ===")
    print("Khoi tao: RapidOCR(use_text_det=False, use_angle_cls=False)")
    print()

    t0 = time.perf_counter()
    ocr = RapidOCR(use_text_det=False, use_angle_cls=False)
    print(f"thoi gian khoi tao: {time.perf_counter() - t0:.2f} s")
    print()

    print("--- crop THAT (xac nhan bang mat) ---")
    tong_dung = 0
    tong_ms = 0.0
    tong_so = 0
    for ten, mong_doi in MAU_THAT:
        duong_dan = THU_MUC / ten
        if not duong_dan.exists():
            print(f"  {ten}: THIEU FILE")
            continue
        anh = cv2.imread(str(duong_dan))
        if anh is None:
            print(f"  {ten}: KHONG DOC DUOC ANH")
            continue

        # warm-up 2 lan
        do_mot(ocr, anh)
        do_mot(ocr, anh)

        chuoi = ""
        for _ in range(SO_LAN):
            ms, kq = do_mot(ocr, anh)
            tong_ms += ms
            tong_so += 1
            chuoi = chuan_hoa(lay_chuoi(kq))

        dung = chuoi == mong_doi
        if dung:
            tong_dung += 1
        h, w = anh.shape[:2]
        print(f"  {ten}")
        print(f"    kich thuoc   : {w}x{h}")
        print(f"    doc ra      : '{chuoi}'")
        print(f"    mong doi    : '{mong_doi}'")
        print(f"    ket luat    : {'DUNG' if dung else 'SAI'}")
        print()

    print(f"TOM: dung {tong_dung}/{len(MAU_THAT)}   "
          f"trung binh {tong_ms / max(tong_so, 1):.1f} ms/anh")
    print()

    print("--- crop SAI (phai rong) ---")
    for ten, _ in MAU_SAI:
        duong_dan = THU_MUC / ten
        if not duong_dan.exists():
            print(f"  {ten}: THIEU FILE")
            continue
        anh = cv2.imread(str(duong_dan))
        if anh is None:
            print(f"  {ten}: KHONG DOC DUOC ANH")
            continue
        do_mot(ocr, anh)
        ms, kq = do_mot(ocr, anh)
        chuoi = chuan_hoa(lay_chuoi(kq))
        h, w = anh.shape[:2]
        print(f"  {ten}  ({w}x{h}) -> '{chuoi}'  {ms:.1f} ms")
    print()

    print("=" * 56)
    if tong_dung == len(MAU_THAT):
        print("KET LUAN: RapidOCR chi DOC DOC DUNG tren crop that.")
        print("=> nut that KHONG phai do phan giai, ma la dinh vi vung bien.")
    else:
        print(f"KET LUAN: chi dung {tong_dung}/{len(MAU_THAT)}. Can xem lai.")
    print("=" * 56)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)