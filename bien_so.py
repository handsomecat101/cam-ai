r"""
CamAI - nhan dien bien so xe Viet Nam bang OCR chay 100% tren may.

KHONG gui gi ra ngoai: module nay khong import network (khong urllib, khong
requests, khong socket). Anh bien so chi duoc ghi xuong dia may.

Dung truc tiep:
    from bien_so import BoDocBienSo

    bo_doc = BoDocBienSo(nguong_tin_cay=0.5, thu_muc_luu="anh_bien_so",
                         vung="0.1,0.3,0.9,0.8")
    for r in bo_doc.doc(anh_bgr, so_mat_rang=0):
        print(r.chuoi, r.tin_cay, r.duong_dan)

Cach tim vung bien so (theo thu tu uu tien):
1. Class `plate` (hoac `plates`, `license_plate`) neu model YOLO dang chay co
   class do. Model COCO mac dinh (yolo11n.pt) KHONG co class nay.
2. Vung cu dinh (ROI) do nguoi dung truyen vao (`vung`). Chuan hoa:
   - 4 so <= 1  -> toa do TUONG DOI (0..1) so voi khung hinh.
   - 4 so > 1   -> toa do PIXEL.
3. Khong co gi ca -> dung ca khung hinh (cham hon, log canh bao 1 lan).

Bien so 2 hang (xe tai, khung bien lon): neu OCR ca vung khong ra mau dung,
module tu cat vung thanh 2 hang va ghep chuoi: hang tren + hang duoi.

VE CHU TIENG VIET CO DAU: dung PIL/Pillow. KHONG dung cv2.putText (font
Hershey chi co ASCII, se ra chu loi).

--- HAI ENGINE OCR (do thuc 2026-10-19, xem _kiem_chung/plate_thu/kiem_v3/) ---
`rapidocr-onnxruntime` 1.2.3 chi doc tham so `use_text_det` luc KHOI TAO,
luc GOI engine thi BO QUA. Vi vay phai khoi tao HAI engine rieng:
  * `self.ocr`      = RapidOCR(use_text_det=False, use_angle_cls=False)
                      -> CHI DOC: doc nguyen 1 dong cua crop.
                      5-10 ms/crop, nhanh gap ~100 lan engine co tim chu,
                      va doc CHINH XAC hon (engine co tim chu cat nho bien
                      thanh manh vun: "M7z" + "POLIZIA" thay vi "POLIZIA M7318").
                      Dung cho DUONG CHINH: crop bien so da dinh vi.
  * `self.ocr_tim`  = RapidOCR() -> CO TIM CHU: tach manh chu trong ca
                      khung hinh. 300-1500 ms/khung hinh -> CHI dung khi
                      phai TU DO vung bien so trong ca khung hinh, va CHAY
                      O THREAD NEN (xem muc "THREAD NEN" ben duoi).
Ca hai engine deu NAP LAZY: app khoi dong khong bi cham.

--- THREAD NEN: doc() KHONG BAO GIO chan (keo cua so khong giat) ---
Pha TIM VUNG trong ca khung hinh (engine "co tim chu", 300-1500 ms) va pha
NAP ENGINE deu chay o MOT THREAD NEN (daemon). `doc()` chi:
  - lay vung da tim trong CACHE (bien so di chuyen cham -> cache vai giay
    la hop ly), va
  - doc cac vung do bang engine "chi doc" (5-10 ms/vung), co HAN CHI PHI
    (NGAN_CHI_PHI_MS) va ngan so luot OCR.
Ket qua: `doc()` tra ve trong < 100 ms o CA HAI che do (co ROI / tu tim).

--- CHUAN HOA THAT (khong duoc bia ra bien so) ---
`chuan_hoa_bien_so` CHI tra ve chuoi khop dung mau bien so Viet Nam:
`^\d{2}[A-Z]\d{4}$` hoac `^\d{2}[A-Z]\d{5}$` (2 so + DUNG 1 chu + 4/5 so).
Bien nuoc ngoai (MS WL 345, SZ 62144, AG 11655...) bi loai ve "".
KHONG bao gio tu them/bot ky tu, khong gop ky tu lai.
"""

from __future__ import annotations

import os
import re
import threading
import time
import weakref
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import cv2
import numpy as np

__all__ = [
    "BoDocBienSo", "KetQuaBienSo", "chuan_hoa_bien_so", "lam_sach",
    "ve_khung_bien_so", "LOP_BIEN_SO_MAC_DINH", "RA_TRONG",
    "khop_mau_bien_so_vn",
]

# Gia tri rong cho `vung` = tu tim bang class plate cua YOLO.
RA_TRONG = ""

# Cac ten class YOLO duoc coi la bien so (khac nhau giua cac model bien so).
LOP_BIEN_SO_MAC_DINH = (
    "plate", "plates", "license_plate", "license plate", "bien_so", "biensoxe",
)

BIEN_SO_MAC_DINH_TIN_CAY = 0.5
NHAN_LAI_MAC_DINH_GIAY = 30.0

# Bien so nho hon muc nay thi bo qua (OCR khong doc duoc, chi lao nhieu).
KICH_THUOC_BIEN_SO_TOI_DA = (40, 10)

# --- mau bien so Viet Nam (khop CHAT) ---
# 2 chu so dau + DUNG 1 chu cai + 4 hoac 5 chu so cuoi.
# KHONG chap nhan bien 2 chu (80FD-1234) va khong chap nhan 6 so cuoi.
MAU_BIEN_SO_VN = re.compile(r"^\d{2}[A-Z]\d{4}$|^\d{2}[A-Z]\d{5}$")
SO_DAU = 2              # so ky tu dau la chu so
SO_CHU = 1              # so ky tu giua la chu cai
VI_TRI_CHU = SO_DAU     # index (0-based) cua ky tu chu cai
SO_CUOI_MIN = 4         # it nhat bao nhieu chu so cuoi
SO_CUOI_MAX = 5         # toi da bao nhieu chu so cuoi

# So ky tu duoc PHA TINH SAI duoc sua trong 1 chuoi.
# GIU 1 de chong "MS WL 345" (Duc) bi bien thanh "50W-1345" (bien so Viet
# Nam bia ra). Bien so that bi doc sai 2 ky tro len thi bo qua - thiet ke
# "reject an toan hon" (thieu bien so con hon bao bien so sai).
SO_SUA_TOI_DA = 1

# --- chuan hoa ky tu hay nham khi OCR ---
# Dung khi KIEM TRA O CHO CHU SO (2 so dau va 4-5 so cuoi).
# CHI giu DUNG 3 cap nham ma yeu cau cho phep: O<->0, I<->1, L<->1.
# KHONG them S/Z/G/B/... : nham yeu, va se bien bien so nuoc ngoai thanh bien
# so Viet Nam ("B1X-23456" (Anh) -> "81X-23456" (Viet Nam) - bia bien so).
CHU_SO_HAY = {
    "O": "0",
    "I": "1", "L": "1",
}
# Dung khi KIEM TRA O CHO CHU CAI (1 chu giua 2 so dau va so cuoi).
# CHI sua 0 -> O. Cac truong hop khac (1, 5, 8...) KHONG sua: bien so that
# doc sai con so o cho chu thi de bi tu cho la bien so -> reject an toan hon.
CHU_CAI_HAY = {"0": "O"}

# --- tham so OCR ---
# Crop thap hon nuc nay -> phong to truoc khi OCR (chu nho, RapidOCR doc sai).
OCR_CAO_TOI_THIEU = 48
# Gioi han be rong sau khi phong to de khong no RAM.
OCR_RONG_TOI_DA = 1200
# rong/cao > 8 -> vung qua rong, khong phai bien so (RapidOCR cung bo qua
# vung nhu vay, va doc se ra rac).
OCR_TY_LE_RONG_TOI_DA = 8.0
# Nguong "muc toi" (ky tu toi) de cat bo vien trang thua. Bien so xoay nhe
# co vien trang lon -> vach ngang tach 2 hang cat qua giua ky tu -> mat chu.
OCR_NGUONG_MUC_TOI = 205
# Goc xoay thu khi OCR that bai (bien so xoay nhe, camera lech 5-10 do).
# CHI thu khi that bai - KHONG xoay luon (anh nghieng va anh phang deu duoc).
GOC_XOAY_THU = (-3, 3, -6, 6, -9, 9)
# Crop rong hon muc nay khong phai bien so (la anh xe/canh) -> khong thu xoay.
OCR_RONG_TOI_DA_XOAY = 600

# --- xac nhan da khung hinh ---
# Mot chuoi bien so CHI duoc coi la "DOC CHAC" khi xuat hien o >= toi thieu
# so khung hinh lien tiep. Ly do: OCR 1 khung hinh hay doc sai (bien so xoay
# nhe -> "30A 12346" thay vi "30A 12345") -> ghi sai bien so vao bao cao.
# Chuoi chi xuat hien 1 khung hinh van duoc NHICH LAI (trang thai "nghi") nhung
# KHONG ghi vao CSV va KHONG luu anh.
XAC_NHAN_TOI_THIEU = 2
# Hai lan doc cung 1 chuoi cach nhau qua gio -> khong con la "lien tiep".
NGUONG_LIEN_TIEP_GIAY = 0.5
# Do dai khung hinh uoc luong -> cua lien tiep = max(0.5s, 3 lan do dai khung
# hinh) de khong phu thuoc fps (may cham van phai xac nhan duoc).
HE_SO_CUA_LIEN_TIEP = 3.0
# Xoa chuoi da lau khong xuat hien nua (tranh nho tang dan).
XOA_NHO_GIAY = 120.0
# Bien so nghien >= nuc nay -> doc thang khong tin duoc (OCR doc sai mot chu so
# khi anh xoay: "30A 12346" thay vi "30A 12345") -> so sanh them voi ban DA
# PHANG. Hai cach doc lech nhau -> khong ro bien so that -> KHONG bao cao
# (thieu bien so con hon bao bien so sai).
SKEW_TOI_DA = 8.0
# Engine "co tim chu" cham 300-1500 ms/khung hinh -> PHA TIM VUNG chay o
# THREAD NEN. Vung da tim duoc giu lai trong CACHE nhieu GIYAY_GIAM_TAN giay
# (bien so di chuyen cham, cache vai giay la hop ly).
GIYAY_GIAM_TAN = 2.0
# So vung ung vien toi da xem la bien so khi tu do trong ca khung hinh.
SO_UNG_VIEN_TOI_DA = 6

# --- HAN CHI PHI: doc() KHONG BAO GIO chan qua 100 ms ---
# Trong 1 lan doc(), tong thoi gian OCR (luong chinh) khong duoc vuot qua
# NGAN_CHI_PHI_MS. Qua han -> dung lai, tra ve ket qua hien co.
NGAN_CHI_PHI_MS = 50.0
# Toi da so lan OCR cho 1 vung (vung rong co the lam 24 lan OCR -> 200+ ms).
SO_LUOT_OCR_TOI_DA = 8
# Toi da so vung doc trong 1 khung hinh.
SO_VUNG_DOC_TOI_DA = 4
# Vung rong > 250.000 px la anh xe/canh, khong phai bien so -> bo qua som
# (roi/cao > 8 da lo roi o duoi).
OCR_DIEN_TICH_TOI_DA = 250_000
# Vung rong > 60.000 px -> pha TIM VUNG trong vung do chay o THREAD NEN,
# luong chinh chi doc vung NHO da tim duoc (nhanh + doc dung hon).
# (Bien so Viet Nam that ~11.000-57.000 px, nen vung lon hon vay thi engine
# "chi doc" doc ca vung ra chu rac.)
OCR_DIEN_TICH_VUNG_LON = 60_000
# Cache vung da tim: dung lai toi da 10 s (nhac phong trong khi thread nen
# die). Thread nen lam moi cache moi GIYAY_GIAM_TAN giay.
GOC_VUNG_TTL_GIAY = 10.0
# Khi THIEU engine "chi doc", phai dung engine "co tim chu" (cham 30-80 ms
# cho vung nho) -> chi doc vung nho, vung lon bo qua de khong treo khung hinh.
OCR_DIEN_TICH_DOC_NEN_MAX = 40_000

_LUU_FONT: dict[int, object] = {}


@dataclass
class KetQuaBienSo:
    """Mot bien so doc duoc trong 1 khung hinh."""

    chuoi: str = ""            # da chuan hoa, vi du "30A-12345"
    chuoi_goc: str = ""        # OCR tho ra truoc khi chuan hoa
    tin_cay: float = 0.0       # tin cay OCR (0..1)
    khung: tuple = (0, 0, 0, 0)   # (x1, y1, x2, y2) trong anh goc
    duong_dan: str = ""        # file anh da luu (rong = chua luu)
    so_hang: int = 1           # 1 = bien 1 hang, 2 = bien 2 hang
    nguon: str = ""            # "plate" (class YOLO) | "vung" (ROI) | "toan_khung"
    goc_xoay: str = ""         # goc xoay da dung khi doc ("+6", "-3") - rong = khong xoay
    xac_nhan: str = ""         # "chac" (da xac nhan da khung hinh) | "nghi" (moi 1 khung hinh)
    mau_thuan: bool = False    # True = 2 cach doc lech nhau (anh nghieng) -> khong bao cao

    def __str__(self) -> str:
        return f"{self.chuoi} ({self.tin_cay:.2f})"


# ------------------------------------------------------------------ chuan hoa

@dataclass
class _TrangThaiBienSo:
    """Trang thai xac nhan cua 1 chuoi bien so trong chuoi video."""

    chuoi: str = ""
    so_khung: int = 1       # so khung hinh lien tiep doc duoc chuoi nay
    lan_cuoi: float = 0.0   # thoi gian (monotonic) doc gan nhat
    lan_dau: float = 0.0    # thoi gian doc lan dau

    @property
    def da_chac(self) -> bool:
        return self.so_khung >= XAC_NHAN_TOI_THIEU


def lam_sach(chuoi: str) -> str:
    """Viet HOA + bo moi ky tu khong phai 0-9/A-Z (bo khoang, dau '.', dau '-')."""
    return re.sub(r"[^0-9A-Z]", "", str(chuoi).upper())


def khop_mau_bien_so_vn(chuoi: str) -> bool:
    """True neu chuoi khop DUNG mau bien so Viet Nam (2 so + 1 chu + 4/5 so).

    KHONG sua gi them. Dung cho noi khac can kiem tra mau ma khong muon
    chuan hoa (vi du tin cay cuoi).
    """
    return bool(chuoi) and MAU_BIEN_SO_VN.match(chuoi) is not None


def _sua_ky_tu_theo_vi_tri(sach: str) -> tuple[str, int]:
    """Sua ky tu o VI TRI bat buoc cua bien so Viet Nam.

    Tra (chuoi da sua, so ky tu da sua). Neu khong sua duoc -> ("", 0).

    Quy tac (KHONG duoc nioi long):
    - Vi tri thu 3 (VI_TRI_CHU): BAT BUOC la chu cai. Chi sua '0' -> 'O'.
    - Moi vi tri con lai: BAT BUOC la chu so. Chi sua nham loi OCR ro rang
      (O->0, I/L->1, S->5, Z->2, G->6, B->8) theo CHU_SO_HAY.
    - KHONG bao gio them ky tu, bot ky tu hay gop ky tu lai.
    - Tong so ky tu sua khong duoc vuot qua SO_SUA_TOI_DA.

    Do do, bien khong phai Viet Nam ("MSWL345", "SZ62144"...) se bi loai
    thay vi duoc "Sua" thanh mot chuoi co dang bien so Viet Nam.
    """
    do_dai_ok = (SO_DAU + SO_CHU + SO_CUOI_MIN, SO_DAU + SO_CHU + SO_CUOI_MAX)
    if len(sach) not in do_dai_ok:
        return "", 0

    ra: list[str] = []
    sua = 0
    for i, ky in enumerate(sach):
        if i == VI_TRI_CHU:
            # BAT BUOC la chu cai
            if ky.isalpha():
                ra.append(ky)
            elif ky in CHU_CAI_HAY:
                ra.append(CHU_CAI_HAY[ky])
                sua += 1
            else:
                return "", 0
        else:
            # BAT BUOC la chu so
            if ky.isdigit():
                ra.append(ky)
            elif ky in CHU_SO_HAY:
                ra.append(CHU_SO_HAY[ky])
                sua += 1
            else:
                return "", 0
    if sua > SO_SUA_TOI_DA:
        return "", 0
    return "".join(ra), sua


def chuan_hoa_bien_so(chuoi_goc: str) -> str:
    """Chuan hoa chuoi OCR thanh bien so Viet Nam. Tra "" neu khong khop mau.

    Mau Viet Nam (khop CHAT, xem MAU_BIEN_SO_VN):
        2 chu so + DUNG 1 chu cai + 4 hoac 5 chu so -> 30A-12345, 51F-9876

    Duoc phep: bo ky tu la, viet hoa chu, them dau gach '-', va sua loi OCR
    ro rang ORI VI TRI bat buoc (vi tri 3 bat buoc la chu, 2 vi tri dau va
    4-5 vi tri sau bat buoc la so) - toi da SO_SUA_TOI_DA ky tu.

    KHONG duoc: tu them/bot ky tu, gop ky tu lai, hoac tra ve chuoi co dang
    bien so Viet Nam khi chuoi goc khong khop mau. Vi du "MS WL 345" (Duc)
    ra "" chu khong phai "50W-1345".
    """
    sach = lam_sach(chuoi_goc)
    if not sach:
        return ""

    da_sua, _n_sua = _sua_ky_tu_theo_vi_tri(sach)
    if not da_sua or not khop_mau_bien_so_vn(da_sua):
        return ""
    return f"{da_sua[:SO_DAU]}{da_sua[VI_TRI_CHU]}-{da_sua[VI_TRI_CHU + 1:]}"


def tach_hang(muc: list[dict]) -> list[dict]:
    """Sap xep cac manh chu OCR ve dung thu tu doc.

    Cung 1 hang (trung keo nhau doc) -> sap theo x.
    Nhieu hang -> sap theo hang roi theo x (bieu 2 hang).
    """
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


def _log_an_toan(log, dong: str) -> None:
    """Log tieng Viet co dau; console Windows cp1252 khong in duoc -> lui ve
    ban khong dau.

    Log KHONG bao gio lam chet luong phan tich (xem ISSUE_LOG.md muc
    "Console Windows khong in duoc tieng Viet").
    """
    try:
        log(dong)
        return
    except UnicodeEncodeError:
        pass
    except Exception:                                   # noqa: BLE001
        return
    try:
        import unicodedata

        log(unicodedata.normalize("NFD", dong)
            .encode("ascii", "ignore").decode("ascii"))
    except Exception:                                   # noqa: BLE001
        pass


def _gom_hang(muc: list[dict]) -> list[list[dict]]:
    """Nhom cac manh chu theo hang (manh chu trung keo nhau theo chieu doc)."""
    if not muc:
        return []
    muc = sorted(muc, key=lambda m: float(m["box"][:, 1].min()))
    nhom: list[list[dict]] = []
    for m in muc:
        y0 = float(m["box"][:, 1].min())
        y1 = float(m["box"][:, 1].max())
        cao = max(1.0, y1 - y0)
        for n in nhom:
            ny0 = min(float(x["box"][:, 1].min()) for x in n)
            ny1 = max(float(x["box"][:, 1].max()) for x in n)
            ncao = max(1.0, ny1 - ny0)
            if min(y1, ny1) - max(y0, ny0) >= 0.5 * min(cao, ncao):
                n.append(m)
                break
        else:
            nhom.append([m])
    return nhom


# --------------------------------------------------------------------- overlay

def _font(co: int):
    """Font TTF cho PIL. Windows luon co segoeuib.ttf -> ve duoc tieng Viet."""
    if co in _LUU_FONT:
        return _LUU_FONT[co]
    from PIL import ImageFont

    font = None
    for ten in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf",
                "calibrib.ttf", "tahoma.ttf"):
        try:
            font = ImageFont.truetype(ten, co)
            break
        except Exception:                                   # noqa: BLE001
            continue
    if font is None:                       # truong hop hiem - font mac dinh
        font = ImageFont.load_default()
    _LUU_FONT[co] = font
    return font


def ve_khung_bien_so(anh_bgr, ket_qua: list, mau_bi_goc=(0, 220, 255)) -> np.ndarray:
    """Ve khung + nhan tieng Viet co dau len anh (PIL, KHONG cv2.putText).

    ket_qua: list[KetQuaBienSo] (gia tri rong / rong -> ve con khung).
    Tra ve anh da ve. Khong bao gio nem loi.
    """
    if anh_bgr is None or not len(ket_qua):
        return anh_bgr
    try:
        from PIL import Image, ImageDraw
    except Exception:                                       # noqa: BLE001
        return anh_bgr

    rgb = cv2.cvtColor(anh_bgr, cv2.COLOR_BGR2RGB)
    ve = Image.fromarray(rgb)
    bo = ImageDraw.Draw(ve)
    # mau truyen vao theo thu tu BGR (nhu cv2) -> PIL can RGB.
    mau = (int(mau_bi_goc[2]), int(mau_bi_goc[1]), int(mau_bi_goc[0]))

    co = max(14, min(30, anh_bgr.shape[1] // 34))
    font = _font(co)
    for r in ket_qua:
        if not r.chuoi:
            continue
        x1, y1, x2, y2 = (int(v) for v in r.khung)
        if x2 <= x1 or y2 <= y1:
            continue
        bo.rectangle([x1, y1, x2, y2], outline=mau, width=2)
        chu = f"Biển số: {r.chuoi}"
        if getattr(r, "goc_xoay", ""):
            chu += f" (xoay {r.goc_xoay} do)"
        bb = bo.textbbox((0, 0), chu, font=font)
        nen_y = max(0, y1 - (bb[3] - bb[1]) - 8)
        bo.rectangle(
            [x1, nen_y, x1 + (bb[2] - bb[0]) + 10, nen_y + (bb[3] - bb[1]) + 8],
            fill=(0, 0, 0),
        )
        bo.text((x1 + 5, nen_y + 4), chu, font=font, fill=mau)
    return cv2.cvtColor(np.array(ve), cv2.COLOR_RGB2BGR)


# --------------------------------------------------------------- doc bien so

_HAAR = None                  # cascade Haar (None = OpenCV khong con class nay)
_HAAR_THU = True               # True = thu nap 1 lan roi, False = da biet khong co


def _lay_cascade():
    """Haar cascade cua OpenCV. Tra None neu khong co (OpenCV 5 da bo class nay)."""
    global _HAAR, _HAAR_THU
    if _HAAR is not None or not _HAAR_THU:
        return _HAAR
    _HAAR_THU = False           # chi thu 1 lan, khong lap lai moi khung hinh
    try:
        duong = os.path.join(cv2.data.haarcascades,
                             "haarcascade_frontalface_default.xml")
        if not hasattr(cv2, "CascadeClassifier") or not os.path.exists(duong):
            return None
        cascade = cv2.CascadeClassifier(duong)
        _HAAR = None if cascade.empty() else cascade
    except Exception:                                   # noqa: BLE001
        _HAAR = None
    return _HAAR


def _mua_giao(box, khung) -> float:
    """Ty le phan dien tich cua box (mat) nam trong khung (crop bien so)."""
    x1 = max(float(box[0]), float(khung[0]))
    y1 = max(float(box[1]), float(khung[1]))
    x2 = min(float(box[2]), float(khung[2]))
    y2 = min(float(box[3]), float(khung[3]))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    dt = (x2 - x1) * (y2 - y1)
    return dt / max(1.0, (khung[2] - khung[0]) * (khung[3] - khung[1]))


def _dat_uu_tien_thap() -> None:
    """Gioi han CPU cho thread nen (Windows). That bai -> bo qua.

    Pha tim vung chay o thread nen: uu tien thap + CHI dung vai core de no
    khong chiem het CPU -> luong chinh (keo cua so) khong bi tre khi may
    dang chay viec khac.
    """
    try:
        import ctypes

        k32 = ctypes.windll.kernel32
        handle = k32.GetCurrentThread()
        k32.SetThreadPriority(handle, 1)          # THREAD_PRIORITY_BELOW_NORMAL
        n_cpu = os.cpu_count() or 1
        if 2 < n_cpu <= 63:
            # 2 core cuoi -> pha quet vung khong lan sang phan app chinh.
            mask = (1 << (n_cpu - 2)) | (1 << (n_cpu - 1))
            k32.SetThreadAffinityMask(handle, ctypes.c_ulong(mask))
    except Exception:                                   # noqa: BLE001
        pass


def _vong_nen(self_ref) -> None:
    """Vong lam viec cua THREAD NEN (module-level: KHONG giu object song mai).

    Lam 2 viec, KHONG bao gio chan luong chinh:
      1. Nap engine OCR (600-700 ms) - app khoi dong khong bi cham.
      2. Tim vung bien so trong ca khung hinh (300-1500 ms) -> cache.

    `self_ref` la weakref: khi `BoDocBienSo` bi huy, weakref tra None ->
    thread ket thuc ngay (khong de thread chay sau khi doi tuong bi huy).
    """
    _dat_uu_tien_thap()
    while True:
        obj = self_ref()
        if obj is None or obj._dung_nen:
            return
        obj._su_kien_nen.wait(0.2)
        obj = self_ref()
        if obj is None or obj._dung_nen:
            return
        obj._su_kien_nen.clear()
        try:
            obj._xuly_viec_nen()
        except Exception:                                   # noqa: BLE001
            pass


class BoDocBienSo:
    """Doc bien so Viet Nam trong khung hinh. KHONG gui gi ra ngoai may khac.

    Bien so duoc TIM theo thu tu: class `plate` cua YOLO -> ROI `vung` ->
    ca khung hinh. OCR (rapidocr-onnxruntime) chi duoc NAP LAZILY, khi bat
    dau doc lan dau -> app khoi dong khong bi cham.

    Tu dong luu anh crop bien so vao `thu_muc_luu`. CHONG GHI TRUNG: cung mot
    bien so chi luu 1 lan trong `nhoan_lai_giay` (mac dinh 30 giay).

    QUYEN RIENG TU (privacy): mac dinh KHONG luu anh crop nao co khuon mat
    ro rang (`cho_phep_luu_mat=False`). Chi khi nguoi dung chu dong bat
    `cho_phep_luu_mat=True` thi moi luu.

    Cach phat hien mat (KHONG tai them model, KHONG goi mang):
    1. `doc(..., khuon_mat=[...])` - dung lai khuon mat pipeline chinh da nhan
       trong khung hinh (Insightface SCRFD). Day la duong chinh.
    2. Haar cascade cua OpenCV - DU PHONG. LUU Y: OpenCV 5 da BO HAN class
       `CascadeClassifier` khoi API Python, nen tren may nay khong co duong
       nay. Khi both signals deu khong co (vi du chay `--no-face`), module
       KHONG tu phat hien mat va van luu - ghi ro dong canh bao 1 lan. Muon
       fail-closed thi dung `cho_phep_luu_mat` hoac bat nhan dien mat.
    """

    def __init__(
        self,
        nguong_tin_cay: float = BIEN_SO_MAC_DINH_TIN_CAY,
        bien_so_mac_dinh: str = RA_TRONG,
        thu_muc_luu: str = "",
        nhoan_lai_giay: float = NHAN_LAI_MAC_DINH_GIAY,
        vung: str | None = None,
        lop_bien_so: tuple = LOP_BIEN_SO_MAC_DINH,
        cho_phep_luu_mat: bool = False,
        ten_lop: dict | None = None,
        log: Callable[[str], None] | None = None,
    ):
        self.nguong_tin_cay = float(nguong_tin_cay)
        self.bien_so_mac_dinh = bien_so_mac_dinh or RA_TRONG
        self.thu_muc_luu = thu_muc_luu or ""
        self.nhoan_lai_giay = max(0.0, float(nhoan_lai_giay))
        self.vung = vung
        self.lop_bien_so = tuple(ten.lower() for ten in lop_bien_so)
        self.cho_phep_luu_mat = bool(cho_phep_luu_mat)
        self.log = log or (lambda _dong: None)

        # class_id -> ten class cua model YOLO (dung de tim class `plate`)
        self.ten_lop = dict(ten_lop or {})
        self.id_bien_so = [
            cid for cid, ten in self.ten_lop.items()
            if str(ten).strip().lower() in self.lop_bien_so
        ]

        self.ocr = None                 # engine RapidOCR CHI DOC, nap lazy
        self.ocr_tim = None             # engine RapidOCR CO TIM CHU, nap lazy
        self.loi = ""                  # ly do khong bat duoc OCR
        self.da_bao_loi = False
        self.da_bao_loi_1_engine = False
        self.nap_doc_that_bai = False
        self.nap_tim_that_bai = False
        self.bao_loi_vung = False
        self.lan_tim_cuoi = 0.0
        self.so_lan_qua_rong = 0
        self.so_lan_qua_lon = 0

        # --- THREAD NEN (pha tim vung + nap engine) ---
        # Khoa rieng cho tung engine: 2 thread KHONG bao gio goi cung 1
        # engine RapidOCR/onnxruntime (khong an toan khi chay song song).
        self._khoa_ocr_doc = threading.Lock()     # engine "chi doc"
        self._khoa_ocr_tim = threading.Lock()     # engine "co tim chu"
        self._khoa_nap = threading.Lock()         # nap engine (1 lan duy nhat)
        self._khoa_cache = threading.Lock()       # cache vung da tim
        self._khoa_viec = threading.Lock()        # hang viec cho thread nen
        self._tl = threading.local()              # han chi phi / dem luot (theo thread)
        self._thread_nen = None                   # thread nen (daemon, tao lazy)
        self._su_kien_nen = threading.Event()     # co viec moi cho thread nen
        self._viec_nen = None                     # viec dang cho (1 viec)
        self._quet_dang_chay = False              # dang quet toan khung
        self._dung_nen = False                    # yeu cau dung thread nen
        # cache vung da tim: "luc" (monotonic), "w"/"h" (kich thuoc anh
        # goc), "vung" (toa do TUONG DOI), "nguon".
        self._cache_vung = {"luc": 0.0, "w": 0, "h": 0, "vung": [], "nguon": ""}
        self.so_lan_quet = 0
        # --- xac nhan da khung hinh ---
        # chuoi -> trang thai (so khung hinh lien tiep, thoi gian gan nhat)
        self.trang_thai_bien_so: dict[str, _TrangThaiBienSo] = {}
        self._chuoi_lan_truoc: set[str] = set()   # chuoi doc duoc o khung hinh truoc
        self._lan_doc_cuoi = 0.0                  # thoi gian doc khung hinh truoc
        self._gap_khung_hinh = 0.0                # do dai khung hinh uoc luong
        self.so_lan_nghi = 0
        self._da_bao_mau_thuan: set[str] = set()   # chuoi da canh bao mau thuan
        self.luu_lan_cuoi: dict[str, float] = {}   # bien so -> giay vua luu
        self.so_lan_bo_qua_mat = 0
        self.so_lan_khong_tin_hieu_mat = 0
        self.da_luu = 0
        self.tong_ms = 0.0
        self.so_lan_doc = 0

    # -------------------------------------------------------------- trang thai
    @property
    def bat_duoc(self) -> bool:
        return self.ocr is not None or self.ocr_tim is not None

    def _nap_engine(self, loai: str) -> bool:
        """Nap 1 engine RapidOCR. loai: 'doc' (chi doc) | 'tim' (co tim chu).

        HAI ENGINE RIENG BIET, vi `rapidocr-onnxruntime` 1.2.3 chi doc tham so
        `use_text_det` luc KHOI TAO, luc GOI thi BO QUA. Dung chung 1 engine
        se mat ~100 lan toc do va doc sai (cat nho bien thanh manh vun).

        Khoa `_khoa_nap`: luong chinh va thread nen khong nap trung nhau.
        """
        if loai == "doc":
            if self.ocr is not None:
                return True
            if self.nap_doc_that_bai:
                return False
        else:
            if self.ocr_tim is not None:
                return True
            if self.nap_tim_that_bai:
                return False
        with self._khoa_nap:
            # Kiem tra LAI trong khoa (2 thread co the goi cung luc).
            if loai == "doc":
                if self.ocr is not None:
                    return True
                if self.nap_doc_that_bai:
                    return False
            else:
                if self.ocr_tim is not None:
                    return True
                if self.nap_tim_that_bai:
                    return False
            try:
                from rapidocr_onnxruntime import RapidOCR

                if loai == "doc":
                    # CHI DOC: doc nguyen 1 dong cua crop -> 5-10 ms/crop.
                    self.ocr = RapidOCR(use_text_det=False, use_angle_cls=False)
                else:
                    # CO TIM CHU: tach manh chu trong ca khung hinh -> 300-1500 ms.
                    self.ocr_tim = RapidOCR()
                return True
            except Exception as exc:                            # noqa: BLE001
                if loai == "doc":
                    self.ocr = None
                    self.nap_doc_that_bai = True
                else:
                    self.ocr_tim = None
                    self.nap_tim_that_bai = True
                self.loi = f"{type(exc).__name__}: {exc}"
                self._canh_bao_khong_bat_duoc(loai)
                return False

    def nap(self) -> bool:
        """Nap engine OCR (lazy) de app khoi dong khong bi cham.

        False + canh bao tieng Viet neu khong nap duoc engine nao.
        """
        if self._nap_engine("doc"):
            return True
        # Engine "chi doc" that bai -> thu engine "co tim chu" (cham hon
        # nhung van chay duoc, va doc van dung).
        return self._nap_engine("tim")

    def _canh_bao_khong_bat_duoc(self, loai: str = "doc") -> None:
        if self.da_bao_loi:
            return
        self.da_bao_loi = True
        ten = "chỉ đọc" if loai == "doc" else "có tìm chữ"
        _log_an_toan(self.log,
            f"[biển số] KHÔNG nạp được engine OCR {ten}: {self.loi}. "
            "Dùng engine còn lại nếu có (chậm hơn nhưng vẫn chạy được); "
            "nếu cả hai engine đều hỏng thì chỉ mất tính năng đọc biển số "
            "(app vẫn chạy bình thường)."
        )
        _log_an_toan(self.log,
            "[biển số] Cài bằng lệnh này rồi chạy lại: "
            f".venv\\Scripts\\python.exe -m pip install rapidocr-onnxruntime  ({self.loi})"
        )

    # ------------------------------------------------------------------ vung
    def _vung_px(self, anh_shape: tuple) -> tuple[int, int, int, int] | None:
        """Doi `vung` (chuoi "x1,y1,x2,y2") toa do pixel cua khung hinh nay."""
        if not self.vung:
            return None
        try:
            # "192,81,768,513" -> 4 so. Cho phep tach bang khoang trang hoac dau phay.
            parts = [p for p in re.split(r"[\s,;]+", str(self.vung).strip()) if p]
            if len(parts) != 4:
                raise ValueError("can dung 4 so")
            x1, y1, x2, y2 = (float(p) for p in parts)
        except Exception as exc:                            # noqa: BLE001
            if not self.da_bao_loi:
                self.da_bao_loi = True
                _log_an_toan(self.log,
                    f"[biển số] vùng ROI sai định dạng (cần 'x1,y1,x2,y2'): "
                    f"{self.vung} ({exc})"
                )
            return None
        chieu_rong, chieu_cao = anh_shape[1], anh_shape[0]
        if max(x1, y1, x2, y2) <= 1.0:          # toa do tuong doi 0..1
            x1, y1, x2, y2 = x1 * chieu_rong, y1 * chieu_cao, x2 * chieu_rong, y2 * chieu_cao
        return (
            max(0, int(x1)), max(0, int(y1)),
            min(chieu_rong, int(x2)), min(chieu_cao, int(y2)),
        )

    def tim_vung(self, anh_bgr, detections=None) -> list[tuple]:
        """Tra ve danh sach vung (x1, y1, x2, y2) co the co bien so.

        detections: sv.Detections cua khung hinh nay (dung lai ket qua YOLO
        san co, KHONG chay them 1 lan YOLO).
        """
        vung = self._vung_co_dinh(anh_bgr, detections)
        if vung:
            return [k for k, _nguon in vung]

        # --- ca khung hinh (cham nhat, canh bao 1 lan) ---
        self._canh_bao_toan_khung()
        h, w = anh_bgr.shape[:2]
        return [(0, 0, w, h)]

    def _vung_co_dinh(self, anh_bgr, detections=None) -> list[tuple]:
        """Vung bien so CO DINH. Tra list[(khung, nguon)] hoac rong.

        nguon: "plate" (class YOLO) | "vung" (ROI do nguoi dung dat).
        """
        # --- 1. class `plate` cua YOLO ---
        if self.id_bien_so and detections is not None and len(detections):
            cls = np.asarray(detections.class_id)
            xyxy = np.asarray(detections.xyxy, dtype=float)
            ra = []
            for i in np.where(np.isin(cls, self.id_bien_so))[0]:
                x1, y1, x2, y2 = xyxy[i]
                ra.append(((int(x1), int(y1), int(x2), int(y2)), "plate"))
            if ra:
                return ra

        # --- 2. ROI co dinh ---
        vung = self._vung_px(anh_bgr.shape)
        if vung and vung[2] > vung[0] and vung[3] > vung[1]:
            return [(vung, "vung")]
        return []

    def _canh_bao_thieu_engine_chi_doc(self) -> None:
        """Canh bao 1 lan: chi nap duoc engine 'co tim chu' (cham) -> tam dung
        doc bien so o luong chinh de khong treo khung hinh."""
        if self.da_bao_loi_1_engine:
            return
        self.da_bao_loi_1_engine = True
        _log_an_toan(self.log,
            "[biển số] Chỉ nạp được engine OCR 'có tìm chữ' (chạy 250-1500 ms "
            "mỗi lần) - TẠM DỪNG đọc biển số để không treo khung hình. Cài lại: "
            ".venv\\Scripts\\python.exe -m pip install --force-reinstall "
            "rapidocr-onnxruntime"
        )

    def _canh_bao_toan_khung(self) -> None:
        """Canh bao 1 lan: khong co class 'plate' va khong co ROI."""
        if self.bao_loi_vung:
            return
        self.bao_loi_vung = True
        if not self.id_bien_so:
            _log_an_toan(self.log,
                "[biển số] Model này KHÔNG có class 'plate' "
                f"(model đang dùng có: {len(self.ten_lop)} lớp khác) -> "
                "đọc OCR cả khung hình. Chậm hơn, nên cần vùng biển số rồi: "
                "--vung-bien-so x1,y1,x2,y2"
            )
        else:
            _log_an_toan(self.log,
                "[biển số] không tìm thấy class 'plate' trong khung hình này")

    # ------------------------------------------------------------------- OCR
    def _engine(self, tim_chu: bool):
        """Chon engine OCR. Uu tien dung dung loai, fallback sang engine con lai."""
        if tim_chu:
            return self.ocr_tim or self.ocr
        return self.ocr or self.ocr_tim

    def _ocr_muc(self, crop, tim_chu: bool = False) -> list[dict]:
        """Chay OCR -> list manh chu (box/text/conf) sau khi loc theo nguong.

        tim_chu=False -> engine CHI DOC (mac dinh): doc nguyen crop nhieu
                        dong 1 -> nhanh, dung khi crop da la vung bien so.
        tim_chu=True  -> engine CO TIM CHU: tach manh chu trong anh, dung
                        khi phai TU DO vung bien so trong ca khung hinh.

        BA VE AN TOAN THREAD:
        - Khoa rieng cho tung engine: 2 thread KHONG bao gio goi cung 1
          engine RapidOCR/onnxruntime (khong an toan khi chay song song).
        - HAN CHI PHI (NGAN_CHI_PHI_MS) va NGAN SO LUOT OCR chi ap dung o
          LUONG CHINH (luong chinh set trong `doc()`). Thread nen co han rieng
          (thread-local) -> pha tim vung khong bi cat.
        """
        if crop is None or getattr(crop, "size", 0) == 0:
            return []
        # --- han chi phi + ngan so luot OCR (chi luong chinh) ---
        han = float(getattr(self._tl, "han", 0.0))
        if han and time.perf_counter() > han:
            return []
        ngan = int(getattr(self._tl, "ngan", 0))
        if ngan and int(getattr(self._tl, "luot", 0)) >= ngan:
            return []
        engine = self._engine(tim_chu)
        if engine is None:
            return []
        self._tl.luot = int(getattr(self._tl, "luot", 0)) + 1
        with self._khoa_cua_engine(engine):
            muc, _elapse = engine(crop)
        ds = []
        for it in (muc or []):
            if len(it) < 3:
                continue
            # rapidocr-onnxruntime tra tin cay o dang CHUOI ('0.74'), khong phai
            # float -> dung float() co bat loi, KHONG dung isinstance (tu do ra
            # conf=0 va loc sach moi manh chu, khong doc duoc gi).
            try:
                conf = float(it[2])
            except (TypeError, ValueError):
                conf = 0.0
            ds.append({
                "box": np.asarray(it[0], dtype=float),
                "text": str(it[1]),
                "conf": conf,
            })
        return [m for m in ds if m["conf"] >= self.nguong_tin_cay]

    def _khoa_cua_engine(self, engine):
        """Khoa dung cho engine dang chay (RapidOCR khong an toan khi goi
        dong thoi tu 2 thread)."""
        if engine is not None and engine is self.ocr_tim:
            return self._khoa_ocr_tim
        return self._khoa_ocr_doc

    def _qua_han(self) -> bool:
        """True neu luong chinh da qua HAN CHI PHI (de dung viec khong can
        thi, ke ca viec khong phai OCR: cat muc, xoay anh...)."""
        han = float(getattr(self._tl, "han", 0.0))
        return bool(han) and time.perf_counter() > han

    def _ocr_anh(self, crop, tim_chu: bool = False) -> tuple[str, float]:
        """OCR 1 anh -> (chuoi tho gop theo thu tu doc, tin cay lon nhat)."""
        ds = tach_hang(self._ocr_muc(crop, tim_chu=tim_chu))
        return ("".join(m["text"] for m in ds),
                max((m["conf"] for m in ds), default=0.0))

    def _phong_to(self, crop):
        """Phong to crop thap cho OCR doc duoc. Tra (anh, he so phong to).

        RapidOCR bo qua / doc sai anh nho. Dung cv2.INTER_CUBIC va gioi han
        be rong (OCR_RONG_TOI_DA) de khong no RAM.
        """
        cao, rong = crop.shape[:2]
        if cao >= OCR_CAO_TOI_THIEU:
            return crop, 1
        he = max(1, int(round(OCR_CAO_TOI_THIEU / max(1, cao))))
        if rong * he > OCR_RONG_TOI_DA:
            he = max(1, int(OCR_RONG_TOI_DA // max(1, rong)))
        if he <= 1:
            return crop, 1
        return cv2.resize(crop, (rong * he, cao * he),
                           interpolation=cv2.INTER_CUBIC), he

    def _cat_muc(self, anh):
        """Cat bo vien trang thua, giu lai phan co ky tu toi.

        Bien so xoay nhe hay co vien trang lon. Vach tach 2 hang chay
        ngang se cat qua giua ky tu ("30A" -> "30") -> mat bien so.
        Cat muc truoc khi tach hang la fix goc do.
        """
        if anh is None or getattr(anh, "size", 0) == 0:
            return anh
        try:
            xam = cv2.cvtColor(anh, cv2.COLOR_BGR2GRAY)
            ys, xs = np.where(xam < OCR_NGUONG_MUC_TOI)
            if len(xs) == 0:
                return anh
            x1, x2 = int(xs.min()), int(xs.max()) + 1
            y1, y2 = int(ys.min()), int(ys.max()) + 1
            if (x2 - x1) < 4 or (y2 - y1) < 4:
                return anh
            return anh[y1:y2, x1:x2]
        except Exception:                                   # noqa: BLE001
            return anh

    def _xoa_y_goc(self, anh, do: float):
        """Xoay anh 'do' do quanh tam. KHONG cat mat ky tu nao.

        Canh mo rong bang chuc nhat moi de moi goc xoay deu vua khung.
        Vien moi to bang trang.
        """
        if anh is None or getattr(anh, "size", 0) == 0:
            return anh
        h, w = anh.shape[:2]
        tam = (w / 2.0, h / 2.0)
        M = cv2.getRotationMatrix2D(tam, float(do), 1.0)
        cos, sin = abs(M[0, 0]), abs(M[0, 1])
        w_moi = max(1, int(h * sin + w * cos))
        h_moi = max(1, int(h * cos + w * sin))
        M[0, 2] += w_moi / 2.0 - tam[0]
        M[1, 2] += h_moi / 2.0 - tam[1]
        return cv2.warpAffine(anh, M, (w_moi, h_moi),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255, 255, 255))

    def _do_nghieng(self, anh) -> float:
        """Uoc luong goc nghien (do) cua chu trong anh. 0 = phang.

        Voi moi cot x, tinh trung tam muc toi theo y -> fit duong thang ->
        goc = atan(slope). Do chinh xac ~0.3 do (do thuc tren anh bien so gia
        xoay 4/7/11 do). Anh phang -> ~0 do.
        """
        if anh is None or getattr(anh, "size", 0) == 0:
            return 0.0
        try:
            xam = cv2.cvtColor(anh, cv2.COLOR_BGR2GRAY)
            mask = (xam < OCR_NGUONG_MUC_TOI).astype(np.float32)
            if float(mask.sum()) < 50.0:
                return 0.0
            cot = mask.sum(axis=0)
            idx = np.where(cot > 0)[0]
            if len(idx) < 10:
                return 0.0
            mask = mask[:, int(idx[0]):int(idx[-1]) + 1]
            if mask.shape[1] < 10:
                return 0.0
            ys = np.arange(mask.shape[0], dtype=np.float32)[:, None]
            tong = mask.sum(axis=0)
            ok = tong > 0
            if int(ok.sum()) < 10:
                return 0.0
            x = np.arange(mask.shape[1], dtype=np.float32)[ok]
            y = (mask * ys).sum(axis=0)[ok] / tong[ok]
            a, _b = np.polyfit(x, y, 1)
            do = float(np.degrees(np.arctan(a)))
            return do if -45.0 < do < 45.0 else 0.0
        except Exception:                                   # noqa: BLE001
            return 0.0

    def _doc_1_anh(self, anh):
        """Doc 1 anh (da phong to) -> (chuoi tho, tin cay, so hang, chuoi chuan hoa).

        Thu doc ca anh (1 hang). Neu khong ra bien so, tach thanh 2 phan
        (bien so 2 hang) va ghep chuoi.
        """
        tho, tin_cay = self._ocr_anh(anh)
        chuoi = chuan_hoa_bien_so(tho)
        so_hang = 1
        if not chuoi and anh.shape[0] >= 24 and not self._qua_han():
            # Bien 2 hang: cat thanh 2 phan (co chong 15%) va ghep chuoi.
            y = int(anh.shape[0] * 0.575)
            tren = anh[:y, :]
            duoi = anh[int(anh.shape[0] * 0.425):, :]
            tho_tren, tin_tren = self._ocr_anh(tren)
            tho_duoi, tin_duoi = self._ocr_anh(duoi)
            chuoi = chuan_hoa_bien_so(tho_tren + " " + tho_duoi)
            if chuoi:
                tho = f"{tho_tren} {tho_duoi}"
                tin_cay = max(tin_tren, tin_duoi)
                so_hang = 2
        return tho, tin_cay, so_hang, chuoi

    def _doc_2_anh(self, anh):
        """Doc 1 anh theo duong DAY DU: doc thang, neu khong ra -> cat muc toi
        roi doc lai. Tra (tho, tin cay, so hang, chuoi)."""
        tho, tin_cay, so_hang, chuoi = self._doc_1_anh(anh)
        if chuoi:
            return tho, tin_cay, so_hang, chuoi
        return self._doc_1_anh(self._cat_muc(anh))

    def _duoc_thu_xoay(self, sach: str, rong: int) -> bool:
        """Co nen thu cac goc xoay khong?

    - Crop rong hon OCR_RONG_TOI_DA_XOAY la anh xe/canh, khong phai bien so.
    - Doc duoc qua 8 ky tu -> khong phai bien so, xoay cung khong giup.
    - Doc duoc 7-8 ky tu VA co chu cai dung o vi tri 3 -> da co dang bien so,
      xoay cung khong giup (bien so nuoc ngoai cung vay).
    - Con lai (OCR that bai that: doc qua it ky tu, hoac thieu chu cai o
      vi tri 3 do bien so xoay nhe) -> thu goc xoay.
    """
        if rong > OCR_RONG_TOI_DA_XOAY:
            return False
        n = len(sach)
        if n > 8:
            return False
        if n >= 7 and sach[VI_TRI_CHU].isalpha():
            return False
        return True

    def _doc_crop(self, anh_ocr):
        """Doc 1 crop bien so.

        Tra (tho, tin cay, so hang, chuoi, goc xoay, mau_thuan).

        Cac buoc, chi thu tiep khi buoc truoc that bai:
        1. Doc truc tiep (1 hang), neu khong ra bien so -> tach 2 hang.
        2. Cat muc toi (bo vien trang) -> doc lai. Bien so xoay nhe hay co
           vien trang lon: vach tach 2 hang cat qua giua ky tu -> mat chu.
        3. Anh NGHIENG >= SKEW_TOI_DA ma 2 cach doc lech nhau -> mau_thuan
           (khong ro bien so that -> KHONG bao cao).
        4. Thu goc xoay +-3, +-6, +-9 do (chi khi OCR that bai that).
        """
        tho, tin_cay, so_hang, chuoi = self._doc_1_anh(anh_ocr)
        anh_muc = self._cat_muc(anh_ocr)

        # --- 3. anh NGHIENG: 2 cach doc lech nhau -> khong ro bien so that ---
        # Bien so xoay ~11 do: doc thang ra "30A-12346", doc ban cat muc toi
        # ra "30A-12345". Hai ket qua khac nhau -> KHONG chac chan -> KHONG
        # bao cao (thieu bien so con hon bao bien so sai).
        # Chi kiem tra khi anh nghien >= SKEW_TOI_DA (anh phang: doc 1 lan,
        # khong ton them chi phi).
        if chuoi and abs(self._do_nghieng(anh_muc)) >= SKEW_TOI_DA:
            _t, _tc, _s, chuoi_muc = self._doc_1_anh(anh_muc)
            if chuoi_muc and chuoi_muc != chuoi:
                return tho, tin_cay, so_hang, chuoi, "", True
        if chuoi:
            return tho, tin_cay, so_hang, chuoi, "", False

        # --- 2. cat muc toi (bo vien trang thua) ---
        if self._qua_han():
            return tho, tin_cay, so_hang, chuoi, "", False
        tho_m, tin_m, sh_m, chuoi_m = self._doc_1_anh(anh_muc)
        if chuoi_m:
            return tho_m, tin_m, sh_m, chuoi_m, "", False

        # --- 4. thu goc xoay (chi khi OCR that bai that) ---
        sach = lam_sach(tho_m if len(tho_m) >= len(tho) else tho)
        if not self._duoc_thu_xoay(sach, anh_muc.shape[1]):
            return tho, tin_cay, so_hang, chuoi, "", False
        for do in GOC_XOAY_THU:
            if self._qua_han():
                break
            anh_x = self._cat_muc(self._xoa_y_goc(anh_muc, do))
            tho_x, tin_x, sh_x, chuoi_x = self._doc_1_anh(anh_x)
            if chuoi_x:
                return tho_x, tin_x, sh_x, chuoi_x, f"{do:+d}", False
        return tho, tin_cay, so_hang, chuoi, "", False

    def _tim_bien_so_trong_khung_hinh(self, anh_bgr) -> list[tuple]:
        """TU DO vung bien so trong ca khung hinh (khi khong co class 'plate'
        cua YOLO va khong co ROI).

        Engine "chi doc" doc nguyen 1 dong -> khong tach duoc vung bien so.
        Phai dung engine "co tim chu" de tach manh chu, roi dung engine
        "chi doc" de doc tung vung ung vien.

        Engine "co tim chu" cham (300-1500 ms/khung hinh) -> ham nay CHAY O
        THREAD NEN (xem `_quet_toan_khung_nen`). Ham nay chi dung khi can
        tim ngay tren luong chinh (khong dung trong `doc()`).
        """
        if not self._nap_engine("tim"):
            if self.ocr is not None and not self.da_bao_loi_1_engine:
                self.da_bao_loi_1_engine = True
                _log_an_toan(self.log,
                    "[biển số] Chỉ nạp được engine OCR 'chỉ đọc' -> KHÔNG tự dò "
                    "được vùng biển số trong cả khung hình. Hãy đặt ROI biển số: "
                    "--vung-bien-so x1,y1,x2,y2"
                )
            return []

        muc = self._ocr_muc(anh_bgr, tim_chu=True)
        if not muc:
            return []
        return self._ung_vien_bien_so(muc)[:SO_UNG_VIEN_TOI_DA]

    def _ung_vien_bien_so(self, muc: list[dict]) -> list[tuple]:
        """Tu cac manh chu tim duoc, chon cac vung co hinh dang giong bien so.

        Bien so Viet Nam luon dai ngang, it chu, 1 hoac 2 hang.
        """
        hang = _gom_hang(muc)
        ra: list[tuple] = []
        for i, nhom in enumerate(hang):
            y0 = min(float(m["box"][:, 1].min()) for m in nhom)
            y1 = max(float(m["box"][:, 1].max()) for m in nhom)
            for j in (i, i + 1):
                if j >= len(hang):
                    continue
                nhom2 = hang[j]
                x1 = min(float(m["box"][:, 0].min()) for m in nhom2)
                x2 = max(float(m["box"][:, 0].max()) for m in nhom2)
                yy0 = min(y0, min(float(m["box"][:, 1].min()) for m in nhom2))
                yy1 = max(y1, max(float(m["box"][:, 1].max()) for m in nhom2))
                w, h = x2 - x1, yy1 - yy0
                if w < 40 or h < 6:
                    continue
                if w / max(1.0, h) < 1.2:        # bien so luon dai ngang
                    continue
                ra.append((int(x1), int(yy0), int(x2), int(yy1)))
        return ra

    def doc_vung(self, crop, khung, nguon="vung") -> list[KetQuaBienSo]:
        """OCR 1 vung da cat. Xu ly ca bien 1 hang va bien 2 hang."""
        ra: list[KetQuaBienSo] = []
        if crop is None or getattr(crop, "size", 0) == 0:
            return ra
        cao, rong = crop.shape[:2]
        if rong < KICH_THUOC_BIEN_SO_TOI_DA[0] or cao < KICH_THUOC_BIEN_SO_TOI_DA[1]:
            return ra

        # Vung qua rong -> khong phai bien so. RapidOCR cung bo qua vung
        # nhu vay, va neu ep doc se ra chu rac.
        if rong / max(1, cao) > OCR_TY_LE_RONG_TOI_DA:
            self.so_lan_qua_rong += 1
            if self.so_lan_qua_rong == 1:
                _log_an_toan(self.log,
                    "[biển số] Vùng quá rộng (rộng/cao > 8) - không phải biển số, "
                    "bỏ qua. Hãy chỉ rõ vùng biển số bằng --vung-bien-so x1,y1,x2,y2"
                )
            return ra

        # Vung DIEN TICH lon -> anh xe/canh, khong phai bien so -> bo qua som
        # (doc anh lon chi ton thoi gian, khong them gia tri).
        if rong * cao > OCR_DIEN_TICH_TOI_DA:
            self.so_lan_qua_lon += 1
            if self.so_lan_qua_lon == 1:
                _log_an_toan(self.log,
                    "[biển số] Vùng quá lớn (trên 250.000 px) - không phải biển "
                    "số, bỏ qua. Hãy chỉ rõ vùng biển số bằng "
                    "--vung-bien-so x1,y1,x2,y2"
                )
            return ra

        # Khong co engine "chi doc" -> phai dung engine "co tim chu" (cham
        # 30-80 ms cho vung nho) -> chi doc vung nho de khong treo khung hinh.
        if self.ocr is None and rong * cao > OCR_DIEN_TICH_DOC_NEN_MAX:
            return ra

        # Crop qua thap -> phong to truoc khi OCR.
        anh_ocr, _he = self._phong_to(crop)

        # Ngan so luot OCR cho vung nay (vung rong co the lam 24 luot ->
        # 200+ ms -> treo khung hinh). Reset o finally de cac lan goi
        # truc tiep `doc_vung` khong bi anh huong.
        self._tl.luot = 0
        self._tl.ngan = SO_LUOT_OCR_TOI_DA
        t0 = time.perf_counter()
        try:
            tho, tin_cay, so_hang, chuoi, goc_xoay, mau_thuan = self._doc_crop(anh_ocr)
        finally:
            self._tl.luot = 0
            self._tl.ngan = 0
        self.tong_ms += (time.perf_counter() - t0) * 1000.0
        self.so_lan_doc += 1

        if not chuoi:
            return ra

        x1, y1, x2, y2 = khung
        ra.append(KetQuaBienSo(
            chuoi=chuoi, chuoi_goc=tho, tin_cay=round(tin_cay, 3),
            khung=(x1, y1, x2, y2), so_hang=so_hang, nguon=nguon,
            goc_xoay=goc_xoay, mau_thuan=mau_thuan,
        ))
        return ra

    def tin_cay_cuoi(self, chuoi_tho: str) -> float:
        """Tin lay OCR: chuoi khop DUNG mau bien so Viet Nam -> 0.95, con lai 0.0."""
        chuoi = chuan_hoa_bien_so(chuoi_tho)
        return 0.95 if khop_mau_bien_so_vn(chuoi) else 0.0

    # ------------------------------------------------------------------ luu anh
    def _crop(self, anh_bgr, khung):
        x1, y1, x2, y2 = khung
        return anh_bgr[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]

    def _co_mat_rang(self, crop, khung, khuon_mat) -> bool:
        """True neu co tin hieu mat trong crop bien so (xem ghi chu privacy o docstring).

        khuon_mat: list box (x1,y1,x2,y2) ma pipeline chinh nhan duoc trong
        khung hinh. Khong co list rong -> xem nhu khong co tin hieu mat.
        """
        if self.cho_phep_luu_mat:
            return False
        co_tin_hieu = False
        for box in (khuon_mat or []):
            co_tin_hieu = True
            if _mua_giao(box, khung) > 0.15:      # mat che > 15% crop
                return True
        cascade = _lay_cascade()                 # duong phong (OpenCV < 5)
        if cascade is not None:
            co_tin_hieu = True
            try:
                xam = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                nhan = cascade.detectMultiScale(
                    xam, scaleFactor=1.15, minNeighbors=5,
                    minSize=(max(20, crop.shape[1] // 4),
                             max(20, crop.shape[0] // 4)),
                )
                if len(nhan):
                    return True
            except Exception:                               # noqa: BLE001
                pass
        if not co_tin_hieu:
            self.so_lan_khong_tin_hieu_mat += 1
            if self.so_lan_khong_tin_hieu_mat == 1:
                _log_an_toan(self.log,
                    "[biển số] KHÔNG có tín hiệu khuôn mặt (đã tắt nhận diện mặt) "
                    "-> vẫn lưu ảnh biển số. Bật nhận diện mặt, hoặc đặt "
                    "cho_phep_luu_mat, nếu anh muốn kiện số an toàn hơn."
                )
        return False

    def _luu_anh(self, crop, khung, chuoi: str, khuon_mat=None) -> str:
        """Luu crop bien so. Chong ghi trung: cung bien so chi 1 lan / nhoan_lai_giay."""
        if not self.thu_muc_luu:
            return ""
        now = time.monotonic()
        lan_cuoi = self.luu_lan_cuoi.get(chuoi, 0.0)
        if self.nhoan_lai_giay > 0 and (now - lan_cuoi) < self.nhoan_lai_giay:
            return ""

        if self._co_mat_rang(crop, khung, khuon_mat):
            self.so_lan_bo_qua_mat += 1
            if self.so_lan_bo_qua_mat == 1:
                _log_an_toan(self.log,
                    f"[biển số] KHÔNG lưu ảnh của {chuoi}: crop có khuôn mặt rõ ràng. "
                    "Muốn lưu, hãy bật cho_phep_luu_mat (vẫn dùng trên máy này, "
                    "không gửi ra ngoài)."
                )
            return ""

        try:
            os.makedirs(self.thu_muc_luu, exist_ok=True)
            nhan = datetime.now().strftime("%Y%m%d_%H%M%S")
            ten = f"bien_so_{nhan}_{chuoi}.jpg"
            duong = os.path.join(self.thu_muc_luu, ten)
            if os.path.exists(duong):            # trung 1 giay -> them _1, _2
                k = 1
                while os.path.exists(os.path.join(self.thu_muc_luu,
                                                  f"bien_so_{nhan}_{chuoi}_{k}.jpg")):
                    k += 1
                duong = os.path.join(self.thu_muc_luu, f"bien_so_{nhan}_{chuoi}_{k}.jpg")
            if not cv2.imwrite(duong, crop, [int(cv2.IMWRITE_JPEG_QUALITY), 92]):
                return ""
            self.luu_lan_cuoi[chuoi] = now
            self.da_luu += 1
            return duong
        except Exception:                                       # noqa: BLE001
            return ""

    # ------------------------------------------------------------------- doc
    def doc(self, anh_bgr, detections=None, so_mat_rang: int = 0,
            khuon_mat=None) -> list[KetQuaBienSo]:
        """Doc bien so trong 1 khung hinh. Tra ve list[KetQuaBienSo] (rong = khong co).

        CHI tra ve cac bien so da XAC NHAN (xuat hien o >= XAC_NHAN_TOI_THIEU
        khung hinh lien tiep) -> CSV, thu muc luu anh va khung ve tren video
        chi co bien so da chac chan. Xem _cap_nhat_xac_nhan().

        detections: sv.Detections cua khung hinh nay (dung lai YOLO san co).
        so_mat_rang: so mat ma pipeline chinh da nhan trong khung hinh nay
                     (chi de thong bao).
        khuon_mat: list box mat da nhan duoc - dung de KHIEM TRA RIENG TU
                   (khong luu anh crop co mat) trong _luu_anh().

        HAN CHI PHI: ham nay PHAI tra ve nhanh (keo cua so khong giat).
        - Nap engine va tim vung trong ca khung hinh -> THREAD NEN.
        - Doc vung -> HAN CHI PHI (NGAN_CHI_PHI_MS) + ngan so luot OCR.
        """
        if anh_bgr is None or not hasattr(anh_bgr, "shape") or anh_bgr.size == 0:
            return []

        # Han chi phi cho LUONG CHINH (thread-local: thread nen khong bi cat).
        self._tl.han = time.perf_counter() + NGAN_CHI_PHI_MS / 1000.0
        try:
            if self.ocr is None and self.ocr_tim is None:
                # Chua nap engine -> nap o THREAD NEN (khong treo khung hinh).
                # Khung hinh nay bo trong (khong doc gi) - an toan hon la treo.
                self._yeu_cau_nap_nen()
                return []
            if self.ocr is None:
                # Chi co engine "co tim chu" (cham 250-1500 ms ke ca tren crop
                # nho) -> KHONG doc o luong chinh de khong treo khung hinh.
                self._canh_bao_thieu_engine_chi_doc()
                return []

            # --- 1. DOC: moi vung trong khung hinh nay ---
            phat_hien: list[tuple] = []
            for khung, nguon in self._vung_can_doc(anh_bgr, detections)[:SO_VUNG_DOC_TOI_DA]:
                if self._qua_han():
                    break                      # het han -> dung, khong treo
                crop = self._crop(anh_bgr, khung)
                for r in self.doc_vung(crop, khung, nguon=nguon):
                    phat_hien.append((r, crop, khung))
        finally:
            self._tl.han = 0.0

        # --- 2. XAC NHAN DA KHUNG HINH ---
        # Chuoi chi xuat hien 1 khung hinh -> trang thai "nghi": van nho lai
        # nhung KHONG ghi vao bao cao, KHONG luu anh.
        self._cap_nhat_xac_nhan({r.chuoi for r, _c, _k in phat_hien})

        # --- 3. CHI tra ve (va chi luu anh) bien so da xac nhan ---
        ra: list[KetQuaBienSo] = []
        for r, crop, khung in phat_hien:
            if r.chuoi in {x.chuoi for x in ra}:
                continue
            if r.mau_thuan:
                # Anh nghien: 2 cach doc lech nhau -> khong ro bien so that.
                # KHONG ghi vao bao cao, KHONG luu anh (thieu con hon bao sai).
                if r.chuoi not in self._da_bao_mau_thuan:
                    self._da_bao_mau_thuan.add(r.chuoi)
                    _log_an_toan(self.log,
                        f"[biển số] '{r.chuoi}' đọc KHÔNG NHẤT QUÁN (ảnh nghiêng, "
                        "2 cách đọc lệch nhau) - không chắc chắn nên KHÔNG ghi "
                        "vào báo cáo.")
                continue
            if not self.xac_nhan_chac(r.chuoi):
                continue
            r.xac_nhan = "chac"
            if self.thu_muc_luu:
                r.duong_dan = self._luu_anh(crop, khung, r.chuoi, khuon_mat)
            ra.append(r)
        return ra

    # ------------------------------------------------------- xac nhan khung hinh
    def _cap_nhat_xac_nhan(self, chuoi_lan_nay: set[str]) -> None:
        """Nho cac chuoi vua doc duoc + dem so khung hinh lien tiep.

        - Chua tung thay -> so_khung = 1 -> trang thai "nghi" (CHUA CHAC CHAN):
          van nho lai nhung KHONG ghi vao bao cao, KHONG luu anh.
        - Xuat hien tiep trong khoang lien tiep -> so_khung += 1.
        - so_khung >= XAC_NHAN_TOI_THIEU -> "DOC CHAC": duoc ghi vao CSV, duoc
          luu anh crop, duoc ve khung.

        "Lien tiep" = xuat hien o khung hinh ngay truoc HOAC cach lan doc gan
        nhat khong qua cua (cua = max(NGUONG_LIEN_TIEP_GIAY, 3 lan do dai khung
        hinh uoc luong) -> khong phu thuoc fps cua may).
        """
        now = time.monotonic()
        if self._lan_doc_cuoi > 0:
            gap = now - self._lan_doc_cuoi
            if gap > 0:
                self._gap_khung_hinh = (gap if self._gap_khung_hinh <= 0
                                        else 0.7 * self._gap_khung_hinh + 0.3 * gap)
        self._lan_doc_cuoi = now
        cua = max(NGUONG_LIEN_TIEP_GIAY, HE_SO_CUA_LIEN_TIEP * self._gap_khung_hinh)

        for chuoi in chuoi_lan_nay:
            tt = self.trang_thai_bien_so.get(chuoi)
            if tt is None:
                self.trang_thai_bien_so[chuoi] = _TrangThaiBienSo(
                    chuoi=chuoi, so_khung=1, lan_cuoi=now, lan_dau=now)
                self.so_lan_nghi += 1
                _log_an_toan(self.log,
                    f"[biển số] Đọc được '{chuoi}' nhưng CHƯA XÁC NHẬN "
                    "(mới 1 khung hình) - chưa ghi vào báo cáo, chờ khung hình "
                    "tiếp theo xác nhận.")
                continue
            lien_tiep = (chuoi in self._chuoi_lan_truoc
                         or (now - tt.lan_cuoi) <= cua)
            tt.so_khung = tt.so_khung + 1 if lien_tiep else 1
            tt.lan_cuoi = now

        # don chuoi da lau khong xuat hien nua (tranh nho tang dan)
        for chuoi in list(self.trang_thai_bien_so):
            if (now - self.trang_thai_bien_so[chuoi].lan_cuoi) > XOA_NHO_GIAY:
                del self.trang_thai_bien_so[chuoi]
        self._chuoi_lan_truoc = set(chuoi_lan_nay)

    def xac_nhan_chac(self, chuoi: str) -> bool:
        """True neu chuoi da duoc xac nhan (>= XAC_NHAN_TOI_THIEU khung hinh)."""
        tt = self.trang_thai_bien_so.get(chuoi)
        return bool(tt) and tt.da_chac

    def danh_sach_nghi(self) -> list[str]:
        """Cac chuoi moi doc duoc nhung CHUA xac nhan (chi 1 khung hinh).

        CHUA duoc ghi vao CSV va chua luu anh. Neu muon hien thi rieng, can sua
        cam_ai_core.py (de them cot "nghi") - hien tai CSV giu nguyen so cot
        cu (10 cot, hoac 12 khi bat doc bien so).
        """
        return [c for c, tt in self.trang_thai_bien_so.items() if not tt.da_chac]

    def _vung_can_doc(self, anh_bgr, detections=None) -> list[tuple]:
        """Danh sach (khung, nguon) can doc bien so trong khung hinh nay.

        nguon: "plate" (class YOLO) | "vung" (ROI) | "tim_chu" (tu do trong
        ca khung hinh bang engine co tim chu).

        Khi khong co class 'plate' va khong co ROI: pha TIM VUNG chay o
        THREAD NEN (300-1500 ms). o day chi lay vung da tim trong CACHE ->
        `doc()` KHONG bao gio cho.
        """
        vung = self._vung_co_dinh(anh_bgr, detections)
        if vung:
            # --- Vung co dinh (class YOLO hoac ROI do nguoi dung dat) ---
            for k, nguon in vung:
                x1, y1, x2, y2 = k
                if (x2 - x1) * (y2 - y1) > OCR_DIEN_TICH_VUNG_LON:
                    # Vung RONG (anh xe/canh chua bien so) -> pha tim vung
                    # bien so trong vung do chay o THREAD NEN; doc() chi doc
                    # vung NHO da tim duoc -> nhanh va doc dung hon.
                    return self._vung_roi_rong_nen(anh_bgr, k)
            return vung

        # Khong co class 'plate' va khong co ROI -> tu do bang engine CO TIM
        # CHU. Pha nay chay o THREAD NEN; day chi lay ket qua CACHE.
        self._canh_bao_toan_khung()
        vung = self._vung_tu_cache(anh_bgr.shape, "toan_khung")
        if not vung:
            self._yeu_cau_quet(anh_bgr, "toan_khung", (0, 0, 0, 0))
            return []
        return [(k, "tim_chu") for k in vung]

    def _vung_roi_rong_nen(self, anh_bgr, khung_roi) -> list[tuple]:
        """Vung ROI rong: doc vung bien so DA TIM (thread nen) trong ROI do."""
        vung = self._vung_tu_cache(anh_bgr.shape, "roi")
        if not vung:
            self._yeu_cau_quet(anh_bgr, "roi", khung_roi)
            return []
        return [(k, "tim_chu") for k in vung]

    # ------------------------------------------------------------ thread nen
    def _khoi_dong_thread_nen(self) -> None:
        """Tao thread nen (lazy, 1 lan duy nhat, daemon)."""
        if self._thread_nen is not None and self._thread_nen.is_alive():
            return
        self._dung_nen = False
        self._thread_nen = threading.Thread(
            target=_vong_nen, args=(weakref.ref(self),),
            name="bien-so-nen", daemon=True)
        try:
            self._thread_nen.start()
        except Exception:                                   # noqa: BLE001
            self._thread_nen = None

    def _yeu_cau_nap_nen(self) -> None:
        """Yeu cau nap engine OCR o thread nen (khong chan khung hinh)."""
        if self.nap_doc_that_bai and self.nap_tim_that_bai:
            return
        with self._khoa_viec:
            if self._viec_nen is not None:
                return
            self._viec_nen = ("nap", None)
        self._khoi_dong_thread_nen()
        self._su_kien_nen.set()

    def _yeu_cau_quet(self, anh_bgr, che_do: str, khung_roi) -> None:
        """Yeu cau TIM VUNG o thread nen (khong cho).

        che_do: "toan_khung" (quet ca khung hinh) | "roi" (quet trong ROI).
        Khong cho: chi dat 1 viec cho, va khong quet lai trong khoang
        GIYAY_GIAM_TAN giay (cache vung cu con hieu luc).
        """
        if anh_bgr is None or getattr(anh_bgr, "size", 0) == 0:
            return
        with self._khoa_viec:
            if self._quet_dang_chay or self._viec_nen is not None:
                return
            with self._khoa_cache:
                if (time.monotonic() - self._cache_vung["luc"]) < GIYAY_GIAM_TAN:
                    return
            self._quet_dang_chay = True
            self._viec_nen = ("quet", (anh_bgr.copy(), che_do, tuple(khung_roi)))
        self._khoi_dong_thread_nen()
        self._su_kien_nen.set()

    def _xuly_viec_nen(self) -> None:
        """Lay 1 viec cho va chay (chi trong thread nen)."""
        with self._khoa_viec:
            viec = self._viec_nen
            self._viec_nen = None
        if not viec:
            return
        loai, du_lieu = viec
        try:
            if loai == "nap":
                # Nap engine "chi doc"; neu that bai -> thu engine "co tim chu".
                if not self._nap_engine("doc"):
                    self._nap_engine("tim")
            elif loai == "quet":
                anh, che_do, khung_roi = du_lieu
                self._quet_nen(anh, che_do, khung_roi)
        except Exception:                                   # noqa: BLE001
            pass
        finally:
            if loai == "quet":
                with self._khoa_viec:
                    self._quet_dang_chay = False

    def _quet_nen(self, anh_bgr, che_do: str, khung_roi) -> None:
        """TIM VUNG bien so (chi trong thread nen).

        Engine "co tim chu" cham 300-1500 ms -> vung tim duoc luu vao CACHE
        (toa do tuong doi) de cac khung hinh sau doc lai, khong phai quet
        lai tu dau.
        """
        if anh_bgr is None or getattr(anh_bgr, "size", 0) == 0:
            return
        if not self._nap_engine("tim"):
            if self.ocr is not None and not self.da_bao_loi_1_engine:
                self.da_bao_loi_1_engine = True
                _log_an_toan(self.log,
                    "[biển số] Chỉ nạp được engine OCR 'chỉ đọc' -> KHÔNG tự dò "
                    "được vùng biển số trong cả khung hình. Hãy đặt ROI biển số: "
                    "--vung-bien-so x1,y1,x2,y2"
                )
            return
        if che_do == "roi":
            x1, y1, x2, y2 = khung_roi
            crop = anh_bgr[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
            goc = (x1, y1)
        else:
            crop = anh_bgr
            goc = (0, 0)
        if crop is None or getattr(crop, "size", 0) == 0:
            return
        muc = self._ocr_muc(crop, tim_chu=True)
        vung = self._ung_vien_bien_so(muc)[:SO_UNG_VIEN_TOI_DA] if muc else []
        # Chuyen sang toa do TUONG DOI cua ca khung hinh goc.
        h, w = anh_bgr.shape[:2]
        if w <= 0 or h <= 0:
            return
        rel = []
        for (vx1, vy1, vx2, vy2) in vung:
            rel.append(((vx1 + goc[0]) / w, (vy1 + goc[1]) / h,
                        (vx2 + goc[0]) / w, (vy2 + goc[1]) / h))
        with self._khoa_cache:
            self._cache_vung = {"luc": time.monotonic(), "w": w, "h": h,
                                "vung": rel, "nguon": che_do}
        self.so_lan_quet += 1

    def _vung_tu_cache(self, anh_shape, nguon: str) -> list[tuple]:
        """Vung da tim trong cache -> toa do pixel cua khung hinh hien tai.

        Vung duoc them vien nho (bien so di chuyen cham) va TOI DA SO VUNG
        doc trong 1 khung hinh (xem SO_VUNG_DOC_TOI_DA).
        """
        h, w = anh_shape[0], anh_shape[1]
        with self._khoa_cache:
            c = self._cache_vung
            if not c["vung"] or c["w"] <= 0 or c["h"] <= 0:
                return []
            if c["nguon"] != nguon:
                return []
            if (time.monotonic() - c["luc"]) > GOC_VUNG_TTL_GIAY:
                return []
            # Vung trong cache luu o TOA DO TUONG DOI (0..1) -> nhan voi kich
            # thuoc khung hinh hien tai.
            vung = list(c["vung"])
        ra = []
        for (rx1, ry1, rx2, ry2) in vung:
            x1, y1 = rx1 * w, ry1 * h
            x2, y2 = rx2 * w, ry2 * h
            dw = (x2 - x1) * 0.05          # them vien nho: bien so di chuyen
            dh = (y2 - y1) * 0.08
            x1 = max(0, int(x1 - dw))
            y1 = max(0, int(y1 - dh))
            x2 = min(w, int(x2 + dw))
            y2 = min(h, int(y2 + dh))
            if x2 - x1 < 20 or y2 - y1 < 6:
                continue
            ra.append((x1, y1, x2, y2))
        return ra

    def close(self) -> None:
        """Dung thread nen (goi khi app dong).

        Thread la daemon nen app van tho du du khong goi `close()`, nhung goi
        thi giai phong ngay. Thread nen KHONG chay tiep sau khi doi tuong
        nay bi huy (weakref trong `_vong_nen`).
        """
        self._dung_nen = True
        self._su_kien_nen.set()

    # ------------------------------------------------------------------ thong ke
    def thong_ke(self) -> dict:
        return {
            "da_luu": self.da_luu,
            "bo_qua_mat": self.so_lan_bo_qua_mat,
            "so_lan_doc": self.so_lan_doc,
            "ms_trung_binh": round(self.tong_ms / self.so_lan_doc, 1) if self.so_lan_doc else 0.0,
            "qua_rong": self.so_lan_qua_rong,
            "qua_lon": self.so_lan_qua_lon,
            "so_lan_quet": self.so_lan_quet,
            "vung_trong_cache": len(self._cache_vung["vung"]),
            "engine_chi_doc": self.ocr is not None,
            "engine_tim_chu": self.ocr_tim is not None,
            # xac nhan da khung hinh
            "xac_nhan_toi_thieu": XAC_NHAN_TOI_THIEU,
            "so_bien_so_nghi": len(self.danh_sach_nghi()),
            "danh_sach_nghi": self.danh_sach_nghi(),
            "loi": self.loi,
        }