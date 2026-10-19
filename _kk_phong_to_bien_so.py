# -*- coding: utf-8 -*-
"""Kiem chung: PHONG TO vung bien so co giup OCR doc duoc khong?

Do that: 30 crop bien so that tu video_mau/moi/xe-co-giao-thong.mp4 deu rat nho
(13x21 den 85x33 px) -> RapidOCR va EasyOCR doc duoc 0/30.
Gia thuyen: anh qua nho -> phong to + tang tuong phan truoc khi dua vao OCR se giup.

Script nay CHI DO, KHONG sua ma san pham.
"""
import os
import re
import sys
import time
import traceback

import cv2
import numpy as np

VIDEO = "video_mau/moi/xe-co-giao-thong.mp4"
MODEL_YOLO = "yolo11n.pt"
THU_KET_QUA = "_kiem_chung/phong_to"
FONT = "C:/Windows/Fonts/arialbd.ttf"

# Crop bien so: 40% - 85% chieu cao xe, can theo chieu ngang (gia do san co).
TY_LE_DOC = 0.38          # nua chieu rong moi ben
TY_LE_TREN = 0.40         # bien so bat dau o 40% chieu cao xe
TY_LE_DUOI = 0.85         # va cham 85%
LON_NHAT_CROP = 20        # < 20x10 px -> bo (khong doc noi)
RONG_NHAT_CROP = 10
TOI_DA_CROP = 25          # gioi han de script chay nhanh

# Mau bien so Viet Nam: 2 chu so + 1-2 ky tu + 4-5 chu so
MAU_BIEN_SO = re.compile(r"\d{2}[A-Z0-9]{1,2}[- ]?\d{4,5}")

LOAI_XE = {"car", "truck", "bus", "motorcycle"}


# ----------------------------------------------------------------- tien ich
def chuan_hoa(s):
    """Viet HOA, bo khoang trang / dau cham / dau '-' / cham sau chu cai."""
    return re.sub(r"[^0-9A-Z]", "", str(s).upper())


def chuan_hoa_de_khop(s):
    """Chuan hoa them cho PHA so sanh: O->0, I/L->1. KHONG dung de bao cao hien thi."""
    return chuan_hoa(s).replace("O", "0").replace("I", "1").replace("L", "1")


def _flat_rapid(kq):
    """RapidOCR co the tra ve long nhau. CHI lay chuoi, bo diem so (float)."""
    ra = []

    def walk(x):
        if isinstance(x, str):
            try:
                float(x)
                return
            except ValueError:
                pass
            ra.append(x)
        elif isinstance(x, (int, float)):
            return
        elif isinstance(x, (list, tuple)):
            if x and isinstance(x[0], str):
                walk(x[0])
            else:
                for y in x:
                    walk(y)

    walk(kq)
    return ra


def doc_rapid(ocr, img):
    """CHI DOC: da tat khai tim o luc khoi tao (use_text_det=False)."""
    kq, _ = ocr(img)
    if not kq:
        return ""
    return "".join(_flat_rapid(kq))


def doc_easy(reader, img):
    kq = reader.readtext(img, detail=1, paragraph=False)
    if not kq:
        return ""
    return " ".join(x[1] for x in kq)


# ------------------------------------------------------- bien the xu ly anh
def bien_the(crop):
    """Tra ve dict ten -> anh da xu ly."""
    h, w = crop.shape[:2]

    def resize(k, interp):
        return cv2.resize(crop, (max(1, w * k), max(1, h * k)), interpolation=interp)

    x4c = resize(4, cv2.INTER_CUBIC)
    x8c = resize(8, cv2.INTER_CUBIC)
    g4 = cv2.cvtColor(x4c, cv2.COLOR_BGR2GRAY)
    g8 = cv2.cvtColor(x8c, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    return {
        "goc": crop.copy(),
        "x2_cubic": resize(2, cv2.INTER_CUBIC),
        "x4_cubic": x4c,
        "x4_lanczos": resize(4, cv2.INTER_LANCZOS4),
        "x6_cubic": resize(6, cv2.INTER_CUBIC),
        "x4_clahe": clahe.apply(g4),
        "x8_clahe": clahe.apply(g8),
        "x4_thresh": cv2.threshold(g4, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
    }


THU_TU = ["goc", "x2_cubic", "x4_cubic", "x4_lanczos", "x6_cubic", "x4_clahe", "x8_clahe", "x4_thresh"]
# Hang can ve trong anh so sanh (theo yeu cau: bo x2_cubic)
HANG_ANH = ["goc", "x4_cubic", "x4_lanczos", "x6_cubic", "x4_clahe", "x8_clahe", "x4_thresh"]
NHAN_ANH = {
    "goc": "goc (khong xu ly)",
    "x4_cubic": "x4 cubic",
    "x4_lanczos": "x4 lanczos",
    "x6_cubic": "x6 cubic",
    "x4_clahe": "x4 cubic + CLAHE",
    "x8_clahe": "x8 cubic + CLAHE",
    "x4_thresh": "x4 cubic + Otsu",
}


# ------------------------------------------------------------- tach crop
def lay_crop_bien_so():
    """YOLO11n tim xe -> cat vung bien so. Bo xe co vung bien so qua nho."""
    from ultralytics import YOLO

    if not (os.path.exists(VIDEO) and os.path.exists(MODEL_YOLO)):
        print("THIEU video hoac model:", VIDEO, MODEL_YOLO)
        return []

    mo = YOLO(MODEL_YOLO)
    cap = cv2.VideoCapture(VIDEO)
    tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("Video: %d khung" % tong, flush=True)

    crops = []
    for f in (0.03, 0.12, 0.25, 0.38, 0.5, 0.62, 0.75, 0.88, 0.97):
        if len(crops) >= TOI_DA_CROP:
            break
        idx = int(tong * f)
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, khung = cap.read()
        if not ok:
            continue
        r = mo(khung, conf=0.30, verbose=False)[0]
        ten_loai = r.names
        for xyxy, cid in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist()):
            if ten_loai[int(cid)] not in LOAI_XE:
                continue
            x0, y0, x1, y1 = xyxy
            bw, bh = x1 - x0, y1 - y0
            if bw < 20 or bh < 10:
                continue
            # bien so: 40%-85% chieu cao xe, can theo chieu ngang
            ax0 = x0 + bw * (0.5 - TY_LE_DOC)
            ax1 = x0 + bw * (0.5 + TY_LE_DOC)
            ay0 = y0 + bh * TY_LE_TREN
            ay1 = y0 + bh * TY_LE_DUOI
            c = khung[max(0, int(ay0)):int(ay1), max(0, int(ax0)):int(ax1)]
            if c.size == 0 or c.shape[1] < RONG_NHAT_CROP or c.shape[0] < LON_NHAT_CROP:
                continue
            crops.append({
                "anh": c.copy(),
                "nhan": "khung%d %dx%d" % (idx, c.shape[1], c.shape[0]),
                "xe": "%dx%d" % (int(bw), int(bh)),
            })
        print("  khung %d: tong crop = %d" % (idx, len(crops)), flush=True)
    cap.release()
    return crops[:TOI_DA_CROP]


# ---------------------------------------------------------- anh so sanh
def luu_anh_so_sanh(crops, ket_qua, duong):
    """Ghep <=8 crop x 7 hang, nhan tieng Viet khong dau."""
    from PIL import Image, ImageDraw, ImageFont

    n = min(8, len(crops))
    if n == 0:
        return False
    cao_hang = 46
    rong_nhan = 210
    font = ImageFont.truetype(FONT, 16)

    hang_h = []
    for i in range(n):
        for ten in HANG_ANH:
            a = ket_qua[i][ten]
            if a.ndim == 2:
                a = cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)
            ty = cao_hang / max(1, a.shape[0])
            a = cv2.resize(a, (max(1, int(a.shape[1] * ty)), cao_hang),
                           interpolation=cv2.INTER_NEAREST)
            hang_h.append(a)
        rong_max = max(h.shape[1] for h in hang_h[len(HANG_ANH) * i:len(HANG_ANH) * (i + 1)])
        hang_h.append(np.full((cao_hang, rong_max - 12, 3), 40, np.uint8))  # hang trong

    cao_h = len(HANG_ANH) + 1  # 7 anh + 1 o trong
    tong_rong = rong_nhan + sum(h.shape[1] for h in hang_h)
    tong_cao = 34 + n * cao_h * cao_hang
    toan = np.full((tong_cao, tong_rong, 3), 25, np.uint8)

    y = 34  # duoi dong tieu de
    for i in range(n):
        for ten in HANG_ANH:
            idx_h = i * cao_h + HANG_ANH.index(ten)
            a = hang_h[idx_h]
            toan[y:y + cao_hang, rong_nhan:rong_nhan + a.shape[1]] = a
            y += cao_hang
        y += cao_hang  # o trong

    anh = Image.fromarray(toan[:, :, ::-1])
    d = ImageDraw.Draw(anh)
    font_nho = ImageFont.truetype(FONT, 13)
    d.text((6, 8), "SO SANH PHONG TO BIEN SO (%d crop)" % n, fill="white", font=font)
    y = 34
    for i in range(n):
        for ten in HANG_ANH:
            d.text((6, y + cao_hang // 2 - 8), NHAN_ANH[ten], fill=(200, 220, 255), font=font_nho)
            y += cao_hang
        d.text((6, y + cao_hang // 2 - 8),
               "crop %d: %s | xe %s" % (i + 1, crops[i]["nhan"], crops[i]["xe"]),
               fill=(120, 255, 160), font=font_nho)
        y += cao_hang
    anh.save(duong)
    return True


# ------------------------------------------------------------------ main
def chay():
    import easyocr
    from rapidocr_onnxruntime import RapidOCR

    os.makedirs(THU_KET_QUA, exist_ok=True)

    print("=== 1. Lay crop bien so that tu video ===", flush=True)
    crops = lay_crop_bien_so()
    print("DUNG %d crop (gioi han %d)" % (len(crops), TOI_DA_CROP), flush=True)
    if not crops:
        return 1

    print("\n=== 2. Tao 8 bien the xu ly anh ===", flush=True)
    bien_thes = [bien_the(c["anh"]) for c in crops]

    # rapidocr-onnxruntime 1.2.3: tham so use_det=False khi goi() KHONG duoc ho tro
    # (chi nhan box_thresh / unclip_ratio / text_score). Phai TAT khai tim luc
    # khoi tao bang use_text_det=False. Da kiem tra bang source + do chay that.
    print("\n=== 3. Khoi tao OCR (chi doc) ===", flush=True)
    print("RapidOCR: khoi tao...", flush=True)
    ocr = RapidOCR(use_text_det=False, use_angle_cls=False)
    assert ocr.use_text_det is False, "RapidOCR van bat khai tim"
    print("  use_text_det=%s use_angle_cls=%s" % (ocr.use_text_det, ocr.use_angle_cls), flush=True)
    print("EasyOCR: khoi tao Reader...", flush=True)
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    # warm-up: bo 3 lan dau khoi do
    print("Warm-up 3 lan...", flush=True)
    for i in range(3):
        doc_rapid(ocr, bien_thes[i % len(bien_thes)]["x4_cubic"])
        doc_easy(reader, bien_thes[i % len(bien_thes)]["x4_cubic"])

    print("\n=== 4. Chay 8 bien the x 2 OCR ===", flush=True)
    so = {t: {"rapid_doc": 0, "rapid_mau": 0, "rapid_ms": 0.0,
               "easy_doc": 0, "easy_mau": 0, "easy_ms": 0.0} for t in THU_TU}
    ket_qua = []

    for i, bt in enumerate(bien_thes):
        dong = {}
        for t in THU_TU:
            a = bt[t]
            t0 = time.perf_counter()
            s1 = doc_rapid(ocr, a)
            ms1 = (time.perf_counter() - t0) * 1000
            t0 = time.perf_counter()
            s2 = doc_easy(reader, a)
            ms2 = (time.perf_counter() - t0) * 1000

            so[t]["rapid_ms"] += ms1
            so[t]["easy_ms"] += ms2
            if chuan_hoa(s1):
                so[t]["rapid_doc"] += 1
            if chuan_hoa(s2):
                so[t]["easy_doc"] += 1
            if MAU_BIEN_SO.search(str(s1).upper()):
                so[t]["rapid_mau"] += 1
            if MAU_BIEN_SO.search(str(s2).upper()):
                so[t]["easy_mau"] += 1
            dong[t] = a
            print("  crop%02d %-11s rapid=%-12r %6.0fms | easy=%-12r %6.0fms"
                  % (i + 1, t, s1[:12], ms1, s2[:12], ms2), flush=True)
        ket_qua.append(dong)
        print("", flush=True)

    # ------------------------------------------------------------ bao cao
    n = len(crops)
    dong = []
    dong.append("=" * 96)
    dong.append("KEM CHUNG PHONG TO BIEN SO - %s" % VIDEO)
    dong.append("=" * 96)
    dong.append("So crop thu nghiem: %d (gioi han %d, bo xe co vung bien so < %dx%d px)"
                % (n, TOI_DA_CROP, LON_NHAT_CROP, RONG_NHAT_CROP))
    dong.append("Kich thuoc crop: rong %d-%d px, cao %d-%d px"
                % (min(c["anh"].shape[1] for c in crops), max(c["anh"].shape[1] for c in crops),
                   min(c["anh"].shape[0] for c in crops), max(c["anh"].shape[0] for c in crops)))
    dong.append("Vung bien so: %.0f%%-%.0f%% chieu cao xe, can theo chieu ngang (nua %.0f%%)"
                % (TY_LE_TREN * 100, TY_LE_DUOI * 100, TY_LE_DOC * 100))
    dong.append("OCR che do CHI DOC: RapidOCR(use_text_det=False, use_angle_cls=False)")
    dong.append("                   EasyOCR(readtext, detail=1, paragraph=False)")
    dong.append("Mau bien so Viet Nam kiem tra: \\d{2}[A-Z0-9]{1,2}[- ]?\\d{4,5}")
    dong.append("")
    dong.append("%-12s | %-26s | %-26s" % ("bien the", "RAPIDOCR", "EASYOCR"))
    dong.append("%-12s | %6s %6s %8s | %6s %6s %8s"
                % ("", "doc", "mau", "ms/anh", "doc", "mau", "ms/anh"))
    dong.append("-" * 96)
    for t in THU_TU:
        r = so[t]
        dong.append("%-12s | %6d %6d %8.1f | %6d %6d %8.1f"
                    % (t, r["rapid_doc"], r["rapid_mau"], r["rapid_ms"] / n,
                       r["easy_doc"], r["easy_mau"], r["easy_ms"] / n))
    dong.append("-" * 96)
    dong.append("(%d crop) 'doc' = chuoi khac rong, 'mau' = khop mau bien so Viet Nam"
                % n)
    dong.append("")

    tot_r = max(THU_TU, key=lambda t: (so[t]["rapid_mau"], so[t]["rapid_doc"]))
    tot_e = max(THU_TU, key=lambda t: (so[t]["easy_mau"], so[t]["easy_doc"]))
    nhan_r = "khong bien the nao doc duoc" if so[tot_r]["rapid_doc"] == 0 else \
             "%s (%d/%d doc, %d khop mau, %.0f ms/anh)" % (tot_r, so[tot_r]["rapid_doc"], n,
                                                          so[tot_r]["rapid_mau"], so[tot_r]["rapid_ms"] / n)
    nhan_e = "khong bien the nao doc duoc" if so[tot_e]["easy_doc"] == 0 else \
             "%s (%d/%d doc, %d khop mau, %.0f ms/anh)" % (tot_e, so[tot_e]["easy_doc"], n,
                                                          so[tot_e]["easy_mau"], so[tot_e]["easy_ms"] / n)
    dong.append("KET LUAN")
    dong.append("  RapidOCR tot nhat : %s" % nhan_r)
    dong.append("  EasyOCR  tot nhat : %s" % nhan_e)
    cs_goc_r = so["goc"]["rapid_ms"] / n
    tot_r_ms = so[tot_r]["rapid_ms"] / n
    cs_goc_e = so["goc"]["easy_ms"] / n
    tot_e_ms = so[tot_e]["easy_ms"] / n
    dong.append("  doi phi RapidOCR : goc %.1f -> tot nhat %.1f ms/anh (x%.2f)"
                % (cs_goc_r, tot_r_ms, tot_r_ms / max(1e-9, cs_goc_r)))
    dong.append("  doi phi EasyOCR  : goc %.1f -> tot nhat %.1f ms/anh (x%.2f)"
                % (cs_goc_e, tot_e_ms, tot_e_ms / max(1e-9, cs_goc_e)))
    dong.append("")

    b = "\n".join(dong)
    print("\n" + b)

    duong_txt = os.path.join(THU_KET_QUA, "phong_to_bien_so.txt")
    with open(duong_txt, "w", encoding="utf-8") as f:
        f.write(b + "\n")
    print("\nDa luu: %s" % duong_txt)

    duong_png = os.path.join(THU_KET_QUA, "so_sanh_phong_to.png")
    if luu_anh_so_sanh(crops, ket_qua, duong_png):
        print("Da luu: %s" % duong_png)
    else:
        print("Khong tao duoc anh so sanh (thieu crop)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)