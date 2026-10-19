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
from duong_dan import APP_DIR

# Phan tach rieng: ve overlay + panel "Đối tượng phát hiện".
# gui.py KHÔNG vẽ bằng tay, chỉ gọi hàm ở đây (xem gui_khung.py đầu file).
import gui_khung as GK
from gui_khung import PanelSuKien, cat_anh_moi, ve_khung_hinh

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
LABEL_WIDTH = 118                  # be ngan can cua 1 hang cau hinh
FONT = "Segoe UI"
FONT_SO = "Consolas"

# --- BANG MAU CHUAN ------------------------------------------------------
# Phong cach: "dark tech + xanh trang thai".
# TAT CA ma mau cua gui.py deu lay tu dict nay - KHONG viet hex tay ben ngoai.
MAU = {
    "nen":            "#0F172A",   # nen chinh cua cua so
    "the":            "#1B2336",   # nen the / thanh tieu de nhom
    "the_phu":        "#272F42",   # nen phu (o nhap, hang nho)
    "chu":            "#F8FAFC",   # chu chinh
    "chu_phu":        "#94A3B8",   # chu phu tren nen chinh
    "chu_phu_the":    "#CBD5E1",   # chu phu tren nen the (de doc hon)
    "nut":            "#22C55E",   # nut chinh (CTA) + chu bao thanh cong
    "nut_hover":      "#16A34A",
    "nut_phu":        "#334155",   # nut phu
    "nut_phu_hover":  "#475569",
    "vien":           "#334155",   # vien 1px
    "loi":            "#EF4444",   # chu bao loi
    "focus":          "#FFFFFF",   # vien sang khi focus
}

# --- BO GOC + KHOANG CACH ------------------------------------------------
BO_GOC_THE = 10      # the / khung
BO_GOC_NUT = 8       # nut
BO_GOC_O_NHAP = 6    # o nhap
KHOANG_CACH = 8      # khoang cach toi thieu giua 2 phan tu
LE_NGOAI = 16        # le ngoai toi thieu cua cua so


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
RONG_COT_TRAI = 300                 # cot CAI DAT ben trai
RONG_COT_SU_KIEN = 320              # cot DANH SACH SU KIEN ben phai
# --- BE NGAT DONG TRONG COT CAI DAT ---
# Do that 2026-10-19 bang `_kk_agent_b_do_le.py`: khung noi dung ben trong
# CTkScrollableFrame chi rong 268px (300 - le ngoai 16 - thanh cuon ~16).
# Nhieu nhan cu dat `wraplength` 180-300px => Tk xuong dong o be 180-300px
# NHUNG widget chi rong 104-232px => CHU BI CAT NGANG GIUA DONG.
# Phai tinh wraplength tu be rong THAT con lai, khong dat so tu nghieng.
BE_NOI_DUNG_TRONG_NHOM = 268        # be ngang that cua khung 1 nhom
LE_MO_TA_NHOM = 36                  # le cua dong mo ta (dinh nghia o NhomTinhNang)
LE_GHI_Y = 10                       # le cua dong ghi chu nho
WRAP_MO_TA_NHOM = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - 8      # 224
WRAP_GHI_Y = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - LE_GHI_Y - 8  # 214
# Chu cua 1 checkbox trong khung cau hinh (tru 24px o check + 6px khe).
# Be trong cua khung cau hinh = 268 - 36 (le cua nhom) = 232px.
WRAP_CHECKBOX = BE_NOI_DUNG_TRONG_NHOM - LE_MO_TA_NHOM - 24 - 6 - 2  # 200
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
    "1 → 5,2 khung/giây · 2 → 7,6 · 5 → 12,5 · 10 → 23,4. "
    "Đếm người KHÔNG đổi, chỉ giảm số lần quét mặt. "
    "Máy chấm công (người đứng ở cửa) để 5 là đủ. "
    "Giám sát người đi qua nhanh thì để 1–2. "
    "Camera vắng người thì nhận được nhiều hơn các số trên.":
        "Measured on a busy video (10 people per frame): 1 → 5.2 fps · "
        "2 → 7.6 · 5 → 12.5 · 10 → 23.4. People counting does not change, "
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
    "Ví dụ: car, motorcycle, dog, cat — cách nhau bằng dấu phẩy. "
    "Để trống = nhóm lớp phổ biến. Gõ all = mọi lớp trừ người.":
        "Example: car, motorcycle, dog, cat — separated by commas. "
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
    "▶  BẮT ĐẦU": "▶  START",
    "●  DỪNG": "●  STOP",
    "▶": "▶",
    "▼": "▼",
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
    "Mở video kết quả": "Open result video",
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

# Mau nen cua HUYEN TRANG THAI - nhin la biet ngay, khong phai doc chu.
MAU_TRANG_THAI = {
    "chua_chay": "#334155",
    "chay": "#15803D",
    "khung_hinh_day_du": "#15803D",
    "khung_hinh": "#15803D",
    "tam_dung": "#B45309",
    "loi": "#B91C1C",
    "dung_giua": "#B45309",
    "xong": "#15803D",
}

# BIEU TU trang thai (ky tu HINH HOC, KHONG phai emoji - quy tac cua anh).
# Chi doc bang mat, khong can dich.
BIEU_TU_TRANG_THAI = {
    "chua_chay": "○",           # vong rong - chua chay
    "chay": "▶",                # tam giac - dang chay
    "khung_hinh_day_du": "▶",
    "khung_hinh": "▶",
    "tam_dung": "❙❙",          # hai vet dung - tam dung
    "loi": "✖",                 # dau X - loi
    "dung_giua": "■",           # vuong - dung giua chung
    "xong": "✔",                # dau tick - xong
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
    """Tooltip don gian: hien 1 doan chu khi rê chuột vao widget.

    Dung khi o nhap bi CAT CHU (vi du duong dan thu muc dai hon o). Chuot
    vao -> hien toan bo noi dung; ra -> an.

    Khong dung `tkinter` tooltip co san: CustomTkinter khong kem. Cua so
    tooltip dung `overrideredirect(True)` + `topmost` de khong chiem focus,
    nen bam chuot van bam duoc xuong o ben duoi.
    """

    def __init__(self, widget, noi_dung, font=None, do_rong_max: int = 460):
        self.widget = widget
        self.noi_dung = noi_dung
        self.font = font
        self.do_rong_max = do_rong_max
        self.cua_so = None
        # CTkEntry la 1 Frame chua tkinter.Entry ben trong (`_entry`).
        # Rê chuot vao vung TEXT thi chi `_entry` nhan <Enter>, nen bind
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

    def _noi_dung_hien_tai(self) -> str:
        """Lay noi dung hien thi. `noi_dung` co the la callable (doc o bien)."""
        n = self.noi_dung
        if callable(n):
            try:
                n = n()
            except Exception:
                return ""
        return str(n or "")

    def _vao(self, _event=None) -> None:
        self._ra()
        noi_dung = self._noi_dung_hien_tai()
        if not noi_dung:
            return
        try:
            self.cua_so = tk.Toplevel(self.widget)
            self.cua_so.overrideredirect(True)
            self.cua_so.attributes("-topmost", True)
            lbl = tk.Label(
                self.cua_so, text=noi_dung, justify="left",
                background="#1b1f27", foreground="#f2f4f8",
                font=self.font, padx=8, pady=5, wraplength=self.do_rong_max,
            )
            lbl.pack()
            self.cua_so.update_idletasks()
            # Toa do man hinh: `winfo_pointerx` cua TOPLEVEL = toa do man hinh.
            goc = self.dich.winfo_toplevel()
            x = goc.winfo_pointerx() + 14
            y = goc.winfo_pointery() + 20
            chieu_rong = self.cua_so.winfo_width()
            man_hinh = goc.winfo_screenwidth()
            if x + chieu_rong > man_hinh - 8:
                x = max(8, man_hinh - chieu_rong - 8)
            self.cua_so.geometry(f"+{x}+{y}")
        except Exception:
            self.cua_so = None

    def _ra(self, _event=None) -> None:
        if self.cua_so is not None:
            try:
                self.cua_so.destroy()
            except Exception:
                pass
            self.cua_so = None


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
    """MOT tinh nang trong menu: 1 dong tieu de + 1 khung cau hinh an/hi.

    Tieu de:  [▶/▼] [x] Ten tinh nang
    Khi mo:   them 1 dong ghi chu nho xam + 1 khung cau hinh ngay ben duoi.
    Dung grid() + grid_remove() de an hien (KHONG dung pack_forget).
    """

    def __init__(self, master, ten, var, lenh="", font=None, font_nho=None,
                 mac_dinh=(), co_checkbox=True) -> None:
        super().__init__(master, fg_color=MAU["nen"])
        self.var = var
        self.co_checkbox = co_checkbox
        self.dang_mo = False
        self._mac_dinh = list(mac_dinh)     # [(var, gia_tri_mac_dinh), ...]
        self.grid_columnconfigure(1, weight=1)

        # --- THANH TIEU DE: nen the, chu trang, bom rong day ---
        self.thanh = ctk.CTkFrame(
            self, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
            border_width=1, border_color=MAU["vien"],
        )
        self.thanh.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.thanh.grid_columnconfigure(1, weight=1)

        self.btn_mo = ctk.CTkButton(
            self.thanh, text="▶", width=30, height=28,
            fg_color="transparent", hover_color=MAU["nut_phu"],
            text_color=MAU["chu"], font=font, corner_radius=BO_GOC_NUT,
            command=self._doi_trang_thai,
        )
        # nut mui ten giu nguyen mau trong suot - khong cho vong mau chung doi.
        self.btn_mo._bo_toc_style = True
        self.btn_mo.grid(row=0, column=0, sticky="w", padx=(6, KHOANG_CACH),
                         pady=6)

        if co_checkbox:
            self.chk = ctk.CTkCheckBox(
                self.thanh, text=ten, variable=var, font=font,
                text_color=MAU["chu"], fg_color=MAU["nut"],
                hover_color=MAU["nut_hover"], border_color=MAU["nut_phu"],
                command=self._doi_checkbox, onvalue="1", offvalue="0"
            )
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
        """Mo / dong phan cau hinh. Moi loai goi Tkinter tu day vao hang doi UI."""
        self.dang_mo = mo
        if mo:
            self.lbl_lenh.grid()
            self.khung.grid()
            self.btn_mo.configure(text="▼")
        else:
            self.lbl_lenh.grid_remove()
            self.khung.grid_remove()
            self.btn_mo.configure(text="▶")

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

        # --- chu: Segoe UI cho chu, Consolas chi cho so / bang / nhat ky ---
        self.font_title = ctk.CTkFont(family=FONT, size=20, weight="bold")
        self.font_group = ctk.CTkFont(family=FONT, size=18, weight="bold")
        self.font_nhom = ctk.CTkFont(family=FONT, size=15)          # tieu de nhom
        self.font_tieu_de = ctk.CTkFont(family=FONT, size=14)
        self.font_nut = ctk.CTkFont(family=FONT, size=15)
        self.font_nho = ctk.CTkFont(family=FONT, size=12)
        self.font_nho_bold = ctk.CTkFont(family=FONT, size=12, weight="bold")
        self.font_nho_xam = ctk.CTkFont(family=FONT, size=12)
        self.font_code = ctk.CTkFont(family=FONT_SO, size=12)
        self.font_so = ctk.CTkFont(family=FONT_SO, size=13)        # so lieu
        self.font_stat = ctk.CTkFont(family=FONT_SO, size=20, weight="bold")
        # so lieu noi bat: TO de doc tu xa (yeu cau cua anh Tuấn)
        self.font_stat_lon = ctk.CTkFont(family=FONT, size=30, weight="bold")
        self.font_bam = ctk.CTkFont(family=FONT, size=15, weight="bold")

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
        self._mau_trang_thai = "chua_chay"
        self._du_lieu_trang_thai = {}

        self._khoi_tao_bien()
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

    def _canh_giua_trong_vung_lam_viec(self) -> None:
        """Dat cua so giua vung lam viec cua man hinh, tranh bi taskbar che.

        KHONG doi kich thuoc (noi dung can dung 1180x980), chi doi vi tri.
        Cho den khi cua so that su co dung kich thuoc da dinh nghia: luc
        moi mo, Tk tra kich thuoc mac dinh 200x200, dung no se tinh sai
        vi tri roi giu nguyen sai so do.
        """
        if getattr(self, "_da_canh_giua", False):
            return
        if (self.winfo_width() != KICH_THUOC_CUA_SO[0]
                or self.winfo_height() != KICH_THUOC_CUA_SO[1]):
            self.after(120, self._canh_giua_trong_vung_lam_viec)
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

        ctk.CTkLabel(khung, text="Video mẫu dùng thử", font=self.font_tieu_de,
                     text_color=MAU["chu"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(khung, text="Bấm vào thẻ để chọn video",
                     font=self.font_nho_xam, text_color=MAU["chu_phu"],
                     anchor="w").grid(row=0, column=1, sticky="w",
                                      padx=(10, 0), pady=(8, 2))
        self.btn_video_mau = ctk.CTkButton(
            khung, text="Ẩn", width=64, height=26, font=self.font_nho_xam,
            command=self._doi_hien_video_mau,
        )
        self.btn_video_mau.grid(row=0, column=2, sticky="e", padx=(0, 12),
                                pady=(8, 2))

        self.luu_video_mau = GK.LuoiVideoMau(
            khung, VIDEO_MAU, dich=self.dich, font_nho=self.font_nho_xam,
            font_nho_bold=self.font_nho_bold, command=self._dung_video_mau,
            so_cot=len(VIDEO_MAU),
        )
        self.luu_video_mau.grid(row=1, column=0, columnspan=3, sticky="ew",
                                padx=6, pady=(0, 8))
        self._video_mau_dang_hien = True
        self._dong_bo_the_video_mau()

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
        # Huyện trạng thái: MÀU + BIỂU TỰ HÌNH HỌC (không phải emoji) + CHỮ NGẮN.
        # CHỮ NGẮN Ở ĐÂY là chủ ý: chi tiết "2/250 · 1%" do nhãn TIẾN TRÌNH bên
        # cạnh lo. Trước đây huyện in luôn cả chuỗi dài đó nên hai nhãn bị đè
        # vào nhau ở góc trên phải khi cửa sổ nhỏ lại.
        ngan = self.dich(NHAN_TRANG_THAI_NGAN.get(
            self._mau_trang_thai, TRANG_THAI_TIEN_TRINH[self._mau_trang_thai]))
        if getattr(self, "huyen", None) is not None:
            self.huyen.configure(
                text=f"{BIEU_TU_TRANG_THAI.get(self._mau_trang_thai, '')}  "
                     + ngan,
                fg_color=MAU_TRANG_THAI.get(self._mau_trang_thai, MAU["nut_phu"]),
            )

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
        self.v_nhan_ten = ctk.StringVar(value="1")   # rut ten len khung video
        self._tam_dung_xem = threading.Event()   # set = dang tam dung hinh
        self._ket_thuc_xem = threading.Event()   # set = thread xem phai dung
        self._anh_tk = None                      # GIU lai tham chieu ImageTk
        self._anh_gu = None                      # khung goc cuoi (de ve lai)
        self._anh_dang_co = False
        self._xem_dang_chay = False
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

        ctk.CTkLabel(
            self, text="CamAI — Phân tích video giám sát",
            font=self.font_title, text_color=MAU["chu"], anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=LE_NGOAI,
               pady=(12, 6))

        # Nut doi ngon ngu Tieng Viet <-> English, goc tren ben phai.
        self.btn_ngon_ngu = ctk.CTkButton(
            self, text="English", width=150, height=34,
            font=self.font_nho, command=self._doi_ngon_ngu,
            fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
            corner_radius=BO_GOC_NUT,
        )
        self.btn_ngon_ngu._bo_toc_style = True
        self.btn_ngon_ngu._bo_ngon_ngu = True      # tu quan ly chu rieng
        # COT 1 (cot hien thi) chu KHONG dat nut nay o cot 2: cot 2 se no
        # ra het be rong nut (~166px) va lam cot video bi eo lai.
        self.btn_ngon_ngu.grid(row=0, column=1, sticky="e", padx=(0, LE_NGOAI),
                               pady=(12, 6))

        self._cot_cai_dat()
        self._cot_hien_thi()
        self._ap_dung_theme()          # mau chung cho toan bo widget da tao
        self._bang_video_mau()         # dai the video mau co anh xem truoc

        self.lbl_loi = ctk.CTkLabel(
            self, text="", font=self.font_nho, text_color=MAU["loi"],
            anchor="w", wraplength=520, justify="left",
        )
        self.lbl_loi.grid(row=3, column=0, columnspan=3, sticky="ew",
                          padx=LE_NGOAI, pady=(0, 8))

    # ------------------------------------------------ cot 0: CAI DAT

    def _cot_cai_dat(self):
        """Cot ben trai: chon video + 8 dong tinh nang + nut dieu khien."""
        f = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=MAU["nut_phu"],
            scrollbar_button_hover_color=MAU["nut_phu_hover"],
            label_text="",
        )
        f.grid(row=1, column=0, sticky="nsew", padx=(LE_NGOAI, 0), pady=(0, 4))
        f.grid_columnconfigure(0, weight=1)
        self._hang_video(f)
        self._khung_tinh_nang(f)
        self._hang_dieu_khien(f)

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

        # Huyen trang thai: 1 o mau + bieu tu HINH HOC, nhin la biet ngay.
        self.huyen = ctk.CTkLabel(
            f, text="", font=self.font_nho_bold, text_color="#FFFFFF",
            fg_color=MAU_TRANG_THAI["chua_chay"], corner_radius=BO_GOC_THE,
            width=be_huyen, height=34, anchor="center",
        )
        self.huyen._bo_toc_style = True
        self.huyen._bo_ngon_ngu = True      # huyen tu quan ly chu rieng
        self.huyen.grid(row=0, column=0, padx=(0, KHOANG_CACH))

        self.bar = ctk.CTkProgressBar(f, height=16)
        self.bar.grid(row=0, column=1, sticky="ew", padx=(0, KHOANG_CACH))
        self.bar.set(0)

        ctk.CTkLabel(f, textvariable=self.v_tien_trinh, font=self.font_nho,
                     text_color=MAU["chu_phu"], anchor="e", width=be_tien_trinh
                     ).grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------ mau sac

    def _ap_dung_theme(self, goc=None) -> None:
        """Gan bang mau chuan cho MOI widget da tao (nut, checkbox, o nhap).

        Chi doi MAU + bo goc, KHONG doi bo cuc (grid/padx/pady) va KHONG
        dung trong <Configure> nen khong ton hao gi khi rê chuot.
        Widget co `_bo_toc_style` (nut mui ten, 2 nut dieu khien) duoc bo qua.
        """
        goc = self if goc is None else goc

        def quet(wdg):
            if getattr(wdg, "_bo_toc_style", False):
                pass
            elif isinstance(wdg, ctk.CTkButton):
                wdg.configure(
                    fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
                    text_color=MAU["chu"], border_width=0,
                    corner_radius=BO_GOC_NUT, font=self.font_nut,
                )
                self._vong_focus(wdg, be_rong=0)
            elif isinstance(wdg, ctk.CTkCheckBox):
                wdg.configure(
                    fg_color=MAU["nut"], hover_color=MAU["nut_hover"],
                    border_color=MAU["nut_phu"], checkmark_color=MAU["chu"],
                    text_color=MAU["chu"],
                )
            elif isinstance(wdg, ctk.CTkEntry):
                wdg.configure(
                    fg_color=MAU["the_phu"], border_color=MAU["vien"],
                    border_width=1, text_color=MAU["chu"],
                    corner_radius=BO_GOC_O_NHAP,
                )
                self._vong_focus(wdg)
            elif isinstance(wdg, ctk.CTkOptionMenu):
                wdg.configure(
                    fg_color=MAU["the_phu"], button_color=MAU["nut_phu"],
                    button_hover_color=MAU["nut_phu_hover"],
                    text_color=MAU["chu"], corner_radius=BO_GOC_O_NHAP,
                )
            elif isinstance(wdg, ctk.CTkProgressBar):
                wdg.configure(fg_color=MAU["the_phu"], progress_color=MAU["nut"],
                              corner_radius=BO_GOC_NUT)
            elif isinstance(wdg, ctk.CTkTextbox):
                wdg.configure(fg_color=MAU["the"], border_width=1,
                              border_color=MAU["vien"], text_color=MAU["chu_phu"],
                              corner_radius=BO_GOC_THE)
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

    def _hang_video(self, parent):
        """2 khoi chon file (Video + Luu ket qua), xep theo COT HOP de vua
        khoi cau hinh ben trai khoang 470px.

        Video mau KHONG nam o day: no la MOT DAI THE ANH XEM TRUOC chay
        ngang o duoi cua so (`_bang_video_mau`) - 7 the xuong nhau moi
        kiem duoc 1 hang, con xep doc se day nut BẮT ĐẦU xuống duoi man hình.
        """
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        f.grid_columnconfigure(1, weight=1)

        # --- 1. VIDEO ---
        ctk.CTkLabel(f, text="Video", font=self.font_tieu_de,
                     text_color=MAU["chu"], anchor="w",
                     width=110).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ctk.CTkEntry(f, textvariable=self.v_video).grid(
            row=0, column=1, sticky="ew", pady=(0, 4))
        f_nut = ctk.CTkFrame(f, fg_color="transparent")
        f_nut.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, KHOANG_CACH))
        f_nut.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(f_nut, text="Chọn video…", width=130,
                      command=self._chon_video).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(f_nut, text="Mở thư mục clip", width=150,
                      fg_color=MAU["nut_phu"], hover_color=MAU["nut_phu_hover"],
                      command=self._mo_thu_muc_clip
                      ).grid(row=0, column=1, sticky="w", padx=(KHOANG_CACH, 0))

        # --- 2. LUU KET QUA ---
        ctk.CTkLabel(f, text="Lưu kết quả", font=self.font_tieu_de,
                     text_color=MAU["chu"], anchor="w",
                     width=110).grid(row=2, column=0, sticky="w", padx=(0, 10))
        ctk.CTkEntry(f, textvariable=self.v_output).grid(
            row=2, column=1, sticky="ew")
        f_out = ctk.CTkFrame(f, fg_color="transparent")
        f_out.grid(row=3, column=0, columnspan=2, sticky="ew")
        ctk.CTkButton(f_out, text="Chọn…", width=130,
                      command=self._chon_output).grid(row=0, column=0, sticky="w")
        # Ghi chu phai nam o HANG RIENG ben duoi nut: dat cung hang voi nut
        # 130px thi con it chua 130px chu -> bi cat ngang giua dong.
        ctk.CTkLabel(f_out,
                     text="Tự thêm đuôi: _ket_qua.mp4 và _bao_cao.csv",
                     font=self.font_nho_xam, text_color=MAU["chu_phu"],
                     anchor="w", wraplength=WRAP_GHI_Y, justify="left"
                     ).grid(row=1, column=0, columnspan=2, sticky="w",
                            pady=(2, 0))

    # ---------------------------------------------------- khung tinh nang

    def _khung_tinh_nang(self, parent):
        """10 dong tinh nang. MAC DINH THU GON HET, chi tinh nang anh bat
        moi mo. Moi nhom duoc gan vao self.nhom_* de tien kiem chung."""
        b = ctk.CTkFrame(parent, fg_color="transparent")
        b.grid(row=1, column=0, sticky="ew", pady=(KHOANG_CACH, 2))
        b.grid_columnconfigure(0, weight=1)

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

        self.nhom_bien_so = self._them_nhom(
            b, 6, "Đọc biển số xe", self.v_bien_so,
            "Đọc chữ trên biển số xe Việt Nam bằng RapidOCR — chạy 100% "
            "trên máy này, không gửi ảnh ra ngoài.",
            [(self.v_bien_so_vung, ""), (self.v_bien_so_giay, "30")])
        self._n_bien_so(self.nhom_bien_so.khung)

        self.nhom_tu_chup = self._them_nhom(
            b, 7, "Tự chụp ảnh khi có sự kiện", self.v_tu_chup,
            "Khi có người đông, vượt vùng hoặc thấy người quen thì chụp "
            "lại khung hình lưu thành ảnh. Mặc định tắt.",
            [(self.v_tu_chup_giay, "10")])
        self._n_tu_chup(self.nhom_tu_chup.khung)

        self.nhom_tach_o = self._them_nhom(
            b, 8, "Nhận người ở xa (chậm hơn)", self.v_tach_o,
            "Video quay xa, người nhỏ như hạt thì CamAI hay bỏ sót. Bật lên "
            "phần mềm sẽ chia khung hình thành các ô nhỏ để dò kỹ hơn. "
            "CHẬM HƠN KHOẢNG 5 LẦN nên xem chậm hơn — chỉ bật khi thật sự "
            "cần. Camera treo cao quay gần thì không cần.")
        self._n_tach_o(self.nhom_tach_o.khung)

        self.nhom_canh_bao = self._them_nhom(
            b, 9, "Cảnh báo (gửi tin ra ngoài)", self.v_canh_bao,
            "Khi có sự kiện thì báo ra ngoài máy này (chuông / hộp thoại / "
            "Telegram). Mặc định TẮT, và mặc định chỉ thử chứ không gửi thật.",
            [(self.v_cb_mo_phong, "1"), (self.v_cb_go, "60"),
             (self.v_cb_gioi_han, "5")])
        self._n_canh_bao(self.nhom_canh_bao.khung)

        self.nhom_model = self._them_nhom(
            b, 10, "Thông tin mô hình AI", ctk.StringVar(value="1"),
            "Xem phần mềm đang dùng model nào, nặng bao nhiêu, chạy trên GPU hay CPU.",
            co_checkbox=False)
        self._n_model(self.nhom_model.khung)

        self.nhom_thiet_bi = self._them_nhom(
            b, 11, "Máy này chạy bằng gì", ctk.StringVar(value="1"),
            "Máy có GPU thì CamAI tự chạy bằng card màn hình cho nhanh. "
            "Máy không có GPU thì chạy bằng CPU, vẫn chạy được nhưng chậm hơn. "
            "Không rành thì cứ để “Tự động”.",
            co_checkbox=False)
        self._n_thiet_bi(self.nhom_thiet_bi.khung)

    def _them_nhom(self, parent, dong, ten, var, lenh, mac_dinh=(),
                   co_checkbox=True) -> NhomTinhNang:
        nhom = NhomTinhNang(
            parent, ten, var, lenh=lenh, font=self.font_nhom,
            font_nho=self.font_nho_xam, mac_dinh=mac_dinh, co_checkbox=co_checkbox,
        )
        nhom.grid(row=dong, column=0, sticky="ew", pady=(0, KHOANG_CACH))
        return nhom

    def danh_sach_nhom(self) -> list[tuple[str, NhomTinhNang]]:
        """Danh sach (ten hien thi, nhom) theo dung thu tu tren man hinh.

        Dung cho _kiem_tra_gui.py va cho nguoi sau de doc lai file nay.
        """
        return [
            (getattr(self, ten).chk.cget("text"), getattr(self, ten))
            for ten in ("nhom_phat_hien", "nhom_mat", "nhom_dem", "nhom_vung",
                        "nhom_clip", "nhom_vat_the", "nhom_bien_so",
                        "nhom_tu_chup", "nhom_tach_o",
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

        `wraplength = do_rong` rat quan trong: CTkLabel tu do rong theo CHU,
        nen nhan dai ("Danh sách lớp cần nhận") se lon hon cot va TRAN QUA
        sang o dieu khien ben phai, khong con khoang hở nao. Bat wraplength
        thi chu xuong dong trong dung be 118px -> khong bao gio cham o nhap.
        """
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=self._dong_moi(parent), column=0, sticky="ew",
               pady=(KHOANG_CACH, 0))
        f.grid_columnconfigure(1, weight=1)
        if ten:
            ctk.CTkLabel(
                f, text=ten, anchor="w", width=do_rong, justify="left",
                font=self.font_nho, text_color=MAU["chu_phu_the"],
                wraplength=do_rong,
            ).grid(row=0, column=0, sticky="w", padx=(0, 12))
        return f

    def _hang_rong(self, parent, ten: str) -> ctk.CTkFrame:
        """Hang cau hinh DUNG rong: nhan o dong TREN, o dieu khien o dong DUOI.

        Dung khi 1 hang khong du chua nhan + o nhap + nut: be trong cua nhom
        chi 232px nen 3 thu tren cung 1 hang se lam o nhap bijep (chi con
        ~6px - khong go duoc). O day nhan doc 1 dong rieng, o nhap + nut
        duoc hieu rong cua ca khoi cau hinh.
        """
        ctk.CTkLabel(
            parent, text=ten, anchor="w", justify="left",
            font=self.font_nho, text_color=MAU["chu_phu_the"],
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
            text_color=MAU["chu_phu_the"],
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
            variable=self.v_model, width=170,
        ).grid(row=0, column=1, sticky="w")
        self._ghi_y(b, "yolo11n = nhẹ nhất, chạy nhanh nhất. Không rành thì để yolo11n.")

        f = self._hang(b, "Chạy bằng")
        ctk.CTkOptionMenu(
            f, values=list(GIA_TRI_CHE_THIET_BI),
            variable=self.v_thiet_bi, width=170,
        ).grid(row=0, column=1, sticky="w")
        self._ghi_y(b, "Đo thật trên máy này: card màn hình nhanh hơn CPU "
                       "khoảng 2 lần khi chỉ đếm người, khoảng 2,5 lần khi "
                       "bật nhận diện mặt. Máy không có card thì để "
                       "“Tự động” là chạy được.")

        self._don_vach(b)
        f = self._hang(b, "Hiển thị trên video")
        # 3 checkbox, MOI CAI 1 DONG RIENG: truoc day 3 cai cung 1 hang
        # thi cai 1 bi ep con 1px (khong bam duoc) va cai 2 bi cat chu.
        for ten, bien in (("Vẽ khung người", self.v_khung),
                          ("Vẽ nhãn tên", self.v_nhan),
                          ("Làm mờ nền, giữ rõ chỗ có người",
                           self.v_pixelate)):
            f2 = self._hang(b, "")
            self._checkbox(f2, ten, bien, font=self.font_nho,
                           onvalue="1", offvalue="0").grid(
                row=0, column=1, sticky="w")

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

        f = self._hang(b, "Bỏ qua mặt nhỏ hơn")
        ctk.CTkEntry(f, textvariable=self.v_min_face, width=90).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="px", font=self.font_nho_xam,
                     text_color=MAU["chu_phu_the"],
                     anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._ghi_y(b, "Mặt nhỏ hơn cỡ này thì bỏ qua, không hỏi ai. Để 0 = không bỏ.")

        f = self._hang(b, "Quét mặt mỗi")
        ctk.CTkEntry(f, textvariable=self.v_face_every, width=90).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="khung hình", font=self.font_nho_xam,
                     text_color=MAU["chu_phu_the"], anchor="w").grid(
            row=0, column=2, sticky="w", padx=(8, 0))
        self._ghi_y(b, "Đo thật trên video đông người (10 người/khung): "
                       "1 → 5,2 khung/giây · 2 → 7,6 · 5 → 12,5 · 10 → 23,4. "
                       "Đếm người KHÔNG đổi, chỉ giảm số lần quét mặt. "
                       "Máy chấm công (người đứng ở cửa) để 5 là đủ. "
                       "Giám sát người đi qua nhanh thì để 1–2. "
                       "Camera vắng người thì nhận được nhiều hơn các số trên.")

        f = self._hang_rong(b, "Thư mục ảnh đã học")
        ctk.CTkEntry(f, textvariable=self.v_faces_dir).grid(
            row=0, column=0, sticky="ew")
        ctk.CTkButton(f, text="Chọn…", width=70,
                      command=self._chon_faces_dir).grid(
            row=0, column=1, padx=(6, 0))
        self._ghi_y(b, "Cấu trúc: known_faces / <Tên> / *.jpg — mỗi người một thư mục con.")

        f = self._hang(b, "")
        self.btn_hoc_lai = ctk.CTkButton(
            f, text="Đọc lại danh sách người đã học", width=280,
            command=self._ve_lai_nguoi_hoc,
        )
        self.btn_hoc_lai.grid(row=0, column=1, sticky="w")

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
        ctk.CTkButton(f, text="Chọn…", width=70,
                      command=self._chon_vung_file).grid(
            row=0, column=1, padx=(6, 0))

        f = self._hang(b, "")
        ctk.CTkButton(f, text="Vẽ vùng trên video này", width=280,
                      command=self._mo_ve_vung).grid(row=0, column=1, sticky="w")
        self._ghi_y(b, "Mở cửa sổ riêng: xem video, kéo chuột khoanh vùng, "
                       "lưu lại thành file .txt.")

        f = self._hang(b, "")
        self._checkbox(f, "Chỉ cần một phần chân vào vùng là bị báo",
                       self.v_vung_nhay, font=self.font_nho,
                       onvalue="1", offvalue="0").grid(row=0, column=1, sticky="w")
        self._ghi_y(b, "Tắt = chặt: cả người phải nằm hẳn trong vùng mới báo. "
                       "Bật = nhạy: thân chạm vùng là báo ngay.")

        f = self._hang(b, "Cảnh báo khi vượt quá")
        ctk.CTkEntry(f, textvariable=self.v_vung_max, width=90).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="người", font=self.font_nho_xam,
                     text_color=MAU["chu_phu_the"],
                     anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._ghi_y(b, "Nhập 0 để tắt cảnh báo này.")

        f = self._hang(b, "Cảnh báo khi người đứng lâu")
        ctk.CTkEntry(f, textvariable=self.v_canh_lau, width=90).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="giây", font=self.font_nho_xam,
                     text_color=MAU["chu_phu_the"],
                     anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._ghi_y(b, "Nhập 0 để tắt cảnh báo này.")

    # -------------------------------------------------------- nhom 5: clip

    def _n_clip(self, b):
        f = self._hang(b, "Tổng thời lượng 1 clip")
        ctk.CTkEntry(f, textvariable=self.v_clip_giay, width=90).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="giây", font=self.font_nho_xam,
                     text_color=MAU["chu_phu_the"],
                     anchor="w").grid(row=0, column=2, sticky="w", padx=(8, 0))
        self._ghi_y(b, "Chia đôi: một nửa trước sự kiện, một nửa sau sự kiện.")

        f = self._hang(b, "")
        ctk.CTkCheckBox(
            f, text="Ghi clip cả khi không bật canh vùng",
            font=self.font_nho, variable=self.v_clip_tat_ca, onvalue="1", offvalue="0"
        ).grid(row=0, column=1, sticky="w")
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
        HuongDan(o_lop, "Để trống = dùng nhóm lớp mặc định. "
                       "Gõ all = mọi lớp trừ người.",
                 font=self.font_nho)
        self._ghi_y(b, "Ví dụ: car, motorcycle, dog, cat — cách nhau bằng dấu phẩy. "
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
        ctk.CTkButton(f, text="Chọn…", width=70,
                      command=self._chon_bien_so_dir).grid(
            row=0, column=1, padx=(6, 0))

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

        f = self._hang(b, "Nghỉ giữa 2 lần")
        ctk.CTkEntry(f, textvariable=self.v_bien_so_giay, width=90).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="giây", font=self.font_nho_xam,
                     text_color=MAU["chu_phu_the"], anchor="w").grid(
            row=0, column=2, sticky="w", padx=(8, 0))

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
        ctk.CTkButton(f, text="Chọn…", width=70,
                      command=self._chon_tu_chup_dir).grid(
            row=0, column=1, padx=(6, 0))

        f = self._hang(b, "Nghỉ giữa 2 lần")
        ctk.CTkEntry(f, textvariable=self.v_tu_chup_giay, width=90).grid(
            row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="giây", font=self.font_nho_xam,
                     text_color=MAU["chu_phu_the"], anchor="w").grid(
            row=0, column=2, sticky="w", padx=(8, 0))

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

        f = self._hang(b, "Gộp tin")
        ctk.CTkEntry(f, textvariable=self.v_cb_go, width=90
                      ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="giây", font=self.font_nho,
                     text_color=MAU["chu_phu_the"], anchor="w").grid(
            row=0, column=2, sticky="w", padx=(8, 0))

        f = self._hang(b, "Giới hạn")
        ctk.CTkEntry(f, textvariable=self.v_cb_gioi_han, width=90
                     ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(f, text="tin/phút", font=self.font_nho,
                     text_color=MAU["chu_phu_the"], anchor="w").grid(
            row=0, column=2, sticky="w", padx=(8, 0))

        f = self._hang(b, "")
        ctk.CTkButton(f, text="Thử gửi 1 cảnh báo", width=220,
                      command=self._thu_canh_bao).grid(row=0, column=1, sticky="w")

    # ------------------------------------------------------ nhom 11: model

    def _n_model(self, b):
        f = self._hang(b, "")
        ctk.CTkButton(f, text="Xem thông tin mô hình AI đang dùng", width=340,
                      command=self._mo_thong_tin_model).grid(
            row=0, column=1, sticky="w")

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

    def _hang_dieu_khien(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=2, column=0, sticky="ew", pady=(KHOANG_CACH, 6))
        f.grid_columnconfigure(0, weight=1)

        g = ctk.CTkFrame(f, fg_color="transparent")
        g.grid(row=0, column=0, sticky="ew")
        g.grid_columnconfigure(0, weight=1)
        # 2 nut dieu khien XEP DONG (cot cai dat da thu gon ~300px nen khong
        # the nao cung 1 hang) - moi nut gian het be rong cot nen chu bao gio
        # bi cat.
        self.btn_chay = ctk.CTkButton(
            g, text="▶  BẮT ĐẦU", command=self._bat_dau, height=42,
            font=self.font_bam, fg_color=MAU["nut"], hover_color=MAU["nut_hover"],
            corner_radius=BO_GOC_NUT,
        )
        self.btn_chay._bo_toc_style = True
        self.btn_chay.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.btn_dung = ctk.CTkButton(
            g, text="●  DỪNG", command=self._dung, height=42,
            font=self.font_bam, state="disabled", fg_color=MAU["nut_phu"],
            hover_color=MAU["nut_phu_hover"], corner_radius=BO_GOC_NUT,
        )
        self.btn_dung._bo_toc_style = True
        self.btn_dung.grid(row=1, column=0, sticky="ew")

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

        ctk.CTkLabel(khung, text="Xem video", font=self.font_nho_bold,
                     text_color=MAU["chu"], anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 0))
        self.lbl_khung_hinh = ctk.CTkLabel(
            khung, text="", font=self.font_nho_xam,
            text_color=MAU["chu_phu"], anchor="e")
        self.lbl_khung_hinh.grid(row=0, column=1, sticky="e", padx=12,
                                 pady=(10, 0))
        self.btn_tam_dung_xem = ctk.CTkButton(
            khung, text="Tạm dừng", width=120, height=28, state="disabled",
            command=self._doi_tam_dung_xem,
        )
        self.btn_tam_dung_xem.grid(row=0, column=2, padx=(0, 12), pady=(8, 0))

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
        hang_duoi.grid_columnconfigure(2, weight=1)
        self.chk_xem_video = ctk.CTkCheckBox(
            hang_duoi, text="Xem video khi chạy", variable=self.v_xem_video,
            font=self.font_nho_xam, command=self._doi_bat_xem_video, onvalue="1", offvalue="0"
        )
        self.chk_xem_video.grid(row=0, column=0, sticky="w")
        self.chk_nhan_ten = ctk.CTkCheckBox(
            hang_duoi, text="Nhận diện tên trên ảnh", variable=self.v_nhan_ten,
            font=self.font_nho_xam, onvalue="1", offvalue="0"
        )
        self.chk_nhan_ten.grid(row=0, column=1, sticky="w", padx=(18, 0))
        self.lbl_goi_y_xem = ctk.CTkLabel(
            hang_duoi,
            text="Tên lấy từ bộ nhận diện mặt đang chạy song song. "
                 "Tắt đi thì nhẹ máy hơn.",
            font=self.font_nho_xam, text_color=MAU["chu_phu"], anchor="e",
        )
        self.lbl_goi_y_xem.grid(row=0, column=2, sticky="e")

    def _bang_so_lieu_gon(self, parent):
        """Dải số liệu GỌN 1 hàng ngay dưới khung video.

        6 ô nằm ngang, chữ nhỏ - để video (và cột sự kiện) được nhiều chỗ.
        Không còn panel "đối tượng phát hiện": vai trò đó do DANH SÁCH SỰ
        KIỆN bên phải đảm nhiệm (có ảnh crop thật + thời gian + tên + tin cậy).
        """
        s = ctk.CTkFrame(parent, fg_color="transparent")
        s.grid(row=2, column=0, sticky="ew", pady=(0, KHOANG_CACH))
        for col in range(6):
            s.grid_columnconfigure(col, weight=1)
        o_so_lieu = [
            ("Người", self.v_so_nguoi, MAU["chu"]),
            ("Mặt", self.v_so_mat, MAU["chu"]),
            ("Người quen", self.v_so_quen, MAU["nut"]),
            ("Vào", self.v_so_vao, MAU["chu"]),
            ("Ra", self.v_so_ra, MAU["chu"]),
            ("Trong vùng", self.v_so_trong_vung, MAU["chu"]),
        ]
        for idx, (ten, var, mau) in enumerate(o_so_lieu):
            cell = ctk.CTkFrame(s, fg_color=MAU["the"], corner_radius=BO_GOC_THE,
                                border_width=1, border_color=MAU["vien"])
            cell.grid(row=0, column=idx, sticky="ew",
                      padx=(0 if idx == 0 else KHOANG_CACH, 0))
            ctk.CTkLabel(cell, textvariable=var, font=self.font_stat,
                         text_color=mau).pack(pady=(2, 0))
            ctk.CTkLabel(cell, text=ten, font=self.font_nho_xam,
                         text_color=MAU["chu_phu_the"]).pack(pady=(0, 2))

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
                     font=self.font_nho_bold, text_color=MAU["chu"],
                     anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(8, 0))
        self.btn_mo_ket_qua = ctk.CTkButton(
            f, text="Mở video kết quả", width=175, height=32,
            command=self._mo_video_ket_qua, state="disabled",
        )
        self.btn_mo_ket_qua.grid(row=0, column=1, padx=(0, KHOANG_CACH),
                                 pady=(6, 0))
        self.btn_bao_cao = ctk.CTkButton(
            f, text="Xem báo cáo", width=150, height=32,
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
        if os.path.exists(self.result.out_path):
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
                "Thiếu video", "Hãy chọn video trước khi vẽ vùng.")
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

    def _tao_cau_hinh(self) -> AnalysisConfig:
        face = self.v_face.get() == "1"
        zone = self.v_vung.get() == "1"
        source = self.v_video.get().strip()
        if not source:
            raise ValueError("Chưa chọn video.")
        if not os.path.isfile(source):
            raise ValueError(f"Không tìm thấy video:\n{source}")

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
        ten_goc = os.path.splitext(os.path.basename(source))[0] or "video"

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
        if self.v_xem_video.get() == "1":
            self._bat_xem_truc_tiep(cfg)
        threading.Thread(target=self._chay_pipeline, args=(cfg,), daemon=True).start()

    def _chay_pipeline(self, cfg: AnalysisConfig):
        """CHAY TREN THREAD NEN. Chi day vao hang doi, khong go widget."""
        old_stdout = sys.stdout
        sys.stdout = QueueWriter(self.queue)
        result = None
        try:
            result = run_analysis(
                cfg,
                progress_cb=self._tien_trinh_cb,
                log=lambda text: self.queue.put(("log", text)),
            )
        except CamAIError as exc:
            self.queue.put(("error", str(exc)))
        except Exception as exc:                      # noqa: BLE001 - GUI phai
            self.queue.put(                            # bat moi loi lai
                ("error", f"Lỗi không mong đợi: {exc.__class__.__name__}: {exc}")
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
        """
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
                    from PIL import ImageTk
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
            elif kind == "result":
                self.result = payload
                self._hien_ket_qua(payload)
            elif kind == "done":
                self._dung_xem_truc_tiep()
                self._che_do_busy(False)
                self._cap_nhat_trang_thai()
            elif kind == "xem_xong":
                self._ket_thuc_hinh()
        if dong_log:
            self._ghi_log_nhieu(dong_log)
        if khung_hinh is not None:
            self._hien_khung_hinh(khung_hinh)
        else:
            # Keo / doi kich thuoc cua so: ve lai khung CUOI cho vua khung cha
            # (khong them vong `after()` rieng).
            self._ve_lai_khung_hinh()
        self.after(PUMP_MS, self._hut_hang_doi)

    @staticmethod
    def _doi_neu_khac(var, gia_tri_moi) -> bool:
        """Chi goi .set() khi gia tri THAT SU doi - tranh ve lai widget
        10 lan/giay khi so khong doi (do la nguyen nhan giat nhe nhat)."""
        chuoi = str(gia_tri_moi)
        if var.get() == chuoi:
            return False
        var.set(chuoi)
        return True

    def _hien_tien_trinh(self, p: Progress):
        if p.total_frames:
            self._set_trang_thai(
                "khung_hinh_day_du", frame=p.frame_index, tong=p.total_frames,
                phan_tram=f"{p.percent:.0f}",
            )
        else:
            self._set_trang_thai("khung_hinh", frame=p.frame_index)
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
        self.bar.set(1.0)
        self._dung_xem_truc_tiep()      # ket thuc khung xem ngay khi xong
        self._set_trang_thai("dung_giua" if result.stopped else "xong")
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
            elif yeu_cau[0].lower() == "all":
                chon = [t for t in detector.names.values() if t != "person"]
            else:
                chon = yeu_cau
            # Lop go sai khong duoc lam VONG XEM CHET: bo qua + bao nhat ky,
            # dung lai chay tiep voi cac lop con lai. Truoc day `id_lop[t]`
            # nem KeyError lam ca khung xem truc tiep tat.
            sai = [t for t in chon if t not in id_lop]
            chon = [t for t in chon if t in id_lop]
            if sai:
                self.queue.put((
                    "log",
                    f"> [vật thể] Bỏ qua l không có: {', '.join(sai)}. "
                    f"Các lớp đang nhận: "
                    f"{', '.join(chon) if chon else 'không còn lớp nào'}",
                ))
            vat_the_ids = np.array(
                sorted({id_lop[t] for t in chon if id_lop[t] != PERSON_CLASS_ID}),
                dtype=int,
            )
            ten_lop = {cid: ten_vat_the(ten) for cid, ten in detector.names.items()}
            if vat_the_ids.size:
                self.queue.put((
                    "log",
                    f"> [vật thể] Đang nhận {len(vat_the_ids)} lớp: "
                    f"{', '.join(ten_lop[int(i)] for i in vat_the_ids)}",
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
                        ("A→B", f"{dem_vao + dem_ra}"),
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
        """Mo khung xem video (chi khi nguoi dung con bam 'Xem video khi chay')."""
        if self._xem_dang_chay or cfg.input == "0":
            if cfg.input == "0":
                self._ghi_log("> Xem trực tiếp không dùng được với webcam.")
            return
        self._xem_dang_chay = True
        self._ket_thuc_xem.clear()
        self._tam_dung_xem.clear()
        self.btn_tam_dung_xem.configure(state="normal",
                                         text=self.dich("Tạm dừng"))
        self.o_hinh.configure(image=None, text="")
        self.lbl_khung_hinh.configure(text=os.path.basename(cfg.input))
        self._ghi_log("> Bật xem video trực tiếp (tốn thêm một ít máy).")
        threading.Thread(target=self._chay_xem_truc_tiep, args=(cfg,),
                         daemon=True).start()

    def _dung_xem_truc_tiep(self) -> None:
        self._ket_thuc_xem.set()
        self._xem_dang_chay = False
        if getattr(self, "btn_tam_dung_xem", None) is not None:
            self.btn_tam_dung_xem.configure(state="disabled")

    def _ket_thuc_hinh(self) -> None:
        """Thread xem da dung.

        QUAN TRONG: neu phan tich CHINH còn chay thi GIỮ NGUYEN khung hinh
        cuối cùng (dong bang) - khong dua ve "Chua chay video", vi vay nguoi
        dung thay video bien mat dung luc phan tich chua xong.
        """
        self._xem_dang_chay = False
        self.btn_tam_dung_xem.configure(state="disabled")
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

    def _doi_bat_xem_video(self) -> None:
        """Bam checkbox 'Xem video khi chay' khi phan tich dang chay."""
        self._ghi_log("> Tắt xem video trực tiếp." if self.v_xem_video.get() != "1"
                      else "> Bật xem video trực tiếp (tốn thêm một ít máy).")
        self._xem_video_bat = self.v_xem_video.get() == "1"

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
        if not self._xem_dang_chay:
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