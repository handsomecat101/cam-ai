# -*- coding: utf-8 -*-
"""BENCHMARK doc bien so (OCR): rapidocr-onnxruntime vs easyocr.

Muc dich: so sanh bang SO THAT truoc khi chon thu vien nao dua vao san pham.
Tra loi 3 cau hoi: cai nao doc DUNG hon, cai nao NHANH hon, cai nao CHIEM BAO NHIEU dia bang.

KHONG sua code san pham. Script chi DOC va TAO file trong _kiem_chung/plate_thu/.

Anh thu gom 2 nguon:
  1. Anh TONG HOP (PIL ve) co NHAN BIET TRUOC -> do chinh xac tuyet doi.
     KHONG thay the duoc anh that, chi de so sanh 2 thu vien voi nhau.
  2. Anh BIEN SO CROP tu video (YOLO tim xe -> cat vung bien so) -> khong co
     nhan that, chi dem 'co doc ra chuoi hop le bien so hay khong'.

Chay: .venv\\Scripts\\python.exe _kk_bien_so.py
"""

import importlib.metadata as md
import json
import os
import re
import statistics
import sys
import time
import traceback

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

for _s in ("stdout", "stderr"):
    try:
        getattr(sys, _s).reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GOC = os.path.dirname(os.path.abspath(__file__))
THU_MUC = os.path.join(GOC, "_kiem_chung", "plate_thu")
THU_TONG_HOP = os.path.join(THU_MUC, "synthetic")
THU_VIDEO = os.path.join(THU_MUC, "video")
FILE_BAO_CAO = os.path.join(THU_MUC, "bench_bien_so.txt")
FILE_ANH = os.path.join(THU_MUC, "ten_thu_vi.png")
VIDEO = os.path.join(GOC, "video_mau", "moi", "xe-co-giao-thong.mp4")
MODEL_YOLO = os.path.join(GOC, "yolo11n.pt")

# ---------------- tham so do ----------------
KICH_THUOC = (220, 50)          # px, giong bien so that tren camera
CO_FONT = 34
TY_LE_NHO = 0.5                 # che do phu: thu bien so nho (110x25)
LOC_MOI = 0.6                   # GaussianBlur - mo bien so nhe nhu camera that
NGUONG_CONF = 0.30              # EasyOCR: bo ket qua tin cay thap
SO_KHUNG_VIDEO = 30             # so khung quet de tim bien so trong video
SO_ANH_VIDEO = 8                # so anh crop giu lai tu video
SO_ANH_VE = 8                   # so dong ve vao PNG (de anh nhìn bằng mắt cho ro)
XE_CO = {2: "car", 3: "moto", 5: "bus", 7: "truck"}
NHAN_SACH = [
    "30A-12345", "51F-678.90", "29B-123.45", "B1X-234.56",
    "61A-999.99", "30H-876.54", "77B-123.45", "51A-111.11",
]
BIEU_HOP_LE = re.compile(r"^[0-9]{2}[A-Z]{1,2}[0-9]{4,6}$")
MAU_DUNG = (0, 170, 0)
MAU_SAI = (220, 0, 0)
MAU_KHUNG = (240, 160, 0)
MAU_NEN = (24, 24, 28)
MAU_CHU = (255, 255, 255)


def tai_font(co):
    duong = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arialbd.ttf")
    if os.path.exists(duong):
        return ImageFont.truetype(duong, co)
    return ImageFont.load_default(size=co)


def ban_anh(duong, ty_le=1.0):
    """Doc anh (PIL) -> mang BGR cho OCR, co phong to/thu nho theo ty_le."""
    img = Image.open(duong).convert("RGB")
    if ty_le != 1.0:
        img = img.resize((max(1, int(round(img.width * ty_le))),
                          max(1, int(round(img.height * ty_le)))), Image.LANCZOS)
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# ================== 1. ANH TONG HOP (co nhan biet truoc) ==================
def ve_bien_so(nhan):
    """Ve mot bien so VN tren nen trang, tu co gian chu cho vua khung."""
    anh = Image.new("RGB", KICH_THUOC, "white")
    d = ImageDraw.Draw(anh)
    d.rectangle([1, 1, KICH_THUOC[0] - 2, KICH_THUOC[1] - 2], outline=(70, 70, 70), width=2)
    co = CO_FONT
    while co > 18:
        if d.textlength(nhan, font=tai_font(co)) <= KICH_THUOC[0] - 30:
            break
        co -= 1
    d.text((15, 7), nhan, font=tai_font(co), fill="black")
    return anh


def tao_anh_tong_hop():
    """Sinh 2 ban moi nhan: ban sach + ban mo nhe. Co nhan -> do chinh xac tuyet doi."""
    os.makedirs(THU_TONG_HOP, exist_ok=True)
    ds = []
    for i, nhan in enumerate(NHAN_SACH):
        for lo, anh in (
            ("sach", ve_bien_so(nhan)),
            ("mo", ve_bien_so(nhan).filter(ImageFilter.GaussianBlur(LOC_MOI))),
        ):
            ten = "%02d_%s_%s.png" % (i, lo, nhan.replace("-", "").replace(".", ""))
            duong = os.path.join(THU_TONG_HOP, ten)
            anh.save(duong)
            ds.append({"duong": duong, "nhan": nhan, "loai": "tong_hop", "phu": lo})
    with open(os.path.join(THU_TONG_HOP, "nhan.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump([{"ten": os.path.basename(d["duong"]), "nhan": d["nhan"], "phu": d["phu"]}
                   for d in ds], f, ensure_ascii=False, indent=1)
    return ds


# ================== 2. ANH BIEN SO THAT TU VIDEO (khong co nhan) ==================
def diem_bien_so(crop):
    """Cham diem 1 vung co gia bien so: nen sang + chu toi dam + nhich so ky tu."""
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if g.size == 0:
        return -1.0
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    den = (bw == 0)
    r = float(den.mean())
    if not (0.05 <= r <= 0.45):
        return -1.0
    trang = g[~den]
    toi = g[den]
    if trang.size < 40 or toi.size < 40:
        return -1.0
    if float(trang.mean()) < 110.0:           # nen phai sang
        return -1.0
    tuong_phan = float(trang.mean() - toi.mean()) / 255.0
    cot = den.mean(axis=0).astype(np.float32)
    bien = float(np.abs(np.diff(cot)).sum()) / (0.55 * len(cot))   # nhich sọc ngang = ky tu
    return tuong_phan * min(1.0, bien)


def _iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    giao = (x1 - x0) * (y1 - y0)
    la = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - giao
    return giao / la if la > 0 else 0.0


def lay_anh_tu_video():
    """YOLO tim xe -> cat vung bien so khu vuc duoi -> cham diem -> giu vung tot nhat."""
    if not (os.path.exists(VIDEO) and os.path.exists(MODEL_YOLO)):
        return []
    os.makedirs(THU_VIDEO, exist_ok=True)
    from ultralytics import YOLO
    mo = YOLO(MODEL_YOLO)
    cap = cv2.VideoCapture(VIDEO)
    tong = int(cap.get(7))
    if not cap.isOpened() or tong <= 0:
        cap.release()
        return []
    hang = int(cap.get(4))
    rong = int(cap.get(3))
    ds = []
    for i in range(SO_KHUNG_VIDEO):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(tong * (i + 0.5) / SO_KHUNG_VIDEO))
        ok, khung = cap.read()
        if not ok:
            continue
        r = mo.predict(khung, conf=0.30, verbose=False)[0]
        for xyxy, cid in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist()):
            if int(cid) not in XE_CO:
                continue
            x0, y0, x1, y1 = xyxy
            bw, bh = x1 - x0, y1 - y0
            if bw < 40 or bh < 20:
                continue
            for rx0, ry0, rx1, ry1 in ((0.15, 0.70, 0.85, 1.00), (0.20, 0.55, 0.80, 0.85)):
                ax0, ay0 = x0 + rx0 * bw, y0 + ry0 * bh
                ax1, ay1 = x0 + rx1 * bw, y0 + ry1 * bh
                if ax1 - ax0 < 30 or ay1 - ay0 < 8:
                    continue
                c = khung[int(ay0):int(ay1), int(ax0):int(ax1)]
                d = diem_bien_so(c)
                if d > 0:
                    ds.append((d, i, int(ax0), int(ay0), int(ax1), int(ay1), c.copy()))
        print("  khung %d/%d - ung vien: %d" % (i + 1, SO_KHUNG_VIDEO, len(ds)), flush=True)
    cap.release()
    ds.sort(key=lambda z: -z[0])
    ra, vung = [], []
    for d, i, x0, y0, x1, y1, c in ds:
        hinh = (x0 / rong, y0 / hang, x1 / rong, y1 / hang)
        if any(_iou(hinh, v) > 0.35 for v in vung):
            continue
        vung.append(hinh)
        ten = "crop_%02d_khung%d_%dx%d_diem%.3f.png" % (len(ra) + 1, i, x1 - x0, y1 - y0, d)
        cv2.imwrite(os.path.join(THU_VIDEO, ten), c)
        ra.append({"duong": os.path.join(THU_VIDEO, ten), "nhan": None,
                   "loai": "video", "phu": "xe %dx%d" % (x1 - x0, y1 - y0)})
        if len(ra) >= SO_ANH_VIDEO:
            break
    return ra


# ================== 3. CHUAN HOA + CHAY OCR ==================
def chuan_hoa(s):
    """Viet HOA, bo khoang trang / dau cham / dau '-' / cham sau chu cai."""
    return re.sub(r"[^0-9A-Z]", "", str(s).upper())


def xep_hang(muc):
    """Ghep cac manh chu ve dung thu tu doc.
    Neu tat ca cac manh cung 1 hang (trung keo nhau doc theo chieu doc) -> sap theo x.
    Neu nhieu hang -> sap theo hang roi theo x."""
    if len(muc) < 2:
        return list(muc)
    y0 = [float(m["box"][:, 1].min()) for m in muc]
    y1 = [float(m["box"][:, 1].max()) for m in muc]
    cao = [max(1.0, b - a) for a, b in zip(y0, y1)]
    cung_hang = True
    for i in range(len(muc)):
        for j in range(i + 1, len(muc)):
            trung = min(y1[i], y1[j]) - max(y0[i], y0[j])
            if trung < 0.5 * min(cao[i], cao[j]):
                cung_hang = False
                break
        if not cung_hang:
            break
    if cung_hang:
        return sorted(muc, key=lambda m: float(m["box"][:, 0].min()))
    nhom = max(8.0, (max(y1) - min(y0)) * 0.4)
    return sorted(muc, key=lambda m: (int((float(m["box"][:, 1].min()) - min(y0)) / nhom),
                                     float(m["box"][:, 0].min())))


class RapidOcr:
    ten = "RapidOCR"

    def __init__(self):
        import rapidocr_onnxruntime
        self.mod = "rapidocr-onnxruntime " + md.version("rapidocr-onnxruntime")
        self.thu_muc_model = os.path.join(os.path.dirname(rapidocr_onnxruntime.__file__), "models")
        self.engine = rapidocr_onnxruntime.RapidOCR()

    def doc(self, img):
        res, _ = self.engine(img)
        muc = []
        for it in (res or []):
            conf = it[2] if isinstance(it[2], (int, float)) else 0.0
            muc.append({"box": np.asarray(it[0], dtype=float), "text": str(it[1]), "conf": float(conf)})
        return muc


class EasyOcr:
    ten = "EasyOCR"

    def __init__(self):
        import easyocr
        self.mod = "easyocr " + md.version("easyocr")
        self.thu_muc_model = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")),
                                          ".EasyOCR", "model")
        self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def doc(self, img):
        muc = []
        for box, text, conf in self.reader.readtext(img):
            muc.append({"box": np.asarray(box, dtype=float), "text": str(text), "conf": float(conf)})
        return [m for m in muc if m["conf"] >= NGUONG_CONF]


def chay_va_chuan_hoa(dv, img):
    muc = xep_hang(dv.doc(img))
    hien = " | ".join(m["text"].strip() for m in muc) if muc else "(khong doc ra gi)"
    return {"muc": muc, "hien": hien, "chuoi": chuan_hoa("".join(m["text"] for m in muc)),
            "conf": max([m["conf"] for m in muc], default=0.0)}


# ================== 4. VE ANH SO SANH ==================
def chu_nen(ve, xy, chu, font, mau):
    """Chu co nen den nen de doc duoc tren anh sang."""
    bb = ve.textbbox(xy, chu, font=font)
    ve.rectangle([bb[0] - 3, bb[1] - 2, bb[2] + 3, bb[3] + 2], fill=(0, 0, 0))
    ve.text(xy, chu, font=font, fill=mau)


def ve_anh(bang, duong_out):
    """Mot dong = anh thu (khung OCR cua 2 thu vien) + bang ket qua ben canh."""
    f_tieu = tai_font(26)
    f_chu = tai_font(20)
    f_nho = tai_font(18)
    rong_img, rong_chu = 640, 420
    tong_rong = rong_img + rong_chu + 16
    dong = []
    for b in bang:
        img = Image.open(b["duong"]).convert("RGB")
        anh_anh = img.resize((rong_img, max(1, int(img.height * rong_img / img.width))), Image.LANCZOS)
        ty_le = rong_img / float(img.width)          # khung OCR nam trong toan bo anh goc
        ve = ImageDraw.Draw(anh_anh)
        mau = MAU_DUNG if b["dung_r"] else MAU_SAI
        for m in b["muc_e"]:
            ve.polygon([(float(p[0]) * ty_le, float(p[1]) * ty_le) for p in m["box"]], outline=MAU_KHUNG)
        if b["muc_r"]:
            tat = np.concatenate([m["box"] for m in b["muc_r"]], axis=0)
            x0, y0 = float(tat[:, 0].min()) * ty_le, float(tat[:, 1].min()) * ty_le
            x1, y1 = float(tat[:, 0].max()) * ty_le, float(tat[:, 1].max()) * ty_le
            for m in b["muc_r"]:
                ve.polygon([(float(p[0]) * ty_le, float(p[1]) * ty_le) for p in m["box"]], outline=mau)
            ve.rectangle([x0, y0, x1, y1], outline=MAU_KHUNG, width=3)
            chu_nen(ve, (max(0, x0), max(0, y0 - 21)),
                    "RapidOCR: " + (b["hien_r"] if b["muc_r"] else "KHONG DOC RA"), f_nho, MAU_KHUNG)
        if b["muc_e"]:
            chu_nen(ve, (4, anh_anh.height - 21),
                    "EasyOCR: " + " ".join("[%s %.0f%%]" % (m["text"].strip(), m["conf"] * 100)
                                           for m in b["muc_e"]), f_nho, MAU_KHUNG)

        chieu = max(anh_anh.height, 200)
        khung = Image.new("RGB", (tong_rong, chieu + 34), (243, 243, 243))
        kd = ImageDraw.Draw(khung)
        kd.rectangle([0, 0, tong_rong, 33], fill=MAU_NEN)
        kd.text((8, 6), "%s  |  nhan: %s" % (os.path.basename(b["duong"])[:52],
                                              b["nhan"] if b["nhan"] else "(khong ro)"),
                font=f_tieu, fill=MAU_CHU)
        khung.paste(anh_anh, (0, 34))
        cx, dong_y = rong_img + 12, 42
        for ten, hien, dung, ms in (("RapidOCR", b["hien_r"], b["dung_r"], b["ms_r"]),
                                    ("EasyOCR", b["hien_e"], b["dung_e"], b["ms_e"])):
            kd.text((cx, dong_y), ten, font=f_chu, fill=(0, 0, 0)); dong_y += 25
            for i in range(0, max(1, len(hien)), 22):
                kd.text((cx, dong_y), hien[i:i + 22], font=f_chu, fill=(0, 0, 0)); dong_y += 25
            kd.text((cx, dong_y + 4), "DUNG" if dung else "SAI", font=f_chu,
                    fill=(0, 150, 0) if dung else (200, 0, 0)); dong_y += 34
            kd.text((cx, dong_y), "%.0f ms" % ms, font=f_chu, fill=(95, 95, 95)); dong_y += 36
        dong.append(khung)

    tieu = Image.new("RGB", (tong_rong, 104), MAU_NEN)
    td = ImageDraw.Draw(tieu)
    td.text((8, 6), "SO SANH OCR BIEN SO - RapidOCR (xanh=khop dung, do=sai) vs EasyOCR (cam=vang)",
            font=f_tieu, fill=MAU_CHU)
    td.text((8, 38), "Chuoi chuan hoa = viet HOA + bo ky tu khong phai 0-9/A-Z. Khop = khop TUYET DOI.",
            font=f_chu, fill=(200, 200, 200))
    td.text((8, 62), "Khung cam = EasyOCR. Khung xanh/do = RapidOCR. Khung cam bao = tap hop RapidOCR.",
            font=f_chu, fill=(200, 200, 200))
    td.text((8, 86), "Anh tong hop KHONG thay the anh that video - chi de so sanh 2 thu vien.",
            font=f_chu, fill=(200, 200, 200))
    tong_cao = 104 + sum(d.height for d in dong) + 8 * (len(dong) - 1)
    ra = Image.new("RGB", (tong_rong, tong_cao), (255, 255, 255))
    ra.paste(tieu, (0, 0))
    y = 104
    for i, d in enumerate(dong):
        ra.paste(d, (0, y))
        y += d.height
        if i < len(dong) - 1:
            for yy in range(y, y + 8):
                for x in range(0, tong_rong):
                    ra.putpixel((x, yy), (205, 205, 205) if yy % 2 else (255, 255, 255))
            y += 8
    os.makedirs(os.path.dirname(duong_out), exist_ok=True)
    ra.save(duong_out)
    return ra.size


def kich_thuoc_model(thu_muc):
    if not thu_muc or not os.path.isdir(thu_muc):
        return 0, 0
    tong = n = 0
    for g, _, fs in os.walk(thu_muc):
        for f in fs:
            try:
                tong += os.path.getsize(os.path.join(g, f))
                n += 1
            except OSError:
                pass
    return n, tong


def mb(x):
    return "%.1f MB" % (x / 1048576.0)


# ================== 5. CHUONG TRINH CHINH ==================
def do_thu_vien(dv, anh, ten_b, ty_le=1.0, in_tien_do=True):
    """Warm-up rieng (khong tinh vao so lieu) roi do ms/anh tren tung anh thu."""
    t0 = time.perf_counter()
    for i in range(min(3, len(anh))):
        dv.doc(ban_anh(anh[i]["duong"], ty_le))
    warm = (time.perf_counter() - t0) * 1000.0
    print("  [%s] warm-up xong %.0f ms (khong tinh vao so lieu)" % (ten_b, warm), flush=True)
    bang = []
    for a in anh:
        img = ban_anh(a["duong"], ty_le)
        t = time.perf_counter()
        kq = chay_va_chuan_hoa(dv, img)
        ms = (time.perf_counter() - t) * 1000.0
        kq["ms"] = ms
        bang.append(kq)
        if in_tien_do:
            print("  [%s] %-40s %-24s %7.0f ms" % (ten_b, os.path.basename(a["duong"])[:40],
                                                    kq["hien"][:24], ms), flush=True)
    return bang, warm


def main():
    bat_dau = time.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(THU_MUC, exist_ok=True)
    print("=" * 70)
    print("BENCHMARK OCR BIEN SO: rapidocr-onnxruntime vs easyocr")
    print("=" * 70)

    print("[1] Tao anh thu tong hop (PIL ve, co nhan biet truoc)...", flush=True)
    thu = tao_anh_tong_hop()
    print("    -> %d anh tong hop (%d nhan x sach/mo)" % (len(thu), len(NHAN_SACH)), flush=True)
    print("[2] Crop bien so that tu video (YOLO tim xe -> cat vung bien so)...", flush=True)
    tu_video = lay_anh_tu_video()
    print("    -> %d anh crop tu video (khong co nhan that)" % len(tu_video), flush=True)
    anh = thu + tu_video
    if not thu:
        raise SystemExit("Khong tao duoc anh thu tong hop.")

    print("[3] RapidOCR (warm-up roi do)...", flush=True)
    t = time.perf_counter()
    r = RapidOcr()
    print("    khoi tao %.0f ms" % ((time.perf_counter() - t) * 1000), flush=True)
    kq_r, warm_r = do_thu_vien(r, anh, "RapidOCR")

    print("[4] EasyOCR (warm-up roi do)...", flush=True)
    t = time.perf_counter()
    e = EasyOcr()
    print("    khoi tao Reader %.0f ms" % ((time.perf_counter() - t) * 1000), flush=True)
    kq_e, warm_e = do_thu_vien(e, anh, "EasyOCR")

    # ---- che do phu: bien so nho (mo phong khu vuc cat tu video) ----
    nho = [a for a in thu if a["phu"] == "sach"]
    print("[5] Che do phu: bien so nho %dx%d cho ca 2 thu vien..." % (
        int(KICH_THUOC[0] * TY_LE_NHO), int(KICH_THUOC[1] * TY_LE_NHO)), flush=True)
    kq_rn, _ = do_thu_vien(r, nho, "RapidOCR nho", TY_LE_NHO, in_tien_do=False)
    kq_en, _ = do_thu_vien(e, nho, "EasyOCR nho", TY_LE_NHO, in_tien_do=False)
    dung_rn = sum(1 for a, k in zip(nho, kq_rn) if chuan_hoa(a["nhan"]) == k["chuoi"])
    dung_en = sum(1 for a, k in zip(nho, kq_en) if chuan_hoa(a["nhan"]) == k["chuoi"])
    ms_rn = statistics.median([k["ms"] for k in kq_rn])
    ms_en = statistics.median([k["ms"] for k in kq_en])

    # ---- cham diem ----
    bang = []
    for i, a in enumerate(anh):
        nhan = chuan_hoa(a["nhan"]) if a["nhan"] else None
        bang.append({
            "duong": a["duong"], "nhan": a["nhan"], "loai": a["loai"], "phu": a["phu"],
            "hien_r": kq_r[i]["hien"], "hien_e": kq_e[i]["hien"],
            "chuoi_r": kq_r[i]["chuoi"], "chuoi_e": kq_e[i]["chuoi"],
            "dung_r": nhan is not None and kq_r[i]["chuoi"] == nhan,
            "dung_e": nhan is not None and kq_e[i]["chuoi"] == nhan,
            "ms_r": kq_r[i]["ms"], "ms_e": kq_e[i]["ms"],
            "muc_r": kq_r[i]["muc"], "muc_e": kq_e[i]["muc"],
        })

    co_nhan = [b for b in bang if b["nhan"]]
    khong_nhan = [b for b in bang if not b["nhan"]]
    dung_r = sum(1 for b in co_nhan if b["dung_r"])
    dung_e = sum(1 for b in co_nhan if b["dung_e"])
    hop_r = sum(1 for b in khong_nhan if BIEU_HOP_LE.match(b["chuoi_r"]))
    hop_e = sum(1 for b in khong_nhan if BIEU_HOP_LE.match(b["chuoi_e"]))
    doc_r = sum(1 for b in khong_nhan if b["chuoi_r"])
    doc_e = sum(1 for b in khong_nhan if b["chuoi_e"])
    ms_r = statistics.median([b["ms_r"] for b in bang])
    ms_e = statistics.median([b["ms_e"] for b in bang])
    tb_r = statistics.mean([b["ms_r"] for b in bang])
    tb_e = statistics.mean([b["ms_e"] for b in bang])
    n_rm, gb_r = kich_thuoc_model(r.thu_muc_model)
    n_em, gb_e = kich_thuoc_model(e.thu_muc_model)

    print("[6] Ket qua", flush=True)
    print("    Tong dung (co nhan): RapidOCR %d/%d - EasyOCR %d/%d" % (dung_r, len(co_nhan), dung_e, len(co_nhan)), flush=True)
    print("    Bien so nho (%dx%d): RapidOCR %d/%d - EasyOCR %d/%d" % (
        int(KICH_THUOC[0] * TY_LE_NHO), int(KICH_THUOC[1] * TY_LE_NHO),
        dung_rn, len(nho), dung_en, len(nho)), flush=True)
    print("    Video (khong nhan):  RapidOCR doc %d/%d chuoi (hop le %d) - EasyOCR doc %d/%d (hop le %d)" % (
        doc_r, len(khong_nhan), hop_r, doc_e, len(khong_nhan), hop_e), flush=True)
    print("    Trung vien ms/anh:   RapidOCR %.1f ms - EasyOCR %.1f ms" % (ms_r, ms_e), flush=True)

    ve = ([b for b in co_nhan if b["phu"] == "sach"][:2]
          + [b for b in co_nhan if b["phu"] == "mo"][:2]
          + [b for b in khong_nhan][:2])
    kich = ve_anh(ve, FILE_ANH)
    print("[7] Anh so sanh: %s (%dx%d, %d dong)" % (FILE_ANH, kich[0], kich[1], len(ve)), flush=True)

    # ---- bao cao ----
    L = []
    A = L.append
    A("=" * 78)
    A("BENCHMARK OCR BIEN SO - rapidocr-onnxruntime vs easyocr")
    A("Chay luc: %s | Python %s | may: %s" % (bat_dau, sys.version.split()[0], os.environ.get("COMPUTERNAME", "?")))
    A("=" * 78)
    A("")
    A("[1] DIEU KIEN DO")
    A("    %s" % r.mod)
    A("    %s | Reader(['en'], gpu=False, verbose=False)" % e.mod)
    A("    Anh dua VAO OCR o kich thuoc goc (khong phong to them): bien so tong hop 220x50,")
    A("    bien so crop tu video kich thuoc that. Ca 2 thu vien nhan DUNG cung kich thuoc.")
    A("    EasyOCR bo ket qua tin cay < %.2f. Cac manh chu bi ghep theo thu tu doc" % NGUONG_CONF)
    A("    (cung 1 hang -> theo x, nhieu hang -> theo hang roi theo x).")
    A("    Chuoi chuan hoa: viet HOA + bo moi ky tu khong phai 0-9/A-Z (bo khoang trong,")
    A("      dau cham, dau '-', cham sau chu cai). So sanh = KHop TUYET DOI chuoi.")
    A("    Anh thu: %d anh tong hop (co nhan) + %d anh bien so crop video (khong nhan) = %d" % (
        len(co_nhan), len(khong_nhan), len(bang)))
    A("    Thoi gian DO khong gom: warm-up (RapidOCR %.0f ms, EasyOCR %.0f ms) va thoi gian" % (warm_r, warm_e))
    A("    khoi tao model. Lan chay dau tien EasyOCR tai model ~100MB - thoi gian tai do NAM")
    A("    TRONG warm-up, khong co trong ms/anh.")
    A("")
    A("[2] BANG DOI CHIEU (DUNG = khop tuyet doi voi nhan da biet)")
    A("")
    A("  %-36s %-12s %-14s %-14s %-6s %-6s" % ("ANH THU", "NHAN", "RAPIDOCR", "EASYOCR", "RAPID", "EASY"))
    A("  " + "-" * 94)
    for b in bang:
        A("  %-36s %-12s %-14s %-14s %-6s %-6s" % (
            os.path.basename(b["duong"])[:36], (b["nhan"] or "(khong ro)")[:12],
            (b["chuoi_r"] or "-")[:14], (b["chuoi_e"] or "-")[:14],
            "DUNG" if b["dung_r"] else "sai", "DUNG" if b["dung_e"] else "sai"))
    A("")
    A("[3] TONG KET DO CHINH XAC")
    A("    * Anh tong hop, co nhan (%d anh): RapidOCR DUNG %d/%d | EasyOCR DUNG %d/%d" % (
        len(co_nhan), dung_r, len(co_nhan), dung_e, len(co_nhan)))
    A("    * Che do phu, bien so nho %dx%d (%d anh): RapidOCR DUNG %d/%d | EasyOCR DUNG %d/%d" % (
        int(KICH_THUOC[0] * TY_LE_NHO), int(KICH_THUOC[1] * TY_LE_NHO), len(nho),
        dung_rn, len(nho), dung_en, len(nho)))
    if khong_nhan:
        A("    * Bien so crop tu video, khong co nhan (%d anh):" % len(khong_nhan))
        A("        RapidOCR doc ra chuoi gi: %d/%d | trong do chuoi HOP LE bien so: %d/%d" % (
            doc_r, len(khong_nhan), hop_r, len(khong_nhan)))
        A("        EasyOCR  doc ra chuoi gi: %d/%d | trong do chuoi HOP LE bien so: %d/%d" % (
            doc_e, len(khong_nhan), hop_e, len(khong_nhan)))
        if hop_r == 0 and hop_e == 0:
            A("        -> Video nay co xe nho + nhoeu nhieu manh, KHONG co bien so nao doc duoc.")
            A("           Phan nay khong phan biet duoc 2 thu vien, khong dung de ket luan.")
    A("")
    A("[4] TOC DO (trung vien ms/anh, DA LOAI TRUOC warm-up)")
    A("    RapidOCR: trung vien %7.1f ms | trung binh %7.1f ms | nhanh nhat %7.1f | cham nhat %7.1f" % (
        ms_r, tb_r, min(b["ms_r"] for b in bang), max(b["ms_r"] for b in bang)))
    A("    EasyOCR : trung vien %7.1f ms | trung binh %7.1f ms | nhanh nhat %7.1f | cham nhat %7.1f" % (
        ms_e, tb_e, min(b["ms_e"] for b in bang), max(b["ms_e"] for b in bang)))
    A("    Che do phu (bien so nho %dx%d): RapidOCR trung vien %7.1f ms | EasyOCR trung vien %7.1f ms" % (
        int(KICH_THUOC[0] * TY_LE_NHO), int(KICH_THUOC[1] * TY_LE_NHO), ms_rn, ms_en))
    A("    => EasyOCR cham hon RapidOCR %.1f lan o che do chinh (theo trung vien)." % (ms_e / ms_r if ms_r else 0))
    A("")
    A("[5] DUNG LUONG MODEL TREN DIA")
    A("    RapidOCR: %d file, %s" % (n_rm, mb(gb_r)))
    A("              %s" % r.thu_muc_model)
    A("    EasyOCR : %d file, %s" % (n_em, mb(gb_e)))
    A("              %s" % e.thu_muc_model)
    A("    (Tinh ca model, KHONG tinh thu vien + torch. Cai dat EasyOCR keo theo ca torch")
    A("     (~2 GB trong .venv), RapidOCR chi can onnxruntime.)\n")
    A("[6] KET LUAN")
    if dung_r > dung_e:
        A("    Chon RapidOCR: doc dung nhieu hon (%d vs %d) VA nhanh hon (%.1f vs %.1f ms/anh)." % (
            dung_r, dung_e, ms_r, ms_e))
    elif dung_e > dung_r:
        A("    Chon EasyOCR: doc dung nhieu hon (%d vs %d), cham hon %.1f lan (%.1f vs %.1f ms/anh)." % (
            dung_e, dung_r, ms_e / ms_r if ms_r else 0, ms_e, ms_r))
    else:
        A("    Hai thu vien doc dung nhat nhieu (%d/%d) - khoang cach quyet dinh nam o TOC DO:" % (
            dung_r, len(co_nhan)))
        A("    %s (%.1f vs %.1f ms/anh)." % ("RapidOCR nhanh hon" if ms_r < ms_e else "EasyOCR nhanh hon", ms_r, ms_e))
    A("    Tien model tren dia: RapidOCR %s vs EasyOCR %s." % (mb(gb_r), mb(gb_e)))
    A("")
    A("[7] CANH BAO - DOC TRUOC KHI CHOT")
    A("    - Anh tong hop la anh PIL ve: nen trang, chu in, sang deu. KHONG thay the duoc")
    A("      anh that tu camera (nhieu nhieu, nho, mo, nghieung, anh sang). Do chinh xac")
    A("      tren anh that SE THAP HON so voi bang tren.")
    A("    - Bien so crop tu video nay xe chi 80-130px nen bien so rat nho + nhieu nhieu:")
    A("      khong thu vien nao doc duoc. Can video ro nhat (FullHD, xe gan) de cham lai.")
    A("    - RapidOCR chi tach bien so thanh 2-3 doan; bang nay da ghep theo thu tu doc,")
    A("      neu doan nao doc sai thi ca chuoi sai.")
    A("    - Chay lai de xac nhan: .venv\\Scripts\\python.exe _kk_bien_so.py")
    A("")

    bao_cao = "\n".join(L) + "\n"
    with open(FILE_BAO_CAO, "w", encoding="utf-8", newline="\n") as f:
        f.write(bao_cao)
    print(bao_cao)
    print("BAO CAO: %s" % FILE_BAO_CAO)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)