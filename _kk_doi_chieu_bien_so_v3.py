# -*- coding: utf-8 -*-
"""DO SO SAU bien_so.py - OCR bien so: engine nao, bao lau, bien nao doc/loai.

Chay: .venv\\Scripts\\python.exe -W ignore _kk_doi_chieu_bien_so_v3.py

Tao bang chung trong _kiem_chung/plate_thu/kiem_v3/ :
  - do_doi_chieu_bien_so_v3.txt   : ket qua do (dung de so sanh TRUOC/SAU)
  - bang_chung_anh/               : anh crop + chu OCR ghi len anh

KHONG sua san pham. Script chi DOC va TAO file trong _kiem_chung/.
"""

import json
import os
import sys
import time

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

import cv2
import numpy as np

from bien_so import BoDocBienSo, chuan_hoa_bien_so, lam_sach

CROP_DIR = os.path.join(GOC, "_kiem_chung", "plate_thu", "crops")
TONG_HOP_DIR = os.path.join(GOC, "_kiem_chung", "plate_thu", "synthetic")
OUT_DIR = os.path.join(GOC, "_kiem_chung", "plate_thu", "kiem_v3")
OUT_ANH = os.path.join(OUT_DIR, "bang_chung_anh")

# So lan do lai moi crop -> lay trung vi (so do on dinh, khong phu thuoc may).
SO_LAN_DO = 5

# 6 crop THAT cua coordinator. "nuoc" = quoc gia that cua bien so.
CROP_THAT = [
    ("bien-so-trong", "POLIZIA M7318", "Y"),
    ("xe-chay-duong-1-lan", "MS WL 345", "Duc"),
    ("bien-so-ra-cong", "SZ 62144", "Thuy Sy"),
    ("xe-ra-vao-bai", "AG 11655", "Duc"),
    ("xe-dap-tuyen-pho", "ZH 129527", "Thuy Sy"),
    ("bien-so-gan", "MS WL 545", "Duc"),
]

# Bang chuan hoa: (chuoi vao, ket qua mong doi, co phai bien so VN that khong)
BANG_CHUAN_HOA = [
    # --- bien so Viet Nam that ---
    ("30A-12345", "30A-12345", True),
    ("30A12345", "30A-12345", True),
    ("30a-12345", "30A-12345", True),
    ("51F 98765", "51F-98765", True),
    ("29B-54321", "29B-54321", True),
    ("30A-1234", "30A-1234", True),
    ("O0A-12345", "00A-12345", True),
    ("1A-12345", "", False),        # thieu 1 so dau -> khong khop mau
    # --- bien so nuoc ngoai: PHAI bi loai ---
    ("ABC-XYZ", "", False),
    ("", "", False),
    ("MSHL345", "", False),
    ("MSWL345", "", False),
    ("MSML345", "", False),
    ("SZ62144", "", False),
    ("AG11655", "", False),
    ("ZH129527", "", False),
    ("CAG1165", "", False),
    ("WESTOLOTTO", "", False),
    ("PoLiZiAM7318", "", False),
    ("TL0523001218", "", False),
    ("CHZO129527TL0523001218", "", False),
    ("30A123456", "", False),      # 6 so cuoi -> khong khop mau
    ("80FD1234", "", False),       # bien 2 chu -> khong khop mau chiet
    ("30-12345", "", False),       # thieu chu giua
    ("301A2345", "", False),       # 3 so dau
    ("B1X-23456", "", False),      # bien Anh -> khong duoc sua thanh "81X-23456"
    ("OLA12345", "", False),       # 2 loi OCR -> vuot gioi han sua 1 ky tu
    ("POLIZIA", "", False),        # chu khong phai bien so
]


def dong(title):
    print()
    print("=" * 92)
    print(title)
    print("=" * 92)


def tai_font(co):
    for ten in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
        duong = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", ten)
        if os.path.exists(duong):
            from PIL import ImageFont
            return ImageFont.truetype(duong, co)
    from PIL import ImageFont
    return ImageFont.load_default()


def ve_bang_chung(ten, crop, tho, ket_qua, chap_nhan, nhan_that, ms):
    """Ghi chu OCR + ket qua len anh crop -> luu ra _kiem_chung/plate_thu/kiem_v3/."""
    from PIL import Image, ImageDraw

    img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    chu_anh = []
    if tho:
        chu_anh.append("OCR: %s" % tho)
    chu_anh.append("Chuan hoa: %r" % ket_qua)
    chu_anh.append("%s | %s | %.1f ms" % (
        "CHAP NHAN" if chap_nhan else "TU CHOI",
        nhan_that, ms))

    f = tai_font(15)
    chieu = 20 * len(chu_anh) + 8
    khung = Image.new("RGB", (img.width, img.height + chieu), (18, 18, 22))
    khung.paste(img, (0, 0))
    ve = ImageDraw.Draw(khung)
    mau = (70, 220, 120) if chap_nhan else (240, 90, 90)
    y = img.height + 4
    for dong_chu in chu_anh:
        ve.text((4, y), dong_chu, font=f, fill=mau)
        y += 20
    os.makedirs(OUT_ANH, exist_ok=True)
    duong = os.path.join(OUT_ANH, "%s.png" % ten)
    khung.save(duong)
    return duong


def do_raw_ocr():
    """So sanh 2 kieu RapidOCR truc tiep tren 6 crop that (khong qua bien_so.py)."""
    dong("A. SO SANH 2 ENGINE RAPIDOCR (do truc tiep, khong qua bien_so.py)")
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception as exc:                        # noqa: BLE001
        print("  KHONG import duoc rapidocr:", exc)
        return
    print("  A1. RapidOCR() - CO TIM CHU")
    t0 = time.perf_counter()
    ocr_tim = RapidOCR()
    print("      khoi tao: %.0f ms" % ((time.perf_counter() - t0) * 1000))
    print("  A2. RapidOCR(use_text_det=False, use_angle_cls=False) - CHI DOC")
    t0 = time.perf_counter()
    ocr_doc = RapidOCR(use_text_det=False, use_angle_cls=False)
    print("      khoi tao: %.0f ms" % ((time.perf_counter() - t0) * 1000))

    print()
    print("  %-24s %-10s %10s  %-34s %10s  %s" % (
        "crop", "kich thuoc", "ms", "CO TIM CHU", "ms", "CHI DOC"))
    for ten, nhan, quoc in CROP_THAT:
        p = os.path.join(CROP_DIR, ten + "_crop.png")
        if not os.path.exists(p):
            continue
        img = cv2.imread(p)
        h, w = img.shape[:2]

        t0 = time.perf_counter()
        r_tim, _ = ocr_tim(img)
        ms_tim = (time.perf_counter() - t0) * 1000
        s_tim = " | ".join("%s(%.2f)" % (x[1], float(x[2])) for x in (r_tim or [])) or "(rong)"

        t0 = time.perf_counter()
        r_doc, _ = ocr_doc(img)
        ms_doc = (time.perf_counter() - t0) * 1000
        s_doc = " | ".join("%s(%.2f)" % (x[1], float(x[2])) for x in (r_doc or [])) or "(rong)"

        print("  %-24s %-10s %10.1f  %-34s %10.1f  %s" % (
            ten, "%dx%d" % (w, h), ms_tim, s_tim[:34], ms_doc, s_doc[:44]))


def do_chuan_hoa():
    dong("B. CHUAN HOA - BANG CA DINH (bien VN phai dung, bien nuoc ngoai phai loai)")
    print("  %-26s -> %-16s %-16s %s" % ("vao", "mong doi", "thuc te", "ket qua"))
    sai = 0
    for vao, mong_doi, la_vn in BANG_CHUAN_HOA:
        try:
            thuc_te = chuan_hoa_bien_so(vao)
        except Exception as exc:                    # noqa: BLE001
            thuc_te = "LOI: %s" % exc
        dung = (thuc_te == mong_doi)
        if not dung:
            sai += 1
        print("  %-26r -> %-16r %-16r %s" % (
            vao, mong_doi, thuc_te,
            "OK" if dung else "SAI (loai bien %s)" % ("VN" if la_vn else "nuoc ngoai")))
    print()
    print("  -> %d/%d dong dung" % (len(BANG_CHUAN_HOA) - sai, len(BANG_CHUAN_HOA)))
    return sai


def do_pipeline():
    """Chay DUNG duong san pham: BoDocBienSo.doc_vung tren crop that."""
    dong("C. DUONG SAN PHAM - BoDocBienSo.doc_vung() tren crop that")
    b = BoDocBienSo(nguong_tin_cay=0.3, thu_muc_luu="", log=lambda d: None)
    if not b.nap():
        print("  KHONG NAP DUOC RapidOCR - bo qua")
        return
    print("  engine da nap. bat_duoc =", b.bat_duoc)
    print()
    print("  %-24s %-10s %9s  %-26s %-12s %s" % (
        "crop", "kich thuoc", "ms", "OCR tho", "chuan hoa", "ket qua"))

    nhan_dung = 0
    tong_ms = 0.0
    so_dong = 0
    dung = 0
    tong = 0
    for ten, nhan_that, quoc in CROP_THAT:
        p = os.path.join(CROP_DIR, ten + "_crop.png")
        if not os.path.exists(p):
            continue
        img = cv2.imread(p)
        h, w = img.shape[:2]
        # Do nhieu lan -> lay trung vi de so do on dinh
        ms_list = []
        kq = []
        for _i in range(SO_LAN_DO):
            t0 = time.perf_counter()
            kq = b.doc_vung(img, (0, 0, w, h))
            ms_list.append((time.perf_counter() - t0) * 1000)
        ms = sorted(ms_list)[len(ms_list) // 2]
        tong_ms += ms
        so_dong += 1
        chuoi = kq[0].chuoi if kq else ""
        # Lay tho OCR truc tiep de thay chuoi tho ke ca khi bi loai
        tho = b._ocr_anh(b._phong_to(img)[0])[0]
        chap_nhan = bool(chuoi)
        nhan_dung += 1 if chap_nhan else 0
        print("  %-24s %-10s %9.1f  %-26s %-12s %s" % (
            ten, "%dx%d" % (w, h), ms, tho[:26] or "(rong)", chuoi or "(loai)",
            "CHAP NHAN" if chap_nhan else "TU CHOI"))
        ve_bang_chung(ten, img, tho, chuoi, chap_nhan,
                      "%s (%s)" % (nhan_that, quoc), ms)

    # --- bien so Viet Nam tong hop (anh ve, co nhan biet truoc) ---
    duong_nhan = os.path.join(TONG_HOP_DIR, "nhan.json")
    if os.path.exists(duong_nhan):
        with open(duong_nhan, encoding="utf-8") as f:
            ds = json.load(f)
        print()
        print("  --- Bien so Viet Nam TONG HOP (anh ve, nhan biet truoc) ---")
        print("  %-34s %9s  %-14s %-14s %s" % (
            "anh", "ms", "OCR tho", "chuan hoa", "mong doi"))
        dung = 0
        for m in ds:
            p = os.path.join(TONG_HOP_DIR, m["ten"])
            if not os.path.exists(p):
                continue
            img = cv2.imread(p)
            if img is None:
                continue
            h, w = img.shape[:2]
            ms_list = []
            kq = []
            for _i in range(SO_LAN_DO):
                t0 = time.perf_counter()
                kq = b.doc_vung(img, (0, 0, w, h))
                ms_list.append((time.perf_counter() - t0) * 1000)
            ms = sorted(ms_list)[len(ms_list) // 2]
            tong_ms += ms
            so_dong += 1
            tho = b._ocr_anh(b._phong_to(img)[0])[0]
            chuoi = kq[0].chuoi if kq else ""
            mong_doi = chuan_hoa_bien_so(m["nhan"])
            khop = (chuoi == mong_doi)
            dung += 1 if khop else 0
            tong += 1
            print("  %-34s %9.1f  %-14s %-14s %s" % (
                m["ten"][:34], ms, tho[:14] or "(rong)", chuoi or "(loai)",
                ("DUNG (%s)" % mong_doi) if khop else "SAI (mong doi %s)" % mong_doi))
            ve_bang_chung("vn_" + os.path.splitext(m["ten"])[0], img, tho, chuoi,
                          khop, "VN " + m["nhan"], ms)
        print()
        print("  -> Bien VN tong hop: doc DUNG %d/%d" % (dung, tong))

    # nhan_dung = so bien ngoai quoc bi CHAP NHAN (phai la 0)
    nhan_loi = nhan_dung
    print()
    print("  -> Bien ngoai quoc bi CHAP NHAN SAI = %d / %d (phai la 0)" % (
        nhan_loi, len(CROP_THAT)))
    print("  -> Bien VN tong hop doc dung: %d/%d" % (dung, tong))
    print("  -> Trung binh %d crop: %.1f ms/crop" % (
        so_dong, tong_ms / max(1, so_dong)))
    return nhan_loi, None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    dong("KIEM CHUNG bien_so.py - OCR bien so (chay %s)" % time.strftime("%Y-%m-%d %H:%M:%S"))
    do_raw_ocr()
    sai = do_chuan_hoa()
    nhan_loi, _bang = do_pipeline()
    dong("KET LUAN")
    print("  Bang chuan hoa sai: %d dong" % sai)
    print("  Bien ngoai quoc bi CHAP NHAN SAI: %d (phai la 0)" % nhan_loi)
    print("  Anh bang chung: %s" % OUT_ANH)


if __name__ == "__main__":
    main()
