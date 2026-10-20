"""
CamAI - giao dien do hoa (CustomTkinter) - ban v2.

Yeu cau cua chu so huu:
    "Menu dung co lam chan lan kieu day. Chon tinh nang gi de detect
     thi no mo setting cua no ra thoi, dung co ke 1 dong dai ngoang."

Cach lam trong file nay:
    * MOI TINH NANG = 1 DONG TIEU DE (mui ten + checkbox + ten tieng Viet).
    * MAC DINH THU GON HET. Vua mo phan mem len chi thay vai dong, khong thay doi o.
    * Bam vao tieu de (hoac mui ten) -> mo phan cai dat rieng cua tinh nang do
      ngay ben duoi. Bam lai -> an lai.
    * Bat checkbox -> tu bung phan cai dat. Tat checkbox -> tu thu lai VA
      khoi phuc lai gia tri mac dinh.
    * "Thong tin mo hinh AI" khong nhet bang vao cua so chinh, ma mo o cua so con.
    * Cua so chinh KHONG co thanh cuon: phai nhin thay het moi dung.

Nguyen tac ky thuat (giu nguyen tu ban cu):
1. Pipeline chay o THREAD rieng (daemon=True). Khong bao gio chay tren luong UI,
   neu khong cua so se bi treo.
2. Thread chi day vao hang doi (queue.Queue). Cuong sau moi ~120ms mot lan
   root.after() moi cap nhat widget -> khong bao gio go widget Tkinter tu
   thread nen (se crash).
3. Loi trong thread dua ve GUI qua hang doi, khong de app bien mat.
4. Callback tien trinh tra False = nguoi dung bam "Dung".
5. Doc code/log noi bo KHONG dau, nhan tren giao dien CO dau de de doc.
6. KHONG goi os.chdir() - duong dan tuong doi giu nguyen mac dinh cua app.
"""

from __future__ import annotations

import io
import ctypes
import json
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import numpy as np

from cam_ai_core import (AnalysisConfig, CamAIError, Progress, VERSION,
                         chon_providers, chon_thiet_bi, run_analysis)
# v3.6: nguon vao co 4 kieu (video / anh / camera may / camera IP).
# DOC cam_ai_core, KHONG sua. Dung `import ... as CORE` de 1 ham bi doi
# trong cam_ai_core khong lam GUI chet ngay luc import.
import cam_ai_core as CORE
# v3.6: bang tra cuu lop TIENG VIET <-> TIENG ANH (lop_viet.py). File nay tach
# rieng (khong import ultralytics/torch) nen khoi dong app van nhanh.
# Import co FALLBACK: app van chay duoc neu file chua co / bi loi - chi la
# khong tra cuu duoc ten lop tieng Viet.
try:
    import lop_viet
except Exception:                                     # noqa: BLE001
    lop_viet = None
from duong_dan import APP_DIR

# Phan tach rieng: ve overlay + panel "Đối tượng phát hiện".
# gui.py KHÔNG vẽ bằng tay, chỉ gọi hàm ở đây (xem gui_khung.py đầu file).
import gui_khung as GK
from gui_khung import PanelSuKien, cat_anh_moi, ve_khung_hinh

# HANG SO THIET KE tach rieng sang `giao_dien.py` (design system da chot):
# mau, font, khoang cach, bo goc, kich thuoc, bieu tuong Windows.
# gui.py KHONG viet hex tay ben ngoai - mau lay tu `MAU`.
import giao_dien as GD
from giao_dien import (MAU, MAU_TRANG_THAI, BO_GOC, BO_GOC_NUT,
                       BO_GOC_O_NHAP, BO_GOC_THE, KICH_THUOC,
                       anh_bieu_tuong, bieu_tượng, xac_nhan_font)

PYTHON_EXE = sys.executable
VE_VUNG = os.path.join(APP_DIR, "ve_vung.py")
BAO_CAO = os.path.join(APP_DIR, "bao_cao_tong_ket.py")
THU_MUC_CLIP = os.path.join(APP_DIR, "clip_da_luu")
# v3.0: thu muc luu crop bien so + anh su kien. Dat trong APP_DIR de khong
# phu thuoc thu muc dang chay cua may.
THU_MUC_BIEN_SO = os.path.join(APP_DIR, "anh_bien_so")
THU_MUC_ANH_SU_KIEN = os.path.join(APP_DIR, "anh_su_kien")

VIDEO_FILETYPES = [
    ("Video", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.m4v"),
    ("Tat ca file", "*.*"),
]
ZONE_FILETYPES = [("File vung", "*.txt"), ("Tat ca file", "*.*")]

# v3.6: bo loc file ANH cho hop thoai chon anh.
# DUOI_ANH lay tu cam_ai_core (1 noi duy nhat) - fallback neu core doi ten.
DUOI_ANH_MAC_DINH = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")
ANH_FILETYPES = [
    ("Anh", " ".join("*" + d for d in DUOI_ANH_MAC_DINH)),
    ("Tat ca file", "*.*"),
]

# Loai nguon (xem `cam_ai_core.loai_nguon`).
LOAI_ANH = "anh"
LOAI_CAMERA = "camera"
LOAI_MANG = "mang"
LOAI_VIDEO = "video"

# Tien to dia chi camera IP ( dung de kiem tra nhanh o GUI).
TIEN_DO_MANG = ("rtsp://", "rtmp://", "http://", "https://")


def loai_nguon(input_str) -> str:
    """Loai nguon vao: 'anh' | 'camera' | 'mang' | 'video'.

    Uu tien ham cua `cam_ai_core` (1 noi duy nhat quyet dinh). Neu core chua
    co ham nay (dang sua) -> tu suy ra cho app van chay duoc.
    """
    ham = getattr(CORE, "loai_nguon", None)
    if ham is not None:
        return ham(input_str)
    goc = str(input_str or "").strip()
    if not goc:
        return LOAI_VIDEO
    if goc == "0":
        return LOAI_CAMERA
    if goc.lower().startswith(TIEN_DO_MANG):
        return LOAI_MANG
    duoi = getattr(CORE, "DUOI_ANH", DUOI_ANH_MAC_DINH)
    if os.path.splitext(goc.lower())[1] in duoi:
        return LOAI_ANH
    return LOAI_VIDEO


def la_live(input_str) -> bool:
    """True neu nguon la camera (may hoac IP) -> chay lien tuc, tong frame = 0."""
    return loai_nguon(input_str) in (LOAI_CAMERA, LOAI_MANG)


def duoi_anh() -> tuple:
    """Cac duoi file duoc coi la ANH TINH (doc tu cam_ai_core)."""
    return tuple(getattr(CORE, "DUOI_ANH", DUOI_ANH_MAC_DINH))


def _la_tat_ca_lop(chuoi: str) -> bool:
    """'all' / 'tat ca' -> True (dung chung quy uoc voi `lop_viet`).

    Fallback khi `lop_viet` khong co: chi nhan dung chu "all".
    """
    if lop_viet is not None:
        ham = getattr(lop_viet, "LA_TAT_CA", None)
        if ham is not None:
            try:
                return bool(ham(chuoi))
            except Exception:                             # noqa: BLE001
                pass
    return str(chuoi or "").strip().lower() == "all"


def _chon_lop_cho_xem(chuoi: str, id_lop: dict) -> tuple[list[str], list[str]]:
    """Chon lop vatu thu tu chuoi nguoi dung nhap (dung cho KHUNG XEM TRUC TIEP).

    DUNG CHUNG ham `_chon_lop` cua `cam_ai_core` -> GUI va CLI cho ra cung
    ket qua: nhan duoc ca ten lop tieng Anh va tieng Viet ("o to, xe may").

    - `cam_ai_core` chua co ham nay (ban cu) -> fallback tu tra cuu.
    - `lop_viet` cung khong co -> fallback chi nhan ten lop tieng Anh.

    Tra (danh sach lop hop le, danh sach token khong nhan ra).
    """
    ham = getattr(CORE, "_chon_lop", None)
    if ham is not None:
        try:
            return ham(chuoi, id_lop)
        except Exception:                                 # noqa: BLE001
            pass
    # Fallback: core chua co `_chon_lop` -> tu lam theo cung quy tac.
    ra: list[str] = []
    sai: list[str] = []
    tach = getattr(lop_viet, "TACH_LOP_VIET", None) if lop_viet else None
    tra = getattr(lop_viet, "TRA_CUU_LOP_VIET", None) if lop_viet else None
    if tach is None or tra is None:
        for phan in [x.strip() for x in str(chuoi).split(",") if x.strip()]:
            if phan in id_lop:
                ra.append(phan)
            else:
                sai.append(phan)
        return ra, sai
    for phan in tach(chuoi):
        if phan in id_lop:
            if phan not in ra:
                ra.append(phan)
            continue
        ten = tra(phan)
        if ten and ten[0] in id_lop:
            if ten[0] not in ra:
                ra.append(ten[0])
        else:
            sai.append(phan)
    return ra, sai

MAX_LOG_LINES = 200
# Chu kỳ bơm hàng đợi. ĐÂY LÀ TRẦN SỐ KHUNG HÌNH NGƯỜI DÙNG THẤY.
# Vòng bơm mỗi lần chỉ lấy khung hình CUỐI trong hàng đợi, nên 1 khung/giây
# = PUMP_MS/1000. Đo thật trên máy này (2026-10): 120 ms -> 5.7 fps,
# 80 -> 7.6, 50 -> 10.3, 30 -> 15.4 fps (0/29 giây rơi dưới 10 fps).
# 30 ms là chọn để có dư địa: thời gian mỗi lần bơm (~46 ms: giải mã JPEG +
# resize + tạo PhotoImage) vẫn nằm gọn trong chu kỳ.
# Không sợ kéo cửa sổ giật: lúc đang kéo, `_hien_khung_hinh` và
# `_ve_lai_khung_hinh` đều thoát sớm (chỉ ghi nhớ khung), việc nặng chỉ chạy
# 1 lần sau khi ngừng kéo.
PUMP_MS = 30
PROGRESS_THROTTLE = 0.10          # giay - khong doi GUI nhanh hon muc nay
SO_MUC_1_VONG = 400               # toi da rut bao nhieu muc hang doi trong 1 vong
# --- xem video truc tiep (xem ghi chu o _vong_xem) ---
# GOM YOLO trong KHUNG HINH cua chinh phan tich: cam_ai_core khong dua anh
# qua Progress nen phai chay them 1 vong doc video rieng. De may khong bi
# cham, so khung hinh bo qua giua 2 lan chay YOLO duoc TU TINH theo thoi
# gian chay thuc te, sao cho YOLO chi chiem ~1/4 cua 1 loi xu ly.
XEM_VIDEO_PHI_CHAY = 4           # YOLO chiem toi da 1/4 cua mot loi xu ly
XEM_VIDEO_CU_MAX = 0.6            # giay - bo qua toi da bao nhieu khung lien tiep
TEN_GIU_NAM = 8.0                  # giay - giu ten tren khung sau khi quay mat
XEM_VIDEO_MO_RONG_TOI_DA = 1280  # anh gui qua hang toi da rong bao nhieu
DOI_TUONG_CAP_NHAT_MS = 550       # ms - it nhat giua 2 lan gui danh sach the
SU_KIEN_CAP_NHAT_MS = 400         # ms - it nhat giua 2 lan quet su kien
SO_SU_KIEN_1_VONG = 6             # toi da bao nhieu su kien trong 1 vong
BA_VUNG_MOI_N_KHUNG = 5           # cong don thong ke vung moi N khung hinh
MAT_MOI_N_LAN = 3                 # chay nhan dien mat moi bao nhieu vong YOLO
MAT_MOI_N_GIAY = 3.0              # ... va CHI toi da 3 lan/giay (gioi han that)
ANH_THE = 150                     # canh anh crop vuong cua 1 the
XEM_VIDEO_JPEG = 85               # chat luong anh day qua hang doi
XEM_VIDEO_JPEG_THE = 80           # chat luong anh crop cua 1 the
# --- v3.2: khung hinh che do phan tich theo lo (batch) ---
# Pipeline gui khung hinh co overlay ra GUI. Gioi han ~10 fps: du hien thi
# nhung, khong lam cham phan tich (va khong phinh bo nho).
# CHI PHI (do that 2026-10-20, 960x540, yolo11n + ArcFace):
#   encode JPEG q=80 = 2.80 ms/khung.
#   interval=0 (moi khung hinh) -> +2.81 ms/khung (~+5% so voi pipeline).
#   interval=0.1 (10 fps, muc nay) -> +1.07 ms/khung (~+2%).
KHOUNG_HINH_FPS = 10

# --- KEO CUA SO: tach viec RE khoi viec DAT -------------------------------
# Keo cua so thi kich thuoc o hinh doi LIEN TUC. Neu moi lan doi deu
# resize + tao anh thi luong UI bi chan -> cua so "giat". Chi khi dung keo
# (mat RESIZE_CHO_MS) moi ve lai 1 lan cho dung kich thuoc moi nhat.
RESIZE_CHO_MS = 180                # ms - ngung keo bao lau thi ve lai khung hinh
# Kich thuoc TOI DA cua o hinh video. Thuc te o hinh tu co giang theo khung
# cha (letterbox) - xem `_hien_khung_hinh`. 2 so nay chi la TRAN DUNG khi
# chua do duoc khung cha (lan dau mo / cua so bi nho).
XEM_VIDEO_BE_RONG = 1100
XEM_VIDEO_CAO = 620
LABEL_WIDTH = 124                  # be ngan can cua 1 hang cau hinh (cot CUNG)

# --- BO GOC + KHOANG CACH + MAU ---------------------------------------------
# TAT CA lay tu `giao_dien.py` (design system da chot) - khong viet hex tay.
KHOANG_CACH = GD.KHOANG_CACH["nho"]      # 8  - giua 2 hang cau hinh
LE_NGOAI = GD.LE_NGOAI                  # 16 - le ngoai quanh mep cua so


# ---------------------------------------------------------------- VIDEO MAU

# Danh sach video demo CO DINH (ghi cung ten file, KHONG quet o dia moi lan mo).
# Muc 1: ten DAY DU, dung khi can chuoi dai (nhan tien do / tieu de cu so).
# Muc 2: ten NGAN ngan gon, in tren the video mau (anh phai doc nhanh).
# Muc 3: dong mo ta ngan dung 1 dong, in duoi ten tren the.
# Muc 4: ten file that trong thu muc video_mau.
# Muc 5: dung luong de nguoi dung do truoc khi mo.
VIDEO_MAU = [
    ("Video mẫu 1 — Người đi ngang từng người",
     "Người đi ngang",
     "Từng người một đi qua",
     "one-by-one-person-detection.mp4", "3,1 MB"),
    ("Video mẫu 2 — Nhóm người đông",
     "Nhóm người đông",
     "Nhiều người cùng lúc",
     "people-detection.mp4", "5,2 MB"),
    ("Video mẫu 3 — Có xe (kiểm tra không đếm nhầm xe là người)",
     "Có xe",
     "Kiểm tra không đếm nhầm xe",
     "car-detection.mp4", "2,7 MB"),
    ("Video mẫu 4 — Công nhân trong khu vực làm việc",
     "Công nhân làm việc",
     "Người mặc đồ bảo hộ",
     "worker-zone-detection.mp4", "12 MB"),
    ("Video mẫu 5 — Lối đi trong cửa hàng",
     "Lối đi cửa hàng",
     "Khách đi trong cửa hàng",
     "store-aisle-detection.mp4", "8,8 MB"),
    ("Video mẫu 6 — Phòng học",
     "Phòng học",
     "Học sinh trong lớp",
     "classroom.mp4", "12,9 MB"),
    ("Video mẫu 7 — Người đi bộ (có khuôn mặt)",
     "Đi bộ, thấy mặt",
     "Thử nhận diện khuôn mặt",
     "face-demographics-walking.mp4", "6,1 MB"),
    # --- Video da tai them 2026-10-19 (thu muc moi/). Nguon + giay phep:
    # --- video_mau\moi\NGUON_LICENSE.md (Public Domain / CC-BY / CC-BY-SA).
    ("Video mẫu 8 — Người đi lại trên đường",
     "Đi lại",
     "Camera cao, người đi qua lại",
     "moi/nguoi-di-lai.mp4", "8,6 MB"),
    ("Video mẫu 9 — Cửa hàng: nhân viên và khách",
     "Cửa hàng",
     "Quầy thu ngân",
     "moi/cua-hang.mp4", "6,3 MB"),
    ("Video mẫu 10 — Xe cộ giao thông",
     "Xe cộ",
     "Kiểm tra nhận xe",
     "moi/xe-co-giao-thong.mp4", "7,6 MB"),
    ("Video mẫu 11 — Người xếp hàng, đứng chờ",
     "Xếp hàng",
     "Thử cảnh báo đứng lâu",
     "moi/nguoi-dung-cho.mp4", "4,9 MB"),
    ("Video mẫu 12 — Đám đông đông",
     "Đám đông",
     "Thử giới hạn người trong vùng",
     "moi/dam-dong.mp4", "8,3 MB"),
    ("Video mẫu 13 — Trẻ em ngoài sân",
     "Trẻ em",
     "Mặt nhỏ, người xa",
     "moi/tre-em-san-choi.mp4", "10,3 MB"),
]


# ------------------------------------------------------- NGON NGU VI / EN

NGON_NGU_MAC_DINH = "vi"
NGON_NGU_FILE = os.path.join(APP_DIR, "gui_ngon_ngu.json")

# Tieu de cua so chinh. La MA (chuoi mau) de gan phien ban vao sau, tranh
# phai dich lai tung ban ra tu dau moi lan.
TIEU_DE_CUA_SO = "CamAI v{phien_ban} — Phân tích video giám sát"

# Kich thuoc cua so chinh. CUA SO KHONG CO THANH CUON - phai nhin thay
# het moi dung - nen mac dinh lay gap man hinh, roi cat nho theo VUNG LAM
# VIEC THAT (xem `_kich_thuoc_cua_so`) de khong bao gio trinh taskbar.
KICH_THUOC_CUA_SO = (1610, 980)
KICH_THUOC_TOI_DA = (1240, 720)     # be nho nhat con dung duoc
LE_KHUNG = 60                        # de trong giua man hinh khi cat nho
# --- BO CUC 3 VUNG (mau tham chieu: video lon ~76%, danh sach su kien ~24%) ---
# Cot TRAI da thu gon de video duoc rong ra; cot SU KIEN giu nguyen bang chuc
# nang (anh crop that) nhung hep hon. Ty le video/(video+su kien) ~ 76%.
RONG_COT_TRAI = 320                 # cot CAI DAT ben trai (MASTER: 280-320)
RONG_COT_SU_KIEN = 320              # cot DANH SACH SU KIEN ben phai
# --- BE NGAT DONG TRONG COT CAI DAT ---
# Do that 2026-10-19 bang `_kk_agent_b_do_le.py`: khung noi dung ben trong
# CTkScrollableFrame chi rong 268px (300 - le ngoai 16 - thanh cuon ~16).
# v3.4: cot trai rong 320px -> noi dung 288px (320 - le ngoai 16 - cuon ~16).
# Phai tinh wraplength tu be rong THAT con lai, khong dat so tu nghieng.
BE_NOI_DUNG_TRONG_NHOM = 288        # be ngang that cua khung 1 nhom
LE_MO_TA_NHOM = 24                  # le cua dong mo ta (dinh nghia o NhomTinhNang)
LE_GHI_Y = 24                       # le cua dong ghi chu nho (thut lui ve trong)
WRAP_MO_TA_NHOM = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - 8      # 256
WRAP_GHI_Y = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - LE_GHI_Y - 8  # 232
# Chu cua 1 checkbox trong khung cau hinh (tru 24px o check + 6px khe).
# Be trong cua khung cau hinh = 288 - 24 (le cua nhom) = 264px.
WRAP_CHECKBOX = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - 24 - 6 - 2  # 232
# Be rong TOI THIEU cua cot dieu khien trong 1 hang cau hinh.
# CAN THIET: nhieu nut rong 260px nam o cot 0 + `columnspan=2`. Khi hang
# cau hinh chua duoc ve (nhom con nam trong 1 muc lon dang thu gon) thi Tk
# tinh be rong theo kich thuoc TOI THIEU cua tung cot - cot dieu khien
# (khong co widget truc tiep) se bang 0 -> nut bi bop con 124px va CHU BI
# CAT. Dat `minsize` cho cot dieu khien de hang luon rong du 264px.
BE_DIEU_KHIEN_HANG = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - LABEL_WIDTH  # 140
# --- BO CUC 4 MUC LON (cot trai) ---
# Moi MUC LON = 1 the co tieu de HOA + 1 dong mo ta. Le cua dong mo ta + be
# ngang cho phep de chu khong bi cat (noi dung cot trai rong 288px).
LE_MO_TA_NHOM_LON = 12
WRAP_MO_TA_NHOM_LON = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM_LON - 8   # 268
# Anh xem truoc cua 1 the video mau: NHON HON ban 3.4 (128x72 -> 84x47) de
# dai the video mau gon lai (chieu cao 212px -> ~120px).
RONG_THUMB_MOI = 84
CAO_THUMB_MOI = 47
# Be ngang cho 2 dong chu cua the video mau (ten + mo ta) - 1 dong moi chu.
WRAP_THE_VIDEO_MAU = 124
TY_LE_COT_VIDEO = 76                # video chiem 76% be ngang vung hien thi
# Chieu cao o nhhat ky: giu ngan de khoang chay cho khung video (16:9).
CAO_NHAT_KY = 104
# Khoang cach doc giua cac the su kien trong timeline.
KHOANG_SU_KIEN = 2

# O chon "Chạy bằng": CHUOI HIEN THI -> gia tri trong AnalysisConfig.thiet_bi.
# Khoa co dau chinh la noi gui.py dua VAO, nen khong doi.
GIA_TRI_CHE_THIET_BI = {
    "Tự động": "auto",
    "GPU (CUDA)": "cuda",
    "CPU": "cpu",
}


class _RECT(ctypes.Structure):
    """Khung chu nhat cua Windows API (dung cho vung lam viec va kich thuoc)."""
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


# ---------------------------------------------------------------------------
# SUA LOI GIAY KHI KEO CUA SO (do bang profile, khong doan)
# ---------------------------------------------------------------------------
# CustomTkinter 5.2.2: `CTkScrollbar._draw()` ket thuc bang
# `self._canvas.update_idletasks()`. `update_idletasks()` la lenh Tk GOC -
# no xoa HET hang doi ve (idle) cua TOAN BO app, khong phai rieng thanh cuon.
# Khi nguoi dung keo/doi kich thuoc cua so, <Configure> bay len -> canvas
# doi "view" -> goi `yscrollcommand` -> `CTkScrollbar.set()` -> `_draw()` ->
# `update_idletasks()` -> ve lai TOAN BO cay widget (851 widget) -> UI tre
# 600-900 ms o LAN KEO DAU TIEN.
#
# Sua: bo lenh `update_idletasks()` khoi `_draw` cua thanh cuon. Thanh cuon
# van duoc ve lai binh thuong o vong idle tiep theo cua vong lap Tk (Tk tu
# ve canvas khi khong con viec gi), nhung KHONG con ep ve lai ca app.
# => Keo/doi kich thuoc cua so khong con lam tre UI.
def _patch_scrollbar_khong_ep_ve_lai_ca_app() -> None:
    """Bo `update_idletasks()` (lenh Tk goc, ve lai ca app) khoi CTkScrollbar.

    CHI goi 1 lan khi mo app. Khong sua file trong thu vien - chi boc ham
    `_draw` de bo 1 lenh gay tre.
    """
    try:
        from customtkinter.windows.widgets import ctk_scrollbar
    except Exception:                                 # noqa: BLE001
        return
    lop = ctk_scrollbar.CTkScrollbar
    if getattr(lop, "_kk_da_boc_update_idletasks", False):
        return

    def _khong_lam_gi(*_args, **_kwargs) -> None:
        return None

    goc_draw = lop._draw

    def _draw_nhe(self, *args, **kwargs):
        """Ve thanh cuon nhung khong ep Tk ve lai toan bo app."""
        canvas = self._canvas
        goc_flush = canvas.update_idletasks
        canvas.update_idletasks = _khong_lam_gi
        try:
            return goc_draw(self, *args, **kwargs)
        finally:
            canvas.update_idletasks = goc_flush

    lop._draw = _draw_nhe
    lop._kk_da_boc_update_idletasks = True


# BANG ANH XA CHUOI HIEN THI: KHOA = tieng Viet, GIA TRI = tieng Anh.
# CHI doi CHUOI HIEN THI tren man hinh - KHONG doi ten bien / ten ham / logic.
DICH_VI_EN = {
    # --- tieu de cua so ---
    "CamAI — Phân tích video giám sát": "CamAI — Video surveillance analysis",
    "CamAI v{phien_ban} — Phân tích video giám sát":
        "CamAI v{phien_ban} — Video surveillance analysis",

    # --- hang video / video mau ---
    "Video": "Video",
    "Chọn video…": "Choose video…",
    "Mở thư mục clip": "Open clip folder",
    "Lưu kết quả": "Save results to",
    "Chọn…": "Choose…",
    "Tự thêm đuôi: _ket_qua.mp4 và _bao_cao.csv":
        "Suffix added automatically: _ket_qua.mp4 and _bao_cao.csv",

    # --- v3.6: chon nguon (video / anh / camera may / camera IP) ---
    "Nguồn": "Source",
    "Chọn ảnh…": "Choose image…",
    "Chọn camera…": "Choose camera…",
    "Danh sách camera": "Camera list",
    "Chọn ảnh": "Choose image",
    "Chọn camera": "Choose camera",
    "Quét camera": "Scan cameras",
    "Đang quét…": "Scanning…",
    "Huỷ": "Cancel",
    "Đóng": "Close",
    "Địa chỉ camera IP": "IP camera address",
    "Dùng địa chỉ này": "Use this address",
    "Loại nguồn: ": "Source type: ",
    "Ảnh tĩnh": "Still image",
    "Camera máy": "Built-in camera",
    "Camera IP": "IP camera",
    "Chưa chọn": "Not selected",
    "Chọn camera máy trong danh sách bên dưới, hoặc nhập địa chỉ camera IP "
    "phía trên.":
        "Pick a built-in camera from the list below, or type an IP camera "
        "address above.",
    "Chưa quét camera. Bấm nút 'Quét camera' để tìm camera trên máy này.":
        "Not scanned yet. Press 'Scan cameras' to look for cameras on this "
        "machine.",
    "Máy này không có camera nào. Bạn vẫn có thể nhập địa chỉ camera IP "
    "phía trên.":
        "This machine has no camera. You can still type an IP camera address "
        "above.",
    "Địa chỉ camera IP phải bắt đầu bằng rtsp://, rtmp://, http:// hoặc "
    "https://.":
        "IP camera address must start with rtsp://, rtmp://, http:// or "
        "https://.",
    "Đã hủy quét camera.": "Camera scan cancelled.",
    "Camera": "Camera",
    "Số camera tìm thấy: ": "Cameras found: ",
    "Thiếu địa chỉ camera IP": "Missing IP camera address",
    "Hãy nhập địa chỉ camera IP trước khi bấm 'Dùng địa chỉ này'.":
        "Type the IP camera address before pressing 'Use this address'.",
    "Địa chỉ camera IP sai": "Wrong IP camera address",
    "Đã chọn camera máy: ": "Selected built-in camera: ",
    "Đã chọn camera IP: ": "Selected IP camera: ",
    "Nguồn: ": "Source: ",
    "Chỉ vẽ vùng được với nguồn video.":
        "Zones can only be drawn on a video source.",
    "Nguồn camera: dùng luôn khung hình của pipeline để xem, không mở thêm "
    "kết nối camera thứ hai.":
        "Camera source: the pipeline frames are used for preview, no second "
        "camera connection is opened.",
    "Nguồn ảnh tĩnh: hiển thị luôn khung hình đã vẽ khung.":
        "Still image source: the annotated frame is shown directly.",
    "Lỗi phân tích": "Analysis error",
    "Video mẫu dùng thử": "Sample video to try",
    "Dùng video mẫu này": "Use this sample video",
    "Bấm nút để điền đường dẫn, rồi bấm BẮT ĐẦU":
        "Press the button to fill the path, then press START",
    "Video mẫu 1 — Người đi ngang từng người":
        "Sample video 1 — People passing one by one",
    "Video mẫu 2 — Nhóm người đông":
        "Sample video 2 — Crowd of people",
    "Video mẫu 3 — Có xe (kiểm tra không đếm nhầm xe là người)":
        "Sample video 3 — With cars (checks cars are not counted as people)",
    "Video mẫu 4 — Công nhân trong khu vực làm việc":
        "Sample video 4 — Workers in a work area",
    "Video mẫu 5 — Lối đi trong cửa hàng":
        "Sample video 5 — Shop aisle",
    "Video mẫu 6 — Phòng học": "Sample video 6 — Classroom",
    "Video mẫu 7 — Người đi bộ (có khuôn mặt)":
        "Sample video 7 — Walking people (with faces)",

    # --- 8 dong tinh nang ---
    "Phát hiện người": "Person detection",
    "Nhận diện khuôn mặt": "Face recognition",
    "Đếm ra vào": "Count in / out",
    "Canh vùng": "Zone watch",
    "Lưu clip khi có sự kiện": "Save clip on event",
    "Thêm vật thể khác": "Detect extra objects (car, dog, cat)",
    "Nhận người ở xa (chậm hơn)": "Detect distant people (slower)",
    "Cảnh báo": "Alerts",
    "Thông tin mô hình AI": "AI model information",

    # --- mo ta dong tinh nang ---
    "Đếm có bao nhiêu người trong khung hình. Đây là bước đầu tiên, "
    "mọi tính năng khác đều dựa vào nó.":
        "Counts how many people are in the frame. This is the first step, "
        "every other feature depends on it.",
    "Dùng để biết người đó là ai. Cần có ảnh đăng ký trước trong thư mục known_faces.":
        "Used to tell who the person is. Register photos in known_faces first.",
    "Vạch nằm ở giữa khung hình, đếm người đi qua vạch theo hướng vào / ra.":
        "A line sits in the middle of the frame, counting people crossing it in / out.",
    "Khoanh một vùng trong khung hình rồi cảnh báo khi có người vào vùng đó. "
    "Phải vẽ vùng trước bằng nút bên dưới.":
        "Draw a zone in the frame, then get alerted when a person enters it. "
        "Draw the zone first with the button below.",
    "Tự cắt và lưu đoạn video quanh lúc có chuyện vào thư mục clip_da_luu. "
    "Mặc định tắt để cho máy chạy nhẹ.":
        "Automatically cuts and saves the video around the event into the "
        "clip_da_luu folder. Off by default to keep the PC light.",
    "Ngoài người, còn vẽ khung và đếm các vật thể khác. Mặc định tắt.":
        "Besides people, also draws boxes and counts other objects. Off by default.",
    "Khi có sự kiện thì báo ngay trên máy này (chuông / hộp thoại). "
    "Telegram là tuỳ chọn, không có mạng vẫn chạy.":
        "Alerts on this PC right away (sound / pop-up). Telegram is optional, "
        "it still works without internet.",
    "Xem phần mềm đang dùng model nào, nặng bao nhiêu, chạy trên GPU hay CPU.":
        "See which model the software uses, how heavy it is, GPU or CPU.",

    # --- nhom 9: thiet bi chay ---
    "Máy này chạy bằng gì": "What this PC runs on",
    "Máy có GPU thì CamAI tự chạy bằng card màn hình cho nhanh. "
    "Máy không có GPU thì chạy bằng CPU, vẫn chạy được nhưng chậm hơn. "
    "Không rành thì cứ để “Tự động”.":
        "With a GPU, CamAI uses the graphics card for speed. Without one it "
        "runs on CPU - slower but still works. If unsure, keep “Tự động”.",
    "Máy này": "This PC",
    "Máy này CÓ GPU: sẽ chạy bằng card màn hình (nhanh).":
        "This PC HAS a GPU: it will run on the graphics card (fast).",
    "Máy này KHÔNG có GPU: sẽ chạy bằng CPU (chậm hơn nhưng vẫn "
    "chạy được).":
        "This PC has NO GPU: it will run on CPU (slower but still works).",
    "Đang chọn": "Currently set to",
    "Đổi chỗ này ở mục “Phát hiện người”.":
        "Change this under “Phát hiện người”.",

    # --- nhom 1: nguoi ---
    "Ngưỡng tin cậy": "Confidence threshold",
    "0,25 = mặc định. Hạ xuống sẽ bắt được cả người ở xa, "
    "nhưng nhiều khi bắt nhầm.":
        "0.25 = default. Lower it catches people far away, "
        "but also catches false positives.",
    "Mô hình nhận diện": "Detection model",
    "yolo11n.pt": "yolo11n.pt",
    "yolo11n = nhẹ nhất, chạy nhanh nhất. Không rành thì để yolo11n.":
        "yolo11n = lightest and fastest. If unsure, keep yolo11n.",
    "Chạy bằng": "Run on",
    "Đo thật trên máy này: card màn hình nhanh hơn CPU "
    "khoảng 2 lần khi chỉ đếm người, khoảng 2,5 lần khi "
    "bật nhận diện mặt. Máy không có card thì để "
    "“Tự động” là chạy được.":
        "Measured on this PC: the graphics card is about 2x faster than the CPU "
        "when only counting people, about 2.5x when face recognition is on. "
        "On a PC with no graphics card, keep “Automatic” and it still runs.",
    "Tắt ô này thì phần mềm CHỈ đếm người, không nhận "
    "diện ai. Đo thật: nhanh hơn khoảng 2,5 lần lúc "
    "camera đông người, khoảng 2 lần lúc camera vắng. "
    "Đếm người không bị ảnh hưởng.":
        "Turning this off makes the software only count people, not identify "
        "them. Measured: about 2.5x faster on a busy camera, about 2x on an "
        "empty one. People counting is not affected.",
    "Đo thật trên video đông người (10 người/khung): "
    "1 -> 5,2 khung/giây · 2 -> 7,6 · 5 -> 12,5 · 10 -> 23,4. "
    "Đếm người KHÔNG đổi, chỉ giảm số lần quét mặt. "
    "Máy chấm công (người đứng ở cửa) để 5 là đủ. "
    "Giám sát người đi qua nhanh thì để 1–2. "
    "Camera vắng người thì nhận được nhiều hơn các số trên.":
        "Measured on a busy video (10 people per frame): 1 -> 5.2 fps · "
        "2 -> 7.6 · 5 -> 12.5 · 10 -> 23.4. People counting does not change, "
        "only how often faces are scanned. For an attendance clock (people "
        "stand at the door) 5 is enough. For watching people pass by fast, "
        "keep 1–2. An empty camera does better than these numbers.",
    "Hiển thị trên video": "Show on video",
    "Vẽ khung người": "Draw person boxes",
    "Vẽ nhãn tên": "Draw name labels",
    "Làm mờ nền, giữ rõ chỗ có người":
        "Blur the background, keep people sharp",

    # --- nhom 2: mat ---
    "Ước lượng tuổi và giới tính": "Age and gender estimate",
    "Bật (luôn bật, phần mềm không cho tắt)":
        "On (always on, the software cannot turn it off)",
    "Chỉ là ước lượng, không chính xác tuyệt đối. "
    "cam_ai_core không có tham số tắt tính năng này.":
        "It is only an estimate, not exact. "
        "cam_ai_core has no switch to turn this off.",
    "Ngưỡng giống mặt": "Face match threshold",
    "Cao hơn = dễ nhận nhầm người khác. "
    "Thấp hơn = dễ không nhận ra người quen. "
    "Mặc định 0,40.":
        "Higher = easier to mix up other people. "
        "Lower = easier to miss people you know. Default 0.40.",
    "Bỏ qua mặt nhỏ hơn": "Skip faces smaller than",
    "px": "px",
    "Mặt nhỏ hơn cỡ này thì bỏ qua, không hỏi ai. Để 0 = không bỏ.":
        "Faces smaller than this are skipped without asking. 0 = do not skip.",
    "Quét mặt mỗi": "Scan faces every",
    "khung hình": "frames",
    "1 = chính xác nhất nhưng chậm hơn. 3 hoặc 5 = nhanh hơn.":
        "1 = most accurate but slower. 3 or 5 = faster.",
    "Thư mục ảnh đã học": "Learned photos folder",
    "Đọc lại danh sách người đã học": "Reload the learned people list",
    "Cấu trúc: known_faces / <Tên> / *.jpg — mỗi người một thư mục con.":
        "Layout: known_faces / <Name> / *.jpg — one sub-folder per person.",

    # --- nhom 4: vung ---
    "File vùng (.txt)": "Zone file (.txt)",
    "Vẽ vùng trên video này": "Draw the zone on this video",
    "Mở cửa sổ riêng: xem video, kéo chuột khoanh vùng, "
    "lưu lại thành file .txt.":
        "Opens a separate window: watch the video, drag the mouse to mark the "
        "zone, save it as a .txt file.",
    "Chỉ cần một phần chân vào vùng là bị báo":
        "Alert as soon as any part of the person touches the zone",
    "Tắt = chặt: cả người phải nằm hẳn trong vùng mới báo. "
    "Bật = nhạy: thân chạm vùng là báo ngay.":
        "Off = strict: the whole person must be inside the zone. "
        "On = sensitive: touching the zone alerts immediately.",
    "Cảnh báo khi vượt quá": "Alert when more than",
    "người": "people",
    "Nhập 0 để tắt cảnh báo này.": "Enter 0 to turn this alert off.",
    "Cảnh báo khi người đứng lâu": "Alert when someone stands too long",
    "giây": "seconds",

    # --- nhom 5: clip ---
    "Tổng thời lượng 1 clip": "Total length of 1 clip",
    "Ghi clip cả khi không bật canh vùng":
        "Record clips even when zone watch is off",
    "Mặc định chỉ ghi clip khi có chuyện trong vùng canh. "
    "Bật ô này thì thấy người là ghi luôn.":
        "By default clips are only saved when something happens in the watched "
        "zone. Turn this on to record whenever a person appears.",
    "Chia đôi: một nửa trước sự kiện, một nửa sau sự kiện.":
        "Split in half: one half before the event, one half after.",

    # --- nhom 6: vat the ---
    "Danh sách lớp cần nhận": "Classes to detect",
    "để trống = nhóm mặc định": "empty = default group",
    "Gõ lớp cần nhận, cách nhau bằng dấu phẩy. "
    "Nhận được cả tiếng Việt: ô tô, xe máy, chó, mèo… "
    "(để trống = dùng nhóm lớp mặc định, gõ all = mọi lớp trừ người).":
        "Type the classes to detect, separated by commas. "
        "Vietnamese works too: car, motorcycle, dog, cat… "
        "(leave empty = use the default class group, type all = every class "
        "except people).",
    "Ví dụ: ô tô, xe máy, chó, mèo hoặc "
    "car, motorcycle, dog, cat — cách nhau bằng dấu phẩy. "
    "Để trống = nhóm lớp phổ biến. Gõ all = mọi lớp trừ người.":
        "Example: car, motorcycle, dog, cat or "
        "ô tô, xe máy, chó, mèo — separated by commas. "
        "Leave empty = common classes. Type all = every class except people.",
    "Tốc độ: gần như không chậm đi. Đo thật ngày 19/10/2026 trên "
    "video nhiều xe, xem trực tiếp chậm hơn khoảng 3–9%, và "
    "chậm hơn nhiều hơn khi bật lớp `all`.":
        "Speed: barely slower. Measured on 19/10/2026 with a car video, "
        "live view is about 3–9% slower, and slower still with `all`.",
    "Lý do: YOLO vốn đã nhận sẵn toàn bộ 80 lớp trong 1 lượt, "
    "nên bật thêm chỉ tốn công vẽ thêm khung, không phải chạy "
    "model thêm lần nữa.":
        "Why: YOLO already detects all 80 classes in one pass, so enabling "
        "this only costs drawing extra boxes, not another model run.",
    "Lưu ý: khung vật thể vẽ màu cam và KHÔNG tính vào số "
    "người, số vào/ra, cảnh báo vùng.":
        "Note: object boxes are drawn in orange and are NOT counted as "
        "people, in/out counts, or zone alerts.",
    "Vật thể: {n}": "Objects: {n}",
    "> [vật thể] Đang nhận {n} lớp: {ds}":
        "> [objects] Detecting {n} classes: {ds}",
    "> [vật thể] Bỏ qua lớp không có: ": "> [objects] Skipped unknown classes: ",
    "> [vật thể] Các lớp đang nhận: ": "> [objects] Classes being detected: ",
    "> [vật thể] Không còn lớp nào hợp lệ, tắt nhận vật thể.":
        "> [objects] No valid class left, object detection is off.",

    # --- v3.0: nhom doc bien so ---
    "Đọc biển số xe": "Read licence plates",
    "Đọc chữ trên biển số xe Việt Nam bằng RapidOCR — chạy 100% "
    "trên máy này, không gửi ảnh ra ngoài.":
        "Reads Vietnamese licence plates with RapidOCR — runs 100% on this PC, "
        "no images are sent anywhere.",
    "Thư mục lưu ảnh": "Photo folder",
    "Vùng cần quét": "Area to scan",
    "để trống = tự tìm trong khung": "empty = search the whole frame",
    "tự tìm": "auto",
    "mặc định": "default",
    "Nghỉ giữa 2 lần": "Pause between saves",
    "Đọc bằng RapidOCR chạy 100% trên máy này, không gửi ảnh ra ngoài.":
        "RapidOCR runs 100% on this PC, no images are sent anywhere.",
    "Tốc độ: đọc biển số chạy ở luồng nền nên không làm khựng video. "
    "Mỗi lần quét tốn 9–15 ms, khung hình chậm nhất 62 ms "
    "(đo thật trên máy này ngày 19/10/2026). Lúc bật lần đầu máy phải nạp "
    "model nên khựng khoảng 1–2 giây.":
        "Speed: plate reading runs on a background thread, so it never freezes "
        "the video. Each scan takes 9–15 ms; the slowest frame was 62 ms "
        "(measured on this PC on 19/10/2026). The first time you enable it "
        "the model has to load, which pauses things for about 1–2 seconds.",
    "Cùng một biển số chỉ được lưu ảnh 1 lần trong khoảng nghỉ ở trên.":
        "The same plate is only saved once per pause set above.",
    "Vùng cần quét: gõ 4 số theo mẫu x1,y1,x2,y2. Gõ 0,1 – 1,0 là tọa độ "
    "tương đối, số lớn hơn 1 là tọa độ pixel. Để trống = phần mềm tự tìm "
    "trong khung hình.":
        "Area to scan: type 4 numbers as x1,y1,x2,y2. Values from 0,1 – 1,0 "
        "are relative, anything above 1 is in pixels. Leave it empty and the "
        "software searches the whole frame.",
    "Chọn thư mục lưu ảnh biển số": "Choose the licence plate photo folder",

    # --- v3.0: nhom tach o + canh bao ---
    "Máy sẽ dò cả khung hình nguyên vẹn lẫn các ô nhỏ, rồi ghép lại — "
    "nên người ở gần không bị mất, người ở xa thì dễ nhận hơn.":
        "The app scans both the full frame and the small boxes, then merges "
        "them — so close people are not lost and distant ones are easier to "
        "detect.",
    "Đổi lại là chậm hơn khoảng 5 lần. Đo thật ngày 19/10/2026: "
    "video đám đông nhận đúng hơn gấp đôi, nhưng xem sẽ giật hơn.":
        "The trade-off is about 5x slower. Measured on 19/10/2026: crowd "
        "videos are detected more than twice as well, but playback is "
        "choppier.",
    "Bỏ chọn ô này thì cảnh báo sẽ KÊU CHUÔNG và MỞ HỘP "
    "THOẠI ngay trên máy này. Telegram cần có token trong "
    "file canh_bao.ini.":
        "Uncheck this box and alerts will RING and OPEN A DIALOG on this PC. "
        "Telegram needs a token in canh_bao.ini.",

    # --- v3.0: nhom tu chup anh ---
    "Tự chụp ảnh khi có sự kiện": "Take a photo on each event",
    "Khi có người đông, vượt vùng hoặc thấy người quen thì chụp lại "
    "khung hình lưu thành ảnh. Mặc định tắt.":
        "When a crowd, a zone breach or a known person appears, the frame is "
        "saved as a photo. Off by default.",
    "Chụp khi có người đông, vượt vùng canh, thấy người quen hoặc có người "
    "đứng lâu.":
        "Takes a photo on a crowd, a zone breach, a known person or someone "
        "loitering.",
    "Mỗi loại sự kiện chỉ chụp 1 lần trong khoảng nghỉ ở trên.":
        "Each kind of event is only photographed once per pause set above.",
    "Ảnh lưu ngay trên máy này, kèm file _bang_ke_chup.csv ghi lại lúc chụp.":
        "Photos are saved on this PC, with a _bang_ke_chup.csv log of when each "
        "one was taken.",
    "Chọn thư mục lưu ảnh sự kiện": "Choose the event photo folder",

    # --- nhom 7: canh bao ---
    "Cách báo": "How to alert",
    "Phát chuong trên máy": "Play a sound on this PC",
    "Mở hộp thoại": "Show a pop-up",
    "Gửi tin Telegram": "Send a Telegram message",
    "Thử gửi 1 cảnh báo": "Send a test alert",
    "Telegram cần có token trong file canh_bao.ini. "
    "Chưa có thì chỉ chuông / hộp thoại trên máy này hoạt động.":
        "Telegram needs a token in canh_bao.ini. Without it only the sound / "
        "pop-up on this PC works.",

    # --- nhom 8: model ---
    "Xem thông tin mô hình AI đang dùng": "See the AI model information in use",

    # --- dieu khien / tien trinh / so lieu ---
    # Icon nut lay tu font Windows (Segoe MDL2 Assets) - nen chuoi nut
    # chi con CHU, khong con ky tu to hop.
    "BẮT ĐẦU": "START",
    "DỪNG": "STOP",
    "Tiến trình": "Progress",
    "Người": "People",
    "Mặt": "Faces",
    "Vào": "In",
    "Ra": "Out",
    "Nhật ký (cuối {so_dong} dòng)": "Log (last {so_dong} lines)",
    f"Nhật ký (cuối {MAX_LOG_LINES} dòng)": f"Log (last {MAX_LOG_LINES} lines)",
    "Mở video kết quả": "Open result video",
    "Xem báo cáo": "View report",

    # --- chu trang thai ben canh thanh tien trinh ---
    "Chưa chạy": "Not run yet",
    "Khung hình {frame}/{tong} · {phan_tram}%":
        "Frame {frame}/{tong} · {phan_tram}%",
    "Khung hình {frame}": "Frame {frame}",
    "Lỗi — xem nhật ký": "Error — see the log",
    "Đã dừng giữa chừng": "Stopped part way",
    "Xong": "Done",

    # --- nhan nut doi ngon ngu ---
    "English": "English",
    "Tiếng Việt": "Tiếng Việt",

    # --- thong bao / loi ---
    "Chọn thư mục lưu kết quả": "Choose the results folder",
    "Thư mục ảnh người quen": "Folder of known people photos",
    "Chọn file vùng": "Choose the zone file",
    "Lỗi": "Error",
    "Không mở được thư mục clip:\n": "Cannot open the clip folder:\n",
    "Chưa có kết quả": "No result yet",
    "Hãy bấm BẮT ĐẦU chạy trước đã.": "Press START and run it first.",
    "Chưa có báo cáo": "No report yet",
    "Chưa có file báo cáo (CSV).\n": "There is no report file (CSV).\n",
    "Hãy bấm BẮT ĐẦU chạy xong video đã.":
        "Press START and let the video finish first.",
    "Không mở được báo cáo:\n": "Cannot open the report:\n",
    "Thiếu video": "No video chosen",
    "Hãy chọn video trước khi vẽ vùng.":
        "Choose a video before drawing a zone.",
    "Không mở được cửa sổ vẽ vùng:\n":
        "Cannot open the zone drawing window:\n",
    "Chưa bật cảnh báo": "Alerts are not on",
    "Hãy bật ô 'Cảnh báo' trước đã, rồi bấm thử lại.":
        "Turn on the 'Alerts' box first, then try again.",
    "Thiếu phát hiện người": "Person detection is off",
    "Cần bật 'Phát hiện người' thì phần mềm mới biết đâu là người.":
        "Turn on 'Person detection' so the software knows what a person is.",
    "Đang chạy": "Running",
    "Đang xử lý video. Dừng và thoát luôn?":
        "The video is being processed. Stop it and quit?",
    "Chưa chọn video.": "No video chosen yet.",
    "Không tìm thấy video:\n": "Video not found:\n",
    "Ngưỡng tin cậy phải nằm trong khoảng 0,05 – 1,0.":
        "The confidence threshold must be between 0.05 and 1.0.",
    "Thư mục lưu kết quả không có trên máy:\n":
        "The results folder does not exist on this PC:\n",
    " phải là số nguyên.": " must be a whole number.",
    " phải là số.": " must be a number.",
    "Không tìm thấy video mẫu: ": "Sample video not found: ",
    "Đã chọn video mẫu: ": "Sample video chosen: ",
    "Bấm BẮT ĐẦU để chạy thử.": "Press START to try it.",

    # --- khung xem video truc tiep ---
    "Xem video": "Live video",
    "Xem video khi chạy": "Show live video while running",
    "Chưa chạy video": "No video running yet",
    "Tạm dừng": "Pause",
    "Tiếp tục": "Resume",
    "Xem trực tiếp đã tạm dừng": "Live view paused",
    "Xem trực tiếp đã chạy tiếp": "Live view resumed",
    "> Bật xem video trực tiếp (tốn thêm một ít máy).":
        "> Live view turned on (uses a bit more PC).",
    "> Tắt xem video trực tiếp.": "> Live view turned off.",
    "> Không bật được xem video trực tiếp: ":
        "> Live view could not start: ",
    "> Xem video trực tiếp đã kết thúc.": "> Live view finished.",

    # --- dong nhat ky ---
    "BẮT ĐẦU xử lý: ": "START processing: ",
    "Đã yêu cầu DỪNG, đang chờ khung hình hiện tại...":
        "STOP requested, waiting for the current frame...",
    "> Đọc lại danh sách người đã học từ: ":
        "> Reloading the learned people list from: ",
    "> Đã học được: ": "> Learned: ",
    "không có ai": "nobody",
    "Không đọc được danh sách người: ":
        "Cannot read the learned people list: ",
    "[canh bao] không import được: ": "[alerts] cannot import: ",
    "[canh bao] không tạo được: ": "[alerts] cannot create: ",
    "[canh bao] không gửi được: ": "[alerts] cannot send: ",
    "Lỗi không mong đợi: ": "Unexpected error: ",
    "[LỖI] ": "[ERROR] ",
    "Kết quả: ": "Result: ",
    "Báo cáo: ": "Report: ",
    "Nhận diện: ": "Recognised: ",
    "> Xem báo cáo: ": "> Open report: ",
    "> Mở cửa sổ vẽ vùng: ": "> Open the zone drawing window: ",
    "> Đã yêu cầu gửi 1 cảnh báo thử nghiệm.":
        "> A test alert has been requested.",
    "Có ": "There were ",
    " lần vượt quá số người cho phép.":
        " times over the allowed number of people.",

    # --- cua so con: thong tin mo hinh ---
    "Thông tin mô hình AI đang dùng": "AI model information in use",
    "CamAI đang chạy 4 mô hình AI sau đây:":
        "CamAI is running these 4 AI models:",
    "Tính năng": "Feature",
    "Model kỹ thuật": "Technical model",
    "Thư viện": "Library",
    "Dung lượng đo trên máy · trạng thái":
        "Size measured on this PC · status",
    "Vai trò từng mô hình": "Role of each model",
    "Thông số kỹ thuật": "Technical specifications",
    "Phiên bản và tốc độ máy": "Versions and PC speed",
    "Ngưỡng khớp mặt (ArcFace): ": "Face match threshold (ArcFace): ",
    "Thư mục ảnh đã học: ": "Learned photos folder: ",
    " người trong mẫu)": " people in the sample)",
    "CẢNH BÁO: ": "WARNING: ",
    "chưa cài đặt": "not installed",
    "có — chạy bằng card màn hình NVIDIA (nhanh)":
        "yes — runs on the NVIDIA graphics card (fast)",
    "không — chạy bằng CPU (chậm hơn nhưng vẫn chạy được)":
        "no — runs on the CPU (slower but still works)",
    "Chạy trên GPU (CUDA): ": "Running on GPU (CUDA): ",
    "CẢNH BÁO: thiếu file model: ": "WARNING: missing model file: ",
    "Đã kiểm tra trên đĩa: đủ cả 4/4 file model đều có sẵn.":
        "Checked on disk: all 4/4 model files are present.",
    "Không đọc được thông tin mô hình: ":
        "Cannot read the model information: ",

    # --- chu lay tu model_info.py (khong sua file do, chi dich o giao dien) ---
    "Tìm khuôn mặt": "Face detection",
    "Nhận diện người quen": "Recognise known people",
    "Tìm trong khung hình có bao nhiêu NGƯỜI (và cả xe, chó, mèo…). "
    "Đây là bước đầu tiên, mọi thứ khác đều dựa vào kết quả bước này.":
        "Finds how many PEOPLE are in the frame (also cars, dogs, cats…). "
        "This is the first step, everything else builds on this result.",
    "Khoanh vùng khuôn mặt của người đã tìm thấy. "
    "Nếu tắt model này thì không nhận diện được ai.":
        "Marks the faces of the people that were found. "
        "Without this model nobody can be recognised.",
    'Đây là model "nhận diện": so khuôn mặt người lạ với ảnh đã lưu, '
    'đúng thì gọi tên, sai thì ghi "Người lạ". '
    'Đây là model quan trọng nhất với chủ sở hữu.':
        'This is the "recognition" model: it compares a stranger\'s face with '
        'the saved photos, calls the name when it matches, otherwise writes '
        '"Stranger". This is the model the owner cares about most.',
    "Ước lượng khoảng tuổi và giới tính của khuôn mặt. "
    "Chỉ là ƯỚC LƯỢNG, không chính xác tuyệt đối.":
        "Estimates the age range and gender of the face. "
        "It is only an ESTIMATE, never exact.",
    "sẵn sàng (đủ dùng chạy được)": "ready (installed and usable)",
    "thiếu file (chưa đủ dùng chạy)": "file missing (not usable yet)",
    "0,40 là mức cân bằng. Cao hơn = dễ nhận nhầm, thấp hơn = dễ không nhận ra.":
        "0.40 is the balanced value. Higher = easier to mix up, "
        "lower = easier to miss.",
    "2 người đã học sẵn trong thư mục known_faces là DỮ LIỆU GIẢ LẬP "
    "(không phải người thật). Khi dùng thật, hãy xoá chúng trước khi thêm "
    "người thật vào.":
        "The 2 people already learned in the known_faces folder are FAKE DATA "
        "(not real people). For real use, delete them before adding real people.",

    # --- v2.4: khung video + panel doi tuong + so lieu day du ---
    "Xem video": "Live view",
    "Tạm dừng": "Pause",
    "Tiếp tục": "Resume",
    "Chưa chạy video": "No video running yet",
    "Xem video khi chạy": "Show video while running",
    "Xem video đang dừng": "Live view is stopped",
    "Đối tượng phát hiện": "Detected objects",
    "Chỉ người quen": "Known people only",
    "Tất cả": "All",
    "Người": "People",
    "Vật thể khác": "Other objects",
    "Người quen": "Known people",
    "Chưa có đối tượng nào": "No object detected yet",
    "Thông tin": "Info",
    "Số liệu": "Statistics",
    "Người quen": "Known",
    "Trong vùng": "In zone",
    "Vi phạm": "Alerts",
    "Đứng lâu": "Loitering",
    "Tuổi TB": "Avg age",
    "Nam": "Male",
    "Nữ": "Female",
    "Nhật ký": "Log",
    "Cấu hình": "Settings",
    "Lưu kết quả": "Save results to",
    "Mở thư mục clip": "Open clip folder",
    "Video mẫu dùng thử": "Sample video to try",
    "Dùng video mẫu này": "Use this sample video",
    "Chọn video…": "Choose video…",
    "Chọn…": "Choose…",
    "Tự thêm đuôi: _ket_qua.mp4 và _bao_cao.csv":
        "Suffix added automatically: _ket_qua.mp4 and _bao_cao.csv",
    "Đang chạy · khung hình {frame}/{tong} · {phan_tram}%":
        "Running · frame {frame}/{tong} · {phan_tram}%",
    "Mở kết quả": "Open result",
    "Xem báo cáo": "Open report",
    "Nhận diện tên trên ảnh": "Read names on the crops",
    "Tên lấy từ bộ nhận diện mặt đang chạy song song. Tắt đi thì nhẹ máy hơn.":
        "Names come from the face engine running alongside. Turn it off to "
        "make the PC lighter.",

    # --- v2.5: the video mau co ANH XEM TRUOC THAT ---
    "Video mẫu\ndùng thử": "Sample\nvideos",
    "Người đi ngang": "People passing",
    "Từng người một đi qua": "One person at a time",
    "Nhóm người đông": "Crowd of people",
    "Nhiều người cùng lúc": "Many people at once",
    "Có xe": "With cars",
    "Kiểm tra không đếm nhầm xe": "Checks cars are not counted",
    "Công nhân làm việc": "Workers on site",
    "Người mặc đồ bảo hộ": "People in safety gear",
    "Lối đi cửa hàng": "Shop aisle",
    "Khách đi trong cửa hàng": "Shoppers walking through",
    "Phòng học": "Classroom",
    "Học sinh trong lớp": "Students in class",
    "Đi bộ, thấy mặt": "Walking, faces visible",
    "Thử nhận diện khuôn mặt": "Try face recognition",
    "Chưa có video mẫu nào": "No sample video available",
    "không đọc được": "cannot read",
    "Ẩn": "Hide",
    "Hiện": "Show",

    # --- v2.5: huyen trang thai chi noi ngan, chi tiet o nhan ben canh ---
    "Chưa chạy": "Not running",
    "Đang chạy": "Running",
    "Tạm dừng": "Paused",
    "Lỗi": "Error",
    "Đã dừng": "Stopped",
    "Xong": "Done",

    # --- v3.3: 2 o xem video + dang ky nguoi quen + doc bien so thu + ve vung ---
    "Xem trực tiếp": "Live view",
    "Xem khung hình kết quả": "Show result frames",
    "Đang bật 'Xem trực tiếp' nên 'Xem khung hình kết quả' tạm không dùng "
    "(tránh 2 nguồn hình đè nhau).":
        "Live view is on, so 'Show result frames' is not used for now "
        "(avoids 2 image sources overlapping).",
    "> Bật xem khung hình kết quả.": "> Result frames turned on.",
    "> Tắt xem khung hình kết quả.": "> Result frames turned off.",

    # --- dang ky nguoi quen ---
    "Đăng ký người quen…": "Register a known person…",
    "Đăng ký người quen": "Register a known person",
    "Chọn ảnh hoặc video có người quen":
        "Choose a photo or video containing the person",
    "Nhập tên người quen (tối đa 50 ký tự):":
        "Enter the person's name (50 characters max):",
    "Chưa nhập tên": "No name entered",
    "Hãy nhập tên người quen.": "Please enter the person's name.",
    "Tên quá dài": "Name too long",
    "Tên người quen không được quá 50 ký tự.":
        "The person's name must be 50 characters or fewer.",
    "Tên không hợp lệ": "Invalid name",
    "Tên người quen không được chứa các ký tự cấm của tên thư mục.":
        "The person's name must not contain characters that are not allowed "
        "in a folder name.",
    "Thư mục đã tồn tại": "Folder already exists",
    "Thư mục đã tồn tại: ": "Folder already exists: ",
    "Đăng ký lại sẽ XOÁ các ảnh cũ trong thư mục đó. Có tiếp tục không?":
        "Registering again will DELETE the old photos in that folder. "
        "Continue?",
    "> Đăng ký người quen '": "> Registering the known person '",
    "' từ: ": "' from: ",
    "> Tìm thấy ": "> Found ",
    " khuôn mặt trong ảnh/video đã chọn.":
        " faces in the chosen photo/video.",
    "Không tìm thấy khuôn mặt nào trong ảnh/video đã chọn. "
    "Thử video rõ mặt hơn, hoặc ảnh chụp gần hơn.":
        "No face found in the chosen photo/video. "
        "Try a video with clearer faces, or a closer photo.",
    "Không gom được nhóm người nào.": "Could not group any person.",
    "> Đã lưu ảnh cho người quen: ": "> Saved photos for the known person: ",
    "> Số ảnh đã lưu: ": "> Number of photos saved: ",
    " | thư mục: ": " | folder: ",
    "Lỗi khi đăng ký người quen: ": "Error when registering the known person: ",
    "> Không mở được hộp thoại nhập tên.":
        "> Could not open the name input dialog.",
    "Chọn 1 ảnh hoặc 1 video có người quen, phần mềm tự tìm mặt và lưu vào "
    "thư mục của người đó.":
        "Pick 1 photo or 1 video with the person - the software finds the face "
        "and saves it in that person's folder.",

    # --- doc bien so thu ---
    "Đọc biển số thử…": "Test plate reading…",
    "Chọn ảnh có biển số": "Choose a photo with a licence plate",
    "> Thử đọc biển số trong ảnh: ": "> Testing plate reading in the photo: ",
    "Biển số: ": "Plate: ",
    " | tin cậy ": " | confidence ",
    " | số hàng: ": " | rows: ",
    " | vùng: ": " | region: ",
    "Ảnh biển số đã lưu: ": "Saved plate photo: ",
    "Không đọc được biển số trong ảnh này.":
        "Could not read a licence plate in this photo.",
    "Không nạp được engine đọc biển số.":
        "Could not load the plate reading engine.",
    "Không đọc được ảnh: ": "Could not read the photo: ",
    "Lỗi khi thử đọc biển số: ": "Error while testing plate reading: ",
    "Thử trên 1 ảnh. Khi chạy video, biển số phải được xác nhận qua 2 khung "
    "hình liên tiếp mới ghi nhận - nên kết quả thử 1 ảnh chưa giống hệt lúc "
    "chạy video.":
        "This is a test on 1 photo. When running a video, a plate is only "
        "accepted after it is confirmed on 2 consecutive frames - so a "
        "1-photo test is not exactly the same as a video run.",

    # --- ve vung ngay trong cua so ---
    "Vẽ vùng ngay tại đây": "Draw the zone right here",
    "> Đang lấy khung hình để vẽ vùng: ": "> Getting a frame to draw the zone: ",
    "Không mở được video: ": "Could not open the video: ",
    "Không đọc được khung hình nào từ video.":
        "Could not read any frame from the video.",
    "Lỗi khi lấy khung hình: ": "Error while getting the frame: ",
    "Chưa có module ve_vung_gui, hãy dùng nút 'Vẽ vùng trên video này'.":
        "No ve_vung_gui module yet - use the "
        "'Draw the zone on this video' button.",
    "> Đã huỷ vẽ vùng.": "> Zone drawing cancelled.",
    "Lỗi khi vẽ vùng: ": "Error while drawing the zone: ",
    "Lỗi khi lưu file vùng: ": "Error while saving the zone file: ",
    "Đã lưu vùng: ": "Saved zone: ",
    "Vùng (tương đối): ": "Zone (relative): ",
    "Vẽ ngay trong cửa sổ này: kéo chuột khoanh vùng rồi bấm Lưu. "
    "Cần chọn video trước.":
        "Draw it right in this window: drag the mouse over the zone then press "
        "Save. Pick a video first.",

    # --- v3.4 (thiet ke lai): nhan khu vuc + don vi + ghi chu checkbox ---
    "NGUỒN": "SOURCE",
    "PHÂN TÍCH": "ANALYSIS",

    # --- v3.5: 4 MUC LON cua cot trai + mo ta 1 dong ---
    "BIỂN SỐ & ẢNH": "PLATES & PHOTOS",
    "CẢNH BÁO & MÔ HÌNH": "ALERTS & MODEL",
    "Chọn video cần phân tích và nơi lưu kết quả":
        "Pick the video to analyse and where to save the result",
    "Bật các bước nhận diện: người, mặt, ra vào":
        "Turn on the detection steps: people, faces, in / out",
    "Đọc biển số xe và tự chụp ảnh sự kiện":
        "Read vehicle plates and take event photos",
    "Chuông/hộp thoại khi có người lạ, và thông tin AI":
        "Sound / pop-up when someone appears, plus AI model info",
    "Bỏ qua mặt nhỏ hơn (px)": "Skip faces smaller than (px)",
    "Quét mặt mỗi (khung hình)": "Scan faces every (frames)",
    "Cảnh báo khi vượt quá (người)": "Alert when over (people)",
    "Cảnh báo khi người đứng lâu (giây)": "Alert when standing still (seconds)",
    "Tổng thời lượng 1 clip (giây)": "Total length of 1 clip (seconds)",
    "Nghỉ giữa 2 lần (giây)": "Pause between 2 times (seconds)",
    "Gộp tin (giây)": "Group messages (seconds)",
    "Giới hạn (tin/phút)": "Limit (messages/minute)",
    "Vẽ khung quanh mỗi người trong khung hình.":
        "Draw a box around every person in the frame.",
    "Ghi tên lên khung nếu nhận diện được người quen.":
        "Write the name on the box when a known person is recognised.",
    "Làm mờ nền để dễ nhìn thấy người.":
        "Blur the background so people stand out.",
    "Xem video ngay khi đang phân tích.":
        "Watch the video live while the analysis runs.",
    "Xem khung hình đã vẽ khung sau khi phân tích.":
        "See the drawn boxes on the frames after the analysis.",
    "Đường dẫn video đầy đủ": "Full video path",
    "Thư mục lưu kết quả đầy đủ": "Full results folder",
}

# KHOA DUOC PHEP "DICH TIEU DOAN" (chuoi co noi dung bien nhau phia sau).
# Toan bo khoa >= 4 ky tu deu duoc phep; them cac khoa ngan can dung ro.
_KHOA_NGAN_DICH_TIEU = frozenset({"Có "})
# Sap xep gia tri - moi lan, do dai lon truoc: khoa dai duoc so khop truoc.
_KHOA_DICH_TIEU = tuple(
    k for k in sorted(DICH_VI_EN, key=len, reverse=True)
    if len(k) >= 4 or k in _KHOA_NGAN_DICH_TIEU
)

# Chu trang thai ben canh thanh tien trinh. Ten trong dict la MA, gia tri la
# chuoi tieng Viet co dau (khoa dich) - KHONG ghep chuoi o cho khac.
TRANG_THAI_TIEN_TRINH = {
    "chua_chay": "Chưa chạy",
    "chay": "Đang chạy · khung hình {frame}/{tong} · {phan_tram}%",
    "khung_hinh_day_du": "Khung hình {frame}/{tong} · {phan_tram}%",
    "khung_hinh": "Khung hình {frame}",
    "tam_dung": "Tạm dừng",
    "loi": "Lỗi — xem nhật ký",
    "dung_giua": "Đã dừng giữa chừng",
    "xong": "Xong",
}

# CHU NGAN cho HUYEN TRANG THAI. Huyện chi noi "Đang chạy" / "Xong" ...
# CHI TIET khung hinh (2/250 · 1%) do NHAN TIEN TRINH ben canh lo. Truoc day
# ca hai cung hien mot chuoi dai giong nhau -> bi DINH VAO NHAU o goc tren
# phai khi cua so nho lai.
NHAN_TRANG_THAI_NGAN = {
    "chua_chay": "Chưa chạy",
    "chay": "Đang chạy",
    "khung_hinh_day_du": "Đang chạy",
    "khung_hinh": "Đang chạy",
    "tam_dung": "Tạm dừng",
    "loi": "Lỗi",
    "dung_giua": "Đã dừng",
    "xong": "Xong",
}

# BIEU TU trang thai (ky tu HINH HOC cua font WINDOWS, KHONG phai emoji).
# Font: `Segoe MDL2 Assets` (xem `giao_dien.bieu_tuong`).
# Chi doc bang mat, khong can dich.
BIEU_TU_TRANG_THAI = {
    "chua_chay": bieu_tượng("thong_tin"),      # Info - chua chay
    "chay": bieu_tượng("phat"),                # Play - dang chay
    "khung_hinh_day_du": bieu_tượng("phat"),
    "khung_hinh": bieu_tượng("phat"),
    "tam_dung": bieu_tượng("tam_dung"),        # Pause - tam dung
    "loi": bieu_tượng("loi"),                  # Error - loi
    "dung_giua": bieu_tượng("dung"),           # Stop - dung giua chung
    "xong": bieu_tượng("tick"),                # CheckMark - xong
}


def dich(chuoi: str, ngon_ngu: str = NGON_NGU_MAC_DINH) -> str:
    """Doi 1 CHUOI HIEN THI tieng Viet sang tieng Anh (neu dang o che do EN).

    - khop trung het chuoi -> tra ve dung doan do.
    - khop tien doan (doan co dinh + phan con lai co bien/so) -> dich doan
      dau, giu nguyen phan con lai.
    - khong co trong bang -> tra ve nguyen chuoi (an toan, khong loi).
    """
    if ngon_ngu != "en" or not chuoi:
        return chuoi
    if chuoi in DICH_VI_EN:
        return DICH_VI_EN[chuoi]
    for khoa in _KHOA_DICH_TIEU:
        if chuoi.startswith(khoa):
            return DICH_VI_EN[khoa] + chuoi[len(khoa):]
    return chuoi


def doc_ngon_ngu() -> str:
    """Doc ngon ngu da luu. File loi/hong -> dung mac dinh, KHONG bao loi."""
    try:
        with open(NGON_NGU_FILE, "r", encoding="utf-8") as f:
            du_lieu = json.load(f)
        if isinstance(du_lieu, dict) and du_lieu.get("ngon_ngu") in ("vi", "en"):
            return du_lieu["ngon_ngu"]
    except Exception:                             # noqa: BLE001
        pass
    return NGON_NGU_MAC_DINH


def luu_ngon_ngu(ngon_ngu: str) -> None:
    """Ghi ngon ngu xuong file JSON nho canh gui.py. Loi ghi -> bo qua."""
    try:
        with open(NGON_NGU_FILE, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"ngon_ngu": ngon_ngu}, f, ensure_ascii=False, indent=2)
    except Exception:                             # noqa: BLE001
        pass


# ------------------------------------------------------------------ tien ich

class QueueWriter(io.TextIOBase):
    """Giu dong print() cua thu vien (face_engine) vao hang doi cua GUI."""

    def __init__(self, queue_out: queue.Queue) -> None:
        self._queue = queue_out
        self._buffer = ""

    def write(self, text):
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._queue.put(("log", line.rstrip()))
        return len(text)

    def flush(self):
        if self._buffer.strip():
            self._queue.put(("log", self._buffer.strip()))
        self._buffer = ""


def open_in_explorer(path: str) -> None:
    """Mo file / thu muc bang trinh phat mac dinh cua Windows.

    LUU Y: os.startfile KHONG chay duoc voi duong dan tuong doi,
    phai truyen os.path.abspath(...).
    """
    if os.name == "nt":
        os.startfile(os.path.abspath(path))     # API cua Windows
    else:                                       # may khong phai Windows
        subprocess.Popen(["xdg-open", os.path.abspath(path)])


def parse_int(var, default: int, ten: str) -> int:
    raw = var.get().strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{ten} phải là số nguyên.")


def parse_float(var, default: float, ten: str) -> float:
    raw = var.get().strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{ten} phải là số.")


def dem_widget_hien_thi(wdg) -> int:
    """Dem so widget con dang THUC SU hien tren man hinh (de kiem chung).

    1 nhom cau hinh dang mo  -> tra ve so > 0
    1 nhom dang thu gon    -> tra ve 0
    """
    tong = 1 if wdg.winfo_viewable() else 0
    for con in wdg.winfo_children():
        tong += dem_widget_hien_thi(con)
    return tong


def _o_vung(box, zone_px, nhay: bool) -> bool:
    """Kiem tra 1 khung nguoi co nam trong vung canh hay khong.

    `nhay` (vung_nhay) = chi can mot phan chan vao vung cung tinh la co.
    `chac`            = ca nguoi phai nam trong vung moi tinh.
    """
    if zone_px is None:
        return False
    x1, y1, x2, y2 = [float(v) for v in box[:4]]
    zx1, zy1, zx2, zy2 = [float(v) for v in zone_px]
    if nhay:
        return not (x2 < zx1 or x1 > zx2 or y2 < zy1 or y1 > zy2)
    return x1 >= zx1 and y1 >= zy1 and x2 <= zx2 and y2 <= zy2


def _crop_jpeg(frame, box, hop_mat=None, canh: int = 8, be: int = 0) -> bytes:
    """Cat 1 anh crop VUONG cua nguoi va nen lai JPEG de gui qua hang doi.

    Uu tien anh CAT MAT khi nhan dien duoc mat, neu khong thi cat toan nguoi
    (giong het logic cua panel doi tuong truoc day).
    CHAY TREN THREAD NEN - KHONG dung widget Tkinter o day. Tra ve b"" neu loi.
    """
    if frame is None or frame.size == 0:
        return b""
    import cv2

    crop = GK.cat_anh_moi(frame, hop_mat or box, canh=canh, co_ban=False)
    if crop is None:
        return b""
    if crop.shape[0] > be:
        crop = cv2.resize(crop, (be, be), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(
        ".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), XEM_VIDEO_JPEG_THE],
    )
    return buf.tobytes() if ok else b""


def _su_kien(loai: str, ten: str, tin_do: float, gioi: str,
             jpeg: bytes, moc_thoi_gian: float) -> dict:
    """Dong goi 1 su kien de day vao hang doi cho `PanelSuKien`."""
    tong = max(0.0, moc_thoi_gian)
    gio = f"{int(tong) // 60:02d}:{int(tong) % 60:02d}"
    return {
        "loai": loai,
        "ten": ten,
        "tin_do": tin_do,
        "gioi": gioi or "Chưa rõ",
        # Du an KHONG co mo hinh khau trang -> luon "Chưa rõ" (khong doan bai).
        "khuau_trang": "Chưa rõ",
        "gio": gio,
        "jpeg": jpeg,
    }


class HuongDan:
    """Tooltip don gian: hien 1 doan chu khi re chuot vao widget.

    Dung khi o nhap bi CAT CHU (vi du duong dan thu muc dai hon o). Chuot
    vao -> (doi 450 ms) hien toan bo noi dung; ra -> an.

    Khong dung `tkinter` tooltip co san: CustomTkinter khong kem. Cua so
    tooltip dung `overrideredirect(True)` + `topmost` de khong chiem focus,
    nen bam chuot van bam duoc xuong o ben duoi.

    GIAI GIA KHI KEO CUA SO (quan trong):
      - Chi tao DUNG MOT cua so tooltip cho ca doi (tao lazy 1 lan roi tai
        su dung). Hien = `deiconify()`, an = `withdraw()`. KHONG tao/huy
        lien tuc, vi tao/huy 1 cua so native (Toplevel + overrideredirect +
        topmost) lam tre UI hang tram ms -> app bi GIAT khi keo cua so.
      - Hien sau `THOI_GIAN_HIEN` (450 ms) giong mac dinh Windows: khi keo
        cua so, chuot quet qua nhieu o trong < 450 ms -> khong tooltip nao
        kip hien -> khong tao cua so nao -> het giat. Chuot dung yen tren
        1 o -> tooltip VAN hien sau 450 ms.
    """

    # Do tre hien tooltip (ms) - giong mac dinh cua Windows.
    THOI_GIAN_HIEN = 450

    # Danh sach cac tooltip da tao (de dong lai khi app dong).
    _danh_sach: list = []

    def __init__(self, widget, noi_dung, font=None, do_rong_max: int = 460):
        self.widget = widget
        self.noi_dung = noi_dung
        self.font = font
        self.do_rong_max = do_rong_max
        self.cua_so = None
        self._nhan = None
        self._timer_id = None
        # CTkEntry la 1 Frame chua tkinter.Entry ben trong (`_entry`).
        # Re chuot vao vung TEXT thi chi `_entry` nhan <Enter>, nen bind
        # vao `_entry` (fallback: chinh widget) de khong sot.
        dich = getattr(widget, "_entry", None)
        if dich is None:
            dich = widget
        self.dich = dich
        dich.bind("<Enter>", self._vao, add="+")
        dich.bind("<Leave>", self._ra, add="+")
        try:
            dich.bind("<ButtonPress-1>", self._ra, add="+")
        except Exception:
            pass
        HuongDan._danh_sach.append(self)

    def _noi_dung_hien_tai(self) -> str:
        """Lay noi dung hien thi. `noi_dung` co the la callable (doc o bien)."""
        n = self.noi_dung
        if callable(n):
            try:
                n = n()
            except Exception:
                return ""
        return str(n or "")

    # ------------------------------------------------------------ hen gio

    def _tk_he(self):
        """Widget dung de dat hen gio (uu tien toplevel de ben hon o nho)."""
        try:
            return self.widget.winfo_toplevel()
        except Exception:
            return self.widget

    def _huy_hen(self) -> None:
        """Huy hen gio hien tooltip (neu co)."""
        if self._timer_id is None:
            return
        try:
            self._tk_he().after_cancel(self._timer_id)
        except Exception:
            pass
        self._timer_id = None

    # ------------------------------------------------------------ hien / an

    def _vao(self, _event=None) -> None:
        """Chuot vao: CHI hen gio hien tooltip, khong hien ngay.

        Do tre 450 ms la ly do app khong giat khi keo cua so (chuot quet
        qua nhieu o trong < 450 ms -> khong tooltip nao kip hien).
        """
        self._huy_hen()
        try:
            self._timer_id = self._tk_he().after(self.THOI_GIAN_HIEN,
                                                 self._hien_tooltip)
        except Exception:
            self._timer_id = None

    def _ra(self, _event=None) -> None:
        """Chuot ra (hoac bam chuot): huy hen gio + AN tooltip.

        Chi `withdraw()` - KHONG `destroy()`: giu nguyen 1 cua so de dung
        lai (tao/huy lien tuc la nguyen nhan giat khi keo cua so).
        """
        self._huy_hen()
        if self.cua_so is not None:
            try:
                self.cua_so.withdraw()
            except Exception:
                pass

    def _hien_tooltip(self) -> None:
        """Callback cua hen gio: tao (hoac tai su dung) cua so roi hien."""
        self._timer_id = None
        noi_dung = self._noi_dung_hien_tai()
        if not noi_dung:
            return
        try:
            if self.cua_so is not None:
                try:
                    con = bool(self.cua_so.winfo_exists())
                except Exception:
                    con = False
                if not con:
                    self.cua_so = None
                    self._nhan = None
            if self.cua_so is None:
                self._tao_cua_so(noi_dung)
            else:
                self._nhan.configure(text=noi_dung)
            self._dat_vi_tri()
            self.cua_so.deiconify()
            self.cua_so.update_idletasks()
        except Exception:
            pass

    def _tao_cua_so(self, noi_dung: str) -> None:
        """Tao cua so tooltip (chi tao 1 lan cho ca doi)."""
        self.cua_so = tk.Toplevel(self.widget)
        self.cua_so.overrideredirect(True)
        self.cua_so.attributes("-topmost", True)
        self._nhan = tk.Label(
            self.cua_so, text=noi_dung, justify="left",
            background=MAU["the_phu"], foreground=MAU["chu"],
            font=self.font, padx=8, pady=5, wraplength=self.do_rong_max,
        )
        self._nhan.pack()
        # Tao xong -> an ngay, chi hien khi den luc.
        self.cua_so.withdraw()

    def _chieu_rong(self) -> int:
        """Chieu rong cua so tooltip (dung cho canh man hinh)."""
        for w in (self.cua_so, self._nhan):
            if w is None:
                continue
            try:
                r = int(w.winfo_reqwidth())
            except Exception:
                continue
            if r > 1:
                return r
        try:
            return int(self.cua_so.winfo_width())
        except Exception:
            return 0

    def _dat_vi_tri(self) -> None:
        """Dat vi tri tooltip: lech +14/+20 px so voi con tro chuot,
        khong tran ra ngoai man hinh."""
        self.cua_so.update_idletasks()
        # Toa do man hinh: `winfo_pointerx` cua TOPLEVEL = toa do man hinh.
        goc = self.dich.winfo_toplevel()
        x = goc.winfo_pointerx() + 14
        y = goc.winfo_pointery() + 20
        chieu_rong = self._chieu_rong()
        man_hinh = goc.winfo_screenwidth()
        if x + chieu_rong > man_hinh - 8:
            x = max(8, man_hinh - chieu_rong - 8)
        self.cua_so.geometry(f"+{x}+{y}")

    # ------------------------------------------------------------ dong app

    @classmethod
    def dong_tat_toan_bo(cls) -> None:
        """Huy hen gio + dong moi cua so tooltip (goi khi app dong)."""
        for h in list(cls._danh_sach):
            try:
                h._huy_hen()
            except Exception:
                pass
            try:
                if h.cua_so is not None:
                    h.cua_so.destroy()
                    h.cua_so = None
                    h._nhan = None
            except Exception:
                pass
        try:
            cls._danh_sach.clear()
        except Exception:
            pass


class GoiYTronO:
    """Goi y (placeholder) ve CHONG LEN o nhap, khong dung co che placeholder
    co san cua customtkinter.

    Ly do phai tu viet:
    - customtkinter 5.2.2 chi kich hoat placeholder khi `textvariable is
      None` hoac `textvariable == ""` (xem `ctk_entry.py`).
    - `tkinter.StringVar` KHONG dinh nghia `__eq__` nen `bien == ""` LUON
      False -> moi o nhap co bien deu khong bao gio hien placeholder.
    - Sua bang cach `insert` chu placeholder vao o thi Tk dong bien 2 chieu:
      chu placeholder chui thang vao `textvariable`. Do thuc tren may:
      bien bi nhieu "HUONG DAN GIUONG" ngay sau khi go 2 ky tu, nen doc
      gia tri sai hoan toan.

    Giai phap nay: 1 nhan `CTkLabel` dat chong len o. Nhan khong bao gio
    dung vao noi dung cua o nen bien `textvariable` luon sach:
    - bien rong  -> hien nhan
    - bien co gia tri -> an nhan

    CHU Y DO RONG: cot cau hinh ben trai hep (~102px cho o "Vung can quet"),
    nen goi y trong o phai NGAN. Do that bang PIL: "de trong = tu tim trong
    khung" rong 159px -> tran ra ngoai o. "tu tim" rong 31px -> vua khung.
    Phan giai day du da co trong ghi chu ben duoi va trong tooltip.
    """

    def __init__(self, entry, text: str, font=None, text_color=None):
        self.entry = entry
        self.text = text
        self.font = font
        self.text_color = text_color or MAU["chu_phu"]
        self.dang_hien = False
        self.var = None
        try:
            self.var = entry.cget("textvariable")
        except Exception:                             # noqa: BLE001
            self.var = None
        # Nen cua nhan TRUNG VOI nen trong o (khong thay vach).
        #
        # KHONG doc `entry.cget("fg_color")` luc tao: luc do buoc
        # `_ap_dung_theme` (chay SAU khi dung form) chua gan mau cho o, nen
        # `cget` tra ve BANG MAU cua theme mac dinh
        # (['#F9F9FA', '#343638']) chu khong phai mau that cua o
        # (#272F42). Do do nhan se khong mau voi o.
        # Dung thang `MAU["the_phu"]` - dung mau ma `_ap_dung_theme` gan cho
        # MOI o nhap trong app, nen luon khop va khong phu thuoc thu tu tao.
        nen = MAU.get("the_phu", "#272F42")
        # Nhan la con cua CHINH o nhap nen luon nam dung cho o: khong can
        # tinh toa do (o nhap co the chua duoc layout luc khoi tao).
        # Cao 24 (o nhap cao 28) + `place(y=2)` de KHONG de len vien 1px
        # cua o (anh chup truoc day thay vien ben duoi nhan bi che).
        self.nhan = ctk.CTkLabel(entry, text=text, font=font,
                                  text_color=self.text_color,
                                  fg_color=nen, anchor="w", height=24)
        self.nhan.bind("<Button-1>", self._bam_vao)
        if self.var is not None:
            try:
                self.var.trace_add("write", self._bien_doi)
            except Exception:                         # noqa: BLE001
                self.var = None
        self._cap_nhat()

    def _bam_vao(self, _event=None):
        """Bam vao nhan goi y -> dua con tro vao dung o nhap."""
        try:
            self.entry.focus_set()
            self.entry._entry.icursor("end")
        except Exception:                             # noqa: BLE001
            pass
        return "break"

    def _bien_doi(self, *_args) -> None:
        self._cap_nhat()

    def _cap_nhat(self) -> None:
        gia_tri = ""
        if self.var is not None:
            try:
                gia_tri = self.var.get()
            except Exception:                         # noqa: BLE001
                gia_tri = ""
        if str(gia_tri).strip() == "":
            self._hien()
        else:
            self._an()

    def _hien(self) -> None:
        if self.dang_hien:
            return
        self.dang_hien = True
        self._dat_vi_tri()

    def _an(self) -> None:
        if not self.dang_hien:
            return
        self.dang_hien = False
        try:
            self.nhan.place_forget()
        except Exception:                             # noqa: BLE001
            pass

    def _dat_vi_tri(self) -> None:
        try:
            # KHONG truyen `width`/`height` vao `place()`: customtkinter 5.2.2
            # nem ValueError ("'width' and 'height' arguments must be passed
            # to the constructor"). Do do nhan giu chieu cao 24 dat trong
            # constructor va duoc `place(y=2)` -> khong de len vien 1px cua o.
            # `anchor="nw"` de canh theo mep tren (dung "w" se canh giua theo
            # truc y o y=0 -> nhan lot ra tren tren, bi cat chu).
            #
            # Mau nen gan lai luc hien: dung `MAU["the_phu"]` (dung mau ma
            # `_ap_dung_theme` gan cho moi o nhap) chu khong doc
            # `entry.cget("fg_color")` - luc nao theme co the chua chot.
            try:
                self.nhan.configure(fg_color=MAU.get("the_phu", "#272F42"))
            except Exception:                         # noqa: BLE001
                pass
            self.nhan.place(x=12, y=2, anchor="nw")
        except Exception:                             # noqa: BLE001
            pass


# ------------------------------------------------------------------ 1 tinh nang

class NhomTinhNang(ctk.CTkFrame):
    """MOT MUC CON trong 1 MUC LON: 1 dong checkbox + 1 dong ghi chu 12px.

    Tieu de:  [mui ten] Ten muc con (13px `chu`)
    Khi mo:   them 1 dong ghi chu nho xam + 1 khung cau hinh ngay ben duoi.
    Dung grid() + grid_remove() de an hien (KHONG dung pack_forget).
    """

    def __init__(self, master, ten, var, lenh="", font=None, font_nho=None,
                 font_bieu_tuong=None, mac_dinh=(), co_checkbox=True) -> None:
        super().__init__(master, fg_color=MAU["nen"])
        self.var = var
        self.co_checkbox = co_checkbox
        self.dang_mo = False
        self._mac_dinh = list(mac_dinh)     # [(var, gia_tri_mac_dinh), ...]
        # MUC LON chua muc con nay (xem `NhomLon`). Khi muc con duoc MO thi
        # muc lon cha cung duoc mo - neu khong thi muc con "mo" ma khong ai
        # thay duoc (nó nam trong 1 the dang thu gon).
        self.nhom_lon_cha = None
        self.grid_columnconfigure(1, weight=1)

        # --- THANH TIEU DE: nen the, chu trang, bom rong day ---
        self.thanh = ctk.CTkFrame(
            self, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
            border_width=1, border_color=MAU["vien"],
        )
        self.thanh.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.thanh.grid_columnconfigure(1, weight=1)

        self.btn_mo = ctk.CTkButton(
            self.thanh, text=bieu_tượng("mui_phai"), width=36, height=36,
            fg_color="transparent", hover_color=MAU["nut_phu"],
            text_color=MAU["chu"], font=font_bieu_tuong,
            corner_radius=BO_GOC_NUT, command=self._doi_trang_thai,
        )
        # nut mui ten giu nguyen mau trong suot - khong cho vong mau chung doi.
        self.btn_mo._bo_toc_style = True
        # Nut mui ten TU QUAN LY CHU: doi ngon nung KHONG duoc ve lai glyph.
        self.btn_mo._bo_ngon_ngu = True
        self.btn_mo.grid(row=0, column=0, sticky="w", padx=(4, KHOANG_CACH),
                         pady=4)

        if co_checkbox:
            self.chk = ctk.CTkCheckBox(
                self.thanh, text=ten, variable=var, font=font,
                text_color=MAU["chu"], fg_color=MAU["nut"],
                hover_color=MAU["nut_hover"], border_color=MAU["nut_phu"],
                # Dau tick ve bang MAU TOI (nen) tren nen o XANH - neu ve
                # cung mau nen o thi dau tick BIEN MAT hoan toan.
                checkmark_color=MAU["nen"],
                command=self._doi_checkbox, onvalue="1", offvalue="0"
            )
            # Tieu de muc con = 13px `chu` (nho hon tieu de MUC LON 15px HOA).
            self.chk._bo_toc_style = True
        else:
            self.chk = ctk.CTkLabel(self.thanh, text=ten, font=font,
                                    text_color=MAU["chu"], anchor="w")
        self.chk.grid(row=0, column=1, sticky="w", padx=(0, 10))

        self.lbl_lenh = ctk.CTkLabel(
            self, text=lenh, font=font_nho, text_color=MAU["chu_phu"],
            anchor="w", justify="left", wraplength=WRAP_MO_TA_NHOM,
        )
        self.lbl_lenh.grid(row=1, column=0, columnspan=2, sticky="w",
                           padx=(LE_MO_TA_NHOM, 0), pady=(KHOANG_CACH, 0))

        # --- PHAN CAI DAT: nen CHINH #0F172A + vien 1px -> cam giac "long vao"
        self.khung = ctk.CTkFrame(
            self, fg_color=MAU["nen"], corner_radius=BO_GOC_THE,
            border_width=1, border_color=MAU["vien"],
        )
        self.khung.grid_columnconfigure(0, weight=1)
        self.khung.grid(row=2, column=0, columnspan=2, sticky="ew",
                        padx=(LE_MO_TA_NHOM, 0),
                        pady=(KHOANG_CACH, KHOANG_CACH))
        self.khung._dong = 0

        # MAC DINH: thu gon ca chuc nang (ke ca tinh nang dang BAT).
        self.khung.grid_remove()
        self.lbl_lenh.grid_remove()

    # ---------------------------------------------------------- mo / dong

    def _doi_trang_thai(self) -> None:
        self.dat_mo(not self.dang_mo)

    def _doi_checkbox(self) -> None:
        if self.var.get() == "1":
            self.dat_mo(True)
        else:
            self.dat_mo(False)
            # Tat -> thu lai VA khoi phuc gia tri mac dinh.
            for bien, gia_tri in self._mac_dinh:
                bien.set(gia_tri)

    def dat_mo(self, mo: bool) -> None:
        """Mo / dong phan cau hinh. Moi loai goi Tkinter tu day vao hang doi UI.

        Khi MO: muc lon CHA cung duoc mo (neu co) - muc con "mo" ma nam
        trong 1 muc lon dang thu gon thi nguoi dung khong thay duoc gi.
        """
        self.dang_mo = mo
        if mo:
            if self.nhom_lon_cha is not None:
                self.nhom_lon_cha.dat_mo(True)
            self.lbl_lenh.grid()
            self.khung.grid()
            self.btn_mo.configure(text=bieu_tượng("mui_xuong"))
        else:
            self.lbl_lenh.grid_remove()
            self.khung.grid_remove()
            self.btn_mo.configure(text=bieu_tượng("mui_phai"))

    # ---------------------------------------------------------- tien ich

    def dem_widget_hien_thi(self) -> int:
        return dem_widget_hien_thi(self.khung)

    def trang_thai(self) -> str:
        return (f"mo={self.dang_mo} manager={self.khung.winfo_manager()!r} "
                f"xunghinh={self.khung.winfo_viewable()} "
                f"so_widget_hien_thi={self.dem_widget_hien_thi()}")


# ------------------------------------------------------------------ 1 muc lon

class NhomLon(ctk.CTkFrame):
    """MOT MUC LON trong cot trai: the tieu de HOA + 1 dong mo ta + noi dung.

    Muc longom nhom cac MUC CON (`NhomTinhNang`) lai. Mo / dong bang mui ten
    chevron (KHONG dung emoji, KHONG dung ky tu to hop).

    CHI 1 MUC LON MO TAI MOT LUC: khi mo muc lon nay, cac muc lon khac tu
    dong lai -> cot trai luon gon, khong phai cuon nhieu.

    Cay widget:
        NhomLon (nen trong suot)
          row 0: `thanh`  - the nen `the`, chu `chu`, bo goc `BO_GOC_THE`
                            [nut chevron] [tieu de HOA] [mo ta 12px `chu_phu`]
          row 1: `khung`  - noi dung chua cac muc con (an khi dong)
    """

    def __init__(self, master, ten, mo_ta="", font_tieu_de=None, font_mo_ta=None,
                 font_bieu_tuong=None, mo_san=False) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.dang_mo = bool(mo_san)
        # Danh sach TAT CA muc lon - dung de dong nhanh cac muc lon khac.
        # Ganh sau khi tao het cac muc lon (xem `_them_nhom_lon`).
        self._cac_nhom_lon: list = []

        # --- THE TIEU DE: nen `the`, chu `chu`, bo goc `BO_GOC_THE` ---
        self.thanh = ctk.CTkFrame(
            self, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
            border_width=1, border_color=MAU["vien"],
        )
        self.thanh.grid(row=0, column=0, sticky="ew")
        self.thanh.grid_columnconfigure(1, weight=1)

        # Nut chevron: MUOI TEN XOAY khi mo / dong (2 glyph khac nhau).
        # Muc lon MO SAN -> muon XUONG (E70D) ngay tu dau, nguoi dung moi
        # phan biet duoc muc nao dang mo. KHONG goi `dat_mo()` o day (no dong
        # cac muc lon khac -> sai logic "chi 1 muc lon mo").
        self.btn_mo = ctk.CTkButton(
            self.thanh, text=bieu_tượng("mui_xuong" if mo_san else "mui_phai"),
            width=32, height=32,
            fg_color="transparent", hover_color=MAU["nut_phu"],
            text_color=MAU["chu"], font=font_bieu_tuong,
            corner_radius=BO_GOC_NUT, command=self._doi_trang_thai,
        )
        # nut mui ten giu nguyen mau trong suot - khong cho vong mau chung doi.
        self.btn_mo._bo_toc_style = True
        # Nut mui ten TU QUAN LY CHU: doi ngon nung KHONG duoc ve lai glyph
        # (neu ve lai, muc dang mo bi quay ve mui phai -> sai trang thai).
        self.btn_mo._bo_ngon_ngu = True
        self.btn_mo.grid(row=0, column=0, sticky="w", padx=(4, 8), pady=4)

        # Tieu de muc lon: HOA, 15px bold, chu `chu` - noi bat nhat cot trai.
        self.lbl_ten = ctk.CTkLabel(
            self.thanh, text=ten, font=font_tieu_de,
            text_color=MAU["chu"], anchor="w", justify="left",
        )
        self.lbl_ten.grid(row=0, column=1, sticky="w", padx=(0, 10))

        # Mo ta 1 DONG: giup nguoi khong ra chuyen thuat biet muc lon nay
        # lam gi (chi doc 1 dong cung du hieu).
        self.lbl_mo_ta = ctk.CTkLabel(
            self.thanh, text=mo_ta, font=font_mo_ta,
            text_color=MAU["chu_phu"], anchor="w", justify="left",
            wraplength=WRAP_MO_TA_NHOM_LON,
        )
        self.lbl_mo_ta.grid(row=1, column=0, columnspan=2, sticky="w",
                            padx=(LE_MO_TA_NHOM_LON, 0), pady=(0, 6))

        # --- NOI DUNG (cac muc con) ---
        self.khung = ctk.CTkFrame(self, fg_color="transparent")
        self.khung.grid_columnconfigure(0, weight=1)
        self.khung.grid(row=1, column=0, sticky="ew",
                        pady=(KHOANG_CACH, 0))
        self.khung._dong = 0
        # De muc con biet muc long chua no (mo muc con -> mo muc long cha).
        self.khung._nhom_lon = self

        if not self.dang_mo:
            self.khung.grid_remove()

    # ---------------------------------------------------------- mo / dong

    def _doi_trang_thai(self) -> None:
        self.dat_mo(not self.dang_mo)

    def dat_mo(self, mo: bool) -> None:
        """Mo / dong noi dung. Mo muc lon nay -> TU DONG DONG cac muc lon khac.

        Moi loai goi Tkinter tu day vao hang doi UI.
        """
        self.dang_mo = bool(mo)
        if mo:
            self.khung.grid()
            self.btn_mo.configure(text=bieu_tượng("mui_xuong"))
            # CHI 1 muc lon mo tai mot thoi -> cot trai luon gon.
            for nhom in self._cac_nhom_lon:
                if nhom is not self and nhom.dang_mo:
                    nhom.dat_mo(False)
        else:
            self.khung.grid_remove()
            self.btn_mo.configure(text=bieu_tượng("mui_phai"))

    # ---------------------------------------------------------- tien ich

    def dem_widget_hien_thi(self) -> int:
        return dem_widget_hien_thi(self.khung)

    def trang_thai(self) -> str:
        return (f"mo={self.dang_mo} manager={self.khung.winfo_manager()!r} "
                f"xunghinh={self.khung.winfo_viewable()} "
                f"so_widget_hien_thi={self.dem_widget_hien_thi()}")


# ------------------------------------------------------------------ cua so

class CamAIGui(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        # Ngon ngu phai biet TRUOC khi dung bat ky chuoi hien thi nao.
        self.ngon_ngu = doc_ngon_ngu()
        self.title(self._tieu_de())
        # 1180x980 = dung ngay chiều cao noi dung can (976px) o trang thai thu gon.
        # Nho hon thi nhat ky bi bop - cua so chinh khong co thanh cuon.
        self.geometry("{}x{}".format(*KICH_THUOC_CUA_SO))
        self.minsize(1000, 700)
        self._da_canh_giua = False
        # Chi canh giua SAU khi cua so da co dung kich thuoc da dinh nghia.
        self.after(80, self._canh_giua_trong_vung_lam_viec)
        self.configure(fg_color=MAU["nen"])

        # --- KIEM TRA FONT thuc te (tkinter.font.families) -> fallback ---
        # Font chi dung font co san tren Windows. `xac_nhan_font` tra ve dict
        # de in ra kiem chung; neu thieu font bieu tuong Windows thi
        # `co_font_bieu_tuong()` = False va moi noi dung dung CHU THAY ICON.
        self.kiem_tra_font = xac_nhan_font(self)

        # --- chu: Segoe UI cho chu, Cascadia Mono cho so / bang / nhat ky ---
        # Vai tro theo MASTER.md muc 3 (tieu de app 23, tieu de khu vuc 15
        # semibold, nhan o 13, ghi chu 12, so lieu 28 bold).
        self.font_title = ctk.CTkFont(family=GD.FONT_CHU, size=23, weight="bold")
        self.font_group = ctk.CTkFont(family=GD.FONT_DEN, size=18, weight="bold")
        self.font_nhom = ctk.CTkFont(family=GD.FONT_DAM, size=15)   # tieu de nhom
        # Tieu de 4 MUC LON (NGUON / PHAN TICH / BIEN SO / CANH BAO):
        # 15px bold HOA - noi bat nhat cot trai. Muc con ben trong chi 13px.
        self.font_muc_lon = ctk.CTkFont(family=GD.FONT_DAM, size=15, weight="bold")

        self.font_tieu_de = ctk.CTkFont(family=GD.FONT_DAM, size=15)  # tieu de khu vuc
        self.font_nut = ctk.CTkFont(family=GD.FONT_CHU, size=14, weight="bold")
        self.font_nho = ctk.CTkFont(family=GD.FONT_CHU, size=13)      # nhan o
        self.font_nho_bold = ctk.CTkFont(family=GD.FONT_DAM, size=13, weight="bold")
        self.font_nho_xam = ctk.CTkFont(family=GD.FONT_CHU, size=12)  # ghi chu
        self.font_code = ctk.CTkFont(family=GD.FONT_SO, size=12)
        self.font_so = ctk.CTkFont(family=GD.FONT_SO, size=13)        # so lieu
        # so lieu noi bat: 28px bold (MASTER.md muc 3 - badge so lieu).
        self.font_stat = ctk.CTkFont(family=GD.FONT_CHU, size=28, weight="bold")
        self.font_stat_lon = ctk.CTkFont(family=GD.FONT_CHU, size=30, weight="bold")
        self.font_bam = ctk.CTkFont(family=GD.FONT_CHU, size=15, weight="bold")
        # Font bieu tuong Windows (Segoe MDL2 Assets) - rong khi co font.
        self.font_bieu_tuong = ctk.CTkFont(
            family=GD.FONT_BIEU_TUONG or GD.FONT_CHU, size=14)

        self.queue: queue.Queue = queue.Queue()
        self.stop_flag = threading.Event()
        self.busy = False
        self.result = None
        self.log_lines = 0
        self.last_progress_at = 0.0
        self.last_names = ""
        self.last_vi_pham = 0
        self.last_canh_lau = 0
        self._cb = None                 # doi tuong CanhBao (tao lazy)
        self.cua_so_model = None
        # v3.6: nguon vao + hop thoai chon camera.
        self._cua_so_camera = None
        self._huy_quet_camera = False
        self._nguon_live = False       # nguon camera (may/IP) -> bar indeterminate
        self._bar_indeterminate = False
        self._mau_trang_thai = "chua_chay"
        self._du_lieu_trang_thai = {}
        self._anh_icon = None           # anh icon app (neu co file .ico)
        self._anh_icon_pil = None       # ban PIL goc (de ve o thanh dau)

        self._khoi_tao_bien()
        self._cai_icon()                # icon app - thieu file thi bo qua
        self._dung_giao_dien()
        self._cap_nhat_trang_thai()
        self._lam_moi_trang_thai()          # ve huyen trang thai luc moi mo
        # GHI NHAN chu tieng Viet goc cua moi widget, truoc khi doi ngon ngu.
        self._ghi_nhan_chu()
        if self.ngon_ngu != NGON_NGU_MAC_DINH:
            self._lam_moi_ngon_ngu()
        self.protocol("WM_DELETE_WINDOW", self._dong_cua_so)
        self.after(PUMP_MS, self._hut_hang_doi)
        # Anh xem truoc video mau: doc o thread nen, giu GUI khong tre luc mo.
        self.after(220, self._bat_dau_doc_thumb)
        # Do chieu cao that cua dai the video mau (sau khi cua so da ve).
        self.after(300, self._do_chieu_cao_dai)
        # Sua giat khi keo cua so: bo ep ve lai ca app trong thanh cuon.
        _patch_scrollbar_khong_ep_ve_lai_ca_app()
        # Hauong: ve lai cay widget TRUOC khi nguoi dung keo cua so lan dau.
        self._dem_lan_cho_hauong = 0
        self.after(150, self._warm_up_ve_cua_so)

    # --------------------------------------------------- hauong ve cua so
    # Ly do giat: LAN KEO DAU TIEN cua nguoi dung keo cua so ton ~0,75 s.
    # Do bang profile: lan keo dau tien moi la lan Tk phai ve lai TOAN BO
    # cay widget (851 widget) cho cua so. Cac lan keo sau re vi bo cuc da
    # on dinh. => Ep cua so ve dung kich thuoc + ve lai 1 lan luc moi mo
    # app, nguoi dung keo cua so chi doi VI TRI -> khong con giat.

    def _warm_up_ve_cua_so(self) -> None:
        """Ep cua so ve dung kich thuoc + ve lai 1 lan TRUOC khi nguoi dung keo.

        Cho canh giua cua so xong truoc (neu co) + cua so da co kich thuoc
        that moi lam duoc. Ket qua: lan keo DAU TIEN cua nguoi dung chi doi
        vi tri, khong phai doi kich thuoc -> khong phai ve lai 851 widget.
        """
        if getattr(self, "_da_hauong", False):
            return
        # Cho cua so co kich thuoc that truoc (Tk tra 1x1 khi chua map).
        if self.winfo_width() <= 1 or self.winfo_height() <= 1:
            self.after(120, self._warm_up_ve_cua_so)
            return
        # Cho canh giua xong. Neu canh giua khong chay (vi du cua so bi
        # doi kich thuoc ben ngoai), van hauong sau ~1,2 s de khong tre.
        self._dem_lan_cho_hauong = getattr(self, "_dem_lan_cho_hauong", 0) + 1
        if (not getattr(self, "_da_canh_giua", False)
                and self._dem_lan_cho_hauong < 10):
            self.after(120, self._warm_up_ve_cua_so)
            return
        self._da_hauong = True
        try:
            self._ep_kich_thuoc_cua_so_tren_man_hinh()
        except Exception:                             # noqa: BLE001
            pass

    def _ep_kich_thuoc_cua_so_tren_man_hinh(self) -> None:
        """Ep kich thuoc CUA SO TREN MAN HINH = `KICH_THUOC_CUA_SO`.

        Tk geometry (`self.geometry`) dat kich thuoc PHAN CLIENT ben trong.
        Con cua so nhin tren man hinh thi lon hon them khung + thanh tieu de
        Windows. Neu hieu sai (cua so tren man hinh lon hon `KICH_THUOC_CUA_SO`)
        thi LAN KEO DAU TIEN cua nguoi dung se doi kich thuoc cua so -> Tk
        phai ve lai TOAN BO cay widget (851 widget) -> cua so giat ~0,75 s.

        O day ep kich thuoc cua so tren man hinh ve DUNG `KICH_THUOC_CUA_SO`
        (1610x980) va ve lai cay widget 1 lan, de nguoi dung keo cua so thi
        chi doi VI TRI - khong phai doi kich thuoc - nen khong giat.
        """
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            rc = _RECT()
            if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                return
            u32 = ctypes.windll.user32
            u32.MoveWindow(ctypes.c_void_p(hwnd), rc.left, rc.top,
                           KICH_THUOC_CUA_SO[0], KICH_THUOC_CUA_SO[1], 0)
            self.update()
        except Exception:                             # noqa: BLE001
            pass

    # ------------------------------------------------------------ icon app

    def _cai_icon(self) -> None:
        """Nap icon app tu `assets/camai.ico` (neu co).

        Tk KHONG doc duoc file .ico truc tiep -> dung PIL doi sang anh roi
        `PhotoImage`. File CHUA co san (coordinator tao sau) -> BO QUA IM LANG,
        app van chay binh thuong, khong bao loi.
        """
        duong_dan = os.path.join(APP_DIR, "assets", "camai.ico")
        if not os.path.isfile(duong_dan):
            return
        try:
            from PIL import Image, ImageTk
            anh = Image.open(duong_dan)
            anh = anh.convert("RGBA")
            anh.thumbnail((64, 64), Image.LANCZOS)
            self._anh_icon = ImageTk.PhotoImage(anh)
            self._anh_icon_pil = anh
            self.iconphoto(True, self._anh_icon)
        except Exception:                             # noqa: BLE001
            self._anh_icon = None
            self._anh_icon_pil = None
        try:
            # `iconbitmap` nhan file .ico truc tiep tren Windows.
            self.iconbitmap(duong_dan)
        except Exception:                             # noqa: BLE001
            pass

    def _anh_bieu_tuong(self, ma: str, size: int = 16, mau=(255, 255, 255, 255)):
        """Anh icon (font Windows) cho nut - tra ve `CTkImage` hoac None.

        Tk khong ve duoc 2 font khac nhau trong 1 chuoi, nen nut co ca icon
        + chu phai dung `image=` cho icon. Neu may khong co font bieu tuong
        Windows -> None (nut chi hien chu).
        """
        if not GD.co_font_bieu_tuong():
            return None
        anh = anh_bieu_tuong(ma, size, mau)
        if anh is None:
            return None
        try:
            return ctk.CTkImage(light_image=anh, dark_image=anh, size=anh.size)
        except Exception:                             # noqa: BLE001
            return None

    def _tieu_de(self) -> str:
        return self.dich(TIEU_DE_CUA_SO).format(phien_ban=VERSION)

    def _vung_lam_viec(self):
        """Tra (x, y, rong, cao) cua vung lam viec that cua man hinh.

        Tk chi biet kich thuoc TOAN man hinh, khong biet taskbar chat bao
        nhieu px. Tren may anh man hinh 1080px nhung taskbar an 40px, nen
        dung winfo_screenheight() se day cua so xuong duoi taskbar.
        """
        try:
            rc = _RECT()
            # SPI_GETWORKAREA = 0x0030
            ok = ctypes.windll.user32.SystemParametersInfoW(
                0x0030, 0, ctypes.byref(rc), 0)
            if ok and rc.right > rc.left and rc.bottom > rc.top:
                return rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top
        except Exception:
            pass
        return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def _kich_thuoc_that(self):
        """Kich thuoc THAT cua cua so keo ca thanh tieu de.

        winfo_height() chi tra phan CLIENT ben trong; thanh tieu de Windows
        them them ~39px. Canh giua bang so client se day cua so tran duoi
        taskbar, nen phai do bang Win32.
        """
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            rc = _RECT()
            if ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                return rc.right - rc.left, rc.bottom - rc.top
        except Exception:
            pass
        return self.winfo_width(), self.winfo_height()

    def _le_vien_cua_so(self):
        """Tra (le ngang, le cao) giua cua so TREN MAN HINH va phan CLIENT.

        `self.geometry(...)` trong Tk dat kich thuoc PHAN CLIENT (ben trong).
        Con cua so nhin tren man hinh thi lon hon them khung + thanh tieu de
        cua Windows (may anh: +16 px ngang, +39 px cao).
        """
        rong_that, cao_that = self._kich_thuoc_that()
        return (rong_that - self.winfo_width(),
                cao_that - self.winfo_height())

    def _kich_thuoc_client_mong_muon(self):
        """Kich thuoc PHAN CLIENT de cua so tren man hinh = KICH_THUOC_CUA_SO."""
        vien_w, vien_h = self._le_vien_cua_so()
        return (max(400, KICH_THUOC_CUA_SO[0] - vien_w),
                max(400, KICH_THUOC_CUA_SO[1] - vien_h))

    def _canh_giua_trong_vung_lam_viec(self) -> None:
        """Dat cua so giua vung lam viec cua man hinh, tranh bi taskbar che.

        KHONG doi kich thuoc (noi dung can dung 1180x980), chi doi vi tri.
        Cho den khi cua so that su co dung kich thuoc da dinh nghia: luc
        moi mo, Tk tra kich thuoc mac dinh 200x200, dung no se tinh sai
        vi tri roi giu nguyen sai so do.

        THEM: cua so tren MAN HINH phai dung bang `KICH_THUOC_CUA_SO`
        (1610x980). Tk geometry chi dat PHAN CLIENT, con cua so tren man
        hinh con them khung + thanh tieu de Windows. Sai le do khong chi
        lam cua so lon hon mong muon (roi tran taskbar) ma con lam LAN KEO
        DAU TIEN cua nguoi dung phai doi kich thuoc cua so -> Tk ve lai
        TOAN BO cay widget (851 widget) -> cua so giat ~0,7 s. Sua o day.
        """
        if getattr(self, "_da_canh_giua", False):
            return
        if self.winfo_width() <= 1 or self.winfo_height() <= 1:
            self.after(120, self._canh_giua_trong_vung_lam_viec)
            return
        rong_client, cao_client = self._kich_thuoc_client_mong_muon()
        if (self.winfo_width() != rong_client
                or self.winfo_height() != cao_client):
            self.geometry(f"{rong_client}x{cao_client}")
            self.after(60, self._canh_giua_trong_vung_lam_viec)
            return

        x, y, rong, cao = self._vung_lam_viec()
        r_cua, c_cua = self._kich_thuoc_that()
        xuong = x + max(0, (rong - r_cua) // 2)
        doc = y + max(0, (cao - c_cua) // 2)
        self.geometry("+{}+{}".format(xuong, doc))
        self._da_canh_giua = True

    # ---------------------------------------------------------- ngon ngu

    def dich(self, chuoi: str) -> str:
        """Doi 1 chuoi hien thi sang ngon ngu dang chon."""
        return dich(chuoi, self.ngon_ngu)

    def _ghi_nhan_chu(self, goc=None) -> None:
        """Ghi lai chu tieng Viet GOC cua moi widget co option 'text'.

        Chi 1 lan khi moi mo. Sau do doi ngon ngu chi can dua lai chu goc,
        nen khong bao gio 'ke' nhung lan doi ngon ngu lien tiep.
        KHONG goi grid()/grid_remove() -> trang thai mo/dong giu nguyen.
        """
        goc = self if goc is None else goc

        def quet(wdg):
            if getattr(wdg, "_bo_ngon_ngu", False):
                return
            # CHI ghi nhan widget CustomTkinter that su. Bo qua:
            #   * widget goc cua tkinter (Entry/Canvas noi bo, bien PY_VAR...)
            #   * widget "gia dan" cua CustomTkinter (text = ten lop, vd 'CTkLabel')
            # vi do khong phai nhan nguoi dung nhin thay.
            if isinstance(wdg, ctk.CTkBaseClass) and "_chu_vi" not in wdg.__dict__:
                try:
                    chu = wdg.cget("text")
                except Exception:                     # noqa: BLE001
                    chu = None
                if isinstance(chu, str) and chu and chu != type(wdg).__name__:
                    wdg._chu_vi = chu
            for con in wdg.winfo_children():
                quet(con)

        quet(goc)

    def _lam_moi_chu(self, goc=None) -> None:
        """Dua lai chu da ghi nhan, theo ngon ngu hien tai."""
        goc = self if goc is None else goc

        def quet(wdg):
            chu_goc = getattr(wdg, "_chu_vi", None)
            if chu_goc is not None:
                try:
                    wdg.configure(text=self.dich(chu_goc))
                except Exception:                     # noqa: BLE001
                    pass
            for con in wdg.winfo_children():
                quet(con)

        quet(goc)

    def _lam_moi_ngon_ngu(self) -> None:
        """Áp ngôn ngữ đang chọn lên TOÀN BỘ giao diện (dùng lúc mở phần mềm)."""
        self._lam_moi_chu()
        if self.cua_so_model is not None and self.cua_so_model.winfo_exists():
            self._lam_moi_chu(self.cua_so_model)

        if getattr(self, "luu_video_mau", None) is not None:
            self.luu_video_mau.lam_moi_chu()

        self.title(self._tieu_de())
        self.btn_ngon_ngu.configure(text="English" if self.ngon_ngu == "vi"
                                    else "Tiếng Việt")
        self._lam_moi_trang_thai()
        if self.cua_so_model is not None and self.cua_so_model.winfo_exists():
            self.cua_so_model.title(self.dich("Thông tin mô hình AI đang dùng"))

    def _doi_ngon_ngu(self) -> None:
        """Nút đổi ngôn ngữ: đổi ngay, KHÔNG cần đóng/mở lại cửa sổ."""
        self.ngon_ngu = "vi" if self.ngon_ngu == "en" else "en"
        self._lam_moi_ngon_ngu()
        self.lbl_loi.configure(text="")
        luu_ngon_ngu(self.ngon_ngu)

    # ---------------------------------------------------- video mau

    def _duong_dan_video_mau(self, chi_so: int) -> str:
        """Đường dẫn đầy đủ của video mẫu thứ `chi_so` (không kiểm tra tồn tại)."""
        return os.path.join(APP_DIR, "video_mau", VIDEO_MAU[chi_so][3])

    def _dung_video_mau(self, chi_so: int) -> None:
        """Chọn 1 video mẫu (bấm vào thẻ) và điền vào ô 'Video'.

        KHÔNG tự chạy phân tích - người dùng bấm BẮT ĐẦU như các video khác.
        """
        if not (0 <= chi_so < len(VIDEO_MAU)):
            return
        duong_dan = self._duong_dan_video_mau(chi_so)
        if not os.path.isfile(duong_dan):
            self._bao_canh_bao(
                "Không tìm thấy video mẫu",
                self.dich(f"Không tìm thấy video mẫu: {VIDEO_MAU[chi_so][3]}"),
            )
            return
        self.v_video.set(duong_dan)
        if getattr(self, "luu_video_mau", None) is not None:
            self.luu_video_mau.dat_chon(chi_so)
        self.lbl_loi.configure(text=self.dich(
            f"Đã chọn video mẫu: {VIDEO_MAU[chi_so][3]} "
        ) + self.dich("Bấm BẮT ĐẦU để chạy thử."))

    # --------------------------------------------- DAI THE VIDEO MAU (ANH)

    def _bang_video_mau(self):
        """Dai the video mau CHAY NGANG o duoi cua so: moi video = 1 the co
        ANH XEM TRUOC THAT lay tu chinh file video. Bam vao the = chon luon.

        Xep ngang (7 the 1 hang) vi xep doc se day nut BẮT ĐẦU xuống duoi
        man hinh - ma anh Tai Son muon THAY video mau ngay khi mo phan mem.
        """
        khung = ctk.CTkFrame(self, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
                             border_width=1, border_color=MAU["vien"])
        khung.grid(row=2, column=0, columnspan=3, sticky="ew",
                   padx=LE_NGOAI, pady=(KHOANG_CACH, 0))
        khung.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(khung, text="Video mẫu dùng thử", font=self.font_nho_bold,
                     text_color=MAU["chu"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(5, 2))
        ctk.CTkLabel(khung, text="Bấm vào thẻ để chọn video",
                     font=self.font_nho_xam, text_color=MAU["chu_phu"],
                     anchor="w").grid(row=0, column=1, sticky="w",
                                      padx=(10, 0), pady=(5, 2))
        self.btn_video_mau = ctk.CTkButton(
            khung, text="Ẩn", width=68, height=26,
            font=self.font_nho, command=self._doi_hien_video_mau,
            fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
            text_color=MAU["chu"], border_width=1, border_color=MAU["vien"],
            corner_radius=BO_GOC_NUT,
        )
        self.btn_video_mau.grid(row=0, column=2, sticky="e", padx=(0, 12),
                                pady=(5, 2))

        self.luu_video_mau = GK.LuoiVideoMau(
            khung, VIDEO_MAU, dich=self.dich, font_nho=self.font_nho_xam,
            font_nho_bold=self.font_nho_bold, command=self._dung_video_mau,
            so_cot=len(VIDEO_MAU),
        )
        self.luu_video_mau.grid(row=1, column=0, columnspan=3, sticky="ew",
                                padx=6, pady=(0, 4))
        self._thu_nho_the_video_mau()
        self._video_mau_dang_hien = True
        self._dong_bo_the_video_mau()

    def _thu_nho_the_video_mau(self) -> None:
        """RUT GON dai the video mau: the NGANG (anh ben trai - chu ben phai).

        Ban 3.4 moi the video mau cao ~137px (anh tren, ten + mo ta duoi) ->
        ca dai 212px, day man hinh. Nay boi:
          * anh xem truoc nho hon (128x72 -> 84x47),
          * CHUYEN THE sang bo cuc NGANG: anh ben trai, ten + mo ta ben phai
            -> 1 the chi cao ~55px,
          * 2 dong chu ep cao lai (mac dinh CTkLabel cao 28px -> 20/18px).

        KHONG sua `gui_khung.py` (file dung chung) - chi bo lai bo cuc cua
        widget da tao o day.
        """
        luoi = getattr(self, "luu_video_mau", None)
        if luoi is None:
            return
        for the in getattr(luoi, "_the", {}).values():
            try:
                # Anh xem truoc nho hon.
                the.o_anh.configure(width=RONG_THUMB_MOI, height=CAO_THUMB_MOI)
                # BO CUC NGANG: cot 0 = anh, cot 1 = ten + mo ta.
                the.grid_columnconfigure(0, weight=0)
                the.grid_columnconfigure(1, weight=1)
                the.o_anh.grid(row=0, column=0, rowspan=2, sticky="w",
                               padx=(4, 6), pady=(4, 4))
                the.lbl_ten.grid(row=0, column=1, sticky="w",
                                 padx=(0, 6), pady=(4, 0))
                the.lbl_mo_ta.grid(row=1, column=1, sticky="w",
                                   padx=(0, 6), pady=(0, 4))
                # 2 dong chu: ten 13px (cao 20) + mo ta 12px (cao 18).
                the.lbl_ten.configure(height=20, wraplength=WRAP_THE_VIDEO_MAU)
                the.lbl_mo_ta.configure(height=18, wraplength=WRAP_THE_VIDEO_MAU)
            except Exception:                             # noqa: BLE001
                pass
        # Chieu cao tam thoi (dung khi widget chua duoc ve) - se do lai
        # chinh xac o `_do_chieu_cao_dai`.
        try:
            luoi.cuon.configure(height=CAO_THUMB_MOI + 20)
        except Exception:                                 # noqa: BLE001
            pass

    def _do_chieu_cao_dai(self) -> None:
        """Do CHIEU CAO THAT cua the video mau va ep khung cuon ngang vua khop.

        Chay sau khi cua so da ve (xem `after` trong `__init__`) - luc nay Tk
        da tinh xong be cao that cua 1 the (2 dong chu + anh xem truoc).
        """
        luoi = getattr(self, "luu_video_mau", None)
        if luoi is None:
            return
        cao_the = 0
        for the in getattr(luoi, "_the", {}).values():
            try:
                cao_the = max(cao_the, the.winfo_reqheight())
            except Exception:                             # noqa: BLE001
                pass
        if cao_the <= 0:
            return
        try:
            # + 6px: le `grid` cua the (3px tren + 3px duoi).
            luoi.cuon.configure(height=cao_the + 6)
        except Exception:                                 # noqa: BLE001
            pass

    def _doi_hien_video_mau(self) -> None:
        """Nut AN / HIEN dai video mau (mac dinh HIEN de thay ngay ca 7 the)."""
        self._video_mau_dang_hien = not self._video_mau_dang_hien
        if self._video_mau_dang_hien:
            self.luu_video_mau.grid()
        else:
            self.luu_video_mau.grid_remove()
        self.btn_video_mau.configure(
            text="Ẩn" if self._video_mau_dang_hien else "Hiện")

    def _dong_bo_the_video_mau(self) -> None:
        """Tô sáng đúng thẻ video mẫu đang khớp với ô 'Video' (khớp thì không tô)."""
        if getattr(self, "luu_video_mau", None) is None:
            return
        hien_tai = os.path.normcase(os.path.abspath(self.v_video.get() or ""))
        chon = -1
        for i in range(len(VIDEO_MAU)):
            if os.path.normcase(os.path.abspath(
                    self._duong_dan_video_mau(i))) == hien_tai:
                chon = i
                break
        self.luu_video_mau.dat_chon(chon)

    # (giữ tên cũ `_dung_video_mau` vì đây là hàm duy nhất xử lý chọn video mẫu)

    def _bat_dau_doc_thumb(self) -> None:
        """Đọc ảnh xem trước của các video mẫu TRÊN THREAD NÊN.

        Mở + giải mã video là việc NẶNG (lần đầu ~5s cho 7 video) - chạy ở
        đây thì GUI không bị đứng hình lúc mở. Kết quả đẩy vào hàng đợi,
        vòng bơm của UI mới gắn ảnh lên thẻ (giữ đúng quy tắc không bao giờ
        chạm widget Tk từ thread nền).
        """
        if getattr(self, "luu_video_mau", None) is None:
            return
        if self.luu_video_mau.con_cho_doc() <= 0:
            return

        def worker():
            for chi_so, m in enumerate(VIDEO_MAU):
                duong_dan = self._duong_dan_video_mau(chi_so)
                if not os.path.isfile(duong_dan):
                    continue
                try:
                    anh = GK.doc_thumb(duong_dan, None)
                except Exception:                         # noqa: BLE001
                    anh = None
                self.queue.put(("thumb", (chi_so, anh)))

        threading.Thread(target=worker, daemon=True).start()

    # ---------------------------------------------------- trang thai chay

    def _set_trang_thai(self, mau: str, **du_lieu) -> None:
        """Dat chu trang thai ben canh thanh tien trinh (co ban dich 2 ngon ngu)."""
        self._mau_trang_thai = mau
        self._du_lieu_trang_thai = du_lieu
        self._lam_moi_trang_thai()

    def _lam_moi_trang_thai(self) -> None:
        khuôn = TRANG_THAI_TIEN_TRINH[self._mau_trang_thai]
        self.v_tien_trinh.set(self.dich(khuôn).format(**self._du_lieu_trang_thai))
        # Huyen trang thai: MAU + BIEU TUONG FONT WINDOWS + CHU NGAN.
        # CHU NGAN o day la chu y: chi tiet "2/250 · 1%" do nhan TIEN TRINH ben
        # canh lo. Truoc day huyen in luon ca chuoi dai do nen hai nhan bi de
        # vao nhau o goc tren phai khi cua so nho lai.
        ngan = self.dich(NHAN_TRANG_THAI_NGAN.get(
            self._mau_trang_thai, TRANG_THAI_TIEN_TRINH[self._mau_trang_thai]))
        if getattr(self, "huyen", None) is not None:
            self.huyen.configure(
                fg_color=MAU_TRANG_THAI.get(self._mau_trang_thai, MAU["nut_phu"]),
            )
            self.huyen_chu.configure(text=ngan)
            # Khong co font bieu tuong Windows -> dung CHU VIET TAT thay the.
            if GD.co_font_bieu_tuong():
                self.huyen_icon.configure(
                    text=BIEU_TU_TRANG_THAI.get(self._mau_trang_thai, ""))
            else:
                self.huyen_icon.configure(
                    text={"chua_chay": "OK", "chay": ">>", "tam_dung": "||",
                          "loi": "X", "dung_giua": "||", "xong": "OK"}.get(
                              self._mau_trang_thai, ""))
        self._cap_nhat_mau_so_lieu()

    # ------------------------------------------------------------ bien

    def _khoi_tao_bien(self):
        mau = os.path.join(APP_DIR, "video_test.mp4")
        self.v_video = ctk.StringVar(value=mau)
        # "Luu ket qua" la THU MUC luu ket qua, khong phai duong dan file video.
        self.v_output = ctk.StringVar(value=APP_DIR)
        # Video mau dung thu: chon bang cach BAM VAO THE co anh xem truoc.
        # Khong can bien StringVar - lua chon luu trong `luu_video_mau`.

        # --- an toan: phat hien + nhan dien mat BAT, con lai TAT ---
        self.v_phat_hien = ctk.StringVar(value="1")
        self.v_conf = ctk.StringVar(value="0.25")
        self.v_model = ctk.StringVar(value="yolo11n.pt")
        self.v_thiet_bi = ctk.StringVar(value="Tự động")
        self.v_khung = ctk.StringVar(value="1")
        self.v_nhan = ctk.StringVar(value="1")
        self.v_pixelate = ctk.StringVar(value="0")

        self.v_face = ctk.StringVar(value="1")
        self.v_face_threshold = ctk.StringVar(value="0.40")
        self.v_min_face = ctk.StringVar(value="0")
        self.v_face_every = ctk.StringVar(value="3")
        self.v_faces_dir = ctk.StringVar(value=os.path.join(APP_DIR, "known_faces"))

        self.v_dem_ra_vao = ctk.StringVar(value="0")

        self.v_vung = ctk.StringVar(value="0")
        self.v_vung_file = ctk.StringVar(value=os.path.join(APP_DIR, "vung.txt"))
        self.v_vung_nhay = ctk.StringVar(value="0")
        self.v_vung_max = ctk.StringVar(value="2")
        self.v_canh_lau = ctk.StringVar(value="3.0")

        self.v_clip = ctk.StringVar(value="0")
        self.v_clip_giay = ctk.StringVar(value="10")
        self.v_clip_tat_ca = ctk.StringVar(value="0")

        self.v_vat_the = ctk.StringVar(value="0")
        self.v_lop = ctk.StringVar(value="")

        # --- v3.0: doc bien so (RapidOCR, 100% tren may) ---
        # MAC DINH TAT de hanh vi cu khong doi.
        self.v_bien_so = ctk.StringVar(value="0")
        self.v_bien_so_dir = ctk.StringVar(value=THU_MUC_BIEN_SO)
        # rong = tu tim trong khung hinh (None khi dua xuong AnalysisConfig).
        self.v_bien_so_vung = ctk.StringVar(value="")
        self.v_bien_so_giay = ctk.StringVar(value="30")

        # --- v3.0: tu chup anh su kien ---
        # MAC DINH TAT. Khi TAT -> tu_chup_dir = "" (chuoi rong = tat, dung
        # quy tac cua cam_ai_core).
        self.v_tu_chup = ctk.StringVar(value="0")
        self.v_tu_chup_dir = ctk.StringVar(value=THU_MUC_ANH_SU_KIEN)
        self.v_tu_chup_giay = ctk.StringVar(value="10")

        # MAC DINH TAT: bat tach o se cham hon ~5.3 lan, rut fps live view.
        self.v_tach_o = ctk.StringVar(value="0")

        self.v_canh_bao = ctk.StringVar(value="0")
        self.v_cb_chuong = ctk.StringVar(value="1")
        self.v_cb_hop_thoai = ctk.StringVar(value="1")
        self.v_cb_telegram = ctk.StringVar(value="0")
        # --- canh bao noi bo (4 co bat_canh_ao cua AnalysisConfig) ---
        # "Chi thu" = MO PHONG: chi ghi nhat ky, KHONG keu chuong / mo hop
        # thoai / gui tin. MAC DINH BAT de nguoi dung khong bi kich hoat ngoai
        # vo y (mac dinh cua canh_bao.py la gui THAT).
        self.v_cb_mo_phong = ctk.StringVar(value="1")
        self.v_cb_go = ctk.StringVar(value="60")
        self.v_cb_gioi_han = ctk.StringVar(value="5")

        self.v_tien_trinh = ctk.StringVar(
            value=TRANG_THAI_TIEN_TRINH["chua_chay"])
        self.v_so_nguoi = ctk.StringVar(value="0")
        self.v_so_mat = ctk.StringVar(value="0")
        self.v_so_vao = ctk.StringVar(value="0")
        self.v_so_ra = ctk.StringVar(value="0")
        self.v_so_quen = ctk.StringVar(value="0")
        self.v_so_trong_vung = ctk.StringVar(value="0")

        # --- xem video truc tiep ---
        self.v_xem_video = ctk.StringVar(value="1")
        # v3.3: tach 2 o xem. "Xem truc tiep" = thread rieng do YOLO.
        # "Xem khung hinh ket qua" = pipeline gui anh co overlay (che do lo).
        self.v_xem_ket_qua = ctk.StringVar(value="1")
        self.v_nhan_ten = ctk.StringVar(value="1")   # rut ten len khung video
        self._tam_dung_xem = threading.Event()   # set = dang tam dung hinh
        self._ket_thuc_xem = threading.Event()   # set = thread xem phai dung
        self._anh_tk = None                      # GIU lai tham chieu ImageTk
        self._anh_gu = None                      # khung goc cuoi (de ve lai)
        self._anh_dang_co = False
        self._xem_dang_chay = False
        # --- v3.2: khung hinh che do phan tich theo lo (batch) ---
        # HOP THU 1 O (single slot): thread pipeline ghi de gia tri cuoi cung,
        # luong UI doc va xoa. KHONG dua vao `self.queue` (hang doi khong
        # gioi han -> phinh bo nho khi quet video dai).
        self._khung_hinh_moi = None           # bytes JPEG moi nhat
        self._lock_khung_hinh = threading.Lock()
        self._khung_hinh_seq = 0              # so lan co khung hinh moi
        self._khung_hinh_seq_da_doc = 0       # seq da hien thi tren panel
        self._hien_anh_batch = False          # dang hien khung hinh che do batch
        self._luc_gui_hinh = 0.0              # thoi diem gui khung hinh gan nhat
        self._ten_nguoi_quen = ""                # do UI thread gan, thread doc
        self._bar_cu = -1.0
        self._phan_tram_cu = ""
        self._kich_thuoc_hinh_cu = (0, 0)        # kich thuoc o hinh gan nhat
        # --- keo cua so ---
        self._kich_thuoc_cha_cu = (0, 0)    # kich thuoc khung cha vua thay doi
        self._job_ve_lai = None             # lenh after() dang cho ve lai
        self._dang_keo = False              # dang keo -> tam dung ve lai anh

    # -------------------------------------------------------- bo cuc chinh
    #
    # BO CUC 2 COT (anh Tuấn yeu cau "video phai la phan lon nhat"):
    #   cot 0 (co dinh ~430px) = CAI DAT  (chon video + 8 dong tinh nang + nut)
    #   cot 1 (giay)           = PHAN HIEN THI: video lon + so lieu + the doi
    #                            tuong + nhat ky
    # Cach cu 1 cot chong de video chi con mot o nho giua man hinh.
    # Cot cau hinh la CTkScrollableFrame de bam bung 1 tinh nang khong lam
    # day noi dung khong nhin thay het.

    def _dung_giao_dien(self):
        self.grid_columnconfigure(0, weight=0, minsize=RONG_COT_TRAI)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=0)

        # --- THANH DAU 64px (MASTER.md muc 5) ---
        self._thanh_dau()

        self._cot_cai_dat()
        self._cot_hien_thi()
        self._ap_dung_theme()          # mau chung cho toan bo widget da tao
        self._bang_video_mau()         # dai the video mau co anh xem truoc
        self._chuan_hoa_font()         # font Segoe UI cho the video mau

        self.lbl_loi = ctk.CTkLabel(
            self, text="", font=self.font_nho, text_color=MAU["loi"],
            anchor="w", wraplength=520, justify="left",
        )
        self.lbl_loi.grid(row=3, column=0, columnspan=3, sticky="ew",
                          padx=LE_NGOAI, pady=(0, 8))

    # ---------------------------------------------------------- THANH DAU

    def _thanh_dau(self) -> None:
        """THANH DAU 64px (MASTER.md muc 5).

        TRAI  : icon app + ten app (23px bold) + phien ban nho mau `chu_phu`.
        PHAI  : nut doi ngon ngu + nut DUNG + nut hanh dong chinh (BAT DAU).
        Nut dung / bat dau nam o day (khong phai cuoi cot trai) de nguoi dung
        luon thay noi "bat dau" o mot cho du co mo rong cua so hay khong.
        """
        khung = ctk.CTkFrame(self, fg_color=MAU["the"], corner_radius=0)
        khung.grid(row=0, column=0, columnspan=3, sticky="ew")
        khung.grid_propagate(False)
        khung.configure(height=64)
        khung.grid_columnconfigure(1, weight=1)      # cot spacer: day phai
        khung.grid_rowconfigure(0, weight=1)

        # --- TRAI: icon + ten + phien ban ---
        trai = ctk.CTkFrame(khung, fg_color="transparent")
        trai.grid(row=0, column=0, sticky="w", padx=(LE_NGOAI, 0))
        trai.grid_columnconfigure(1, weight=0)
        cot = 0
        if self._anh_icon_pil is not None:
            try:
                anh = ctk.CTkImage(light_image=self._anh_icon_pil,
                                   dark_image=self._anh_icon_pil,
                                   size=(30, 30))
                ctk.CTkLabel(trai, image=anh, text="", width=30).grid(
                    row=0, column=0, sticky="w", padx=(0, 10))
                cot = 1
            except Exception:                         # noqa: BLE001
                cot = 0
        ctk.CTkLabel(trai, text="CamAI", font=self.font_title,
                     text_color=MAU["chu"], anchor="w").grid(
            row=0, column=cot, sticky="w",
            padx=(0 if cot else 0, 8))
        ctk.CTkLabel(trai, text=f"v{VERSION}", font=self.font_nho,
                     text_color=MAU["chu_phu"], anchor="w").grid(
            row=0, column=cot + 1, sticky="w")

        # --- PHAI: nut doi ngon ngu ---
        self.btn_ngon_ngu = ctk.CTkButton(
            khung, text="English", width=112, height=KICH_THUOC["cao_nut"],
            font=self.font_nho, command=self._doi_ngon_ngu,
            fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
            text_color=MAU["chu"], border_width=1, border_color=MAU["vien"],
            corner_radius=BO_GOC_NUT,
        )
        self.btn_ngon_ngu._bo_toc_style = True
        self.btn_ngon_ngu._bo_ngon_ngu = True      # tu quan ly chu rieng
        self.btn_ngon_ngu.grid(row=0, column=2, sticky="e", padx=(0, 8))

        # --- PHAI: nut DUNG (nút phụ) ---
        # Icon = PAUSE (2 thanh doc) chu KHONG phai Stop (hinh vuong dac):
        # hinh vuong doc nho trong nut nho trong y như O VUONG THIEU GLYPH
        # (tofu) -> nguoi dung tuong lai app loi.
        self.btn_dung = ctk.CTkButton(
            khung, text="DỪNG", command=self._dung,
            height=KICH_THUOC["cao_nut"], width=104,
            image=self._anh_bieu_tuong("tam_dung", 14, (248, 250, 252, 255)),
            font=self.font_nut, state="disabled",
            fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
            text_color=MAU["chu"], border_width=1, border_color=MAU["vien"],
            corner_radius=BO_GOC_NUT,
        )
        self.btn_dung._bo_toc_style = True
        self.btn_dung.grid(row=0, column=3, sticky="e", padx=(0, 8))

        # --- PHAI: nut hanh dong chinh (nút chính) ---
        self.btn_chay = ctk.CTkButton(
            khung, text="BẮT ĐẦU", command=self._bat_dau,
            height=KICH_THUOC["cao_nut"], width=136,
            image=self._anh_bieu_tuong("phat", 14, (5, 46, 22, 255)),
            font=self.font_nut, fg_color=MAU["nut"], hover_color=MAU["nut_hover"],
            text_color=MAU["chu_nut"], corner_radius=BO_GOC_NUT,
        )
        self.btn_chay._bo_toc_style = True
        self.btn_chay.grid(row=0, column=4, sticky="e", padx=(0, LE_NGOAI))

    # ------------------------------------------------ cot 0: CAI DAT

    def _cot_cai_dat(self):
        """Cot ben trai: 4 MUC LON co nhom (cuon duoc).

        BOC CUC MOI (thay cho 12 dong tinh nang xep doc roi rac):
          1. NGUON            - mo san: chon video + noi luu ket qua
          2. PHAN TICH        - 7 muc con: nguoi / mat / ra vao / vung / clip /
                                vat the / nguoi o xa
          3. BIEN SO & ANH    - 2 muc con: doc bien so / tu chup anh
          4. CANH BAO & MO HINH - 3 muc con: canh bao / thong tin model /
                                may chay bang gi

        CHI 1 MUC LON MO TAI MOT LUC -> cot trai luon gon, khong phai cuon
        nhieu de tim cau hinh.

        Nut BAT DAU / DUNG da len THANH DAU nen cot nay khong con nut dieu
        khien - người dùng luon thay noi "bat dau" o mot cho.
        """
        f = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=MAU["nut_phu"],
            scrollbar_button_hover_color=MAU["nut_phu_hover"],
            label_text="",
        )
        f.grid(row=1, column=0, sticky="nsew", padx=(LE_NGOAI, 0), pady=(0, 4))
        f.grid_columnconfigure(0, weight=1)
        self._khung_tinh_nang(f)

    # ------------------------------------------------ cot 1: PHAN HIEN THI

    def _cot_hien_thi(self):
        """Cot ben phai: KHUNG VIDEO LON nhat + danh sach su kien ben phai.

        Bo cuc 3 vung theo mau tham chieu:
          * hang tren: huyen trang thai + thanh tien trinh.
          * khoi giua: COT TRAI (~72%) = video + so lieu, COT PHAI (~28%) =
            danh sach su kien (timeline).
          * hang duoi: nhat ky + nut mo ket qua.
        """
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.grid(row=1, column=1, sticky="nsew", padx=(KHOANG_CACH, 0))
        f.grid_columnconfigure(0, weight=TY_LE_COT_VIDEO)   # video: phan lon nhat
        f.grid_columnconfigure(1, weight=0, minsize=RONG_COT_SU_KIEN)
        f.grid_rowconfigure(1, weight=1)

        self._hang_trang_thai(f)

        hang = ctk.CTkFrame(f, fg_color="transparent")
        # PHAI span ca 2 cot: hang nay chua ca video (cot 0) va danh sach su
        # kien (cot 1). Neu chi dat o cot 0, ca khoi se bi bo vao be rong cua
        # cot 0 -> video bi ep nho.
        hang.grid(row=1, column=0, columnspan=2, sticky="nsew",
                  pady=(KHOANG_CACH, KHOANG_CACH))
        hang.grid_columnconfigure(0, weight=TY_LE_COT_VIDEO)
        hang.grid_columnconfigure(1, weight=0, minsize=RONG_COT_SU_KIEN)
        hang.grid_rowconfigure(0, weight=1)
        self._hang_chinh = hang          # canh be rong cot su kien theo cua so
        self._cot_video_va_so_lieu(hang)
        self._cot_su_kien(hang)
        self.after_idle(self._canh_be_rong_cot_su_kien)

        self._bang_nhat_ky(f)

    def _canh_be_rong_cot_su_kien(self) -> None:
        """Cot su kien CO LAI khi cua so hep, video luon giu >=70% be ngang.

        Do that 2026-10-23: cua so 1400px thi video 744px + cot su kien 320px
        = 69.9% -> HA CHIEU muc tieu 70%. O 1610px la 74.9%, o 1900px la 79.5%.
        Nguyen nhan: cot su kien dat `minsize` CO DINH 320 nen khong co lai.

        Cong thuc: b = clamp(200, 320, tong_be_ngang * 0.24). Chon 0.24 vi:
        video ~ tong - b nen video/(tong) luon > 0.70 tren moi kich thuoc cua so
        da do, ma van du chu trong the su kien de doc duoc.

        Phai set ca `minsize` cua cot LAI `width` cua panel: Tk lay be rong cua
        widget tu `reqwidth` (do noi dung thuc day), chi doi `minsize` thi panel
        van noi be rong noi dung va lam cot phinh to len.
        """
        hang = getattr(self, "_hang_chinh", None)
        if hang is None or not hang.winfo_exists():
            return
        panel = getattr(self, "panel_su_kien", None)
        tong = hang.winfo_width()
        if tong < 200:                  # Tk chua chot xong bo cuc
            return
        b = max(200, min(RONG_COT_SU_KIEN, int(tong * 0.24)))
        if abs(b - RONG_COT_SU_KIEN) < 1 and tong > 1400:
            return                      # cua so rong: giu nguyen 320
        hang.grid_columnconfigure(1, minsize=b)
        if panel is not None and panel.winfo_exists():
            panel.configure(width=b)

    def _cot_video_va_so_lieu(self, parent):
        """COT TRAI: video lon + so lieu gon (khong con panel doi tuong)."""
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=0, sticky="nsew", padx=(0, KHOANG_CACH))
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(0, weight=1)      # video an het chỗ cao con lai
        self._khung_xem_video(f)
        self._bang_so_lieu_gon(f)

    def _cot_su_kien(self, parent):
        """COT PHAI: DANH SACH SU KIEN (timeline), thay cho panel doi tuong."""
        self.panel_su_kien = PanelSuKien(
            parent, dich=self.dich, font_nho=self.font_nho_xam,
            font_nho_bold=self.font_nho_bold,
        )
        self.panel_su_kien.grid(row=0, column=1, sticky="nsew")

    def _hang_trang_thai(self, parent):
        """Hang tren: huyen trang thai mau + thanh tien trinh + chu chi tiết.

        3 o rieng biet (cot 0 / 1 / 2), khong cot nao co trong so day:
          * cot 0 - huyen trang thai, CHI CHU ngan ("Dang chay"), be rong co dinh.
          * cot 1 - thanh tien trinh, phan giua co the gian ra / lui vao.
          * cot 2 - nhan CHI TIET khung hinh, can phai, be rong co dinh.
        Nho vay huyen khong bao gio tran sang nhan chi tiet o bat ky kich
        thuoc cua so nao (truoc day ca 2 nhan cung in mot chuoi dai giong
        nhau nen bi dinh vao nhau o goc tren phai).
        """
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=0, sticky="ew")
        be_huyen = 168
        be_tien_trinh = 250
        f.grid_columnconfigure(0, weight=0, minsize=be_huyen)
        f.grid_columnconfigure(1, weight=1, minsize=90)
        f.grid_columnconfigure(2, weight=0, minsize=be_tien_trinh)

        # Huyen trang thai: 1 o mau + BIEU TUONG FONT WINDOWS + CHU ngan.
        # Tk khong ve duoc 2 font trong 1 chuoi -> huyen la 1 khung chua
        # 1 nhan icon (font Segoe MDL2 Assets) + 1 nhan chu (font Segoe UI).
        self.huyen = ctk.CTkFrame(
            f, fg_color=MAU_TRANG_THAI["chua_chay"], corner_radius=BO_GOC_THE,
            width=be_huyen, height=34,
        )
        self.huyen._bo_toc_style = True
        self.huyen._bo_ngon_ngu = True      # huyen tu quan ly chu rieng
        self.huyen.pack_propagate(False)
        self.huyen.grid(row=0, column=0, padx=(0, KHOANG_CACH))
        self.huyen.grid_columnconfigure(1, weight=1)
        self.huyen_icon = ctk.CTkLabel(
            self.huyen, text="", font=self.font_bieu_tuong,
            text_color=MAU["chu"], width=20,
        )
        self.huyen_icon.grid(row=0, column=0, padx=(10, 0))
        self.huyen_chu = ctk.CTkLabel(
            self.huyen, text="", font=self.font_nho_bold,
            text_color=MAU["chu"], anchor="w",
        )
        self.huyen_chu.grid(row=0, column=1, sticky="w", padx=(6, 10))

        self.bar = ctk.CTkProgressBar(f, height=16)
        self.bar.grid(row=0, column=1, sticky="ew", padx=(0, KHOANG_CACH))
        self.bar.set(0)

        ctk.CTkLabel(f, textvariable=self.v_tien_trinh, font=self.font_nho,
                     text_color=MAU["chu_phu"], anchor="e", width=be_tien_trinh
                     ).grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------ mau sac

    def _ap_dung_theme(self, goc=None) -> None:
        """Gan bang mau chuan cho MOI widget da tao (MASTER.md muc 6).

        * Nut phu   : nen `nut_phu`, chu `chu`, vien 1px `vien`, bo goc 8, cao 36.
        * Checkbox  : `checkmark_color` = `nut`, hover `nut_hover`, nhan 13px `chu`.
        * O nhap    : nen `the_phu`, chu `chu`, vien 1px `vien`, bo goc 6, cao 32.
        * Nhat ky   : nen `nen`, chu 12px `chu_phu`, font `Cascadia Mono`.
        Chi doi MAU + bo goc + kich thuoc, KHONG doi bo cuc (grid/padx/pady) va
        KHONG dung trong <Configure> nen khong ton hao gi khi rê chuot.
        Widget co `_bo_toc_style` (nut mui ten, nut tren thanh dau) duoc bo qua.
        """
        goc = self if goc is None else goc

        def quet(wdg):
            if getattr(wdg, "_bo_toc_style", False):
                pass
            elif isinstance(wdg, ctk.CTkButton):
                wdg.configure(
                    fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
                    text_color=MAU["chu"], border_width=1,
                    border_color=MAU["vien"],
                    corner_radius=BO_GOC_NUT, font=self.font_nut,
                    height=KICH_THUOC["cao_nut"],
                )
                self._vong_focus(wdg, be_rong=1)
            elif isinstance(wdg, ctk.CTkCheckBox):
                wdg.configure(
                    fg_color=MAU["nut"], hover_color=MAU["nut_hover"],
                    border_color=MAU["nut_phu"],
                    # Dau tick ve bang MAU TOI (nen) tren nen o XANH: neu ve
                    # cung mau nen o thi dau tick khong thay - nguoi dung
                    # khong biet o da tick hay chua.
                    checkmark_color=MAU["nen"],
                    text_color=MAU["chu"], font=self.font_nho,
                )
            elif isinstance(wdg, ctk.CTkEntry):
                wdg.configure(
                    fg_color=MAU["the_phu"], border_color=MAU["vien"],
                    border_width=1, text_color=MAU["chu"],
                    corner_radius=BO_GOC_O_NHAP,
                    height=KICH_THUOC["cao_o_nhap"], font=self.font_nho,
                )
                self._vong_focus(wdg)
            elif isinstance(wdg, ctk.CTkOptionMenu):
                wdg.configure(
                    fg_color=MAU["the_phu"], button_color=MAU["nut_phu"],
                    button_hover_color=MAU["nut_phu_hover"],
                    text_color=MAU["chu"], corner_radius=BO_GOC_O_NHAP,
                    height=KICH_THUOC["cao_o_nhap"], font=self.font_nho,
                )
            elif isinstance(wdg, ctk.CTkProgressBar):
                wdg.configure(fg_color=MAU["the_phu"], progress_color=MAU["nut"],
                              corner_radius=BO_GOC_NUT)
            elif isinstance(wdg, ctk.CTkTextbox):
                wdg.configure(fg_color=MAU["nen"], border_width=1,
                              border_color=MAU["vien"], text_color=MAU["chu_phu"],
                              corner_radius=BO_GOC_THE, font=self.font_code)
            for con in wdg.winfo_children():
                quet(con)

        quet(goc)
        # Dai the video mau (tao SAU `_ap_dung_theme`) + widget sinh tu dong
        # -> can 1 pass chuan hoa font rieng.
        self._chuan_hoa_font()

    def _chuan_hoa_font(self, goc=None) -> None:
        """Gan font Segoe UI cho widget nao customtkinter MAC DINH "Roboto".

        CustomTkinter mac dinh font la "Roboto" - font do KHONG co san tren
        Windows (app chay 100% offline) nen Tk phai tu tim font thay the.
        Pass nay gan dung font Segoe UI cho moi widget con sot.
        """
        goc = self if goc is None else goc

        def quet(wdg):
            if isinstance(wdg, (ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry,
                                ctk.CTkCheckBox, ctk.CTkOptionMenu)):
                try:
                    f = wdg.cget("font")
                except Exception:                     # noqa: BLE001
                    f = None
                can_doi = f is None
                if not can_doi and hasattr(f, "cget"):
                    try:
                        can_doi = str(f.cget("family")) == "Roboto"
                    except Exception:                 # noqa: BLE001
                        can_doi = False
                if can_doi:
                    try:
                        if isinstance(wdg, ctk.CTkButton):
                            wdg.configure(font=self.font_nut)
                        else:
                            wdg.configure(font=self.font_nho)
                    except Exception:                 # noqa: BLE001
                        pass
            for con in wdg.winfo_children():
                quet(con)

        quet(goc)

    def _vong_focus(self, wdg, be_rong: int = 1) -> None:
        """Vien sang khi focus (CustomTkinter khong co focus ring san san).

        `be_rong` = do dai vien luc KHONG focus (nut = 0, o nhap = 1).
        """
        def vao(_e=None):
            try:
                wdg.configure(border_width=2, border_color=MAU["focus"])
            except Exception:                             # noqa: BLE001
                pass

        def ra(_e=None):
            try:
                wdg.configure(border_width=be_rong,
                              border_color=MAU["vien"])
            except Exception:                             # noqa: BLE001
                pass

        try:
            wdg.bind("<FocusIn>", vao, add="+")
            wdg.bind("<FocusOut>", ra, add="+")
        except Exception:                                 # noqa: BLE001
            pass

    # ---------------------------------------------------------- hang video

    def _be_nut_chu(self, chuoi: str, min_be: int = 90) -> int:
        """Be ngang (px) cua nut vua du cho `chuoi` - tranh chu bi cat.

        Do bang font thuc te (`font_nut`) chu khong do dai chu co dinh ->
        nut luon vua khong cat chu khi cua so / font doi.
        """
        try:
            do = int(self.font_nut.measure(chuoi))
        except Exception:                             # noqa: BLE001
            do = len(chuoi) * 8
        return max(min_be, do + 22)

    def _hang_video(self, parent):
        """Khoi CHON NGUON: video / anh / camera + thu muc luu ket qua.

        Nhan o DONG TREN, o nhap o DONG DUOI (dung rong 288px) - duong dan
        video thuong dai hon 250px, xep cung hang voi nhan thi bi CAT CHU.
        Tooltip (`HuongDan`) hien TOAN BO duong dan khi re chuot vao o.

        O "Nguon" (truoc day la "Video") chua 4 kieu vao:
          * duong dan video (mp4/avi/...)
          * duong dan ANH TINH (jpg/png/...)
          * index camera may ("0")
          * dia chi camera IP (rtsp://... hoac http://...)

        Video mau KHONG nam o day: no la MOT DAI THE ANH XEM TRUOC chay
        ngang o duoi cua so (`_bang_video_mau`).
        """
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=self._dong_moi(parent), column=0, sticky="ew",
               pady=(0, GD.KHOANG_CACH["lon"]))
        f.grid_columnconfigure(0, weight=1)

        # --- 1. NGUON ---
        ctk.CTkLabel(f, text="Nguồn", font=self.font_nho,
                     text_color=MAU["chu"], anchor="w").grid(
            row=0, column=0, sticky="w")
        o_video = ctk.CTkEntry(f, textvariable=self.v_video)
        o_video.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        # Duong dan dai hon o -> tooltip hien day du.
        HuongDan(o_video, lambda: self.v_video.get(), font=self.font_nho_xam)

        # Dong nhan trang thai: loai nguon hien tai. Tu cap nhat moi khi o
        # nguon doi (ke ca khi nguoi dung go tay) - xem `_cap_nhat_nhan_nguon`.
        self.lbl_nguon = ctk.CTkLabel(f, text="", font=self.font_nho_xam,
                                      text_color=MAU["chu_phu"], anchor="w")
        self.lbl_nguon.grid(row=2, column=0, sticky="w", pady=(3, 0))

        f_nut = ctk.CTkFrame(f, fg_color="transparent")
        f_nut.grid(row=3, column=0, sticky="ew",
                   pady=(GD.KHOANG_CACH["nho"], 0))
        f_nut.grid_columnconfigure(0, weight=0)
        f_nut.grid_columnconfigure(1, weight=1)
        # Be ngang nut TINH THEO CHU (do font ra) - tranh chu bi cat khi
        # cua so hep (cot cau hinh chi ~288px).
        ctk.CTkButton(f_nut, text="Chọn video…",
                      width=self._be_nut_chu("Chọn video…"),
                      command=self._chon_video, anchor="w").grid(
            row=0, column=0, sticky="w")
        ctk.CTkButton(f_nut, text="Chọn ảnh…",
                      width=self._be_nut_chu("Chọn ảnh…"),
                      command=self._chon_anh, anchor="w").grid(
            row=0, column=1, sticky="w",
            padx=(GD.KHOANG_CACH["nho"], 0))
        ctk.CTkButton(f_nut, text="Chọn camera…",
                      width=self._be_nut_chu("Chọn camera…"),
                      command=self._chon_camera, anchor="w").grid(
            row=1, column=0, sticky="w",
            pady=(GD.KHOANG_CACH["nho"], 0))
        ctk.CTkButton(f_nut, text="Danh sách camera",
                      width=self._be_nut_chu("Danh sách camera"),
                      command=self._xem_danh_sach_camera, anchor="w").grid(
            row=1, column=1, sticky="w",
            padx=(GD.KHOANG_CACH["nho"], 0),
            pady=(GD.KHOANG_CACH["nho"], 0))
        ctk.CTkButton(f_nut, text="Mở thư mục clip",
                      width=self._be_nut_chu("Mở thư mục clip"),
                      fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
                      command=self._mo_thu_muc_clip
                      ).grid(row=2, column=0, columnspan=2, sticky="w",
                             pady=(GD.KHOANG_CACH["nho"], 0))

        # O nguon doi -> dong nhan loai nguon doi theo.
        self.v_video.trace_add("write", self._cap_nhat_nhan_nguon)
        self._cap_nhat_nhan_nguon()

        # --- 2. LUU KET QUA ---
        ctk.CTkLabel(f, text="Lưu kết quả", font=self.font_nho,
                     text_color=MAU["chu"], anchor="w").grid(
            row=4, column=0, sticky="w", pady=(GD.KHOANG_CACH["vua"], 0))
        o_output = ctk.CTkEntry(f, textvariable=self.v_output)
        o_output.grid(row=5, column=0, sticky="ew", pady=(4, 0))
        HuongDan(o_output, lambda: self.v_output.get(), font=self.font_nho_xam)

        f_out = ctk.CTkFrame(f, fg_color="transparent")
        f_out.grid(row=6, column=0, sticky="ew",
                   pady=(GD.KHOANG_CACH["nho"], 0))
        ctk.CTkButton(f_out, text="Chọn…", width=140,
                      command=self._chon_output, anchor="w").grid(
            row=0, column=0, sticky="w")
        # Ghi chu phai nam o HANG RIENG ben duoi nut: dat cung hang voi nut
        # 140px thi con it chua 140px chu -> bi cat ngang giua dong.
        ctk.CTkLabel(f_out,
                     text="Tự thêm đuôi: _ket_qua.mp4 và _bao_cao.csv",
                     font=self.font_nho_xam, text_color=MAU["chu_phu"],
                     anchor="w", wraplength=WRAP_GHI_Y, justify="left"
                     ).grid(row=1, column=0, columnspan=2, sticky="w",
                            pady=(2, 0))

    # ---------------------------------------------------- khung tinh nang

    def _khung_tinh_nang(self, parent):
        """4 MUC LON + 12 MUC CON ben trong.

        NOI DUNG 12 MUC CON GIANG NGUYEN HET ban cu (cung bien, cung handler,
        cung chu hien thi) - chi doi CACH TRINH BAY: cac muc con nam trong
        muc lon tuong ung thay vi xep doc roi rac.

        Chi 1 muc lon mo tai mot thoi (xem `NhomLon.dat_mo`).
        Moi muc con duoc gan vao self.nhom_* de tien kiem chung.
        """
        self._ds_nhom_lon = []

        # ============================ 1. NGUON (mo san) =========================
        n_nguon = self._them_nhom_lon(
            parent, "NGUỒN",
            "Chọn video cần phân tích và nơi lưu kết quả",
            mo_san=True)
        # Chon video + Luu ket qua: giong het ban cu, chi chuyen vao muc lon.
        self._hang_video(n_nguon.khung)

        # ============================ 2. PHAN TICH =============================
        n_pt = self._them_nhom_lon(
            parent, "PHÂN TÍCH",
            "Bật các bước nhận diện: người, mặt, ra vào")
        b = n_pt.khung

        self.nhom_phat_hien = self._them_nhom(
            b, 0, "Phát hiện người", self.v_phat_hien,
            "Đếm có bao nhiêu người trong khung hình. Đây là bước đầu tiên, "
            "mọi tính năng khác đều dựa vào nó.",
            [(self.v_conf, "0.25"), (self.v_model, "yolo11n.pt"),
             (self.v_khung, "1"), (self.v_nhan, "1"), (self.v_pixelate, "0")])
        self._n_phat_hien(self.nhom_phat_hien.khung)

        self.nhom_mat = self._them_nhom(
            b, 1, "Nhận diện khuôn mặt", self.v_face,
            "Dùng để biết người đó là ai. Cần có ảnh đăng ký trước trong thư mục known_faces.",
            [(self.v_face_threshold, "0.40"), (self.v_min_face, "0"),
             (self.v_face_every, "1"),
             (self.v_faces_dir, os.path.join(APP_DIR, "known_faces"))])
        self._n_mat(self.nhom_mat.khung)

        self.nhom_dem = self._them_nhom(
            b, 2, "Đếm ra vào", self.v_dem_ra_vao,
            "Vạch nằm ở giữa khung hình, đếm người đi qua vạch theo hướng vào / ra.")

        self.nhom_vung = self._them_nhom(
            b, 3, "Canh vùng", self.v_vung,
            "Khoanh một vùng trong khung hình rồi cảnh báo khi có người vào vùng đó. "
            "Phải vẽ vùng trước bằng nút bên dưới.",
            [(self.v_vung_nhay, "0"), (self.v_vung_max, "2"),
             (self.v_canh_lau, "3.0")])
        self._n_vung(self.nhom_vung.khung)

        self.nhom_clip = self._them_nhom(
            b, 4, "Lưu clip khi có sự kiện", self.v_clip,
            "Tự cắt và lưu đoạn video quanh lúc có chuyện vào thư mục clip_da_luu. "
            "Mặc định tắt để cho máy chạy nhẹ.",
            [(self.v_clip_giay, "10"), (self.v_clip_tat_ca, "0")])
        self._n_clip(self.nhom_clip.khung)

        self.nhom_vat_the = self._them_nhom(
            b, 5, "Thêm vật thể khác", self.v_vat_the,
            "Ngoài người, còn vẽ khung và đếm các vật thể khác (xe, chó, mèo). "
            "Mặc định tắt.",
            [(self.v_lop, "")])
        self._n_vat_the(self.nhom_vat_the.khung)

        self.nhom_tach_o = self._them_nhom(
            b, 6, "Nhận người ở xa (chậm hơn)", self.v_tach_o,
            "Video quay xa, người nhỏ như hạt thì CamAI hay bỏ sót. Bật lên "
            "phần mềm sẽ chia khung hình thành các ô nhỏ để dò kỹ hơn. "
            "CHẬM HƠN KHOẢNG 5 LẦN nên xem chậm hơn — chỉ bật khi thật sự "
            "cần. Camera treo cao quay gần thì không cần.")
        self._n_tach_o(self.nhom_tach_o.khung)

        # ========================= 3. BIEN SO & ANH ============================
        n_bs = self._them_nhom_lon(
            parent, "BIỂN SỐ & ẢNH",
            "Đọc biển số xe và tự chụp ảnh sự kiện")
        b = n_bs.khung

        self.nhom_bien_so = self._them_nhom(
            b, 0, "Đọc biển số xe", self.v_bien_so,
            "Đọc chữ trên biển số xe Việt Nam bằng RapidOCR — chạy 100% "
            "trên máy này, không gửi ảnh ra ngoài.",
            [(self.v_bien_so_vung, ""), (self.v_bien_so_giay, "30")])
        self._n_bien_so(self.nhom_bien_so.khung)

        self.nhom_tu_chup = self._them_nhom(
            b, 1, "Tự chụp ảnh khi có sự kiện", self.v_tu_chup,
            "Khi có người đông, vượt vùng hoặc thấy người quen thì chụp "
            "lại khung hình lưu thành ảnh. Mặc định tắt.",
            [(self.v_tu_chup_giay, "10")])
        self._n_tu_chup(self.nhom_tu_chup.khung)

        # ======================= 4. CANH BAO & MO HINH =========================
        n_cb = self._them_nhom_lon(
            parent, "CẢNH BÁO & MÔ HÌNH",
            "Chuông/hộp thoại khi có người lạ, và thông tin AI")
        b = n_cb.khung

        self.nhom_canh_bao = self._them_nhom(
            b, 0, "Cảnh báo (gửi tin ra ngoài)", self.v_canh_bao,
            "Khi có sự kiện thì báo ra ngoài máy này (chuông / hộp thoại / "
            "Telegram). Mặc định TẮT, và mặc định chỉ thử chứ không gửi thật.",
            [(self.v_cb_mo_phong, "1"), (self.v_cb_go, "60"),
             (self.v_cb_gioi_han, "5")])
        self._n_canh_bao(self.nhom_canh_bao.khung)

        self.nhom_model = self._them_nhom(
            b, 1, "Thông tin mô hình AI", ctk.StringVar(value="1"),
            "Xem phần mềm đang dùng model nào, nặng bao nhiêu, chạy trên GPU hay CPU.",
            co_checkbox=False)
        self._n_model(self.nhom_model.khung)

        self.nhom_thiet_bi = self._them_nhom(
            b, 2, "Máy này chạy bằng gì", ctk.StringVar(value="1"),
            "Máy có GPU thì CamAI tự chạy bằng card màn hình cho nhanh. "
            "Máy không có GPU thì chạy bằng CPU, vẫn chạy được nhưng chậm hơn. "
            "Không rành thì cứ để “Tự động”.",
            co_checkbox=False)
        self._n_thiet_bi(self.nhom_thiet_bi.khung)

    def _them_nhom_lon(self, parent, ten: str, mo_ta: str,
                       mo_san: bool = False) -> NhomLon:
        """Tao 1 MUC LON (the co tieu de HOA + mo ta) trong cot trai.

        Moi muc lon duoc ghi vao `self._ds_nhom_lon` de khi mo 1 muc lon thi
        cac muc lon khac tu dong thu gon.
        """
        nhom = NhomLon(
            parent, ten, mo_ta,
            font_tieu_de=self.font_muc_lon,
            font_mo_ta=self.font_nho_xam,
            font_bieu_tuong=self.font_bieu_tuong,
            mo_san=mo_san,
        )
        nhom.grid(row=self._dong_moi(parent), column=0, sticky="ew",
                  pady=(0, KHOANG_CACH))
        self._ds_nhom_lon.append(nhom)
        # Moi muc lon biet cac muc lon khac -> tu dong dong nhanh.
        for n in self._ds_nhom_lon:
            n._cac_nhom_lon = self._ds_nhom_lon
        return nhom

    def _them_nhom(self, parent, dong, ten, var, lenh, mac_dinh=(),
                   co_checkbox=True) -> NhomTinhNang:
        """Tao 1 MUC CON (nhom tinh nang) trong 1 MUC LON.

        Ten muc con dung 13px `chu` (nho hon tieu de muc lon 15px HOA) - muc
        lon moi la noi bat, muc con chi la dong menu ben trong.
        """
        nhom = NhomTinhNang(
            parent, ten, var, lenh=lenh, font=self.font_nho,
            font_nho=self.font_nho_xam, font_bieu_tuong=self.font_bieu_tuong,
            mac_dinh=mac_dinh, co_checkbox=co_checkbox,
        )
        # Muc con -> biet muc long cha (mo muc con -> mo muc long cha).
        nhom.nhom_lon_cha = getattr(parent, "_nhom_lon", None)
        nhom.grid(row=dong, column=0, sticky="ew", pady=(0, KHOANG_CACH))
        return nhom

    def danh_sach_nhom(self) -> list[tuple[str, NhomTinhNang]]:
        """Danh sach (ten hien thi, nhom) theo dung thu tu tren man hinh.

        Thu tu nay KHOAC nhau 4 MUC LON: PHAN TICH / BIEN SO & ANH /
        CANH BAO & MO HINH.

        Dung cho _kiem_tra_gui.py va cho nguoi sau de doc lai file nay.
        """
        return [
            (getattr(self, ten).chk.cget("text"), getattr(self, ten))
            for ten in ("nhom_phat_hien", "nhom_mat", "nhom_dem", "nhom_vung",
                        "nhom_clip", "nhom_vat_the", "nhom_tach_o",
                        "nhom_bien_so", "nhom_tu_chup",
                        "nhom_canh_bao", "nhom_model", "nhom_thiet_bi")
        ]

    # ------------------------------------------- them hang vao khung cau hinh

    def _dong_moi(self, parent) -> int:
        """Cap 1 so dong moi trong khung cau hinh (parent)."""
        dong = getattr(parent, "_dong", 0)
        parent._dong = dong + 1
        return dong

    def _hang(self, parent, ten: str = "", do_rong: int = LABEL_WIDTH) -> ctk.CTkFrame:
        """1 hang trong khung cau hinh: nhan ben trai + o dieu khien ben phai.

        COT NHAN co be rong CO DINH (`do_rong`) va cot dieu khien nam trong
        1 COT CO DINH -> moi hang deu thang hang theo cot, khong lech nhau.
        `wraplength = do_rong` rat quan trong: CTkLabel tu do rong theo CHU,
        nen nhan dai ("Danh sách lớp cần nhận") se lon hon cot va TRAN QUA
        sang o dieu khien ben phai, khong con khoang hở nao. Bat wraplength
        thi chu xuong dong trong dung be 124px -> khong bao gio cham o nhap.

        Cot 1 (o dieu khien) co `minsize` = phan con lai cua 264px. Ly do:
        nut rong 260px dat o cot 0 + `columnspan=2` -> khi hang chua duoc ve
        (nhom con nam trong 1 muc lon dang thu gon) Tk tinh be rong theo kich
        thuoc toi thieu tung cot, cot 1 (khong co widget truc tiep) = 0 -> nut
        bi bop con 124px va CHU BI CAT. `minsize` giu hang luon du rong.
        """
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=self._dong_moi(parent), column=0, sticky="ew",
               pady=(KHOANG_CACH, 0))
        # Cot 0 = NHAN (be rong co dinh), cot 1 = O DIEU KHIEN (phan con lai).
        f.grid_columnconfigure(0, weight=0, minsize=do_rong)
        f.grid_columnconfigure(
            1, weight=1,
            minsize=max(0, BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - do_rong))
        if ten:
            ctk.CTkLabel(
                f, text=ten, anchor="w", width=do_rong, justify="left",
                font=self.font_nho, text_color=MAU["chu"],
                wraplength=do_rong,
            ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        return f

    def _hang_rong(self, parent, ten: str) -> ctk.CTkFrame:
        """Hang cau hinh DUNG rong: nhan o dong TREN, o dieu khien o dong DUOI.

        Dung khi 1 hang khong du chua nhan + o nhap + nut: be trong cua nhom
        chi 264px nen 3 thu tren cung 1 hang se lam o nhap bijep (chi con
        ~6px - khong go duoc). O day nhan doc 1 dong rieng, o nhap + nut
        duoc hieu rong cua ca khoi cau hinh.
        """
        ctk.CTkLabel(
            parent, text=ten, anchor="w", justify="left",
            font=self.font_nho, text_color=MAU["chu"],
        ).grid(row=self._dong_moi(parent), column=0, sticky="w")
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=self._dong_moi(parent), column=0, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        return f

    def _ghi_y(self, parent, text: str) -> None:
        """1 dong ghi chu nho, thut lui ve dung be nhan.

        Be ngat dong tinh tu be rong THAT con lai (do that 2026-10-19) chu
        khong dat so tu nghieng - xem `WRAP_GHI_Y`. Nhan nam ngay duoi hang
        dieu khien, dung le cua khung de doc lai de thay no thuoc ve gi.
        """
        ctk.CTkLabel(
            parent, text=text, font=self.font_nho_xam,
            text_color=MAU["chu_phu"],
            anchor="w", wraplength=WRAP_GHI_Y, justify="left",
        ).grid(row=self._dong_moi(parent), column=0, sticky="w",
               padx=(LE_GHI_Y, 0), pady=(2, 0))

    def _don_vach(self, parent) -> None:
        """Vach ngang phan tach 2 phan cau hinh trong cung 1 nhom."""
        f = ctk.CTkFrame(parent, fg_color="transparent", height=10)
        f.grid(row=self._dong_moi(parent), column=0, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(f, fg_color=MAU["vien"], height=1,
                     corner_radius=0).grid(row=0, column=0, sticky="ew")

    def _checkbox(self, parent, text: str, variable, **kwargs) -> ctk.CTkCheckBox:
        """Checkbox co CHU XUONG DONG khi khung cau hinh hep.

        CustomTkinter khong cho dat `wraplength` truc tiep cho checkbox, nen
        tu dat cho tkinter.Label ben trong (noi dung text cua checkbox).
        Chu dai vay khong bi cat o mep khung cau hinh (cot trong chi 232px).
        """
        chk = ctk.CTkCheckBox(parent, text=text, variable=variable, **kwargs)
        try:
            chk._text_label.configure(wraplength=WRAP_CHECKBOX)
        except Exception:                                     # noqa: BLE001
            pass
        return chk

    def _dich_widget(self, wdg, chu_vi: str):
        """Chuoi hien thi cua widget: dich ngay + GIU chu tieng Viet GOC.

        CANH BAO: `self.dich()` luc TAO widget chi dung khi app khoi dong o
        tieng Viet. Neu app khoi dong o tieng Anh, text da la tieng Anh ->
        `_ghi_nhan_chu` se ghi nham SAI chu goc -> khi chuyen ve tieng Viet
        chu khong doi lai. `_dich_widget` gan `_chu_vi` = chu tieng Viet GOC
        TRUOC khi `_ghi_nhan_chu` chay -> doi ngon ngu 2 chieu deu dung.
        """
        try:
            wdg._chu_vi = chu_vi
        except Exception:                                     # noqa: BLE001
            pass
        return wdg

    # ------------------------------------------------------ nhom 1: nguoi

    def _n_phat_hien(self, b):
        f = self._hang(b, "Ngưỡng tin cậy")
        ctk.CTkEntry(f, textvariable=self.v_conf, width=90).grid(
            row=0, column=1, sticky="w")
        self._ghi_y(b, "0,25 = mặc định. Hạ xuống sẽ bắt được cả người ở xa, "
                       "nhưng nhiều khi bắt nhầm.")

        f = self._hang(b, "Mô hình nhận diện")
        ctk.CTkOptionMenu(
            f, values=["yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt"],
            variable=self.v_model, width=120,
        ).grid(row=0, column=1, sticky="ew")
        self._ghi_y(b, "yolo11n = nhẹ nhất, chạy nhanh nhất. Không rành thì để yolo11n.")

        f = self._hang(b, "Chạy bằng")
        ctk.CTkOptionMenu(
            f, values=list(GIA_TRI_CHE_THIET_BI),
            variable=self.v_thiet_bi, width=120,
        ).grid(row=0, column=1, sticky="ew")
        self._ghi_y(b, "Đo thật trên máy này: card màn hình nhanh hơn CPU "
                       "khoảng 2 lần khi chỉ đếm người, khoảng 2,5 lần khi "
                       "bật nhận diện mặt. Máy không có card thì để "
                       "“Tự động” là chạy được.")

        self._don_vach(b)
        f = self._hang(b, "Hiển thị trên video")
        # 3 checkbox, MOI CAI 1 DONG RIENG: truoc day 3 cai cung 1 hang
        # thi cai 1 bi ep con 1px (khong bam duoc) va cai 2 bi cat chu.
        # Moi checkbox span TRON 2 cot (dung rong 264px) + 1 dong ghi chu.
        for ten, bien, ghi_chu in (
                ("Vẽ khung người", self.v_khung,
                 "Vẽ khung quanh mỗi người trong khung hình."),
                ("Vẽ nhãn tên", self.v_nhan,
                 "Ghi tên lên khung nếu nhận diện được người quen."),
                ("Làm mờ nền, giữ rõ chỗ có người", self.v_pixelate,
                 "Làm mờ nền để dễ nhìn thấy người.")):
            f2 = self._hang(b, "")
            self._checkbox(f2, ten, bien, font=self.font_nho,
                           onvalue="1", offvalue="0").grid(
                row=0, column=0, columnspan=2, sticky="w")
            self._ghi_y(b, ghi_chu)

    # --------------------------------------------------------- nhom 2: mat

    def _n_mat(self, b):
        self._ghi_y(b, "Tắt ô này thì phần mềm CHỈ đếm người, không nhận "
                       "diện ai. Đo thật: nhanh hơn khoảng 2,5 lần lúc "
                       "camera đông người, khoảng 2 lần lúc camera vắng. "
                       "Đếm người không bị ảnh hưởng.")

        f = self._hang_rong(b, "Ước lượng tuổi và giới tính")
        self._checkbox(f, "Bật (luôn bật, phần mềm không cho tắt)",
                       self.v_uoi_gioi(), font=self.font_nho,
                       state="disabled").grid(row=0, column=0, sticky="w")
        self._ghi_y(b, "Chỉ là ước lượng, không chính xác tuyệt đối. "
                       "cam_ai_core không có tham số tắt tính năng này.")

        f = self._hang(b, "Ngưỡng giống mặt")
        ctk.CTkEntry(f, textvariable=self.v_face_threshold, width=90).grid(
            row=0, column=1, sticky="w")
        self._ghi_y(b, "Cao hơn = dễ nhận nhầm người khác. "
                       "Thấp hơn = dễ không nhận ra người quen. "
                       "Mặc định 0,40.")

        f = self._hang(b, "Bỏ qua mặt nhỏ hơn (px)")
        ctk.CTkEntry(f, textvariable=self.v_min_face, width=90).grid(
            row=0, column=1, sticky="w")
        self._ghi_y(b, "Mặt nhỏ hơn cỡ này thì bỏ qua, không hỏi ai. Để 0 = không bỏ.")

        f = self._hang(b, "Quét mặt mỗi (khung hình)")
        ctk.CTkEntry(f, textvariable=self.v_face_every, width=90).grid(
            row=0, column=1, sticky="w")
        self._ghi_y(b, "Đo thật trên video đông người (10 người/khung): "
                       "1 -> 5,2 khung/giây · 2 -> 7,6 · 5 -> 12,5 · 10 -> 23,4. "
                       "Đếm người KHÔNG đổi, chỉ giảm số lần quét mặt. "
                       "Máy chấm công (người đứng ở cửa) để 5 là đủ. "
                       "Giám sát người đi qua nhanh thì để 1–2. "
                       "Camera vắng người thì nhận được nhiều hơn các số trên.")

        f = self._hang_rong(b, "Thư mục ảnh đã học")
        ctk.CTkEntry(f, textvariable=self.v_faces_dir).grid(
            row=0, column=0, sticky="ew")
        ctk.CTkButton(f, text="Chọn…", width=80,
                      command=self._chon_faces_dir).grid(
            row=0, column=1, padx=(GD.KHOANG_CACH["nho"], 0))
        self._ghi_y(b, "Cấu trúc: known_faces / <Tên> / *.jpg — mỗi người một thư mục con.")

        f = self._hang(b, "")
        self.btn_dang_ky = self._dich_widget(ctk.CTkButton(
            f, text=self.dich("Đăng ký người quen…"), width=260,
            command=self._mo_dang_ky_nguoi_quen,
        ), "Đăng ký người quen…")
        self.btn_dang_ky.grid(row=0, column=0, columnspan=2, sticky="w")
        self._ghi_y(b, "Chọn 1 ảnh hoặc 1 video có người quen, phần mềm tự "
                       "tìm mặt và lưu vào thư mục của người đó.")

        f = self._hang(b, "")
        self.btn_hoc_lai = ctk.CTkButton(
            f, text="Đọc lại danh sách người đã học", width=260,
            command=self._ve_lai_nguoi_hoc,
        )
        self.btn_hoc_lai.grid(row=0, column=0, columnspan=2, sticky="w")

    def v_uoi_gioi(self) -> ctk.StringVar:
        """Bien hien thi 'uoc luong tuoi va gioi tinh'.

        cam_ai_core KHONG co tham so de tat uoc luong tuoi/gioi tinh:
        face_engine luon chay genderage khi bat nhan dien khuon mat.
        Vi vay checkbox nay chi de cho anh thay co, va khoa khong cho tat -
        giong het hanh vi that cua phan mem. KHONG sua cam_ai_core.py de them.
        """
        if not hasattr(self, "_v_uoi_gioi"):
            self._v_uoi_gioi = ctk.StringVar(value="1")
        return self._v_uoi_gioi

    # ------------------------------------------------------- nhom 3: dem

    # (nhom "Dem ra vao" khong co o cau hinh rieng: chi 1 checkbox, dung mo
    #  nhom cung khong sao. Cac muc dem chi co 1 bien show_line trong core.)

    # --------------------------------------------------------- nhom 4: vung

    def _n_vung(self, b):
        f = self._hang_rong(b, "File vùng (.txt)")
        ctk.CTkEntry(f, textvariable=self.v_vung_file).grid(
            row=0, column=0, sticky="ew")
        ctk.CTkButton(f, text="Chọn…", width=80,
                      command=self._chon_vung_file).grid(
            row=0, column=1, padx=(GD.KHOANG_CACH["nho"], 0))

        f = self._hang(b, "")
        ctk.CTkButton(f, text="Vẽ vùng trên video này", width=260,
                      command=self._mo_ve_vung).grid(
            row=0, column=0, columnspan=2, sticky="w")
        self._ghi_y(b, "Mở cửa sổ riêng: xem video, kéo chuột khoanh vùng, "
                       "lưu lại thành file .txt.")

        f = self._hang(b, "")
        self.btn_ve_vung_tai_day = self._dich_widget(ctk.CTkButton(
            f, text=self.dich("Vẽ vùng ngay tại đây"), width=260,
            command=self._ve_vung_ngay_tai_day,
        ), "Vẽ vùng ngay tại đây")
        self.btn_ve_vung_tai_day.grid(row=0, column=0, columnspan=2, sticky="w")
        self._ghi_y(b, "Vẽ ngay trong cửa sổ này: kéo chuột khoanh vùng rồi "
                       "bấm Lưu. Cần chọn video trước.")

        f = self._hang(b, "")
        self._checkbox(f, "Chỉ cần một phần chân vào vùng là bị báo",
                       self.v_vung_nhay, font=self.font_nho,
                       onvalue="1", offvalue="0").grid(
            row=0, column=0, columnspan=2, sticky="w")
        self._ghi_y(b, "Tắt = chặt: cả người phải nằm hẳn trong vùng mới báo. "
                       "Bật = nhạy: thân chạm vùng là báo ngay.")

        f = self._hang(b, "Cảnh báo khi vượt quá (người)")
        ctk.CTkEntry(f, textvariable=self.v_vung_max, width=90).grid(
            row=0, column=1, sticky="w")
        self._ghi_y(b, "Nhập 0 để tắt cảnh báo này.")

        f = self._hang(b, "Cảnh báo khi người đứng lâu (giây)")
        ctk.CTkEntry(f, textvariable=self.v_canh_lau, width=90).grid(
            row=0, column=1, sticky="w")
        self._ghi_y(b, "Nhập 0 để tắt cảnh báo này.")

    # -------------------------------------------------------- nhom 5: clip

    def _n_clip(self, b):
        f = self._hang(b, "Tổng thời lượng 1 clip (giây)")
        ctk.CTkEntry(f, textvariable=self.v_clip_giay, width=90).grid(
            row=0, column=1, sticky="w")
        self._ghi_y(b, "Chia đôi: một nửa trước sự kiện, một nửa sau sự kiện.")

        f = self._hang(b, "")
        ctk.CTkCheckBox(
            f, text="Ghi clip cả khi không bật canh vùng",
            font=self.font_nho, variable=self.v_clip_tat_ca, onvalue="1", offvalue="0"
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        self._ghi_y(b, "Mặc định chỉ ghi clip khi có chuyện trong vùng canh. "
                       "Bật ô này thì thấy người là ghi luôn.")

    # ------------------------------------------------------ nhom 6: vat the

    def _n_vat_the(self, b):
        f = self._hang(b, "Danh sách lớp cần nhận")
        o_lop = ctk.CTkEntry(f, textvariable=self.v_lop)
        o_lop.grid(row=0, column=1, sticky="ew")
        # Goi y trong o phai NGAN: cot ben trai hep, do that "de trong = nhom
        # mac dinh" rong 142px -> tran ra ngoai o. Phan giai day du: tooltip.
        GoiYTronO(o_lop, "mặc định", font=self.font_nho)
        # Tooltip dung LAMBDA -> noi dung lay lai luc mo (doi ngon nung thi
        # tooltip hien tieng Anh, khong phai chu Viet cu).
        HuongDan(o_lop, lambda: self.dich(
            "Gõ lớp cần nhận, cách nhau bằng dấu phẩy. "
            "Nhận được cả tiếng Việt: ô tô, xe máy, chó, mèo… "
            "(để trống = dùng nhóm lớp mặc định, gõ all = mọi lớp trừ người)."),
                 font=self.font_nho)
        self._ghi_y(b, "Ví dụ: ô tô, xe máy, chó, mèo hoặc "
                       "car, motorcycle, dog, cat — cách nhau bằng dấu phẩy. "
                       "Để trống = nhóm lớp phổ biến. Gõ all = mọi lớp trừ người.")
        self._ghi_y(b, "Tốc độ: gần như không chậm đi. Đo thật ngày 19/10/2026 trên "
                       "video nhiều xe, xem trực tiếp chậm hơn khoảng 3–9%, và "
                       "chậm hơn nhiều hơn khi bật lớp `all`.")
        self._ghi_y(b, "Lý do: YOLO vốn đã nhận sẵn toàn bộ 80 lớp trong 1 lượt, "
                       "nên bật thêm chỉ tốn công vẽ thêm khung, không phải chạy "
                       "model thêm lần nữa.")
        self._ghi_y(b, "Lưu ý: khung vật thể vẽ màu cam và KHÔNG tính vào số "
                       "người, số vào/ra, cảnh báo vùng.")

    # ------------------------------------------------ nhom 7: doc bien so

    def _n_bien_so(self, b):
        """Cau hinh doc bien so - KHOA vao 4 co cua `AnalysisConfig`.

        `doc_bien_so`           : checkbox tieu de cua nhom (mac dinh TAT).
        `bien_so_dir`           : thu muc luu crop bien so.
        `bien_so_nhoan_lai_giay`: cung 1 bien so chi luu anh 1 lan / N giay.
        `vung_bien_so`          : ROI "x1,y1,x2,y2" (de trong = tu tim).

        Doc bang RapidOCR (module `bien_so.py`) - CHAY 100% TREN MAY, khong
        gui anh ra ngoai.
        """
        f = self._hang_rong(b, "Thư mục lưu ảnh")
        o_bien_so = ctk.CTkEntry(f, textvariable=self.v_bien_so_dir)
        o_bien_so.grid(row=0, column=0, sticky="ew")
        # Duong dan thu muc hay DAI hon o -> bi cat chu. Rê chuot vao xem day du.
        HuongDan(o_bien_so, lambda: self.v_bien_so_dir.get(), font=self.font_nho)
        ctk.CTkButton(f, text="Chọn…", width=80,
                      command=self._chon_bien_so_dir).grid(
            row=0, column=1, padx=(GD.KHOANG_CACH["nho"], 0))

        f = self._hang(b, "Vùng cần quét")
        o_vung_bien_so = ctk.CTkEntry(f, textvariable=self.v_bien_so_vung)
        o_vung_bien_so.grid(row=0, column=1, sticky="ew")
        # Goi y trong o phai NGAN: do that "de trong = tu tim trong khung"
        # rong 159px ma o chi rong ~102px. Phan giai day du: tooltip.
        GoiYTronO(o_vung_bien_so, "tự tìm", font=self.font_nho)
        HuongDan(o_vung_bien_so, "Để trống = phần mềm tự tìm biển số trong "
                                 "cả khung hình. Gõ 4 số theo mẫu x1,y1,x2,y2 "
                                 "để chỉ quét một vùng.",
                 font=self.font_nho)

        f = self._hang(b, "Nghỉ giữa 2 lần (giây)")
        ctk.CTkEntry(f, textvariable=self.v_bien_so_giay, width=90).grid(
            row=0, column=1, sticky="w")

        f = self._hang(b, "")
        self.btn_doc_bien_so_thu = self._dich_widget(ctk.CTkButton(
            f, text=self.dich("Đọc biển số thử…"), width=260,
            command=self._mo_doc_bien_so_thu,
        ), "Đọc biển số thử…")
        self.btn_doc_bien_so_thu.grid(row=0, column=0, columnspan=2, sticky="w")
        self._ghi_y(b, "Thử trên 1 ảnh. Khi chạy video, biển số phải được xác "
                       "nhận qua 2 khung hình liên tiếp mới ghi nhận - nên kết "
                       "quả thử 1 ảnh chưa giống hệt lúc chạy video.")

        self._ghi_y(b, "Đọc bằng RapidOCR chạy 100% trên máy này, không gửi "
                       "ảnh ra ngoài.")
        self._ghi_y(b, "Tốc độ: đọc biển số chạy ở luồng nền nên không làm "
                       "khựng video. Mỗi lần quét tốn 9–15 ms, khung hình chậm "
                       "nhất 62 ms (đo thật trên máy này ngày 19/10/2026). "
                       "Lúc bật lần đầu máy phải nạp model nên khựng khoảng "
                       "1–2 giây.")
        self._ghi_y(b, "Cùng một biển số chỉ được lưu ảnh 1 lần trong khoảng "
                       "nghỉ ở trên.")
        self._ghi_y(b, "Vùng cần quét: gõ 4 số theo mẫu x1,y1,x2,y2. Gõ "
                       "0,1 – 1,0 là tọa độ tương đối, số lớn hơn 1 là tọa độ "
                       "pixel. Để trống = phần mềm tự tìm trong khung hình.")

    # --------------------------------------------- nhom 8: tu chup anh

    def _n_tu_chup(self, b):
        """Cau hinh tu chup anh - KHOA vao 2 co cua `AnalysisConfig`.

        `tu_chup_dir`          : thu muc luu anh. CHUOI RONG = TAT (dung quy
                                 tac cua `cam_ai_core`).
        `tu_chup_nhoan_lai_giay`: moi loai su kien chi chup 1 lan / N giay.
        """
        f = self._hang_rong(b, "Thư mục lưu ảnh")
        o_tu_chup = ctk.CTkEntry(f, textvariable=self.v_tu_chup_dir)
        o_tu_chup.grid(row=0, column=0, sticky="ew")
        # Duong dan thu muc hay DAI hon o -> bi cat chu. Rê chuot vao xem day du.
        HuongDan(o_tu_chup, lambda: self.v_tu_chup_dir.get(), font=self.font_nho)
        ctk.CTkButton(f, text="Chọn…", width=80,
                      command=self._chon_tu_chup_dir).grid(
            row=0, column=1, padx=(GD.KHOANG_CACH["nho"], 0))

        f = self._hang(b, "Nghỉ giữa 2 lần (giây)")
        ctk.CTkEntry(f, textvariable=self.v_tu_chup_giay, width=90).grid(
            row=0, column=1, sticky="w")

        self._ghi_y(b, "Chụp khi có người đông, vượt vùng canh, thấy người "
                       "quen hoặc có người đứng lâu.")
        self._ghi_y(b, "Mỗi loại sự kiện chỉ chụp 1 lần trong khoảng nghỉ ở "
                       "trên.")
        self._ghi_y(b, "Ảnh lưu ngay trên máy này, kèm file _bang_ke_chup.csv "
                       "ghi lại lúc chụp.")

    # ---------------------------------------------------- nhom 9: tach o

    def _n_tach_o(self, b):
        self._ghi_y(
            b,
            "Máy sẽ dò cả khung hình nguyên vẹn lẫn các ô nhỏ, rồi ghép lại — "
            "nên người ở gần không bị mất, người ở xa thì dễ nhận hơn.",
        )
        self._ghi_y(
            b,
            "Đổi lại là chậm hơn khoảng 5 lần. Đo thật ngày 19/10/2026: "
            "video đám đông nhận đúng hơn gấp đôi, nhưng xem sẽ giật hơn.",
        )

    # ------------------------------------------------- nhom 10: canh bao

    def _n_canh_bao(self, b):
        """Cau hinh canh bao - KHOA vao 4 co `AnalysisConfig` cua cam_ai_core.

        `bat_canh_bao`        : checkbox tieu de cua nhom (mac dinh TAT).
        `canh_bao_mo_phong`   : chi thu, khong keu chuong / mo hop thoai / gui
                                tin ra ngoai. MAC DINH BAT (an toan).
        `canh_bao_go`         : gop tin cung loai trong bao nhieu giay.
        `canh_bao_gioi_han`   : toi da bao nhieu tin / phut.

        CANH BAO DO KHONG chay o GUI: `cam_ai_core.CanhBaoNoi` da noi san
        `canh_bao.py` vao pipeline. Neu GUI tu goi them se bao TRUNG.
        """
        f = self._hang_rong(b, "Chế độ")
        self._checkbox(f, "Chỉ thử (không gửi thật)", self.v_cb_mo_phong,
                       font=self.font_nho, onvalue="1", offvalue="0",
                       ).grid(row=0, column=0, sticky="w")
        self._ghi_y(b, "Bỏ chọn ô này thì cảnh báo sẽ KÊU CHUÔNG và MỞ HỘP "
                       "THOẠI ngay trên máy này. Telegram cần có token trong "
                       "file canh_bao.ini.")

        f = self._hang(b, "Gộp tin (giây)")
        ctk.CTkEntry(f, textvariable=self.v_cb_go, width=90
                      ).grid(row=0, column=1, sticky="w")

        f = self._hang(b, "Giới hạn (tin/phút)")
        ctk.CTkEntry(f, textvariable=self.v_cb_gioi_han, width=90
                     ).grid(row=0, column=1, sticky="w")

        f = self._hang(b, "")
        ctk.CTkButton(f, text="Thử gửi 1 cảnh báo", width=260,
                      command=self._thu_canh_bao).grid(
            row=0, column=0, columnspan=2, sticky="w")

    # ------------------------------------------------------ nhom 11: model

    def _n_model(self, b):
        f = self._hang(b, "")
        ctk.CTkButton(f, text="Xem thông tin mô hình AI đang dùng", width=260,
                      command=self._mo_thong_tin_model).grid(
            row=0, column=0, columnspan=2, sticky="w")

    # ----------------------------------------------- nhom 12: thiet bi chay

    def _n_thiet_bi(self, b):
        """Cho biet may nay THUC SU co GPU khong, va hien tai dang chon gi.
        Do bang chon_thiet_bi cua cam_ai_core nen noi ra cai nao se chay."""
        cuda = chon_thiet_bi("auto") == "cuda"
        dong = ("Máy này CÓ GPU: sẽ chạy bằng card màn hình (nhanh)."
                if cuda else
                "Máy này KHÔNG có GPU: sẽ chạy bằng CPU (chậm hơn nhưng vẫn "
                "chạy được).")
        # Dong trang thai phai o HANG RIENG trai nhom, khong nhet vao cot
        # dieu khien cua `_hang`: cot do chi rong ~102px nen chu bi cat
        # ngang giua dong.
        ctk.CTkLabel(
            b, text=dong, font=self.font_nho_bold, text_color=MAU["chu"],
            anchor="w", justify="left", wraplength=WRAP_GHI_Y,
        ).grid(row=self._dong_moi(b), column=0, sticky="w",
               padx=(LE_GHI_Y, 0), pady=(KHOANG_CACH, 0))

        f = self._hang(b, "Đang chọn")
        ctk.CTkLabel(f, textvariable=self.v_thiet_bi, font=self.font_nho,
                      text_color=MAU["chu"], anchor="w",
                      ).grid(row=0, column=1, sticky="w")
        self._ghi_y(b, "Đổi chỗ này ở mục “Phát hiện người”.")

    # ---------------------------------------------------------- dieu khien
    #
    # Nut BAT DAU / DUNG da chuyen len THANH DAU (`_thanh_dau`) nen khong con
    # khoi dieu khien o cuoi cot trai. `self.btn_chay` / `self.btn_dung` van
    # ton tai (ten giong het) nen moi thu giu nguyen dung.

    # ------------------ KHUNG VIDEO / SO LIEU / THE DOI TUONG / NHAT KY
    # Bo cuc nay da tach sang `_cot_hien_thi` (cot 1) de VIDEO duoc lon nhat.

    def _khung_xem_video(self, parent):
        """KHUNG VIDEO LON NHAT cua man hinh.

        O hinh co nen DEN va tu giang theo khung cha (letterbox): anh
        luon gi dung ti le goc, khong bao gio bi keo meo. Kich thuoc anh
        hien thi do `_hien_khung_hinh` tinh lai moi vong bom hang doi.
        """
        khung = ctk.CTkFrame(parent, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
                             border_width=1, border_color=MAU["vien"])
        khung.grid(row=0, column=0, sticky="nsew")
        khung.grid_columnconfigure(1, weight=1)
        khung.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(khung, text="Xem video", font=self.font_tieu_de,
                     text_color=MAU["chu"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 0))
        self.lbl_khung_hinh = ctk.CTkLabel(
            khung, text="", font=self.font_nho_xam,
            text_color=MAU["chu_phu"], anchor="e")
        self.lbl_khung_hinh.grid(row=0, column=1, sticky="e", padx=12,
                                 pady=(10, 0))
        self.btn_tam_dung_xem = ctk.CTkButton(
            khung, text="Tạm dừng", width=120, height=KICH_THUOC["cao_nut"],
            state="disabled", command=self._doi_tam_dung_xem,
        )
        # KHONG grid o day: nut "Tam dung" thuoc che do XEM TRUC TIEP.
        # `_cap_nhat_nut_tam_dung_xem` se hien no (dung vi tri grid o day)
        # khi bat xem truc tiep, va AN di o che do phan tich theo lo.

        # Nen DEN cua khung hinh: moi chuyen do lon nhat se do vao day.
        self.khung_den = ctk.CTkFrame(khung, fg_color="#000000", corner_radius=6)
        self.khung_den.grid(row=1, column=0, columnspan=3, sticky="nsew",
                            padx=10, pady=(KHOANG_CACH, KHOANG_CACH))
        self.khung_den.grid_columnconfigure(0, weight=1)
        self.khung_den.grid_rowconfigure(0, weight=1)
        # KEO CUA SO -> chi ghi nhan + hen gio (viec RE), KHONG ve gi o day.
        self.khung_den.bind("<Configure>", self._khi_keo_cua_so, add="+")

        # mac dinh hien thong bao "Chua chay video"
        self.o_hinh = ctk.CTkLabel(
            self.khung_den, text="Chưa chạy video", font=self.font_nho_bold,
            text_color=MAU["chu_phu"], corner_radius=6,
        )
        self.o_hinh.grid(row=0, column=0, sticky="nsew")
        # NOI DUNG hinh nen trong suot - nen den cua khung_den lo phan chay.
        self.o_hinh.configure(fg_color="transparent")

        hang_duoi = ctk.CTkFrame(khung, fg_color="transparent")
        hang_duoi.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12,
                       pady=(0, 10))
        # v3.3: 2 o xem tach rieng: "Xem truc tiep" va "Xem khung hinh ket qua".
        # MOI o xem = 1 KHUNG CON: checkbox o tren, ghi chu 12px ngay duoi,
        # cung le trai voi CHU cua checkbox (thut vao 24px = be cua o check).
        # Nhan 13px mau `chu` (MASTER.md muc 6) - de doc hon font 12px xam.
        #
        # LUU Y: phai TAO checkbox truc tiep trong khung con `o` (truyen
        # `master=o`). Tkinter `widget.grid()` luon dua widget vao
        # `widget.master` (doi so truyen luc TAO), khong phai vao khung
        # cha hien thi -> neu tao o `hang_duoi` roi grid vao `o` thi 3 o se
        # CHONG NHAU tren cung 1 cho.
        o_xem = [
            (self.dich("Xem trực tiếp"), "Xem trực tiếp", self.v_xem_video,
             self._doi_bat_xem_truc_tiep,
             "Xem video ngay khi đang phân tích."),
            (self.dich("Xem khung hình kết quả"), "Xem khung hình kết quả",
             self.v_xem_ket_qua, self._doi_bat_xem_ket_qua,
             "Xem khung hình đã vẽ khung sau khi phân tích."),
            ("Nhận diện tên trên ảnh", None, self.v_nhan_ten, None,
             "Tên lấy từ bộ nhận diện mặt đang chạy song song. "
             "Tắt đi thì nhẹ máy hơn."),
        ]
        ds_chk = []
        for idx, (chuoi, goc, bien, cmd, ghi_chu) in enumerate(o_xem):
            o = ctk.CTkFrame(hang_duoi, fg_color="transparent")
            o.grid(row=0, column=idx, sticky="nw",
                   padx=(0 if idx == 0 else 18, 0))
            kw = {"variable": bien, "font": self.font_nho,
                  "onvalue": "1", "offvalue": "0"}
            if cmd is not None:
                kw["command"] = cmd
            chk = ctk.CTkCheckBox(o, text=chuoi, **kw)
            if goc is not None:
                chk = self._dich_widget(chk, goc)
            chk.grid(row=0, column=0, sticky="w")
            lbl = ctk.CTkLabel(
                o, text=ghi_chu, font=self.font_nho_xam,
                text_color=MAU["chu_phu"], anchor="w", justify="left",
                wraplength=230,
            )
            lbl.grid(row=1, column=0, sticky="w", padx=(24, 0), pady=(4, 0))
            ds_chk.append((chk, lbl))
        (self.chk_xem_video, lbl1) = ds_chk[0]
        (self.chk_xem_ket_qua, lbl2) = ds_chk[1]
        (self.chk_nhan_ten, self.lbl_goi_y_xem) = ds_chk[2]

    def _bang_so_lieu_gon(self, parent):
        """Dải số liệu GỌN 1 hàng ngay dưới khung video.

        6 o nam ngang: nen `the`, bo goc 10, vien 1px `vien`, so 28px bold,
        nhan 12px `chu_phu`. MAU CUA SO doi theo trang thai (MASTER.md muc 6):
        `chu` khi chua co du lieu, `nut` khi da co du lieu, `canh_bao` khi
        dang chay, `loi` khi co loi.
        Khong con panel "doi tuong phat hien": vai tro do do DANH SACH SU
        KIEN ben phai dam nhiem (co anh crop that + thoi gian + ten + tin cay).
        """
        s = ctk.CTkFrame(parent, fg_color="transparent")
        s.grid(row=2, column=0, sticky="ew", pady=(0, KHOANG_CACH))
        for col in range(6):
            s.grid_columnconfigure(col, weight=1)
        o_so_lieu = [
            ("Người", self.v_so_nguoi),
            ("Mặt", self.v_so_mat),
            ("Người quen", self.v_so_quen),
            ("Vào", self.v_so_vao),
            ("Ra", self.v_so_ra),
            ("Trong vùng", self.v_so_trong_vung),
        ]
        self.lbl_so_lieu = []
        for idx, (ten, var) in enumerate(o_so_lieu):
            cell = ctk.CTkFrame(s, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
                                border_width=1, border_color=MAU["vien"])
            cell.grid(row=0, column=idx, sticky="ew",
                      padx=(0 if idx == 0 else KHOANG_CACH, 0))
            lbl = ctk.CTkLabel(cell, textvariable=var, font=self.font_stat,
                               text_color=MAU["chu"])
            lbl.pack(pady=(6, 0))
            self.lbl_so_lieu.append(lbl)
            ctk.CTkLabel(cell, text=ten, font=self.font_nho_xam,
                         text_color=MAU["chu_phu"]).pack(pady=(0, 6))

    def _cap_nhat_mau_so_lieu(self) -> None:
        """Mau cua 6 o so lieu theo trang thai hien tai (MASTER.md muc 6).

        `loi` > `canh_bao` (dang chay) > `nut` (da co du lieu) > `chu`.
        """
        if not getattr(self, "lbl_so_lieu", None):
            return
        if self._mau_trang_thai == "loi":
            mau = MAU["loi"]
        elif self.busy:
            mau = MAU["canh_bao"]
        else:
            co_du_lieu = False
            for var in (self.v_so_nguoi, self.v_so_mat, self.v_so_quen,
                        self.v_so_vao, self.v_so_ra, self.v_so_trong_vung):
                try:
                    if int(var.get() or 0) > 0:
                        co_du_lieu = True
                        break
                except (TypeError, ValueError):
                    continue
            mau = MAU["nut"] if co_du_lieu else MAU["chu"]
        for lbl in self.lbl_so_lieu:
            try:
                lbl.configure(text_color=mau)
            except Exception:                         # noqa: BLE001
                pass

    def _bang_nhat_ky(self, parent):
        f = ctk.CTkFrame(parent, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
                         border_width=1, border_color=MAU["vien"],
                         height=CAO_NHAT_KY)
        # Khong keo theo chieu cao con lai: giu ngan de khoang chay cho video.
        f.grid_propagate(False)
        f.grid(row=2, column=0, columnspan=2, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(f, text=f"Nhật ký (cuối {MAX_LOG_LINES} dòng)",
                     font=self.font_tieu_de, text_color=MAU["chu"],
                     anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(8, 0))
        self.btn_mo_ket_qua = ctk.CTkButton(
            f, text="Mở kết quả", width=175, height=KICH_THUOC["cao_nut"],
            command=self._mo_video_ket_qua, state="disabled",
        )
        self.btn_mo_ket_qua.grid(row=0, column=1, padx=(0, KHOANG_CACH),
                                 pady=(6, 0))
        self.btn_bao_cao = ctk.CTkButton(
            f, text="Xem báo cáo", width=150, height=KICH_THUOC["cao_nut"],
            command=self._xem_bao_cao,
        )
        self.btn_bao_cao.grid(row=0, column=2, padx=(0, 12), pady=(6, 0))

        self.log_box = ctk.CTkTextbox(f, wrap="word", height=92,
                                      font=self.font_code)
        self.log_box.grid(row=1, column=0, columnspan=3, sticky="nsew",
                          padx=12, pady=(6, 10))
        self.log_box.configure(state="disabled")

    # -------------------------------------------------- trang thai widget

    def _cap_nhat_trang_thai(self):
        """Khoa / mo nut theo trang thai hien tai."""
        co_ket_qua = self.result is not None
        self.btn_mo_ket_qua.configure(state="normal" if co_ket_qua else "disabled")
        if getattr(self, "btn_hoc_lai", None) is not None:
            self.btn_hoc_lai.configure(state="disabled" if self.busy else "normal")

    # ---------------------------------------------------------- chon file

    # --- 3 hop thoai co duoc dich sang 2 ngon ngu ---
    def _bao_loi(self, tieu_de: str, noi_dung: str):
        messagebox.showerror(self.dich(tieu_de), self.dich(noi_dung))

    def _bao_canh_bao(self, tieu_de: str, noi_dung: str):
        messagebox.showwarning(self.dich(tieu_de), self.dich(noi_dung))

    def _bao_thong_bao(self, tieu_de: str, noi_dung: str):
        messagebox.showinfo(self.dich(tieu_de), self.dich(noi_dung))

    def _chon_video(self):
        path = filedialog.askopenfilename(title=self.dich("Chọn video"),
                                          filetypes=VIDEO_FILETYPES)
        if path:
            self.v_video.set(path)

    def _chon_anh(self):
        """Chon 1 ANH TINH (jpg/png/...) - phan tich dung 1 khung hinh."""
        path = filedialog.askopenfilename(
            title=self.dich("Chọn ảnh"),
            filetypes=[("Anh", " ".join("*" + d for d in duoi_anh())),
                       ("Tat ca file", "*.*")],
        )
        if path:
            self.v_video.set(path)

    # --------------------------------------------- v3.6: CHON CAMERA
    #
    # Hop thoai con (CTkToplevel) cho phep:
    #   * quet camera tren may (chay TRONG THREAD - quet mat vai giay),
    #   * chon 1 camera trong danh sach -> gan "0"/"1"/... vao o nguon,
    #   * nhap dia chi camera IP (rtsp://... ) -> gan vao o nguon.
    # Ket qua quet ve bang HANG DOI cua app (`self.queue`) -> khong bao gio
    # doc bien Tk tu thread.

    def _cap_nhat_nhan_nguon(self, *_args) -> None:
        """Dong nhan 'Loai nguon' - tu doi moi khi o nguon doi.

        `trace_add` cua StringVar goi ham nay khi nguoi dung go tay vao o,
        nen nhan luon khop voi noi dung hien tai.
        """
        lbl = getattr(self, "lbl_nguon", None)
        if lbl is None:
            return
        goc = str(self.v_video.get() or "").strip()
        chu = self.dich("Loại nguồn: ") + self._mo_ta_nguon(goc)
        try:
            lbl.configure(text=chu)
        except Exception:                             # noqa: BLE001
            pass

    def _mo_ta_nguon(self, source: str) -> str:
        """Ten loai nguon (tieng Viet co dau, co ban dich EN) de hien thi."""
        goc = str(source or "").strip()
        loai = loai_nguon(goc)
        if loai == LOAI_ANH:
            return self.dich("Ảnh tĩnh")
        if loai == LOAI_CAMERA:
            return self.dich("Camera máy") + f" ({goc})"
        if loai == LOAI_MANG:
            return self.dich("Camera IP")
        if not goc:
            return self.dich("Chưa chọn")
        return self.dich("Video")

    def _chon_camera(self):
        """Mo hop thoai chon camera (may hoac camera IP)."""
        self._mo_hop_thoai_camera(quet_ngay=False)

    def _xem_danh_sach_camera(self):
        """Mo hop thoai chon camera + quet ngay danh sach camera may."""
        self._mo_hop_thoai_camera(quet_ngay=True)

    def _mo_hop_thoai_camera(self, quet_ngay: bool = False):
        """Dung hop thoai chon camera (1 cua so duy nhat, co the mo lai)."""
        win = getattr(self, "_cua_so_camera", None)
        if win is not None:
            try:
                if win.winfo_exists():
                    win.lift()
                    win.focus_force()
                    if quet_ngay:
                        self._bat_dau_quet_camera()
                    return
            except Exception:                         # noqa: BLE001
                pass

        win = ctk.CTkToplevel(self)
        win.title(self.dich("Chọn camera"))
        win.geometry("640x540")
        win.minsize(560, 420)
        win.transient(self)
        win.configure(fg_color=MAU["nen"])
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(2, weight=1)
        self._cua_so_camera = win
        self._huy_quet_camera = False

        # --- 1. dia chi camera IP ---
        ctk.CTkLabel(
            win,
            text="Chọn camera máy trong danh sách bên dưới, hoặc nhập địa "
                 "chỉ camera IP phía trên.",
            font=self.font_nho, text_color=MAU["chu"], anchor="w",
            wraplength=580, justify="left",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))

        f_ip = ctk.CTkFrame(win, fg_color="transparent")
        f_ip.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))
        f_ip.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(f_ip, text="Địa chỉ camera IP", font=self.font_nho_xam,
                     text_color=MAU["chu_phu"], anchor="w").grid(
            row=0, column=0, sticky="w")
        self.v_camera_ip = ctk.StringVar(value="")
        o_ip = ctk.CTkEntry(f_ip, textvariable=self.v_camera_ip)
        o_ip.grid(row=1, column=0, sticky="ew", pady=(2, 0))
        GoiYTronO(o_ip, "rtsp://192.168.1.10:554/stream",
                  font=self.font_nho_xam)
        ctk.CTkButton(f_ip, text="Dùng địa chỉ này", width=160,
                      command=self._dung_dia_chi_camera_ip
                      ).grid(row=1, column=1, sticky="e", padx=(8, 0))

        # --- 2. danh sach camera (scroll) ---
        self.khung_danh_sach_camera = ctk.CTkScrollableFrame(
            win, fg_color=MAU["the"], corner_radius=BO_GOC_THE)
        self.khung_danh_sach_camera.grid(row=2, column=0, sticky="nsew",
                                         padx=14, pady=(0, 6))
        self.khung_danh_sach_camera.grid_columnconfigure(0, weight=1)
        self.lbl_trang_thai_camera = ctk.CTkLabel(
            win, text="", font=self.font_nho_xam, text_color=MAU["chu_phu"],
            anchor="w",
        )
        self.lbl_trang_thai_camera.grid(row=3, column=0, sticky="ew",
                                        padx=14, pady=(0, 6))

        # --- 3. nut ---
        f_nut = ctk.CTkFrame(win, fg_color="transparent")
        f_nut.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 12))
        f_nut.grid_columnconfigure(3, weight=1)
        self.btn_quet_camera = ctk.CTkButton(
            f_nut, text="Quét camera", width=140,
            command=self._bat_dau_quet_camera)
        self.btn_quet_camera.grid(row=0, column=0, sticky="w")
        self.btn_huy_quet_camera = ctk.CTkButton(
            f_nut, text="Huỷ", width=90, command=self._huy_quet_camera_now,
            state="disabled")
        self.btn_huy_quet_camera.grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkButton(f_nut, text="Đóng", width=90,
                      command=self._dong_hop_thoai_camera
                      ).grid(row=0, column=4, sticky="e")

        self._ap_dung_theme(win)
        self._ghi_nhan_chu(win)
        self._lam_moi_chu(win)
        self._lam_moi_trang_thai_camera([], quet_xong=False)
        if quet_ngay:
            self._bat_dau_quet_camera()

    def _dong_hop_thoai_camera(self):
        """Dong hop thoai chon camera (giu lai danh sach da quet)."""
        win = getattr(self, "_cua_so_camera", None)
        if win is None:
            return
        try:
            if win.winfo_exists():
                win.destroy()
        except Exception:                             # noqa: BLE001
            pass
        self._cua_so_camera = None

    def _bat_dau_quet_camera(self):
        """Quet camera tren may - CHAY TRONG THREAD (quet mat vai giay)."""
        win = getattr(self, "_cua_so_camera", None)
        if win is None:
            return
        self._huy_quet_camera = False
        try:
            self.btn_quet_camera.configure(state="disabled")
            self.btn_huy_quet_camera.configure(state="normal")
            self.lbl_trang_thai_camera.configure(
                text=self.dich("Đang quét…"))
        except Exception:                             # noqa: BLE001
            pass
        threading.Thread(target=self._quet_camera_nen, daemon=True).start()

    def _huy_quet_camera_now(self):
        """Bam 'Huy' khi dang quet: bo ket qua cua lan quet (thread van chay
        het roi tra ve hang doi - nhung ket qua bi bo qua)."""
        self._huy_quet_camera = True
        try:
            self.btn_quet_camera.configure(state="normal")
            self.btn_huy_quet_camera.configure(state="disabled")
            self.lbl_trang_thai_camera.configure(
                text=self.dich("Đã hủy quét camera."))
        except Exception:                             # noqa: BLE001
            pass

    def _quet_camera_nen(self):
        """CHAY TREN THREAD NEN: quet camera -> day ket qua vao hang doi."""
        try:
            ds = CORE.quet_camera()
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("quet_camera_loi", str(exc)))
            return
        self.queue.put(("quet_camera", ds))

    def _ket_thuc_quet_camera(self, ds: list) -> None:
        """CHAY TREN LUONG UI: ket qua quet camera -> ve danh sach."""
        # Tra lai nut cho dung trang thai (ke ca khi nguoi dung da bam Huy).
        try:
            self.btn_quet_camera.configure(state="normal")
            self.btn_huy_quet_camera.configure(state="disabled")
        except Exception:                             # noqa: BLE001
            pass
        if getattr(self, "_huy_quet_camera", False):
            return                      # nguoi dung da Huy -> bo qua ket qua
        self._lam_moi_trang_thai_camera(ds, quet_xong=True)

    def _quet_camera_loi(self, loi: str) -> None:
        """CHAY TREN LUONG UI: quet camera loi -> bao trong hop thoai."""
        try:
            self.btn_quet_camera.configure(state="normal")
            self.btn_huy_quet_camera.configure(state="disabled")
            self.lbl_trang_thai_camera.configure(text=str(loi))
        except Exception:                             # noqa: BLE001
            pass
        self._bao_canh_bao("Lỗi quét camera", str(loi))

    def _lam_moi_trang_thai_camera(self, ds: list, quet_xong: bool = False) -> None:
        """CHAY TREN LUONG UI: ve lai danh sach camera trong hop thoai."""
        win = getattr(self, "_cua_so_camera", None)
        if win is None:
            return
        try:
            if not win.winfo_exists():
                return
        except Exception:                             # noqa: BLE001
            return

        # Xoa dong cu trong khung danh sach.
        for con in self.khung_danh_sach_camera.winfo_children():
            try:
                con.destroy()
            except Exception:                         # noqa: BLE001
                pass

        mo_duoc = [c for c in ds if c.get("mo_duoc")]
        if not ds:
            if quet_xong:
                self.lbl_trang_thai_camera.configure(
                    text=self.dich("Máy này không có camera nào. Bạn vẫn có thể "
                                    "nhập địa chỉ camera IP phía trên."))
            else:
                self.lbl_trang_thai_camera.configure(
                    text=self.dich("Chưa quét camera. Bấm nút 'Quét camera' "
                                    "để tìm camera trên máy này."))
            return
        if not mo_duoc:
            self.lbl_trang_thai_camera.configure(
                text=self.dich("Máy này không có camera nào. Bạn vẫn có thể "
                                "nhập địa chỉ camera IP phía trên."))
            return

        self.lbl_trang_thai_camera.configure(
            text=self.dich("Số camera tìm thấy: ") + str(len(mo_duoc)))
        for hang, cam in enumerate(mo_duoc):
            idx = cam.get("index", 0)
            ten = str(cam.get("ten") or "").strip()
            w = int(cam.get("width") or 0)
            h = int(cam.get("height") or 0)
            mo_ta = self.dich("Camera") + f" {idx}"
            if ten:
                mo_ta += f" — {ten}"
            if w and h:
                mo_ta += f" ({w}x{h})"
            nut = ctk.CTkButton(self.khung_danh_sach_camera, text=mo_ta,
                                anchor="w", height=34,
                                command=lambda i=idx: self._dung_camera(i))
            nut.grid(row=hang, column=0, sticky="ew", pady=2, padx=6)

    def _dung_camera(self, index: int):
        """Chon 1 camera may -> gan index vao o nguon."""
        self.v_video.set(str(index))
        self._ghi_log(self.dich("Đã chọn camera máy: ") + f"index {index}")
        self._dong_hop_thoai_camera()

    def _dung_dia_chi_camera_ip(self):
        """Dung dia chi camera IP vua nhap -> gan vao o nguon."""
        dia_chi = str(self.v_camera_ip.get() or "").strip()
        if not dia_chi:
            self._bao_canh_bao(
                "Thiếu địa chỉ camera IP",
                "Hãy nhập địa chỉ camera IP trước khi bấm 'Dùng địa chỉ này'.",
            )
            return
        if not dia_chi.lower().startswith(TIEN_DO_MANG):
            self._bao_canh_bao(
                "Địa chỉ camera IP sai",
                "Địa chỉ camera IP phải bắt đầu bằng rtsp://, rtmp://, "
                "http:// hoặc https://.",
            )
            return
        self.v_video.set(dia_chi)
        self._ghi_log(self.dich("Đã chọn camera IP: ") + dia_chi)
        self._dong_hop_thoai_camera()

    def _chon_output(self):
        # "Luu ket qua" la THU MUC -> phai chon thu muc, khong chon file.
        path = filedialog.askdirectory(
            title=self.dich("Chọn thư mục lưu kết quả"),
            initialdir=self.v_output.get().strip() or APP_DIR,
        )
        if path:
            self.v_output.set(path)

    def _chon_faces_dir(self):
        path = filedialog.askdirectory(
            title=self.dich("Thư mục ảnh người quen"))
        if path:
            self.v_faces_dir.set(path)

    def _chon_vung_file(self):
        path = filedialog.askopenfilename(title=self.dich("Chọn file vùng"),
                                          filetypes=ZONE_FILETYPES)
        if path:
            self.v_vung_file.set(path)

    def _chon_bien_so_dir(self):
        path = filedialog.askdirectory(
            title=self.dich("Chọn thư mục lưu ảnh biển số"),
            initialdir=self.v_bien_so_dir.get().strip() or APP_DIR,
        )
        if path:
            self.v_bien_so_dir.set(path)

    def _chon_tu_chup_dir(self):
        path = filedialog.askdirectory(
            title=self.dich("Chọn thư mục lưu ảnh sự kiện"),
            initialdir=self.v_tu_chup_dir.get().strip() or APP_DIR,
        )
        if path:
            self.v_tu_chup_dir.set(path)

    def _mo_thu_muc_clip(self):
        try:
            os.makedirs(THU_MUC_CLIP, exist_ok=True)
            open_in_explorer(THU_MUC_CLIP)
        except OSError as exc:
            self._bao_loi("Lỗi", f"Không mở được thư mục clip:\n{exc}")

    def _mo_thu_muc(self):
        # v_output la THU MUC -> dung chinh no luon, khong lay dirname.
        target = self.v_output.get().strip() or APP_DIR
        if not os.path.isdir(target):
            target = APP_DIR
        open_in_explorer(target)

    def _mo_video_ket_qua(self):
        """Mo ket qua: VIDEO (mp4) hoac ANH (jpg) - mo bang trinh phat mac dinh."""
        if not self.result or not os.path.exists(self.result.out_path):
            self._bao_thong_bao("Chưa có kết quả", "Hãy bấm BẮT ĐẦU chạy trước đã.")
            return
        open_in_explorer(self.result.out_path)

    def _xem_bao_cao(self):
        """Mo bao_cao_tong_ket.py o cua so con, khong treo giao dien."""
        if not self.result or not os.path.exists(self.result.report_path):
            self._bao_thong_bao(
                "Chưa có báo cáo",
                "Chưa có file báo cáo (CSV).\nHãy bấm BẮT ĐẦU chạy xong video đã.",
            )
            return
        cmd = [PYTHON_EXE, BAO_CAO, "--csv", self.result.report_path]
        # v3.6: ket qua nguon ANH la file .jpg - trinh xem lai CHI doc video
        # (.mp4) -> chi gan them khi that su la video.
        if (os.path.exists(self.result.out_path)
                and os.path.splitext(self.result.out_path)[1].lower()
                not in duoi_anh()):
            cmd += ["--video", self.result.out_path]
        try:
            subprocess.Popen(cmd, cwd=APP_DIR)
        except OSError as exc:
            self._bao_loi("Lỗi", f"Không mở được báo cáo:\n{exc}")
            return
        self._ghi_log(f"> Xem báo cáo: {' '.join(cmd)}")

    def _mo_ve_vung(self):
        if self.busy:
            return
        source = self.v_video.get().strip()
        if not source:
            self._bao_canh_bao(
                "Thiếu nguồn", "Hãy chọn nguồn trước khi vẽ vùng.")
            return
        # v3.6: ve vung chi lam duoc voi nguon VIDEO (file video).
        if loai_nguon(source) != LOAI_VIDEO:
            self._bao_canh_bao(
                "Chỉ vẽ vùng được với nguồn video.",
                "Chỉ vẽ vùng được với nguồn video.",
            )
            return
        cmd = [PYTHON_EXE, VE_VUNG, "--input", source, "--out", self.v_vung_file.get()]
        try:
            subprocess.Popen(cmd, cwd=APP_DIR)
        except OSError as exc:
            self._bao_loi("Lỗi", f"Không mở được cửa sổ vẽ vùng:\n{exc}")
            return
        self._ghi_log(f"> Mở cửa sổ vẽ vùng: {' '.join(cmd)}")

    # ---------------------------------------------------------- canh bao

    def _tao_lai_canh_bao(self):
        """Cai moi doi tuong CanhBao de dung cau hinh moi."""
        self._cb = None

    def _lay_canh_bao(self):
        if self._cb is not None:
            return self._cb
        try:
            from canh_bao import CanhBao
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("log", f"[canh bao] không import được: {exc}"))
            return None
        try:
            self._cb = CanhBao(
                bat_telegram=self.v_cb_telegram.get() == "1",
                bat_chuong=self.v_cb_chuong.get() == "1",
                hien_hop_thoai=self.v_cb_hop_thoai.get() == "1",
                in_thong_bao=False,
            )
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("log", f"[canh bao] không tạo được: {exc}"))
            return None
        return self._cb

    def _gui_canh_bao(self, loai_su_kien: str, chi_tiet: dict) -> None:
        """Goi canh bao o LUONG NEN + try/except:
        loi mang khong bao gio lam treo phan mem."""
        if self.v_canh_bao.get() != "1":
            return
        cb = self._lay_canh_bao()
        if cb is None:
            return
        threading.Thread(
            target=self._gui_canh_bao_nen, args=(cb, loai_su_kien, chi_tiet),
            daemon=True,
        ).start()

    def _gui_canh_bao_nen(self, cb, loai_su_kien: str, chi_tiet: dict) -> None:
        try:
            cb.guii(loai_su_kien, chi_tiet)
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("log", f"[canh bao] không gửi được: {exc}"))

    def _thu_canh_bao(self):
        if self.v_canh_bao.get() != "1":
            self._bao_thong_bao("Chưa bật cảnh báo",
                                "Hãy bật ô 'Cảnh báo (gửi tin ra ngoài)' "
                                "trước đã, rồi bấm thử lại.")
            return
        if self.v_cb_mo_phong.get() == "1":
            self._ghi_log("> Chỉ thử: không gửi thật (đang bật 'Chỉ thử').")
            self._bao_thong_bao(
                "Chỉ thử",
                "Đang bật 'Chỉ thử (không gửi thật)' nên không kêu chuông, "
                "không mở hộp thoại và không gửi tin.\n\nKhi đã sẵn sàng gửi "
                "thật thì bỏ chọn ô đó (cảnh báo sẽ kêu chuông và mở hộp thoại "
                "ngay trên máy này).",
            )
            return
        self._gui_canh_bao("co_nguoi", {"mo_ta": "Đây là cảnh báo thử nghiệm."})
        self._ghi_log("> Đã yêu cầu gửi 1 cảnh báo thử nghiệm (THẬT).")

    # -------------------------------------------------------------- chay

    @staticmethod
    def _ten_nguon_ket_qua(source: str, loai: str) -> str:
        """Ten go (khong duoi) dung cho file ket qua, theo loai nguon.

        * video / anh : ten file goc (bo duoi) -> "video_test", "bus"
        * camera may  : "camera_0"   (index camera)
        * camera IP   : "camera_ip"  (khong lay ten tu duong dan URL)
        """
        if loai == LOAI_CAMERA:
            return f"camera_{str(source).strip()}"
        if loai == LOAI_MANG:
            return "camera_ip"
        ten = os.path.splitext(os.path.basename(source))[0]
        return ten or "video"

    def _tao_cau_hinh(self) -> AnalysisConfig:
        face = self.v_face.get() == "1"
        zone = self.v_vung.get() == "1"
        source = self.v_video.get().strip()
        # v3.6: o "Nguon" chua 4 kieu vao. Camera (may + IP) KHONG phai file
        # tren dia -> khong kiem tra `os.path.isfile` cho 2 loai do.
        loai = loai_nguon(source)
        if not source:
            raise ValueError("Chưa chọn nguồn.")
        if loai in (LOAI_CAMERA, LOAI_MANG):
            pass                       # nguon live -> khong can file
        elif not os.path.isfile(source):
            raise ValueError(f"Không tìm thấy nguồn:\n{source}")

        conf = parse_float(self.v_conf, 0.25, "Ngưỡng tin cậy")
        if not 0.05 <= conf <= 1.0:
            raise ValueError("Ngưỡng tin cậy phải nằm trong khoảng 0,05 – 1,0.")

        clip = self.v_clip.get() == "1"
        clip_giay = max(2.0, parse_float(self.v_clip_giay, 10.0, "Tổng giây mỗi clip"))
        # v3.0: 2 tinh nang moi. TAT = khong gui gi xuong core (mac dinh TAT
        # de hanh vi cu khong doi).
        doc_bien_so = self.v_bien_so.get() == "1"
        tu_chup = self.v_tu_chup.get() == "1"

        # "Lưu kết quả" la THU MUC. cam_ai_core.output_paths() noi them
        # _ket_qua.mp4 / _bao_cao.csv vao cuoi duong dan, nen o day truyen
        # <thu muc> + <ten goc cua video>, ket qua se nam DUNG trong thu muc.
        thu_muc_ket_qua = self.v_output.get().strip() or APP_DIR
        if not os.path.isdir(thu_muc_ket_qua):
            raise ValueError(
                f"Thư mục lưu kết quả không có trên máy:\n{thu_muc_ket_qua}"
            )
        ten_goc = self._ten_nguon_ket_qua(source, loai)

        return AnalysisConfig(
            input=source,
            output=os.path.join(thu_muc_ket_qua, ten_goc),
            no_face=not face,
            faces_dir=self.v_faces_dir.get().strip() or "known_faces",
            model=self.v_model.get(),
            thiet_bi=GIA_TRI_CHE_THIET_BI.get(self.v_thiet_bi.get(), "auto"),
            conf=conf,
            face_every=max(1, parse_int(self.v_face_every, 1, "Quét mặt mỗi")),
            face_threshold=float(self.v_face_threshold.get() or 0.40),
            min_face=max(0, parse_int(self.v_min_face, 0, "Bỏ qua mặt nhỏ hơn")),
            pixelate=self.v_pixelate.get() == "1",
            vung=self.v_vung_file.get().strip() if zone else None,
            vung_nhay=self.v_vung_nhay.get() == "1",
            vung_max=max(0, parse_int(self.v_vung_max, 0, "Cảnh báo vượt quá")),
            canh_lau=max(0.0, parse_float(self.v_canh_lau, 0.0, "Cảnh báo đứng lâu")),
            tu_luu_clip=THU_MUC_CLIP if clip else "",
            clip_giay=clip_giay,
            clip_ghi_tat_ca=self.v_clip_tat_ca.get() == "1",
            nhan_vat_the=self.v_vat_the.get() == "1",
            lop=self.v_lop.get().strip(),
            # --- v3.0: doc bien so (RapidOCR, 100% tren may) ---
            # MAC DINH TAT (v_bien_so = "0") de hanh vi cu khong doi.
            doc_bien_so=doc_bien_so,
            bien_so_dir=self.v_bien_so_dir.get().strip() or THU_MUC_BIEN_SO,
            bien_so_nhoan_lai_giay=max(
                0.0, parse_float(self.v_bien_so_giay, 30.0, "Nghỉ giữa 2 lần")),
            # De trong -> None -> bien_so.py tu tim bang class `plate` cua YOLO.
            # TAT tinh nang -> None (khong dung vung gi khi da tat).
            vung_bien_so=((self.v_bien_so_vung.get().strip() or None)
                          if doc_bien_so else None),
            # --- v3.0: tu chup anh su kien ---
            # TAT -> chuoi rong (dung quy tac cua cam_ai_core: rong = tat).
            tu_chup_dir=(self.v_tu_chup_dir.get().strip() if tu_chup else ""),
            tu_chup_nhoan_lai_giay=max(
                0.0, parse_float(self.v_tu_chup_giay, 10.0, "Nghỉ giữa 2 lần")),
            # MAC DINH TAT. Bat len se cham hon ~5.3 lan.
            tach_o=self.v_tach_o.get() == "1",
            # --- 4 co canh bao noi bo cua cam_ai_core ---
            # MAC DINH TAT (`v_canh_bao` = "0") va mac dinh CHI THU
            # (`v_cb_mo_phong` = "1") -> nguoi dung phai tu bat, va mac dinh
            # khong keu chuong / khong mo hop thoai tren may.
            bat_canh_bao=self.v_canh_bao.get() == "1",
            canh_bao_mo_phong=self.v_cb_mo_phong.get() == "1",
            canh_bao_go=max(0.0, parse_float(self.v_cb_go, 60.0, "Gộp tin")),
            canh_bao_gioi_han=max(1, parse_int(self.v_cb_gioi_han, 5, "Giới hạn")),
            show_box=self.v_khung.get() == "1",
            show_label=self.v_nhan.get() == "1",
            show_line=self.v_dem_ra_vao.get() == "1",
        )

    def _bat_dau(self):
        if self.busy:
            return
        if self.v_phat_hien.get() != "1":
            self._bao_canh_bao(
                "Thiếu phát hiện người",
                "Cần bật 'Phát hiện người' thì phần mềm mới biết đâu là người.",
            )
            return
        try:
            cfg = self._tao_cau_hinh()
        except ValueError as exc:
            self.lbl_loi.configure(text=self.dich(str(exc)))
            return

        self.lbl_loi.configure(text="")
        self.result = None
        self.last_names = ""
        self.last_vi_pham = 0
        self.last_canh_lau = 0
        self._ten_nguoi_quen = ""
        self._bar_cu = -1.0
        # v3.6: nguon LIVE (camera) khong biet tong frame -> thanh tien trinh
        # chuyen sang che do indeterminate (chay vui khong phai %).
        self._nguon_live = la_live(cfg.input)
        if self._nguon_live:
            self._bat_tien_trinh_live()
        else:
            self._ket_tuc_tien_trinh()
            self.bar.set(0)
        # Xoa the doi tuong cua lan truoc + reset so lieu de khong tran
        # so cua video cu vao video moi.
        self.panel_su_kien.xoa_het()
        for var in (self.v_so_nguoi, self.v_so_mat, self.v_so_vao, self.v_so_ra,
                    self.v_so_quen, self.v_so_trong_vung):
            var.set("0")
        self._cap_nhat_trang_thai()
        self._che_do_busy(True)
        self._set_trang_thai("chay", frame=0, tong=0, phan_tram=0)
        self._ghi_log("=" * 52)
        self._ghi_log(f"BẮT ĐẦU xử lý: {cfg.input}")
        # v3.6: noi ro nguon dang phan tich (video / anh / camera may / IP).
        self._ghi_log(self.dich("Nguồn: ") + self._mo_ta_nguon(cfg.input))
        # --- v3.2: 2 che do hien thi khung hinh ---
        # * xem truc tiep (tick "Xem truc tiep"): thread rieng do YOLO.
        # * phan tich theo lo (tick OFF): pipeline gui khung hinh co overlay
        #   qua `frame_cb` -> panel "Xem video" KHONG con den.
        # v3.3: tach 2 o. "Xem khung hinh ket qua" CHI dung khi KHONG bat
        # "Xem truc tiep" - bat ca 2 se co 2 nguon hinh de len nhau.
        self._hien_anh_batch = False
        xem_truc_tiep = self.v_xem_video.get() == "1"
        xem_ket_qua = self.v_xem_ket_qua.get() == "1"
        if self._nguon_live:
            # Nguon LIVE: pipeline chay lien tuc -> KHONG mo them 1 ket noi
            # camera thu hai de xem truc tiep (ton tai nguyen, hay loi).
            # Dung luon khung hinh cua pipeline de xem.
            if xem_truc_tiep:
                self._ghi_log(
                    "Nguồn camera: dùng luôn khung hình của pipeline để xem, "
                    "không mở thêm kết nối camera thứ hai."
                )
            xem_truc_tiep = False
            self._hien_anh_batch = xem_ket_qua
            self._cap_nhat_nut_tam_dung_xem()
            self.lbl_khung_hinh.configure(text=self._mo_ta_nguon(cfg.input))
            self.o_hinh.configure(image=None, text="")
        elif loai_nguon(cfg.input) == LOAI_ANH:
            # v3.6: ANH TINH chi co 1 khung hinh -> khong mo thread xem truc
            # tiep (VideoCapture khong doc duoc file anh). Hien khung hinh
            # da ve khung cua pipeline.
            if xem_truc_tiep:
                self._ghi_log(
                    "Nguồn ảnh tĩnh: hiển thị luôn khung hình đã vẽ khung."
                )
            xem_truc_tiep = False
            self._hien_anh_batch = True
            self._cap_nhat_nut_tam_dung_xem()
            self.lbl_khung_hinh.configure(text=os.path.basename(cfg.input))
            self.o_hinh.configure(image=None, text="")
        elif xem_truc_tiep:
            if xem_ket_qua:
                self._ghi_log(
                    "Đang bật 'Xem trực tiếp' nên 'Xem khung hình kết quả' "
                    "tạm không dùng (tránh 2 nguồn hình đè nhau)."
                )
            self._bat_xem_truc_tiep(cfg)
        else:
            self._hien_anh_batch = xem_ket_qua
            self._cap_nhat_nut_tam_dung_xem()
            self.lbl_khung_hinh.configure(text=os.path.basename(cfg.input))
            self.o_hinh.configure(image=None, text="")
        threading.Thread(
            target=self._chay_pipeline, args=(cfg, xem_truc_tiep, xem_ket_qua),
            daemon=True
        ).start()

    def _chay_pipeline(self, cfg: AnalysisConfig, xem_truc_tiep: bool = True,
                       xem_ket_qua: bool = False):
        """CHAY TREN THREAD NEN. Chi day vao hang doi, khong go widget."""
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.queue)
        result = None
        try:
            result = run_analysis(
                cfg,
                progress_cb=self._tien_trinh_cb,
                log=lambda text: self.queue.put(("log", text)),
                # Che do xem truc tiep: thread rieng da lo anh roi -> KHONG
                # gui them khung hinh tu pipeline (tranh 2 nguon anh).
                # Che do phan tich theo lo: pipeline gui khung hinh co overlay.
                # v3.3: chi gui khi anh TAT "Xem truc tiep" va BAT
                # "Xem khung hinh ket qua".
                frame_cb=(self._cb_khung_hinh_batch
                          if (xem_ket_qua and not xem_truc_tiep) else None),
                frame_cb_interval=1.0 / KHOUNG_HINH_FPS,
            )
        except CamAIError as exc:
            # v3.6: loi PHAN TICH (anh hong, camera khong mo duoc) -> bao
            # nguoi dung bang hop thoai, khong chi dong do chu do.
            self.queue.put(("loi_phan_tich", str(exc)))
        except Exception as exc:                      # noqa: BLE001 - GUI phai
            self.queue.put(                            # bat moi loi lai
                ("loi_phan_tich",
                 f"Lỗi không mong đợi: {exc.__class__.__name__}: {exc}")
            )
        else:
            self.queue.put(("result", result))
        finally:
            sys.stdout = old_stdout
            self.queue.put(("done", None))

    def _tien_trinh_cb(self, p: Progress) -> bool:
        now = time.monotonic()
        if now - self.last_progress_at >= PROGRESS_THROTTLE or p.percent >= 100:
            self.last_progress_at = now
            self.queue.put(("progress", p))
        return not self.stop_flag.is_set()

    def _cb_khung_hinh_batch(self, jpeg: bytes) -> None:
        """CHAY TREN THREAD NEN: nhan khung hinh JPEG tu pipeline phan tich.

        KHONG dua vao `self.queue`: hang doi khong gioi han se PHINH BO NHO
        khi quet video dai (moi khung ~50-150 KB x hang chuc nghin khung).
        Dung HOP THU 1 O (single slot): ghi de gia tri cuoi cung, luong UI
        doc va xoa (`_hut_hang_doi`).
        Gioi han ~10 fps bang `time.monotonic()` de khong lam cham pipeline.
        """
        luc = time.monotonic()
        if luc - self._luc_gui_hinh < 1.0 / KHOUNG_HINH_FPS:
            return
        self._luc_gui_hinh = luc
        with self._lock_khung_hinh:
            self._khung_hinh_moi = jpeg
            self._khung_hinh_seq += 1

    def _dung(self):
        self.stop_flag.set()
        self._ghi_log("Đã yêu cầu DỪNG, đang chờ khung hình hiện tại...")

    def _ve_lai_nguoi_hoc(self):
        if self.busy:
            return
        faces_dir = self.v_faces_dir.get().strip() or "known_faces"
        try:
            threshold = float(self.v_face_threshold.get() or 0.40)
        except ValueError:
            threshold = 0.40
        self._che_do_busy(True)
        self._ghi_log(f"> Đọc lại danh sách người đã học từ: {faces_dir}")
        threading.Thread(
            target=self._chay_ve_nguoi_hoc,
            args=(faces_dir, threshold), daemon=True,
        ).start()

    def _chay_ve_nguoi_hoc(self, faces_dir: str, threshold: float):
        from face_engine import FaceEngine

        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.queue)
        try:
            engine = FaceEngine(faces_dir=faces_dir, threshold=threshold)
            names = sorted({name for name, _ in engine.known})
            self.queue.put(
                ("log", f"> Đã học được: {', '.join(names) if names else 'không có ai'}")
            )
        except SystemExit as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("error", f"Không đọc được danh sách người: {exc}"))
        finally:
            sys.stdout = old_stdout
            self.queue.put(("done", None))

    # ------------------------------------------ v3.3: DANG KY NGUOI QUEN
    #
    # Luu 1 nguoi quen tu 1 ANH hoac 1 VIDEO. Nap model ArcFace mat vai giay
    # nen phai chay o THREAD NEN (khong dung `_che_do_busy` - no do khoa ca
    # app; chi khoa DUNG nut dang ky).

    KY_TU_CAM_TEN = '\\/:*?"<>|'

    def _mo_dang_ky_nguoi_quen(self):
        """Chon 1 anh / video co nguoi quen -> luu vao known_faces/<Ten>/."""
        if self.busy:
            return
        path = filedialog.askopenfilename(
            title=self.dich("Chọn ảnh hoặc video có người quen"),
            filetypes=[
                ("Anh", "*.jpg *.jpeg *.png *.bmp"),
                ("Video", "*.mp4 *.avi *.mov *.mkv"),
                ("Tat ca file", "*.*"),
            ],
        )
        if not path:
            return
        ten = self._hoi_ten_nguoi_quen()
        if ten is None:
            return
        ten = ten.strip()
        if not ten:
            self._bao_canh_bao("Chưa nhập tên", "Hãy nhập tên người quen.")
            return
        if len(ten) > 50:
            self._bao_canh_bao(
                "Tên quá dài", "Tên người quen không được quá 50 ký tự.")
            return
        if any(c in ten for c in self.KY_TU_CAM_TEN):
            self._bao_canh_bao(
                "Tên không hợp lệ",
                "Tên người quen không được chứa các ký tự cấm của tên thư mục.")
            return
        faces_dir = (self.v_faces_dir.get().strip()
                     or os.path.join(APP_DIR, "known_faces"))
        thu_muc = os.path.join(faces_dir, ten)
        if os.path.isdir(thu_muc):
            # `save_group` XOA thu muc cu neu da ton tai -> phai hoi TRUOC.
            hoi = (self.dich("Thư mục đã tồn tại: ") + ten + "\n\n"
                   + self.dich("Đăng ký lại sẽ XOÁ các ảnh cũ trong thư mục "
                               "đó. Có tiếp tục không?"))
            if not messagebox.askyesno(self.dich("Thư mục đã tồn tại"), hoi):
                return
        try:
            threshold = float(self.v_face_threshold.get() or 0.40)
        except ValueError:
            threshold = 0.40
        self.btn_dang_ky.configure(state="disabled")
        self._ghi_log(self.dich("> Đăng ký người quen '") + ten
                      + self.dich("' từ: ") + path)
        threading.Thread(
            target=self._chay_dang_ky_nguoi_quen,
            args=(path, ten, faces_dir, threshold), daemon=True,
        ).start()

    def _hoi_ten_nguoi_quen(self):
        """Hop thoai nhap ten nguoi quen. Tra None neu huy / khong mo duoc."""
        try:
            hop = ctk.CTkInputDialog(
                title=self.dich("Đăng ký người quen"),
                text=self.dich("Nhập tên người quen (tối đa 50 ký tự):"),
                font=self.font_nho,
            )
        except Exception:                             # noqa: BLE001
            self._ghi_log("> Không mở được hộp thoại nhập tên.")
            return None
        try:
            return hop.get_input()
        except Exception:                             # noqa: BLE001
            return None

    def _chay_dang_ky_nguoi_quen(self, source, ten, faces_dir, threshold):
        """CHAY TREN THREAD NEN: nap model + quet mat -> luu known_faces/<Ten>."""
        import contextlib

        from dang_ky_anh import cluster, collect_faces, save_group
        from face_engine import FaceEngine

        def ghi(dong):
            self.queue.put(("log", dong))

        try:
            # `collect_faces` co `print()` -> bat stdout cho vao nhat ky GUI
            # (khong du loi ra cua so console).
            with contextlib.redirect_stdout(QueueWriter(self.queue)):
                engine = FaceEngine(faces_dir=faces_dir, threshold=threshold)
                faces = collect_faces(engine, source, max_frames=60)
            ghi(self.dich("> Tìm thấy ") + f"{len(faces)}"
                + self.dich(" khuôn mặt trong ảnh/video đã chọn."))
            if not faces:
                ghi("Không tìm thấy khuôn mặt nào trong ảnh/video đã chọn. "
                    "Thử video rõ mặt hơn, hoặc ảnh chụp gần hơn.")
                return
            groups = cluster(faces, max_people=1)
            if not groups:
                ghi("Không gom được nhóm người nào.")
                return
            n = save_group(groups[0], ten, faces_dir)
            ghi(self.dich("> Đã lưu ảnh cho người quen: ") + ten)
            ghi(self.dich("> Số ảnh đã lưu: ") + f"{n}"
                + self.dich(" | thư mục: ") + os.path.join(faces_dir, ten))
            # Doc lai danh sach nguoi quen -> GUI co danh sach moi ngay.
            # SUA LOI "main thread is not in main loop": KHONG goi
            # `_nap_lai_danh_sach_nguoi_quen()` o day. Ham do doc
            # `self.v_faces_dir` (tkinter.StringVar) -> goi Tk tu thread nen
            # se nem RuntimeError. Chi day thong bao ve hang doi, de luong UI
            # (trong `_hut_hang_doi`) thuc hien viec nap lai danh sach.
            self.queue.put(("nap_lai_danh_sach", (faces_dir, threshold)))
        except SystemExit as exc:
            self.queue.put(("error", str(exc)))
            return
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("error", self.dich("Lỗi khi đăng ký người quen: ")
                            + str(exc)))
            return
        finally:
            # Luon bat lai nut (ke ca khi loi) - khong dung `_che_do_busy`.
            self.queue.put(("xong_dang_ky", None))

    def _nap_lai_danh_sach_nguoi_quen(self, faces_dir=None, threshold=None):
        """Nap lai danh sach nguoi quen - KHONG dung `_che_do_busy`.

        `_ve_lai_nguoi_hoc` khoa ca app (va "done" cua no se TAT xem truc
        tiep) -> khong dung o day. Day la ban rieng: chi nap lai danh sach.

        CHAY TREN LUONG UI (khong phai thread nen). Neu `faces_dir` /
        `threshold` da duoc dua vao thi dung luon gia tri do (gia tri doc
        o luong UI truoc do) -> khong phai doc bien Tk o day nua. Neu khong
        dua vao -> doc `self.v_faces_dir` / `self.v_face_threshold` (chi an
        toan tren luong UI).
        """
        if faces_dir is None:
            faces_dir = self.v_faces_dir.get().strip() or "known_faces"
        if threshold is None:
            try:
                threshold = float(self.v_face_threshold.get() or 0.40)
            except ValueError:
                threshold = 0.40
        threading.Thread(
            target=self._chay_nap_lai_nguoi_quen,
            args=(faces_dir, threshold), daemon=True,
        ).start()

    def _chay_nap_lai_nguoi_quen(self, faces_dir: str, threshold: float):
        """CHAY TREN THREAD NEN. Chi ghi nhat ky, KHONG dung widget."""
        from face_engine import FaceEngine

        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.queue)
        try:
            engine = FaceEngine(faces_dir=faces_dir, threshold=threshold)
            names = sorted({name for name, _ in engine.known})
            self.queue.put(
                ("log", f"> Đã học được: {', '.join(names) if names else 'không có ai'}")
            )
        except SystemExit as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("error", f"Không đọc được danh sách người: {exc}"))
        finally:
            sys.stdout = old_stdout

    # ------------------------------------------- v3.3: DOC BIEN SO THU
    #
    # CHI DOC 1 ANH. `BoDocBienSo.doc()` chi tra ve bien so da duoc XAC NHAN
    # qua >= 2 khung hinh lien tiep -> goi tren 1 anh se KHONG ra ket qua.
    # Nen o day dung `tim_vung()` + `doc_vung()` (doc truc tiep 1 vung).

    def _mo_doc_bien_so_thu(self):
        """Chon 1 anh -> thu doc bien so (thread nen)."""
        if self.busy:
            return
        path = filedialog.askopenfilename(
            title=self.dich("Chọn ảnh có biển số"),
            filetypes=[("Anh", "*.jpg *.jpeg *.png *.bmp"),
                       ("Tat ca file", "*.*")],
        )
        if not path:
            return
        self.btn_doc_bien_so_thu.configure(state="disabled")
        self._ghi_log(self.dich("> Thử đọc biển số trong ảnh: ") + path)
        threading.Thread(
            target=self._chay_doc_bien_so_thu,
            args=(path, self.v_bien_so_vung.get().strip() or None,
                  self.v_bien_so_dir.get().strip()),
            daemon=True,
        ).start()

    def _chay_doc_bien_so_thu(self, path, vung, thu_muc_luu):
        """CHAY TREN THREAD NEN: nap engine OCR -> tim vung -> doc bien so."""
        import cv2

        from bien_so import BoDocBienSo

        bo = None
        try:
            bo = BoDocBienSo(
                vung=vung,
                thu_muc_luu=thu_muc_luu,
                log=lambda dong: self.queue.put(("log", dong)),
            )
            if not bo.nap():
                self.queue.put(("error", "Không nạp được engine đọc biển số."))
                return
            anh = cv2.imread(path)
            if anh is None:
                self.queue.put(("error", self.dich("Không đọc được ảnh: ") + path))
                return
            so_kq = 0
            for (x1, y1, x2, y2) in bo.tim_vung(anh):
                crop = anh[y1:y2, x1:x2]
                for kq in bo.doc_vung(crop, (x1, y1, x2, y2)):
                    so_kq += 1
                    self.queue.put(("log", self.dich("Biển số: ") + kq.chuoi
                                    + self.dich(" | tin cậy ")
                                    + f"{kq.tin_cay:.2f}"
                                    + self.dich(" | số hàng: ")
                                    + f"{kq.so_hang}"
                                    + self.dich(" | vùng: ")
                                    + str(kq.khung)))
                    duong_dan = self._luu_crop_bien_so_thu(crop, kq, thu_muc_luu)
                    if duong_dan:
                        self.queue.put(("log", self.dich("Ảnh biển số đã lưu: ")
                                        + duong_dan))
            if so_kq == 0:
                self.queue.put(("log", "Không đọc được biển số trong ảnh này."))
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("error", self.dich("Lỗi khi thử đọc biển số: ")
                            + str(exc)))
        finally:
            if bo is not None:
                try:
                    bo.close()
                except Exception:                     # noqa: BLE001
                    pass
            self.queue.put(("xong_doc_bien_so_thu", None))

    def _luu_crop_bien_so_thu(self, crop, kq, thu_muc_luu):
        """Luu anh crop bien so -> tra duong dan (rong = khong luu duoc)."""
        import cv2

        thu_muc = thu_muc_luu or THU_MUC_BIEN_SO
        try:
            os.makedirs(thu_muc, exist_ok=True)
            ten = "".join(c if c.isalnum() else "_" for c in kq.chuoi) or "bien_so"
            duong_dan = os.path.join(
                thu_muc, f"thu_{ten}_{int(time.time())}.jpg")
            if not cv2.imwrite(duong_dan, crop,
                               [cv2.IMWRITE_JPEG_QUALITY, 95]):
                return ""
            return duong_dan
        except Exception:                             # noqa: BLE001
            return ""

    # ----------------------------------------- v3.3: VE VUNG TRONG CUA SO
    #
    # Ve vung bang chuot NGAY trong cua so nay (module `ve_vung_gui`).
    # Module do do agent khac viet - gui.py CHI GOI, khong viet lai.

    def _ve_vung_ngay_tai_day(self):
        """Ve vung ngay trong cua so nay (chuot keo tren khung hinh)."""
        if self.busy:
            return
        source = self.v_video.get().strip()
        if not source:
            self._bao_canh_bao(
                "Thiếu nguồn", "Hãy chọn nguồn trước khi vẽ vùng.")
            return
        # v3.6: nguon CAMERA (may/IP) khong lay duoc khung hinh goc de ve
        # vung tuong doi -> bao ro, khong mo loi.
        if loai_nguon(source) in (LOAI_CAMERA, LOAI_MANG):
            self._bao_canh_bao(
                "Chỉ vẽ vùng được với nguồn video.",
                "Chỉ vẽ vùng được với nguồn video.",
            )
            return
        self._ghi_log(self.dich("> Đang lấy khung hình để vẽ vùng: ") + source)
        threading.Thread(
            target=self._chay_lay_frame_ve_vung, args=(source,), daemon=True
        ).start()

    def _chay_lay_frame_ve_vung(self, source):
        """CHAY TREN THREAD NEN: doc 1 khung hinh (giua video) -> hang doi."""
        import cv2

        try:
            # v3.6: nguon ANH -> doc thang bang imread (VideoCapture khong mo
            # duoc file anh).
            if loai_nguon(source) == LOAI_ANH:
                frame = cv2.imread(source, cv2.IMREAD_COLOR)
                ok = frame is not None
            else:
                cap = cv2.VideoCapture(source)
                if not cap.isOpened():
                    self.queue.put(("error",
                                    self.dich("Không mở được video: ") + source))
                    return
                try:
                    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
                    if total > 10:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
                    ok, frame = cap.read()
                finally:
                    cap.release()
            if not ok or frame is None:
                self.queue.put(
                    ("error", "Không đọc được khung hình nào từ video."))
                return
            # Hang doi luon la cap (loai, du_lieu) -> du lieu la 1 cap.
            self.queue.put(("ve_vung_frame", (frame, source)))
        except Exception as exc:                      # noqa: BLE001
            self.queue.put(("error", self.dich("Lỗi khi lấy khung hình: ")
                            + str(exc)))

    def _xem_ve_vung_trong_gui(self, frame, source):
        """CHAY TREN LUONG UI: mo hop thoai ve vung -> luu file vung.

        `ve_vung_trong_gui` tra ve (x1, y1, x2, y2) TUONG DOI 0..1 hoac None
        neu huy. Import LAZY + try/except: module co the chua co -> chi ghi
        nhat ky, KHONG lam chet app.
        """
        try:
            from ve_vung_gui import ve_vung_trong_gui
        except Exception:                             # noqa: BLE001
            self._ghi_log("Chưa có module ve_vung_gui, hãy dùng nút "
                          "'Vẽ vùng trên video này'.")
            return
        try:
            rect = ve_vung_trong_gui(self, frame, nguon=source, log=self._ghi_log)
        except Exception as exc:                      # noqa: BLE001
            self._ghi_log(self.dich("Lỗi khi vẽ vùng: ") + str(exc))
            return
        if not rect:
            self._ghi_log("> Đã huỷ vẽ vùng.")
            return
        try:
            from ve_vung import save_zone

            h, w = frame.shape[:2]
            rx1, ry1, rx2, ry2 = rect
            path = (self.v_vung_file.get().strip()
                    or os.path.join(APP_DIR, "vung.txt"))
            save_zone(path, (rx1 * w, ry1 * h, rx2 * w, ry2 * h), w, h, source)
        except Exception as exc:                      # noqa: BLE001
            self._ghi_log(self.dich("Lỗi khi lưu file vùng: ") + str(exc))
            return
        finally:
            frame = None              # giai phong anh (khong ro bo nho)
        self.v_vung_file.set(path)
        self._ghi_log(self.dich("Đã lưu vùng: ") + path)
        self._ghi_log(self.dich("Vùng (tương đối): ")
                      + f"x {rx1:.3f} -> {rx2:.3f} | y {ry1:.3f} -> {ry2:.3f}")

    def _che_do_busy(self, dang_chay: bool):
        self.busy = dang_chay
        self.stop_flag.clear()
        self.btn_chay.configure(state="disabled" if dang_chay else "normal")
        self.btn_dung.configure(state="normal" if dang_chay else "disabled")
        self._cap_nhat_trang_thai()

    # ---------------------------------------------------- hang doi -> UI

    def _hut_hang_doi(self):
        """CHAY TREN LUONG UI: rong hang doi roi cap nhat widget.

        GOM NHOM de khoi lam tre cua so (dieu nay quyet dinh do giat khi
        keo cua so):
          * moi vong chi goi widget nhieu LAN MOT LAN,
          * dong nhap ky ghi 1 the o (1 configure + 1 insert + 1 see),
          * chi lay KHUNG HINH CUOI CUNG trong hang doi (anh cu hon chua
            thi cu, khong can ve het),
          * loi / ket qua / xong van xu ly ngay de khong cham.

        CHONG VAO LAI (v3.6): trong vong bom co the mo HOP THOAI MODAL (bao
        loi phan tich, ve vung). Tk chay vong lap rieng cho hop thoai -> timer
        `after()` cua vong bom sau co the chay LAI trong khi vong bom dang
        chay -> 2 vong bom cung luc -> bom 2 lan moi chu ky -> app bi GIAT.
        -> co co danh `_dang_bom`: vong bom vao lai thi THOAT NGAY (khong
        len lich vong moi), vong ngoai van len lich DUNG MOT LAN.
        """
        if getattr(self, "_dang_bom", False):
            return                      # da co bom chay -> khong bom 2 vong
        self._dang_bom = True
        try:
            self._hut_hang_doi_noi_dung()
        finally:
            self._dang_bom = False
            self.after(PUMP_MS, self._hut_hang_doi)

    def _hut_hang_doi_noi_dung(self):
        """Phan than xu ly cua `_hut_hang_doi` (xem ghi chu ben tren)."""
        dong_log = []
        khung_hinh = None
        for _ in range(SO_MUC_1_VONG):
            try:
                kind, payload = self.queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                dong_log.append(payload)
            elif kind == "frame":
                khung_hinh = payload          # giu vong CUOI
            elif kind == "su_kien":
                # 1 su kien -> 1 the trong DANH SACH SU KIEN (cot phai)
                self.panel_su_kien.them_su_kien(payload or {})
            elif kind == "thumb":
                # anh xem truoc video mau: tao PhotoImage o day (luong UI).
                chi_so, anh = payload
                try:
                    from PIL import Image, ImageTk
                    if anh is not None:
                        # Thu nho anh ve kich thuoc the moi (88x50) de dai
                        # video mau gon lai (khong sua gui_khung.py).
                        anh = anh.resize((RONG_THUMB_MOI, CAO_THUMB_MOI),
                                         Image.LANCZOS)
                    tk_anh = ImageTk.PhotoImage(anh) if anh is not None else None
                    self.luu_video_mau.dat_anh(chi_so, tk_anh)
                except Exception:                        # noqa: BLE001
                    self.luu_video_mau.dat_anh(chi_so, None)
            elif kind == "progress":
                self._hien_tien_trinh(payload)
            elif kind == "error":
                dong_log.append(f"[LỖI] {payload}")
                self.lbl_loi.configure(text=self.dich(payload))
                self._set_trang_thai("loi")
            elif kind == "loi_phan_tich":
                # v3.6: loi PHAN TICH (anh hong / camera khong mo duoc) phai
                # BAO CHO NGUOI DUNG bang hop thoai - khong chi dong do chu
                # do trong nhat ky.
                dong_log.append(f"[LỖI] {payload}")
                self.lbl_loi.configure(text=self.dich(payload))
                self._set_trang_thai("loi")
                self._bao_canh_bao("Lỗi phân tích", str(payload))
            elif kind == "quet_camera":
                # v3.6: ket qua quet camera (thread nen -> hang doi -> UI).
                self._ket_thuc_quet_camera(payload)
            elif kind == "quet_camera_loi":
                self._quet_camera_loi(payload)
            elif kind == "result":
                self.result = payload
                self._hien_ket_qua(payload)
            elif kind == "done":
                self._dung_xem_truc_tiep()
                self._che_do_busy(False)
                self._cap_nhat_trang_thai()
            elif kind == "xem_xong":
                self._ket_thuc_hinh()
            elif kind == "ve_vung_frame":
                # v3.3: ve vung ngay trong cua so (module `ve_vung_gui`).
                # CHAY TREN LUONG UI - hop thoai modal, chan den khi anh
                # keo xong + bam Luu.
                self._xem_ve_vung_trong_gui(payload[0], payload[1])
            elif kind == "nap_lai_danh_sach":
                # v3.3: nap lai danh sach nguoi quen sau khi dang ky xong.
                # CHAY TREN LUONG UI -> doc `self.v_faces_dir` (StringVar) an
                # toan. Gia tri (faces_dir, threshold) do thread nen day len.
                f_dir, f_threshold = payload
                self._nap_lai_danh_sach_nguoi_quen(f_dir, f_threshold)
            elif kind == "xong_dang_ky":
                btn = getattr(self, "btn_dang_ky", None)
                if btn is not None:
                    btn.configure(state="normal")
            elif kind == "xong_doc_bien_so_thu":
                btn = getattr(self, "btn_doc_bien_so_thu", None)
                if btn is not None:
                    btn.configure(state="normal")
        if dong_log:
            self._ghi_log_nhieu(dong_log)
        # --- v3.2: khung hinh che do phan tich theo lo ---
        # Doc tu HOP THU 1 O (khong phai hang doi). Chi ve khi seq MOI (khong
        # giai ma lai cung mot khung -> lam cham luong UI).
        if khung_hinh is None:
            with self._lock_khung_hinh:
                if self._khung_hinh_seq != self._khung_hinh_seq_da_doc:
                    self._khung_hinh_seq_da_doc = self._khung_hinh_seq
                    khung_hinh = self._khung_hinh_moi
        if khung_hinh is not None:
            self._hien_khung_hinh(khung_hinh)
        else:
            # Keo / doi kich thuoc cua so: ve lai khung CUOI cho vua khung cha
            # (khong them vong `after()` rieng).
            self._ve_lai_khung_hinh()
        # KHONG len lich vong bom o day - `_hut_hang_doi` (lop ngoai) lo.

    @staticmethod
    def _doi_neu_khac(var, gia_tri_moi) -> bool:
        """Chi goi .set() khi gia tri THAT SU doi - tranh ve lai widget
        10 lan/giay khi so khong doi (do la nguyen nhan giat nhe nhat)."""
        chuoi = str(gia_tri_moi)
        if var.get() == chuoi:
            return False
        var.set(chuoi)
        return True

    def _bat_tien_trinh_live(self):
        """Chuyen thanh tien trinh sang che do INDETERMINATE (nguon live).

        Camera (may hoac IP) khong biet truoc tong so khung hinh -> khong
        co phan tram. Thanh "chay vui" de nguoi dung biet app dang chay,
        thay vi duc yen o 0% (nhu loi chia 0).
        """
        self._bar_indeterminate = True
        try:
            self.bar.configure(mode="indeterminate")
            self.bar.start()
        except Exception:                             # noqa: BLE001
            self._bar_indeterminate = False

    def _ket_tuc_tien_trinh(self):
        """Tra thanh tien trinh ve che do DETERMINATE (video / anh)."""
        self._bar_indeterminate = False
        try:
            self.bar.stop()
            self.bar.configure(mode="determinate")
        except Exception:                             # noqa: BLE001
            pass

    def _hien_tien_trinh(self, p: Progress):
        if p.total_frames:
            self._set_trang_thai(
                "khung_hinh_day_du", frame=p.frame_index, tong=p.total_frames,
                phan_tram=f"{p.percent:.0f}",
            )
        else:
            self._set_trang_thai("khung_hinh", frame=p.frame_index)
        # Nguon live: bar dang o che do indeterminate -> KHONG set() (se
        # lam vong chay nguoc lai thanh "chay vui").
        if not getattr(self, "_bar_indeterminate", False):
            if p.percent != self._bar_cu:      # bar.set() ton 1.8ms, chi khi doi
                self._bar_cu = p.percent
                self.bar.set(p.percent / 100.0)
        self._doi_neu_khac(self.v_so_nguoi, p.so_nguoi)
        self._doi_neu_khac(self.v_so_mat, p.so_mat)
        self._doi_neu_khac(self.v_so_vao, p.vao)
        self._doi_neu_khac(self.v_so_ra, p.ra)
        self._doi_neu_khac(self.v_so_trong_vung, p.trong_vung)
        so_quen = len([t for t in str(p.nhan_dien or "").split("|") if t.strip()])
        self._doi_neu_khac(self.v_so_quen, so_quen)
        if p.nhan_dien and p.nhan_dien != self.last_names:
            self.last_names = p.nhan_dien
            self._ten_nguoi_quen = p.nhan_dien      # cho khung xem video
            self._ghi_log(f"Nhận diện: {p.nhan_dien}")

        # --- canh bao: KHONG goi o day nua ---
        # `cam_ai_core.CanhBaoNoi` da noi san `canh_bao.py` vao pipeline va tu
        # goi cho su kien vuot nguong / dung lau. Neu GUI goi them o day thi
        # moi su kien bi BAO TRUNG (2 lan chuong, 2 hop thoai).
        # GUI chi hien thi so lieu; viec gui tin ra ngoai do LOP LOI lo.

    def _hien_ket_qua(self, result):
        # v3.6: nguon live (camera) -> thanh tien trinh dang chay vui, dung
        # lai thoi. Video / anh -> bar chay toi 100%.
        if getattr(self, "_bar_indeterminate", False):
            self._ket_tuc_tien_trinh()
            try:
                self.bar.set(1.0)
            except Exception:                         # noqa: BLE001
                pass
        else:
            self._ket_tuc_tien_trinh()
            self.bar.set(1.0)
        self._dung_xem_truc_tiep()      # ket thuc khung xem ngay khi xong
        self._set_trang_thai("dung_giua" if result.stopped else "xong")
        # v3.6: ket qua co the la VIDEO (mp4) hoac ANH (jpg) - noi ro loai.
        self._ghi_log(f"Kết quả: {result.out_path}")
        self._ghi_log(f"Báo cáo: {result.report_path}")
        # Khong goi canh bao o day: CanhBaoNoi cua cam_ai_core da gui san
        # (vuot nguong + dung lau). Chi ghi ra nhat ky de nguoi dung doc lai.

    def _ghi_log(self, text: str):
        """Ghi 1 dong vao nhat ky (dong nhat ky cung doi ngon ngu)."""
        self._ghi_log_nhieu([text])

    def _ghi_log_nhieu(self, dong_log: list[str]):
        """Ghi NHOM dong vao nhat ky trong 1 the o widget.

        Truoc day moi dong goi 4 lenh Tkinter rieng (configure + insert +
        delete + see) -> hang dong log lam tre luong UI ~2,3ms moi dong va
        1 vong `after()` co the tre 2 GIAY. Gom lai 1 insert + 1 see.
        """
        if not dong_log:
            return
        chu = "".join(self.dich(dong) + "\n" for dong in dong_log)
        self.log_box.configure(state="normal")
        self.log_box.insert("end", chu)
        self.log_lines += len(dong_log)
        if self.log_lines > MAX_LOG_LINES:
            # Bo dung so dong vua du - KHONG xoa 1/2 nhat ky nhu truoc.
            drop = self.log_lines - MAX_LOG_LINES
            self.log_box.delete("1.0", f"{drop + 1}.0")
            self.log_lines -= drop
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ---------------------------------------- KHUNG XEM VIDEO TRUC TIEP
    #
    # LY DO PHAI CO: cam_ai_core.Progress chi co SO (khong co anh), va
    # file ket qua *.mp4 dang ghi KHONG DOC DUOC khi chua finalize
    # ("moov atom not found" - da do that). nen de co hinh phai doc video
    # 1 lan nua o thread rieng. Thread nay KHONG bao gio go widget.

    def _chay_xem_truc_tiep(self, cfg: AnalysisConfig) -> None:
        """Wrapper cho thread xem video: moi loi -> nhat ky, khong lam tre."""
        try:
            self._vong_xem(cfg)
        except Exception as exc:                          # noqa: BLE001
            self.queue.put(
                ("log", f"> Không bật được xem video trực tiếp: {exc}")
            )
        finally:
            self._ket_thuc_xem.set()
            self._xem_dang_chay = False
            self.queue.put(("xem_xong", None))

    def _vong_xem(self, cfg: AnalysisConfig) -> None:
        """CHAY TREN THREAD NEN. Doc video, chay YOLO (va nhận diện mặt nếu
        anh bật) để vẽ khung CÓ TÊN người, rồi đẩy ảnh JPEG + danh sách
        ẢNH CROP của từng đối tượng vào hàng đợi.

        KHÔNG sửa cam_ai_core: chỉ đọc hằng số / hàm vẽ của nó.
        Overlay vẽ bằng `gui_khung` (PIL) vì `cv2.putText` không có dấu.
        """
        import cv2
        import supervision as sv
        from ultralytics import YOLO

        # CHI DOC, KHÔNG sửa cam_ai_core: dùng lại hằng số + hàm vẽ của nó.
        from cam_ai_core import (PERSON_CLASS_ID, VAT_THE_MAC_DINH,
                                 load_zone, ten_vat_the)

        cap = cv2.VideoCapture(cfg.input)
        if not cap.isOpened():
            raise CamAIError(f"không mở được video: {cfg.input}")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        detector = YOLO(cfg.model)
        tracker = sv.ByteTrack()

        vat_the_ids = np.array([], dtype=int)
        ten_lop: dict = {}
        if cfg.nhan_vat_the:
            id_lop = {ten: cid for cid, ten in detector.names.items()}
            yeu_cau = [x.strip() for x in str(cfg.lop).split(",") if x.strip()]
            if not yeu_cau:
                chon = [t for t in VAT_THE_MAC_DINH if t in id_lop]
                sai = []
            elif _la_tat_ca_lop(yeu_cau[0]):
                chon = [t for t in detector.names.values() if t != "person"]
                sai = []
            else:
                # v3.6: DUNG CHUNG ham chon lop voi cam_ai_core (`_chon_lop`)
                # -> GUI hieu ca ten lop tieng Viet, ket qua GIONG HET CLI.
                chon, sai = _chon_lop_cho_xem(str(cfg.lop), id_lop)
            # Lop go sai khong duoc lam VONG XEM CHET: bo qua + bao nhat ky,
            # dung lai chay tiep voi cac lop con lai. Truoc day `id_lop[t]`
            # nem KeyError lam ca khung xem truc tiep tat.
            if sai:
                self.queue.put((
                    "log",
                    f"> [vật thể] Bỏ qua lớp không có: {', '.join(sai)}.",
                ))
            if chon:
                self.queue.put((
                    "log",
                    f"> [vật thể] Các lớp đang nhận: {', '.join(chon)}",
                ))
            elif sai:
                self.queue.put((
                    "log",
                    "> [vật thể] Không còn lớp nào hợp lệ, tắt nhận vật thể.",
                ))
            vat_the_ids = np.array(
                sorted({id_lop[t] for t in chon if id_lop[t] != PERSON_CLASS_ID}),
                dtype=int,
            )
            ten_lop = {cid: ten_vat_the(ten) for cid, ten in detector.names.items()}
            if vat_the_ids.size:
                # Dich theo MAU (dich roi moi format) - khoa co {n}/{ds} trong
                # DICH_VI_EN la mau, khong phai chuoi literal.
                self.queue.put((
                    "log",
                    self.dich("> [vật thể] Đang nhận {n} lớp: {ds}").format(
                        n=len(vat_the_ids),
                        ds=", ".join(ten_lop[int(i)] for i in vat_the_ids)),
                ))
            else:
                self.queue.put((
                    "log", "> [vật thể] Không còn lớp nào hợp lệ, tắt nhận vật thể."))

        zone_px = None
        if cfg.vung:
            rel = load_zone(cfg.vung)
            zone_px = (int(rel[0] * width), int(rel[1] * height),
                       int(rel[2] * width), int(rel[3] * height))

        # --- NHẬN DIỆN MẶT chạy SONG SONG để ghi TÊN lên khung người ---
        # Đây là cách DUY NHẤT lấy tên mà không sửa cam_ai_core: Progress
        # chỉ trả về 1 chuỗi "An | Bình", không gắn được vào từng khung.
        engine = None
        if self.v_nhan_ten.get() == "1" and not cfg.no_face:
            try:
                from face_engine import FaceEngine
                engine = FaceEngine(faces_dir=cfg.faces_dir,
                                    threshold=cfg.face_threshold,
                                    providers=chon_providers(cfg.thiet_bi))
                self.queue.put(
                    ("log", f"> Khung video: đã bật nhận diện tên ({engine.device})"))
            except Exception as exc:                       # noqa: BLE001
                engine = None
                self.queue.put((
                    "log",
                    f"> Không bật được nhận diện tên trên khung: {exc}",
                ))

        buoc = 1          # bo qua bao nhieu khung giua 2 lan chay YOLO
        dem = 0
        vong = 0
        xy = None         # khung nguoi cua VONG GAN NHAT (giu lai de ve)
        ids: list = []
        do_tin: list = []  # do tin cay cua YOLO cho tung nguoi
        vat_the = None    # vat the khac cua vong gan nhat
        ten_theo_id: dict = {}    # id theo doi -> ten / tuoi / gioi
        x_truoc: dict = {}        # id -> tam x vong truoc (dem qua vach giua)
        vao_vung_luc: dict = {}   # id -> thoi diem vao vung (dung lau)
        # --- phat hien SU KIEN (them vao danh sach su kien) ---
        moc_thoi_gian = 0.0       # giay trong video (de gan nhan gio)
        trong_vung_truoc: dict = {}   # id -> co trong vung vong truoc khong
        da_bao_qua: set = set()   # id da bao "vuot nguong" (khong bao lai)
        ls_vung: list = []          # lich su so nguoi trong vung
        dinh_vung = day_vung = 0    # dinh / day cua so nguoi trong vung
        dem_vao = dem_ra = 0
        lan_gui_the = 0.0
        quet_mat_luc = 0.0
        giua = width / 2.0
        t0_vong = time.perf_counter()
        try:
            while cap.isOpened():
                if self._ket_thuc_xem.is_set():
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                dem += 1
                # Giay trong VIDEO (khong phai giay do) - dung cho nhan gio.
                moc_thoi_gian = dem / max(1.0, fps)

                if dem >= buoc:
                    dem = 0
                    vong += 1
                    t0 = time.perf_counter()
                    tat_ca = sv.Detections.from_ultralytics(
                        detector(frame, verbose=False, conf=cfg.conf)[0]
                    )
                    detections = tat_ca[tat_ca.class_id == PERSON_CLASS_ID]
                    detections = tracker.update_with_detections(detections)
                    # Tu chinh nhip: YOLO chi chiem ~1/4 cua 1 loi xu ly.
                    # CHAY CLAMP: bo qua qua nhieu khung se khung cu bi cu,
                    # nguoi nhin thay nguoi ma khong co khung. Gioi han ~0.6s.
                    thoi_gian = time.perf_counter() - t0
                    buoc = max(1, min(int(fps * thoi_gian * XEM_VIDEO_PHI_CHAY),
                                      max(1, int(fps * XEM_VIDEO_CU_MAX))))

                    if len(detections):
                        xy = detections.xyxy
                        ids = ([int(t) for t in detections.tracker_id]
                               if detections.tracker_id is not None
                               else list(range(len(detections))))
                        do_tin = ([float(c) for c in detections.confidence]
                                  if getattr(detections, "confidence", None)
                                  is not None else [0.0] * len(detections))
                    else:
                        xy, ids, do_tin = None, [], []

                    vat_the = None
                    if vat_the_ids.size and len(tat_ca):
                        vat_the = tat_ca[np.isin(tat_ca.class_id, vat_the_ids)]
                        if not len(vat_the):
                            vat_the = None

                    # Quet mat: gioi han theo VONG (MAT_MOI_N_LAN) VA theo
                    # THOI GIAN (MAT_MOI_N_GIAY). Can gioi han thoi gian vi
                    # khi video chay nhanh, so vong YOLO/giay tang len nhieu
                    # thi quet mat lien tuc - moi lan la mot lan chay nang
                    # (SCRFD + ArcFace + uoc luong tuoi gioi) ~210ms.
                    # Gioi han ~3 lan/giay: ten van hien tren khung (ten duoc
                    # giu them TEN_GIU_NAM giay) nhung khung chay mat hon.
                    if (engine is not None and xy is not None
                            and vong % MAT_MOI_N_LAN == 0
                            and time.monotonic() - quet_mat_luc >= MAT_MOI_N_GIAY):
                        quet_mat_luc = time.monotonic()
                        self._quet_ten_nguoi(engine, frame, xy, ids,
                                              ten_theo_id)

                # ----- dung nhan + mau tu ket qua cua vong gan nhat -----
                bac = time.monotonic()
                boxes_nguoi, nhan_nguoi, mau_nguoi, uu_tien = [], [], [], []
                if xy is not None:
                    for i, box in enumerate(xy):
                        tid = ids[i]
                        info = ten_theo_id.get(tid) or {}
                        # Ten da rut duoc giu lai MOT LUC: nguoi quay mat
                        # di van thay ten tren khung, khong nhay ve
                        # "Nguoi la" khi chi mat thoang quang.
                        con_ten = (info.get("ten")
                                   and bac - info.get("luc", 0.0) <= TEN_GIU_NAM)
                        if con_ten:
                            nhan = info["ten"]
                            if info.get("tuoi"):
                                nhan = f"{nhan} · {info['tuoi']}"
                            if info.get("gioi"):
                                nhan = f"{nhan} · {info['gioi']}"
                            mau = GK.MAU_NGUOI_QUEN if info.get("quen") \
                                else GK.MAU_NGUOI
                            uu_tien.append(bool(info.get("quen")))
                        else:
                            nhan = "Người lạ" if tid is None else f"Người {tid + 1}"
                            mau = GK.MAU_NGUOI
                            uu_tien.append(False)
                        boxes_nguoi.append([float(v) for v in box])
                        nhan_nguoi.append(nhan)
                        mau_nguoi.append(mau)

                boxes_vat, nhan_vat = [], []
                if vat_the is not None and len(vat_the):
                    for box, cls_id in zip(vat_the.xyxy, vat_the.class_id):
                        boxes_vat.append([float(v) for v in box])
                        nhan_vat.append(ten_lop.get(int(cls_id), "Vật thể"))

                # ----- dem qua vach giua -----
                if xy is not None:
                    for i, box in enumerate(xy):
                        tid = ids[i]
                        tam_x = (float(box[0]) + float(box[2])) / 2.0
                        truoc = x_truoc.get(tid)
                        if truoc is not None:
                            if truoc < giua <= tam_x:
                                dem_vao += 1
                            elif truoc >= giua > tam_x:
                                dem_ra += 1
                        x_truoc[tid] = tam_x

                now = time.monotonic()
                trong_vung = 0
                if xy is not None:
                    for i, box in enumerate(xy):
                        if _o_vung(box, zone_px, cfg.vung_nhay):
                            trong_vung += 1
                            vao_vung_luc.setdefault(ids[i], now)
                        else:
                            vao_vung_luc.pop(ids[i], None)

                trang_thai_vung = "trong"
                if zone_px is not None:
                    if cfg.vung_max and trong_vung > cfg.vung_max:
                        trang_thai_vung = "qua"
                    elif cfg.canh_lau and any(
                            now - t >= cfg.canh_lau
                            for t in vao_vung_luc.values()):
                        trang_thai_vung = "dung_lau"
                    elif trong_vung:
                        trang_thai_vung = "co_nguoi"

                # ----- BANG THONG KE VUNG (5 dong, de goc tren trai video) -----
                # Chay tren KHUNG HINH cua phan tich, khong phai tren widget:
                # nho vay so lieu doi theo video thay vi theo nhip ve UI.
                if zone_px is not None and dem % BA_VUNG_MOI_N_KHUNG == 0:
                    ls_vung.append(trong_vung)
                    if len(ls_vung) > 2000:
                        del ls_vung[:1000]
                    if trong_vung > dinh_vung:
                        dinh_vung = trong_vung
                    if len(ls_vung) == 1 or trong_vung < day_vung:
                        day_vung = trong_vung
                bang_vung = None
                if zone_px is not None:
                    tb = (sum(ls_vung) / len(ls_vung)) if ls_vung else 0.0
                    bang_vung = [
                        ("Trong vùng hiện tại", f"{trong_vung}"),
                        ("Trung bình", f"{tb:.1f}"),
                        ("Đỉnh", f"{dinh_vung}"),
                        ("Đáy", f"{day_vung}"),
                        ("A->B", f"{dem_vao + dem_ra}"),
                    ]

                # ----- PHAT HIEN SU KIEN -> danh sach su kien (co gioi han nhip) -----
                if now - lan_gui_the >= SU_KIEN_CAP_NHAT_MS / 1000.0:
                    lan_gui_the = now
                    self._quet_su_kien(
                        frame, xy, ids, do_tin, ten_theo_id, zone_px, cfg,
                        moc_thoi_gian, trong_vung, dem_vao, dem_ra,
                        trong_vung_truoc, vao_vung_luc, da_bao_qua,
                    )

                # ----- ve overlay -----
                so_quen = len({t["ten"] for t in ten_theo_id.values()
                               if t.get("quen") and t.get("ten")})
                badge = [self.dich(f"Người: {len(boxes_nguoi)}")]
                if so_quen:
                    badge.append(self.dich(f"Người quen: {so_quen}"))
                if vat_the_ids.size:
                    # Chi hien khi bat nhan vat the - de nguoi dung thay
                    # ngay duoc so khop cam.
                    badge.append(self.dich(f"Vật thể: {len(boxes_vat)}"))
                if zone_px is not None:
                    badge.append(self.dich(f"Trong vùng: {trong_vung}"))
                hien = GK.ve_khung_hinh(
                    frame,
                    boxes_nguoi=boxes_nguoi, nhan_nguoi=nhan_nguoi,
                    mau_nguoi=mau_nguoi, uu_tien_nguoi=uu_tien,
                    boxes_vat=boxes_vat, nhan_vat=nhan_vat,
                    zone_px=zone_px, trang_thai_vung=trang_thai_vung,
                    nguoi_trong_vung=trong_vung, nguoi_toi_da=cfg.vung_max,
                    vao=dem_vao, ra=dem_ra,
                    hien_khung=cfg.show_box, hien_nhan=cfg.show_label,
                    hien_vach=cfg.show_line, hien_vung=zone_px is not None,
                    chu_dien=badge,
                    bang_vung=bang_vung or (),
                )

                # Thu nho cho vua khung xem, GIU NGUYEN ti le goc.
                cao_h, rong_h = hien.shape[:2]
                ty_le = min(1.0, XEM_VIDEO_MO_RONG_TOI_DA / float(rong_h))
                if ty_le < 1.0:
                    hien = cv2.resize(
                        hien,
                        (max(1, int(rong_h * ty_le)), max(1, int(cao_h * ty_le))),
                        interpolation=cv2.INTER_AREA,
                    )
                ok2, buf = cv2.imencode(
                    ".jpg", hien,
                    [int(cv2.IMWRITE_JPEG_QUALITY), XEM_VIDEO_JPEG],
                )
                if ok2:
                    self.queue.put(("frame", buf.tobytes()))

                # --- GIOI HAN TOC DO: xem video o toc do THAT ---
                # Khong co buoc nay, vong doc se chay het video trong chung
                # co giay: nguoi xem thay video nhung khung nguoi cu la du
                # lieu cu (do buoc bo qua khung), va may het CPU.
                cho = 1.0 / max(1.0, fps) - (time.perf_counter() - t0_vong)
                if cho > 0:
                    self._tam_dung_xem.wait(min(cho, 1.0))
                else:
                    self._tam_dung_xem.wait(0)
                t0_vong = time.perf_counter()
        finally:
            cap.release()

    def _quet_su_kien(self, frame, xy, ids, do_tin, ten_theo_id: dict, zone_px,
                     cfg: AnalysisConfig, moc_thoi_gian: float, trong_vung: int,
                     dem_vao: int, dem_ra: int, trong_vung_truoc: dict,
                     vao_vung_luc: dict, da_bao_qua: set) -> None:
        """CHAY TREN THREAD NEN. Phat hien su kien -> day vao hang doi.

        Moi su kien = 1 the trong `PanelSuKien`, kem anh crop that cua nguoi do.
        Chi bat su kien that (VAO / RA vung, DUNG LAU qua nguong, VUOT nguong,
        QUAA VACH), khong bat trung lap: "vuot nguong" chi bao 1 lan cho moi
        id cho den khi nguoi do ra khoi vung.
        """
        if xy is None:
            return
        now = time.monotonic()
        quet = []          # (loai, ten, tin_do, gioi, hop_mat, box)
        for i, box in enumerate(xy):
            tid = ids[i]
            info = ten_theo_id.get(tid) or {}
            con_ten = (info.get("ten")
                       and now - info.get("luc", 0.0) <= TEN_GIU_NAM)
            ten = info["ten"] if con_ten else f"Người {tid + 1}"
            tin_do = (info.get("score", 0.0) if con_ten
                      else (do_tin[i] if i < len(do_tin) else 0.0))
            gioi = info.get("gioi", "") if con_ten else ""
            hop_mat = info.get("mat") if con_ten else None
            trong = _o_vung(box, zone_px, cfg.vung_nhay)
            truoc = trong_vung_truoc.get(tid, False)

            if zone_px is not None:
                if trong and not truoc:
                    quet.append(("vao_vung", ten, tin_do, gioi, hop_mat, box))
                elif truoc and not trong:
                    quet.append(("ra_vung", ten, tin_do, gioi, hop_mat, box))
                # Dung lau: trong vung > nguong canh_lau -> bao 1 lan.
                if trong and cfg.canh_lau:
                    vao_luc = vao_vung_luc.get(tid)
                    if vao_luc is not None and now - vao_luc >= cfg.canh_lau \
                            and tid not in da_bao_qua:
                        da_bao_qua.add(tid)
                        quet.append(("dung_lau", ten, tin_do, gioi, hop_mat,
                                     box))
            trong_vung_truoc[tid] = trong

            # VUOT nguong: bao 1 lan cho ca khung hinh (khong phai moi nguoi).
            if (cfg.vung_max and trong_vung > cfg.vung_max
                    and not da_bao_qua):
                quet.append(("vuot_nguong", ten, tin_do, gioi, hop_mat, box))

        # Chi giu toi da SO_SU_KIEN_1_VONG the moi de khong lam nghen hang doi.
        for loai, ten, tin_do, gioi, hop_mat, box in quet[:SO_SU_KIEN_1_VONG]:
            jpeg = _crop_jpeg(frame, [float(v) for v in box], hop_mat,
                              be=ANH_THE)
            self.queue.put(("su_kien", _su_kien(
                loai, ten, tin_do, gioi, jpeg, moc_thoi_gian)))
        if quet and zone_px is not None and cfg.vung_max \
                and trong_vung > cfg.vung_max:
            # sau khi bao vuot nguong, danh dau de khong bao lai moi vong
            da_bao_qua.update(ids)

    @staticmethod
    def _quet_ten_nguoi(engine, frame, xy, ids, ten_theo_id: dict) -> None:
        """Quét mặt trên TỪNG người, lưu tên/tuổi/giới vào `ten_theo_id`.

        CHAY TREN THREAD NEN - khong duoc dung widget Tkinter o day.
        Quet tren ANH CAT cua tung nguoi (nho hon nhieu lan so voi ca
        khung hinh) va chi chay moi MAT_MOI_N_LAN vong YOLO.

        KHONG xoa ten khi tam thoi khong thay mat - ten duoc giu them
        `TEN_GIU_NAM` giay (xem vong ve), nguoi quay di van thay ten.
        """
        for i, box in enumerate(xy):
            crop = GK.cat_anh_moi(frame, box, canh=8, co_ban=False)
            if crop is None or min(crop.shape[:2]) < 32:
                continue
            try:
                mats = engine.analyze(crop)
            except Exception:                               # noqa: BLE001
                continue
            if not mats:
                continue
            m = max(mats, key=lambda r: r.face_size)
            canh = float(crop.shape[0])          # crop luon VUONG
            cx = (float(box[0]) + float(box[2])) / 2.0
            cy = (float(box[1]) + float(box[3])) / 2.0
            ox, oy = cx - canh / 2.0, cy - canh / 2.0
            ten_theo_id[ids[i]] = {
                "ten": "Người lạ" if m.name == "Nguoi la" else m.name,
                "tuoi": int(m.age or 0),
                "gioi": {"Nam": "Nam", "Nu": "Nữ"}.get(m.sex, ""),
                "quen": bool(m.is_known),
                "score": float(m.score),
                "luc": time.monotonic(),
                "mat": (m.box[0] + ox, m.box[1] + oy,
                        m.box[2] + ox, m.box[3] + oy),
            }

    def _bat_xem_truc_tiep(self, cfg: AnalysisConfig) -> None:
        """Mo khung xem video (chi khi nguoi dung con bam 'Xem truc tiep')."""
        if self._xem_dang_chay or cfg.input == "0":
            if cfg.input == "0":
                self._ghi_log("> Xem trực tiếp không dùng được với webcam.")
            return
        self._xem_dang_chay = True
        self._ket_thuc_xem.clear()
        self._tam_dung_xem.clear()
        self._cap_nhat_nut_tam_dung_xem()
        self.o_hinh.configure(image=None, text="")
        self.lbl_khung_hinh.configure(text=os.path.basename(cfg.input))
        self._ghi_log("> Bật xem video trực tiếp (tốn thêm một ít máy).")
        threading.Thread(target=self._chay_xem_truc_tiep, args=(cfg,),
                         daemon=True).start()

    def _cap_nhat_nut_tam_dung_xem(self) -> None:
        """Nut 'Tạm dừng' CHỈ có ý nghĩa ở chế độ xem trực tiếp.

        Chế độ phân tích theo lô (batch): AN nút đi -> không bấm nhầm (bấm
        cũng không có tác dụng gì nhưng trông như có).
        """
        btn = getattr(self, "btn_tam_dung_xem", None)
        if btn is None:
            return
        if self._xem_dang_chay:
            btn.grid(row=0, column=2, padx=(0, 12), pady=(8, 0))
            btn.configure(state="normal", text=self.dich("Tạm dừng"))
        else:
            btn.grid_remove()

    def _dung_xem_truc_tiep(self) -> None:
        self._ket_thuc_xem.set()
        self._xem_dang_chay = False
        self._cap_nhat_nut_tam_dung_xem()

    def _ket_thuc_hinh(self) -> None:
        """Thread xem da dung.

        QUAN TRONG: neu phan tich CHINH còn chay thi GIỮ NGUYEN khung hinh
        cuối cùng (dong bang) - khong dua ve "Chua chay video", vi vay nguoi
        dung thay video bien mat dung luc phan tich chua xong.
        """
        self._xem_dang_chay = False
        self._cap_nhat_nut_tam_dung_xem()
        if self.busy or self._anh_dang_co:
            self._set_trang_thai("tam_dung" if self.busy else self._mau_trang_thai)
            self._ghi_log("> Xem video trực tiếp đã kết thúc "
                          "(giữ nguyên khung hình cuối).")
            return
        self._anh_tk = None
        self._anh_gu = None
        self._anh_dang_co = False
        if getattr(self, "o_hinh", None) is not None:
            self.o_hinh.configure(image=None, text=self.dich("Chưa chạy video"))

    def _doi_bat_xem_truc_tiep(self) -> None:
        """Bam checkbox 'Xem truc tiep'."""
        self._ghi_log("> Tắt xem video trực tiếp." if self.v_xem_video.get() != "1"
                      else "> Bật xem video trực tiếp (tốn thêm một ít máy).")
        self._xem_video_bat = self.v_xem_video.get() == "1"
        if self.v_xem_video.get() == "1" and self.v_xem_ket_qua.get() == "1":
            self._ghi_log(
                "Đang bật 'Xem trực tiếp' nên 'Xem khung hình kết quả' "
                "tạm không dùng (tránh 2 nguồn hình đè nhau)."
            )

    def _doi_bat_xem_ket_qua(self) -> None:
        """Bam checkbox 'Xem khung hinh ket qua'."""
        if self.v_xem_video.get() == "1":
            self._ghi_log(
                "Đang bật 'Xem trực tiếp' nên 'Xem khung hình kết quả' "
                "tạm không dùng (tránh 2 nguồn hình đè nhau)."
            )
            return
        self._ghi_log("> Bật xem khung hình kết quả." if self.v_xem_ket_qua.get() == "1"
                      else "> Tắt xem khung hình kết quả.")

    def _doi_tam_dung_xem(self) -> None:
        """Nut Tam dung / Tiep tuc: chi dung HINH, khong dung phan tich."""
        if self._tam_dung_xem.is_set():
            self._tam_dung_xem.clear()
            self.btn_tam_dung_xem.configure(text=self.dich("Tạm dừng"))
            self._ghi_log("Xem trực tiếp đã chạy tiếp")
        else:
            self._tam_dung_xem.set()
            self.btn_tam_dung_xem.configure(text=self.dich("Tiếp tục"))
            self._ghi_log("Xem trực tiếp đã tạm dừng")

    def _resize_anh(self, mang):
        """Thu nho khung hinh cho vua o hinh + doi BGR -> PIL RGB. RẺ.

        DÙNG `cv2.resize(INTER_AREA)` chứ không dùng `PIL.LANCZOS`:
        do o 1280x720 xuong ~889x500 thi PIL ton ~40ms, cv2 ton ~5ms
        (do duoc that tren may nay) - mat thoi gian cho mot viec RE.
        """
        from PIL import Image

        import cv2

        cao_h, rong_h = mang.shape[:2]
        rong_o = self.o_hinh.winfo_width()
        cao_o = self.o_hinh.winfo_height()
        if rong_o <= 1 or cao_o <= 1:
            rong_o, cao_o = XEM_VIDEO_BE_RONG, XEM_VIDEO_CAO
        # Giu nguyen ti le goc: anh vua khung cha theo chieu nao cung thu nho
        # theo chieu do, nen luon co nen den hai ben (khong bao gio keo meo).
        ty_le = min(rong_o / float(rong_h), cao_o / float(cao_h))
        rong_moi = max(1, min(rong_o, int(round(rong_h * ty_le))))
        cao_moi = max(1, min(cao_o, int(round(cao_h * ty_le))))
        if (rong_moi, cao_moi) != (rong_h, cao_h):
            mang = cv2.resize(mang, (rong_moi, cao_moi),
                              interpolation=cv2.INTER_AREA)
        return Image.fromarray(cv2.cvtColor(mang, cv2.COLOR_BGR2RGB))

    def _hien_khung_hinh(self, jpeg: bytes) -> None:
        """CHAY TREN LUONG UI: giai ma JPEG, khop o hinh va dat vao o hinh.

        Khi dang keo cua so: CHI giai ma va giu khung moi vao bo dem, KHONG
        resize + KHONG tao `PhotoImage`.viec dat la nang (~30ms) ma keo cua
        so thi lap lai lien tuc -> se lam cua so giat. Khung hinh cuoi cung
        se duoc ve lai dung kich thuoc moi ngay khi ngu keo
        (`_ve_lai_sau_khi_ngung_keo`).
        """
        if not (self._xem_dang_chay or self._hien_anh_batch):
            return          # xem da ket thuc - bo qua anh con ton tai
        import cv2

        mang = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if mang is None:
            return
        self._anh_gu = mang                       # giu de ve lai khi keo cua so
        if self._dang_keo:
            return          # dang keo -> giu khung, de viec dat cho luc sau

        from PIL import ImageTk

        self._kich_thuoc_hinh_cu = self.o_hinh.winfo_width(), self.o_hinh.winfo_height()
        self._anh_tk = ImageTk.PhotoImage(self._resize_anh(mang))
        self.o_hinh.configure(image=self._anh_tk, text="")
        self._anh_dang_co = True

    def _ve_lai_khung_hinh(self, ep: bool = False) -> None:
        """Ve lai khung hinh CUOI sau khi keo / doi kich thuoc cua so.

        KHONG dung `after()` rieng - chay ngay trong vong bom hang doi duy
        nhat de giu nguyen "1 vong after" (dieu kien de cua so khong giat).
        """
        if not self._anh_dang_co or self._anh_gu is None:
            return
        if self._dang_keo and not ep:
            return          # dang keo -> thoi, ve lai luc ngu keo
        from PIL import ImageTk

        rong_o = self.o_hinh.winfo_width()
        cao_o = self.o_hinh.winfo_height()
        if rong_o <= 1 or cao_o <= 1:
            return
        if (rong_o, cao_o) == self._kich_thuoc_hinh_cu:
            return          # khung cha chua doi - khong ve lai
        self._kich_thuoc_hinh_cu = (rong_o, cao_o)
        self._anh_tk = ImageTk.PhotoImage(self._resize_anh(self._anh_gu))
        self.o_hinh.configure(image=self._anh_tk)

    def _khi_keo_cua_so(self, _e=None) -> None:
        """CHAY TREN LUONG UI khi kich thuoc khung video doi. VIEC RE!

        Keo cua so lam kich thuoc doi lien tuc. Neu moi lan deu resize +
        tao anh (viec nang ~30ms) thi luong UI bi chan va cua so giat.
        Nen o day CHI ghi nhan kich thuoc moi va hen lai gio ve lai. Viec
        dat (resize + `PhotoImage`) chi chay 1 lan sau khi ngu keo.
        """
        # Canh be rong cot su kien TRUOC moi thu tich anh -> keo cua so hep thi
        # video phai giu >=70% ngay tu frame dau tien, khong doi de video co anh.
        self._canh_be_rong_cot_su_kien()

        if not self._anh_dang_co and self._anh_gu is None:
            return          # chua co khung hinh -> khong can ve lai gi
        w, h = self.khung_den.winfo_width(), self.khung_den.winfo_height()
        if (w, h) == self._kich_thuoc_cha_cu:
            return
        self._kich_thuoc_cha_cu = (w, h)
        self._dang_keo = True
        if self._job_ve_lai is not None:
            try:
                self.after_cancel(self._job_ve_lai)
            except Exception:                         # noqa: BLE001
                pass
        self._job_ve_lai = self.after(RESIZE_CHO_MS, self._ve_lai_sau_khi_ngung_keo)

    def _ve_lai_sau_khi_ngung_keo(self) -> None:
        """Ngu keo RESIZE_CHO_MS: ve lai 1 lan cho dung kich thuoc moi nhat."""
        self._job_ve_lai = None
        self._dang_keo = False
        if not self._anh_dang_co or self._anh_gu is None:
            return
        from PIL import ImageTk

        try:
            if self._xem_dang_chay and self._anh_gu is not None:
                # Video con chay: ve lai tu khung moi nhat trong bo dem.
                self._kich_thuoc_hinh_cu = (self.o_hinh.winfo_width(),
                                            self.o_hinh.winfo_height())
                self._anh_tk = ImageTk.PhotoImage(self._resize_anh(self._anh_gu))
                self.o_hinh.configure(image=self._anh_tk, text="")
            else:
                self._kich_thuoc_hinh_cu = (0, 0)     # buoc ve lai ve o hinh
                self._ve_lai_khung_hinh(ep=True)
        except Exception:                             # noqa: BLE001
            pass

    # ------------------------------------------- cua so con: thong tin model

    def _mo_thong_tin_model(self):
        if self.cua_so_model is not None and self.cua_so_model.winfo_exists():
            self.cua_so_model.lift()
            self.cua_so_model.focus_force()
            return
        win = ctk.CTkToplevel(self)
        win.title("Thông tin mô hình AI đang dùng")
        win.geometry("1000x620")
        win.minsize(780, 440)
        win.transient(self)
        win.configure(fg_color=MAU["nen"])
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=1)
        self.cua_so_model = win
        self._ghi_nhan_chu(win)          # nho chu Viet de doi ngon ngu duoc

        ctk.CTkLabel(
            win, text="CamAI đang chạy 4 mô hình AI sau đây:",
            font=self.font_tieu_de, text_color=MAU["chu"], anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=LE_NGOAI, pady=(12, 4))

        khung = ctk.CTkScrollableFrame(win, fg_color="transparent",
                                        corner_radius=BO_GOC_THE)
        khung.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))
        khung.grid_columnconfigure(0, weight=1)
        self._noi_dung_model(khung)
        self._ap_dung_theme(win)
        self._lam_moi_chu(win)        # neu mo trong luc dang o che do English

    def _noi_dung_model(self, parent):
        """Bau truc cua so con. Moi khoi deu boc try/except: loi doc thong tin
        KHONG duoc lam cua so khong mo duoc."""
        try:
            from model_info import (THONG_SO_KY_THUAT, bang_tt_tong_hop,
                                    lay_phien_ban)
        except Exception as exc:                      # noqa: BLE001
            self._dong_loi_model(parent, f"Không đọc được thông tin mô hình: {exc}")
            return
        try:
            bang = bang_tt_tong_hop()
            phien_ban = lay_phien_ban()
        except Exception as exc:                      # noqa: BLE001
            self._dong_loi_model(parent, f"Không đọc được thông tin mô hình: {exc}")
            return

        be = [190, 175, 175, 300]
        for idx, b in enumerate(be):
            parent.grid_columnconfigure(idx, weight=0, minsize=b)

        # --- tieu de bang ---
        for idx, ten in enumerate(["Tính năng", "Model kỹ thuật", "Thư viện",
                                   "Dung lượng đo trên máy · trạng thái"]):
            kh = ctk.CTkFrame(parent, fg_color=MAU["the_phu"],
                              corner_radius=BO_GOC_THE)
            kh.grid(row=0, column=idx, sticky="ew",
                    padx=(0 if idx == 0 else KHOANG_CACH, 0))
            kh.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(kh, text=ten, font=self.font_nho_bold, anchor="w",
                         text_color=MAU["chu"], justify="left",
                         wraplength=be[idx] - 16).grid(
                row=0, column=0, sticky="w", padx=10, pady=8)

        # --- 4 dong model ---
        for so, dong in enumerate(bang, start=1):
            mau = MAU["the"] if so % 2 else MAU["the_phu"]
            gia_tri = [
                dong["ten"],
                f'{dong["model_id"]}\n{dong["file"]}',
                dong["ten_thu_vien_day_du"],
                f'{dong["kich_thuoc_mb_thuc"]} MB\n{dong["trang_thai_tieng_viet"]}',
            ]
            mau_chu = MAU["nut"] if dong["co_file"] else MAU["loi"]
            for idx, gt in enumerate(gia_tri):
                kh = ctk.CTkFrame(parent, fg_color=mau, corner_radius=BO_GOC_THE,
                                  border_width=1, border_color=MAU["vien"])
                kh.grid(row=so, column=idx, sticky="ew",
                        padx=(0 if idx == 0 else KHOANG_CACH, 0),
                        pady=(KHOANG_CACH, 0))
                kh.grid_columnconfigure(0, weight=1)
                kw = {}
                if idx == 3:
                    kw["text_color"] = mau_chu
                else:
                    kw["text_color"] = MAU["chu_phu_the"]
                ctk.CTkLabel(kh, text=gt, font=self.font_nho, anchor="w",
                             justify="left", wraplength=be[idx] - 16, **kw).grid(
                    row=0, column=0, sticky="w", padx=10, pady=8)

        # --- vai tro tung mo hinh ---
        dong = self._dau_khoi(parent, "Vai trò từng mô hình", len(bang) + 1)
        for i, m in enumerate(bang):
            ctk.CTkLabel(
                parent, text=f'{m["ten"]}  ({m["model_id"]}):',
                font=self.font_nho_bold, text_color=MAU["chu"], anchor="w",
                justify="left",
            ).grid(row=dong, column=0, columnspan=4, sticky="w", padx=2, pady=(KHOANG_CACH, 0))
            dong += 1
            ctk.CTkLabel(
                parent, text=m["vai_tro"], font=self.font_nho,
                text_color=MAU["chu_phu"],
                anchor="w", justify="left", wraplength=900,
            ).grid(row=dong, column=0, columnspan=4, sticky="w", padx=2)
            dong += 1

        # --- thong so ky thuat ---
        dong = self._dau_khoi(parent, "Thông số kỹ thuật", dong)
        for gt, mau in [
            (f'Ngưỡng khớp mặt (ArcFace): {THONG_SO_KY_THUAT["nguong_khop_mat"]:.2f}'
             f'  —  {THONG_SO_KY_THUAT["gia_tri_nguong_khop_mat"]}', MAU["chu_phu"]),
            (f'Thư mục ảnh đã học: {THONG_SO_KY_THUAT["thu_muc_anh_da_hoc"]}'
             f'  ({THONG_SO_KY_THUAT["so_nguoi_da_hoc_mau"]} người trong mẫu)',
             MAU["chu_phu"]),
            (f'CẢNH BÁO: {THONG_SO_KY_THUAT["canh_bao_anh_mau"]}', MAU["loi"]),
        ]:
            ctk.CTkLabel(
                parent, text=gt, font=self.font_nho, text_color=mau, anchor="w",
                justify="left", wraplength=900,
            ).grid(row=dong, column=0, columnspan=4, sticky="w", padx=2, pady=2)
            dong += 1

        # --- phien ban + gpu ---
        dong = self._dau_khoi(parent, "Phiên bản và tốc độ máy", dong)
        for ten_goi in ("insightface", "ultralytics", "opencv-python",
                        "onnxruntime", "onnxruntime-gpu"):
            gt = f'{ten_goi:20s}: {phien_ban.get(ten_goi) or "chưa cài đặt"}'
            ctk.CTkLabel(parent, text=gt, font=self.font_code, anchor="w",
                         text_color=MAU["chu_phu"], justify="left").grid(
                row=dong, column=0, columnspan=4, sticky="w", padx=2, pady=1)
            dong += 1

        gpu = ("có — chạy bằng card màn hình NVIDIA (nhanh)"
               if phien_ban.get("cuda") else
               "không — chạy bằng CPU (chậm hơn nhưng vẫn chạy được)")
        ctk.CTkLabel(
            parent, text=f"Chạy trên GPU (CUDA): {gpu}", font=self.font_nho_bold,
            text_color=MAU["chu"], anchor="w", justify="left", wraplength=900,
        ).grid(row=dong, column=0, columnspan=4, sticky="w", padx=2, pady=(KHOANG_CACH, 0))
        dong += 1

        thieu = [m["ten"] for m in bang if not m["co_file"]]
        ctk.CTkLabel(
            parent,
            text=("CẢNH BÁO: thiếu file model: " + ", ".join(thieu)) if thieu else
                 "Đã kiểm tra trên đĩa: đủ cả 4/4 file model đều có sẵn.",
            font=self.font_nho_bold,
            text_color=MAU["loi"] if thieu else MAU["nut"],
            anchor="w", justify="left", wraplength=900,
        ).grid(row=dong, column=0, columnspan=4, sticky="w", padx=2)

    def _dau_khoi(self, parent, tieu_de: str, dong: int) -> int:
        ctk.CTkLabel(parent, text=tieu_de, font=self.font_group,
                     text_color=MAU["chu"], anchor="w").grid(
            row=dong, column=0, columnspan=4, sticky="w", padx=2,
            pady=(KHOANG_CACH * 2, 4))
        return dong + 1

    def _dong_loi_model(self, parent, noi_dung: str) -> None:
        ctk.CTkLabel(
            parent, text=noi_dung, font=self.font_nho, text_color=MAU["loi"],
            anchor="w", justify="left", wraplength=900,
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=2, pady=8)

    # -------------------------------------------------------------- dong

    def destroy(self):
        """Ghi de de dong cua so tooltip truoc khi huy app.

        Tooltip dung 1 cua so Toplevel rieng nen phai dong no lai, tranh
        de lai cua so mo coi khi app bi dong.
        """
        try:
            HuongDan.dong_tat_toan_bo()
        except Exception:                             # noqa: BLE001
            pass
        try:
            super().destroy()
        except Exception:                             # noqa: BLE001
            pass

    def _dong_cua_so(self):
        if self.busy:
            if not messagebox.askyesno(
                self.dich("Đang chạy"),
                self.dich("Đang xử lý video. Dừng và thoát luôn?"),
            ):
                return
            self.stop_flag.set()
            time.sleep(0.4)
        try:
            self.destroy()
        except Exception:                             # noqa: BLE001
            pass


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    CamAIGui().mainloop()


if __name__ == "__main__":
    main()