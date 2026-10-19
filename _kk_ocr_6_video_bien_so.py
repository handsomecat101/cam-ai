# -*- coding: utf-8 -*-
"""Do OCR tren 6 video MOI co bien so ro.

KHONG sua ma san pham. Chi do.

API RapidOCR 1.2.3 (da doc source rapid_ocr_api.py):
  - __call__(img, **kwargs) CHI doc box_thresh / unclip_ratio / text_score.
    `use_det=False` bi BO QUA HOAN TOAN (khong phai loi, ma im lang).
  - Che do CHI DOC dung khi KHOI TAO: RapidOCR(use_text_det=False, use_angle_cls=False)
    -> __init__ khong nap TextDetector/TextClassifier.
  - Them nua __call__ tu bo qua khi tim khi h <= min_height (30) hoac w/h > width_height_ratio (8).
Vi vay can HAI engine, moi loai khoi tao DUNG MOT LAN roi dung lai.
"""
import os
import sys
import time
import json
import traceback
from collections import Counter

import cv2
import numpy as np

GOC = os.path.dirname(os.path.abspath(__file__))
KTC = os.path.join(GOC, "_kiem_chung", "plate_thu")
THU_MUC_CROP = os.path.join(KTC, "crops")
FILE_TXT = os.path.join(KTC, "ocr_6_video.txt")
FONT = "C:/Windows/Fonts/arialbd.ttf"

VIDEO = [
    "bien-so-gan",
    "bien-so-ra-cong",
    "xe-ra-vao-bai",
    "xe-dap-tuyen-pho",
    "bien-so-trong",
    "xe-chay-duong-1-lan",
]

# Mau bien da XAC NHAN BANG MAT tren anh crop. Neu rong -> dung chuoi dong thuan
# nhat trong tat ca ket qua (consensus) va danh dau "chua kiem chung".
MAU_TAY = {
    "bien-so-gan": "MSWL545",          # Duc, "D MS WL 545"
    "bien-so-ra-cong": "SZ62144",      # Thuys Sy, "SZ 62144"
    "xe-ra-vao-bai": "AG11655",        # Duc, "D AG 11655"
    "xe-dap-tuyen-pho": "ZH129527",    # xe may Thuys Sy, "ZH 129527"
    "bien-so-trong": "M7318POLIZIA",   # Y, "POLIZIA M7318"
    "xe-chay-duong-1-lan": "MSWL345",  # Duc, "D MS WL 345"
}

BIEN_VN = None  # filled later


def chuan_hoa(s):
    return "".join(c for c in s.upper() if c.isdigit() or ("A" <= c <= "Z"))


def co_the_la_bien_vn(s):
    """Bien VN: 30A-123.45 / 51F-678.90 -> 2 chu so dau, hoac co dau gach."""
    import re
    t = chuan_hoa(s)
    if not t:
        return False
    if re.match(r"^\d{2}[A-Z]", t):
        return True
    if re.match(r"^\d{2}[A-Z]?\d{3}", t) and len(t) >= 7:
        return True
    return False


# ---------------------------------------------------------------- BUOC 1
def _doc_khung(duong_dan, chi_so):
    cap = cv2.VideoCapture(duong_dan)
    cap.set(cv2.CAP_PROP_POS_FRAMES, chi_so)
    ok, fr = cap.read()
    cap.release()
    return (ok and fr is not None), fr


def vung_bien_theo_yolo(det, fr, lop_xe=(2, 3, 5, 7)):
    """Cach A: YOLO11n + dung ty le trong _kk_xac_nhan_ocr.py (dong 151-152):
    y: cy + chh*0.05 .. cy + chh*0.50 | x: cx - cw*0.38 .. cx + cw*0.38

    Bien so phia sau xe thuong o nua duoi khung xe, nen ty le tren lay
    tu 0.05 den 0.50 chieu cao. Nhung 6 video nay la ANH CANH CANH: hop YOLO
    trong lan khung 33% -> vung cat ra bi tuyet keo bien so (no o canh tren
    khung). Khi do mo phan tren hop xe len den day hop de bien so lot vao.
    """
    res = det(fr, verbose=False, conf=0.25)[0]
    if res is None or len(res.boxes) == 0:
        return None, "khong co xe nao YOLO bat"
    tot = []
    for b in res.boxes:
        if int(b.cls[0].item()) not in lop_xe:
            continue
        x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cw, chh = x2 - x1, y2 - y1
        y_tren = int(cy + chh * 0.05)
        y_duoi = int(cy + chh * 0.50)
        x_tren = int(cx - cw * 0.38)
        x_duoi = int(cx + cw * 0.38)
        vung = fr[y_tren:y_duoi, x_tren:x_duoi]
        if vung.size == 0:
            continue
        mo = "xe %dx%dpx" % (cw, chh)
        if vung.shape[0] * vung.shape[1] > 0.25 * fr.shape[0] * fr.shape[1]:
            # anh canh canh: keo vung cat len den dinh hop xe
            rong = fr[max(0, y1):y_duoi, x_tren:x_duoi]
            if rong.size > 0 and rong.shape[0] > vung.shape[0]:
                vung = rong
                mo += " -> A' mo len tren (anh canh canh)"
        tot.append((cw * chh, vung, mo))
    if not tot:
        return None, "YOLO chi bat lop khong phai xe"
    tot.sort(key=lambda x: -x[0])
    return tot[0][1], tot[0][2]


def _sap_xep_4(diem):
    """Sap xep 4 diem theo thu tu: tren-trai, tren-phai, duoi-phai, duoi-trai."""
    d = np.array(diem, dtype=np.float32).reshape(4, 2)
    c = d.mean(axis=0)
    goc = np.arctan2(d[:, 1] - c[1], d[:, 0] - c[0])
    return d[np.argsort(goc)]


def vung_bien_theo_contour(fr):
    """Cach B: tim bien so tu cum CHU IN DAM (khong dua vao do sang).

    Bien so khong phai luon trang: do 6 video nay, median kenh min trong vung
    bien so dao 124..255 (bien MS WL 345 nam trong bong). Nen dung nguong tuong
    doi adaptiveThreshold de tach chu, gop chu thanh 1 khoi, roi dung
    minAreaRect de bien NGHIENG (bien xe may ZH) van ra dung ti le.
    """
    gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                               cv2.THRESH_BINARY_INV, 31, 8)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 7))
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, k, iterations=2)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    H, W = gray.shape[:2]
    dien_frame = float(H * W)
    ứng = []
    so_danh = []
    for c in cnts:
        if cv2.contourArea(c) < 400:
            continue
        rect = cv2.minAreaRect(c)
        rw, rh = rect[1]
        if rw < 40 or rh < 8:
            continue
        ar = max(rw, rh) / min(rw, rh)
        if not (2.0 <= ar <= 6.5):
            continue
        if max(rw, rh) > 0.75 * max(H, W):
            continue
        box = cv2.boxPoints(rect)
        x0 = int(max(0, box[:, 0].min()))
        y0 = int(max(0, box[:, 1].min()))
        x1 = int(min(W, box[:, 0].max()))
        y1 = int(min(H, box[:, 1].max()))
        if x1 - x0 < 40 or y1 - y0 < 8:
            continue
        roi = gray[y0:y1, x0:x1]
        if roi.size == 0:
            continue
        p10 = float(np.percentile(roi, 10))
        p90 = float(np.percentile(roi, 90))
        tuong_phan = p90 - p10          # chu dam tren nen sang -> bien lon
        so_danh.append((rw, rh, ar, tuong_phan, cv2.contourArea(c)))
        if tuong_phan < 45:
            continue
        # thich chu ngang dai, sat ti le bien so (~3-5), va vung vua phai
        diem = min(tuong_phan / 120.0, 2.0) + min(cv2.contourArea(c) / 9000.0, 2.0)
        diem += 1.0 if 2.5 <= ar <= 5.5 else 0.0
        if (y0 + y1) / 2.0 > (H * 2.0 / 3.0):
            diem += 0.4
        ứng.append((diem, box, x0, y0, x1, y1, tuong_phan, ar,
                    max(rw, rh), min(rw, rh)))
    if os.environ.get("DEBUG_CROP"):
        print("    [DEBUG] %d ung vien truoc bo loc, %d sau" % (len(so_danh), len(ứng)))
        for t in sorted(so_danh, key=lambda z: -(z[2] * z[4]))[:6]:
            print("      rect=%.0fx%.0f ar=%.2f tuong_phan=%.0f area=%.0f"
                  % (t[0], t[1], t[2], t[3], t[4]))
    if not ứng:
        return None, "khong tim thay cum chu co ti le bien so"
    ứng.sort(key=lambda t: -t[0])
    if os.environ.get("DEBUG_CROP"):
        for t in ứng[:4]:
            print("      score=%.2f rect=%.0fx%.0f ar=%.2f tuong_phan=%.0f"
                  % (t[0], t[8], t[9], t[7], t[6]))
    _, box, x0, y0, x1, y1, tp, ar, rw, rh = ứng[0]

    # Cat theo goc nhat -> bien so thang ngan, rat giup OCR
    rw2, rh2 = rw * 1.10, rh * 1.35
    cx, cy = box[:, 0].mean(), box[:, 1].mean()
    goc = np.arctan2(box[:, 1].mean() - cy, 0)  # giu huong nhat cua box
    d = _sap_xep_4(box)
    cxd, cyd = d[:, 0].mean(), d[:, 1].mean()
    hu = d - np.array([cxd, cyd])
    hu = hu * np.array([rw2 / max(rw, 1e-6), rh2 / max(rh, 1e-6)])
    d = hu + np.array([cxd, cyd])
    Wt, Ht = max(int(rw2), 20), max(int(rh2), 8)
    dst = np.float32([[0, 0], [Wt - 1, 0], [Wt - 1, Ht - 1], [0, Ht - 1]])
    M = cv2.getPerspectiveTransform(np.float32(d), dst)
    vung = cv2.warpPerspective(fr, M, (Wt, Ht), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE)
    mo_ta = ("cum chu rect %.0fx%.0fpx ar=%.2f tuong_phan=%.0f%s"
             % (rw, rh, ar, tp,
                " (o 1/3 duoi)" if (y0 + y1) / 2.0 > (H * 2.0 / 3.0) else ""))
    return vung, mo_ta


def vung_bien_theo_ocr_det(ocr, fr, phong=0.08):
    """Cach C: dung bo TIM CHU cua chinh RapidOCR de dinh vi tri bien so.

    Bien so = nhieu khung chu cung hang, ghep lai co ti le 2.0-6.5. Vi du
    "MS" + "WL545" -> 1 khung = ca bien so. Cach nay khong phu thuoc do sang
    nen dung duoc ca khi bien so nam trong bong.
    """
    kq, _ = ocr(fr)
    if not kq:
        return None, "khong tim thay khung chu nao"
    gray = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    H, W = gray.shape[:2]
    hop = []
    for b, t, _ in kq:
        pts = np.array(b, dtype=np.float32).reshape(-1, 2)
        hop.append([float(pts[:, 0].min()), float(pts[:, 1].min()),
                    float(pts[:, 0].max()), float(pts[:, 1].max()), t])
    # nhom cac khung chu cung hang (trong ke doc chong > 50%)
    nhom = []
    for r in sorted(hop, key=lambda z: z[1]):
        for g in nhom:
            y0 = min(z[1] for z in g)
            y1 = max(z[3] for z in g)
            chong = min(r[3], y1) - max(r[1], y0)
            if chong > 0.5 * min(max(r[3] - r[1], 1), max(y1 - y0, 1)):
                g.append(r)
                break
        else:
            nhom.append([r])

    ung = []
    for g in nhom:
        # Thu ca nhom day du, moi khung chu rieng, va cac cap ke nhau.
        # Bien so "MS WL 545" hay bi ghep nhat voi chu ban quang cao ben canh
        # nen phai xet ca khung don le.
        tap = [g] + [[z] for z in g]
        for i in range(len(g) - 1):
            tap.append([g[i], g[i + 1]])
        for t in tap:
            x0 = min(z[0] for z in t)
            y0 = min(z[1] for z in t)
            x1 = max(z[2] for z in t)
            y1 = max(z[3] for z in t)
            w, h = x1 - x0, y1 - y0
            if w < 60 or h < 15:
                continue
            ar = w / float(h)
            if not (2.0 <= ar <= 6.5):
                continue
            # Bien so = nen sang co chu in dam. Chu trang tren nen den
            # (COOPER, KELLER) se bi truong diem.
            roi = gray[int(y0):int(y1), int(x0):int(x1)]
            if roi.size == 0:
                continue
            med = float(np.median(roi))
            # Bien so: nen SANG, chu in DAM -> ti le pixel toi trong vung
            # nho (0.05-0.5). Chu trang tren nen den (COOPER, WESTLOTTO,
            # KELLER) co nen toi nen ti le pixel toi rat lon -> bi lo.
            frac_dam = float((roi < (med - 40)).mean())
            if not (0.04 <= frac_dam <= 0.50):
                continue
            # vung xung quanh (moc rong gap khung) de so sanh
            vong = np.ones((H, W), bool)
            px = int(w * phong)
            py = int(h * phong)
            vong[max(0, int(y0) - py):int(y1) + py,
                 max(0, int(x0) - px):int(x1) + px] = False
            quan = gray[vong]
            med_hoi = float(np.median(quan)) if quan.size else 0.0
            if med < 60:
                continue
            diem = w * h / 1000.0
            if 2.5 <= ar <= 5.5:
                diem += 40
            diem += 6 * len(t)          # uu tien nhom nhieu khung chu
            if (y0 + y1) / 2.0 > H * 2.0 / 3.0:
                diem += 25               # bien so thuong o 1/3 duoi
            diem += max(-2.0, min((med - med_hoi) / 15.0, 3.0))
            diem += 3.0 if 0.10 <= frac_dam <= 0.35 else 0.0
            ung.append((diem, x0, y0, x1, y1, ar, " ".join(z[4] for z in t), len(t)))
    if not ung:
        return None, "co khung chu nhung khong ghep duoc khoi bien so"
    ung.sort(key=lambda z: -z[0])
    _, x0, y0, x1, y1, ar, chu, n_box = ung[0]
    dw, dh = (x1 - x0) * phong, (y1 - y0) * phong
    a0 = int(max(0, x0 - dw))
    b0 = int(max(0, y0 - dh))
    a1 = int(min(W, x1 + dw))
    b1 = int(min(H, y1 + dh))
    vung = fr[b0:b1, a0:a1]
    return (vung if vung.size else None), ("nhom %d khung chu ar=%.2f chu=%r"
                                           % (n_box, ar, chu))


# ---------------------------------------------------------------- BUOC 3
def bien_the(crop):
    out = {}
    out["goc"] = crop
    out["x3_cubic"] = cv2.resize(crop, None, fx=3, fy=3,
                                 interpolation=cv2.INTER_CUBIC)
    x4 = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    out["x4_cubic"] = x4
    g = cv2.cvtColor(x4, cv2.COLOR_BGR2GRAY)
    cl = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(g)
    # Gray -> BGR de ca 2 engine deu nhan 3 kenh
    out["x4_clahe"] = cv2.cvtColor(cl, cv2.COLOR_GRAY2BGR)
    return out


# ---------------------------------------------------------------- OCR
def _flat(kq):
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


class DoKhong:
    """Bo 2 lan warm-up dau tien truoc khi lay so do."""

    def __init__(self, ham):
        self.ham = ham
        self.warm = 0
        self.ms = []

    def goi(self, *a, **k):
        if self.warm < 2:
            self.warm += 1
            self.ham(*a, **k)
            return None, 0.0
        t0 = time.perf_counter()
        r = self.ham(*a, **k)
        d = (time.perf_counter() - t0) * 1000
        self.ms.append(d)
        return r, d


def _rapid_co_tim(ocr, img):
    kq, _ = ocr(img)
    if not kq:
        return ""
    return "|".join(x[1] for x in kq)


def _rapid_chi_doc(ocr, img):
    kq, _ = ocr(img)
    if not kq:
        return ""
    return "|".join(x[1] for x in kq)


def _easy(reader, img):
    kq = reader.readtext(img, detail=1, paragraph=False)
    if not kq:
        return ""
    return "|".join(x[1] for x in kq)


# ---------------------------------------------------------------- anh chung
def ghép_4_bien_the(crop, ten, bien_the_img, ket_qua):
    from PIL import Image, ImageDraw, ImageFont
    # Canh chu: 150px ben trai de ghi nhan + phan anh, anh phai vua khung
    COT = 150
    tiles = []
    H = 150
    for k in ("goc", "x3_cubic", "x4_cubic", "x4_clahe"):
        im = cv2.cvtColor(bien_the_img[k], cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(im)
        r = H / float(pil.height)
        pil = pil.resize((max(1, int(pil.width * r)), H), Image.LANCZOS)
        tiles.append((k, pil))
    Wmax = COT + max(p.width for _, p in tiles) + 10
    tong = Image.new("RGB", (Wmax, H * len(tiles) + 26), (24, 24, 24))
    d = ImageDraw.Draw(tong)
    try:
        f = ImageFont.truetype(FONT, 17)
    except Exception:
        f = ImageFont.load_default()
    d.text((6, 5), "%s  crop %dx%d px" % (ten, crop.shape[1], crop.shape[0]),
           fill=(255, 255, 120), font=f)
    for i, (k, pil) in enumerate(tiles):
        y = 26 + i * H
        d.text((6, y + 4), "%s [%dx%d]" % (k, bien_the_img[k].shape[1],
                                           bien_the_img[k].shape[0]),
               fill=(120, 230, 255), font=f)
        s = ket_qua.get(k, "")
        d.text((6, y + 26), s[:26], fill=(160, 255, 160), font=f)
        d.text((6, y + 46), s[26:52], fill=(160, 255, 160), font=f)
        d.text((6, y + 66), s[52:78], fill=(160, 255, 160), font=f)
        d.text((6, y + 86), s[78:104], fill=(160, 255, 160), font=f)
        tong.paste(pil, (COT, y + 26))
    duong = os.path.join(THU_MUC_CROP, "%s_bien_the.png" % ten)
    tong.save(duong)
    return duong


def main():
    os.makedirs(THU_MUC_CROP, exist_ok=True)
    CHI_CROP = "--chi-crop" in sys.argv
    dong = []
    def p(s="", flush=True):
        print(s, flush=flush)
        dong.append(s)

    p("=" * 100)
    p("DO OCR tren 6 video moi - bien so ro" + ("  [CHI CROP]" if CHI_CROP else ""))
    p("=" * 100)

    ocr_tim = ocr_doc = reader = det = None
    from rapidocr_onnxruntime import RapidOCR
    from ultralytics import YOLO
    p("RapidOCR (co tim vung chu): khoi tao...", flush=True)
    ocr_tim = RapidOCR()
    if CHI_CROP:
        det = YOLO("yolo11n.pt")
    else:
        import easyocr
        p("RapidOCR (CHI DOC - bo qua khai tim): khoi tao...", flush=True)
        ocr_doc = RapidOCR(use_text_det=False, use_angle_cls=False)
        p("EasyOCR: khoi tao Reader (lan dau co the tai model)...", flush=True)
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        p("YOLO11n: nap model...", flush=True)
        det = YOLO("yolo11n.pt")
    p("xong khoi tao.\n")

    d_tim = DoKhong(_rapid_co_tim)
    d_doc = DoKhong(_rapid_chi_doc)
    d_easy = DoKhong(_easy)

    # ---- BUOC 1: tim vung bien
    p("-" * 100)
    p("BUOC 1 - XAC DINH VUNG BIEN")
    p("-" * 100)
    p("%-22s %-10s %-11s %s" % ("video", "cach", "crop px", "ghi chu"))
    crops = {}
    for ten in VIDEO:
        vp = os.path.join(GOC, "video_mau", "moi", ten + ".mp4")
        fr = None
        for idx in (50, 25, 75, 10):
            ok, f = _doc_khung(vp, idx)
            if ok and f is not None:
                fr = f
                break
        if fr is None:
            p("%-22s %s" % (ten, "KHONG DOC DUOC KHUNG"))
            crops[ten] = None
            continue

        cv2.imwrite(os.path.join(THU_MUC_CROP, "%s_khung.png" % ten), fr)

        # Cach A - YOLO + ty le cua _kk_xac_nhan_ocr.py (da mo rong khi anh canh canh)
        vA, moA = vung_bien_theo_yolo(det, fr)

        # Cach B - contour cum chu
        vB, moB = vung_bien_theo_contour(fr)

        # Cach C - bo tim chu cua RapidOCR, ghep khung chu cung hang
        vC, moC = vung_bien_theo_ocr_det(ocr_tim, fr)

        # Luu crop cua ca 3 cach de doi chieu bang mat
        for nhan, v in (("A", vA), ("B", vB), ("C", vC)):
            if v is not None and v.size:
                cv2.imwrite(os.path.join(THU_MUC_CROP, "%s_crop_%s.png" % (ten, nhan)), v)

        # Do tren crop SAT bien so: uu tien C, fallback A' roi B
        if vC is not None:
            crops[ten] = (vC, "C: OCR-det",
                          "C: %s | A: %s | B: %s" % (moC, moA, moB))
        elif vA is not None:
            crops[ten] = (vA, "A: YOLO11n",
                          "A: %s | B: %s | C: %s" % (moA, moB, moC))
        elif vB is not None:
            crops[ten] = (vB, "B: contour",
                          "B: %s | A: %s | C: %s" % (moB, moA, moC))
        else:
            crops[ten] = None
            mo_ta = "A: %s | B: %s | C: %s" % (moA, moB, moC)
        if crops[ten]:
            v, c, m = crops[ten]
            p("%-22s %-10s %-11s %s" % (ten, c, "%dx%d" % (v.shape[1], v.shape[0]), m))
        else:
            p("%-22s %-10s %-11s %s" % (ten, "KHONG CO", "-", mo_ta))
    p("")

    if CHI_CROP:
        for ten in VIDEO:
            c = crops.get(ten)
            if c is not None:
                cv2.imwrite(os.path.join(THU_MUC_CROP, "%s_crop.png" % ten), c[0])
                p("  %s" % os.path.join(THU_MUC_CROP, "%s_crop.png" % ten))
        return 0

    # ---- BUOC 2 + 3
    p("-" * 100)
    p("BUOC 2 + BUOC 3 - OCR 4 bien the x 3 che do")
    p("-" * 100)
    bảng = {}
    duong_crops = {}
    for ten in VIDEO:
        c = crops.get(ten)
        if c is None:
            bảng[ten] = {}
            p("%s: khong co vung bien -> bo qua" % ten)
            continue
        vung, cach, mo_ta = c
        cv2.imwrite(os.path.join(THU_MUC_CROP, "%s_crop.png" % ten), vung)
        duong_crops[ten] = os.path.join(THU_MUC_CROP, "%s_crop.png" % ten)
        bt = bien_the(vung)
        o = {}
        for k, img in bt.items():
            s1, m1 = d_tim.goi(ocr_tim, img)
            s2, m2 = d_doc.goi(ocr_doc, img)
            s3, m3 = d_easy.goi(reader, img)
            o[k] = {"rapid_tim": s1 or "", "rapid_doc": s2 or "", "easy": s3 or "",
                    "ms": [m1, m2, m3]}
        bảng[ten] = o
        p("[%s] %s  crop=%dx%dpx  (%s)" % (ten, cach, vung.shape[1], vung.shape[0], mo_ta))
        p("   %-9s | %-26s %8s | %-26s %8s | %-26s %8s" %
          ("bien the", "RapidOCR CO TIM", "ms", "RapidOCR CHI DOC", "ms", "EasyOCR", "ms"))
        for k in ("goc", "x3_cubic", "x4_cubic", "x4_clahe"):
            r = o[k]
            p("   %-9s | %-26s %8.1f | %-26s %8.1f | %-26s %8.1f" %
              (k, r["rapid_tim"] or "(khong doc)", r["ms"][0],
               r["rapid_doc"] or "(khong doc)", r["ms"][1],
               r["easy"] or "(khong doc)", r["ms"][2]))
        p("")
    p("GHI CHU: 2 lan goi dau tien cua moi engine bi bo (warm-up).")
    p("")

    # ---- Chot mau + thong ke
    p("-" * 100)
    p("BUOC 3 - KET QUA DOI VOI MAU BIEN")
    p("-" * 100)
    khoa = ("rapid_tim", "rapid_doc", "easy")
    nhan = {"rapid_tim": "RapidOCR CO TIM", "rapid_doc": "RapidOCR CHI DOC",
            "easy": "EasyOCR"}
    bienthe = ("goc", "x3_cubic", "x4_cubic", "x4_clahe")
    tong_dem = {(b, k): 0 for b in bienthe for k in khoa}
    tong_ms = {(b, k): [] for b in bienthe for k in khoa}
    tong_ms_tong = {k: [] for k in khoa}

    p("%-22s %-14s %-9s %s" % ("video", "mau (chuoi doc)", "Bien VN?", "OCR thang"))
    for ten in VIDEO:
        o = bảng.get(ten) or {}
        if not o:
            continue
        tat_ca = [chuan_hoa(o[b][k]) for b in bienthe for k in khoa]
        if ten in MAU_TAY:
            mau, nguon = MAU_TAY[ten], "xac nhan bang mat"
        else:
            cnt = Counter([t for t in tat_ca if t])
            mau = cnt.most_common(1)[0][0] if cnt else ""
            nguon = "consensus (CHUA kiem chung bang mat)"
        bảng[ten]["_mau"] = mau
        bảng[ten]["_nguon_mau"] = nguon
        bảng[ten]["_bien_vn"] = co_the_la_bien_vn(mau)

        thang = []
        chua = []
        for k in khoa:
            for b in bienthe:
                r = o[b]
                s = chuan_hoa(r[k])
                if mau and s == mau:
                    tong_dem[(b, k)] += 1
                    thang.append("%s/%s" % (nhan[k], b))
                # "chua mau": chuoi doc co chua day du chuoi bien (thu tu co
                # the khac do - crop rong co chu quang cao quanh bien)
                if mau and len(mau) >= 4:
                    ss = "".join(sorted(s))
                    mm = "".join(sorted(mau))
                    if mm == ss or (mm in ss):
                        chua.append("%s/%s" % (nhan[k], b))
                if r["ms"][khoa.index(k)] > 0:
                    tong_ms[(b, k)].append(r["ms"][khoa.index(k)])
        r0 = o["goc"]
        for idx, k in enumerate(khoa):
            if r0["ms"][idx] > 0:
                tong_ms_tong[k].append(r0["ms"][idx])
        bv = "CO" if co_the_la_bien_vn(mau) else "khong"
        p("%-22s %-14s %-9s %s" % (ten, mau or "(khong doc)", bv,
                                   ", ".join(thang) if thang else "KHONG bien the nao doc KHOP MAU"))
        p("%-22s %-14s %-9s %s" % ("", "", "chua mau:",
                                   ", ".join(chua) if chua
                                   else "khong bien the nao doc ra duoc day du chuoi bien"))
    p("")

    p("%-11s | %-28s | %-28s | %s" % ("bien the", "RapidOCR CO TIM", "RapidOCR CHI DOC", "EasyOCR"))
    p("-" * 100)
    for b in bienthe:
        p("%-11s | %-28s | %-28s | %s" % (
            b,
            "khop %d/%d  tb %.0f ms" % (tong_dem[(b, "rapid_tim")], len(bảng),
                                       (sum(tong_ms[(b, "rapid_tim")]) / max(1, len(tong_ms[(b, "rapid_tim")])))),
            "khop %d/%d  tb %.0f ms" % (tong_dem[(b, "rapid_doc")], len(bảng),
                                       (sum(tong_ms[(b, "rapid_doc")]) / max(1, len(tong_ms[(b, "rapid_doc")])))),
            "khop %d/%d  tb %.0f ms" % (tong_dem[(b, "easy")], len(bảng),
                                       (sum(tong_ms[(b, "easy")]) / max(1, len(tong_ms[(b, "easy")]))))))
    p("-" * 100)
    p("Chi goc:  Rapid CO TIM tb %.0f ms | Rapid CHI DOC tb %.0f ms | EasyOCR tb %.0f ms" %
      (sum(tong_ms_tong["rapid_tim"]) / max(1, len(tong_ms_tong["rapid_tim"])),
       sum(tong_ms_tong["rapid_doc"]) / max(1, len(tong_ms_tong["rapid_doc"])),
       sum(tong_ms_tong["easy"]) / max(1, len(tong_ms_tong["easy"]))))
    p("")

    # ---- BUOC 4: luu anh chung
    for ten in VIDEO:
        o = bảng.get(ten) or {}
        if not o:
            continue
        c = crops[ten]
        bt = bien_the(c[0])
        nhan_dong = {}
        for b in bienthe:
            r = o[b]
            nhan_dong[b] = ("R_tim=%s | R_doc=%s | Easy=%s" %
                            (r["rapid_tim"] or "-", r["rapid_doc"] or "-",
                             r["easy"] or "-"))
        ghép_4_bien_the(c[0], ten, bt, nhan_dong)

    p("-" * 100)
    p("ANH CHUNG")
    p("-" * 100)
    for ten in VIDEO:
        for f in ("%s_crop.png" % ten, "%s_bien_the.png" % ten):
            fp = os.path.join(THU_MUC_CROP, f)
            if os.path.exists(fp):
                p("  " + fp)
    p("")

    p("=" * 100)
    p("KET LUAN")
    p("=" * 100)
    n_khop = 0
    n_chua = 0
    for ten in VIDEO:
        o = bảng.get(ten) or {}
        if not o or not o.get("_mau"):
            continue
        mau = o["_mau"]
        k1 = k2 = False
        for b in bienthe:
            for k in khoa:
                s = chuan_hoa(o[b][k])
                if not mau or not s:
                    continue
                if s == mau:
                    k1 = True
                if "".join(sorted(mau)) in "".join(sorted(s)):
                    k2 = True
        n_khop += 1 if k1 else 0
        n_chua += 1 if (k1 or k2) else 0
        p("  %-22s mau=%-12s  %s" % (
            ten, mau,
            "DOC KHOP MAU" if k1 else ("doc ra duoc chuoi bien" if k2
                                       else "KHONG doc duoc bien so")))
    n = len([t for t in VIDEO if (bảng.get(t) or {})])
    p("")
    p("Video co mau bien xac nhan bang mat: %d/%d" % (n, len(VIDEO)))
    p("Video co >=1 to (bien the x OCR) doc KHOP MAU: %d/%d" % (n_khop, n))
    p("Video co >=1 to doc ra DU DAY chuoi bien: %d/%d" % (n_chua, n))
    bv = [t for t in VIDEO if (bảng.get(t) or {}).get("_bien_vn")]
    p("Bien khu vuc Viet Nam: %s" % (", ".join(bv) if bv else "KHONG - 6 anh deu la bien EU/chau Au"))
    p("Tong so video: %d, tong so lan goi OCR (3 che do x 4 bien the x %d video): %d" %
      (len(VIDEO), len(VIDEO), len(VIDEO) * 4 * 3))

    with open(FILE_TXT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")
    print("\nDa luu: " + FILE_TXT)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(0)
