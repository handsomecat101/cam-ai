"""
CamAI - giao dien WEB chay hoan toan tren may nay (khong gui hinh/video len cloud).

Chay:
    .venv\\Scripts\\python.exe web_server.py
    .venv\\Scripts\\python.exe web_server.py --port 8787

Mo trinh duyet tren may nay: http://127.0.0.1:8787
Mo tren DIEN THOAI (cung Wi-Fi): http://<IP-may-tinh>:8787

Server lang nghe 0.0.0.0 (mac dinh) de dien thoai cung mang LAN truy cap
duoc. CHI phuc vu trong mang LAN noi bo - KHONG mo ra Internet.
Neu Windows Defender Firewall chan, hay cho phep Python (Private network).

UI: neu thu muc giao_dien_web/ co index.html -> GET / tra trang do.
Neu khong co -> van dung UI cu (tuong thich nguoc).

Mat khau dang nhap: PHẢI đặt biến môi trường CAMAI_PASSWORD trước khi chạy
(it nhất 8 ký tự). Không có mật khẩu mặc định trong mã nguồn; thiếu hoặc quá
ngắn thì chương trình in hướng dẫn tiếng Việt rồi thoát với mã lỗi 2.
Trong PowerShell:
    $env:CAMAI_PASSWORD = "mat-khau-cua-ban-it-nhat-8-ky-tu"
    .venv\\Scripts\\python.exe web_server.py

Nguyen tac giu nguyen:
    - Pipeline chay trong THREAD NEN, khong chay trong luong xu ly FastAPI.
    - /api/trang-thai chi doc bien trang thai duoi khoa rat ngan -> khong bi chan.
    - Chi 1 lan phan tich chay tai mot thoi diem.
    - KHONG sua file nao khac; chi import logic co san cua cam_ai_core.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import io
import os
import re
import secrets
import shutil
import socket
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime

# Console Windows cp1252: in tieng Viet duoc, loi se thay bang dau '?'.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # Python qua roi thi bo qua
    pass

APP_DIR = os.path.dirname(os.path.abspath(__file__))
THU_MUC_VIDEO_MAU = os.path.join(APP_DIR, "video_mau")
THU_MUC_TAM = os.path.join(APP_DIR, "_web_tmp")
THU_MUC_UPLOAD = os.path.join(THU_MUC_TAM, "tai_len")
THU_MUC_KET_QUA = os.path.join(THU_MUC_TAM, "ket_qua")
THU_MUC_KHUON_MAT = os.path.join(APP_DIR, "known_faces")
MODEL_YOLO = "yolo11n.pt"
FILE_VUNG_MAC_DINH = os.path.join(APP_DIR, "vung.txt")
# Thu muc giao dien web moi (do agent khac lam). Neu co index.html -> dung no.
THU_MUC_GIAO_DIEN_WEB = os.path.join(APP_DIR, "giao_dien_web")

# --- bao mat ---------------------------------------------------------------
# KHONG co mat khau mac dinh trong file nay: phai dat bien moi truong.
# Neu thieu hoac qua ngan, may chay se tu choi khoi dong (fail closed).
TEN_BIEN_MAT_KHAU = "CAMAI_PASSWORD"
DO_DAI_MAT_KHAU_TOI_THIEU = 8
SO_LAN_SAI_TOI_DA = 5
KHOA_SAI_GIO = 5 * 60            # 5 phut
HET_HAN_PHIEN_GIO = 12           # cookie song 12 gio
TEN_COOKIE = "camai_phien"

# --- gioi han ---------------------------------------------------------------
KICH_THUOC_TAI_TOI_DA = 300 * 1024 * 1024      # 300 MB
DUOI_VIDEO_CHAP_NHAN = (".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v")
SO_DONG_NHAT_TOI_DA = 400                       # gioi han so dong log giu lai
GIU_LAN_CHAY_BAO_NHIEU = 5                      # giu 5 lan chay gan nhat
SO_DONG_TOI_DA = 200                            # tra toi da 200 dong moi nhat (su_kien / nhat_ky)
KICH_THUOC_ANH_TOI_DA = 960                     # canh dai toi da cua anh nen (px)
CHAT_LUONG_ANH = 70                             # chat luong JPEG cua anh nen
KHOA_FRAME_MOI_NHAT = 0.2                       # 0.2s = 5 khung/s cho live view
DUOI_ANH_CHAP_NHAN = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
KICH_THUOC_ANH_NGUOI_QUEN_TOI_DA = 12 * 1024 * 1024      # 12 MB (moi anh nguoi quen)
SO_NGUOI_QUEN_TOI_DA = 200                              # so nguoi toi da trong known_faces

# --- MAU SAC: toan bo mau trong trang web deu lay tu dict nay ----------------
# Khong viet hex rai rac trong HTML: moi noi se the bang tieu de __TEN__.
MAU = {
    "nen": "#0F172A",
    "the": "#1B2336",
    "chu": "#F8FAFC",
    "chu_phu": "#94A3B8",
    "nut_chinh": "#22C55E",
    "nut_phu": "#334155",
    "loi": "#EF4444",
    "vien": "#2A3550",
    "canh": "#0B1220",
    "canh_chinh": "#14532D",
    "vien_chinh": "#166534",
    "vien_loi": "#7F1D1D",
}

VIDEO_MAU = [
    ("Video mẫu 1 — Người đi ngang từng người", "one-by-one-person-detection.mp4"),
    ("Video mẫu 2 — Nhóm người đông", "people-detection.mp4"),
    ("Video mẫu 3 — Có xe (kiểm tra không đếm nhầm xe là người)", "car-detection.mp4"),
    ("Video mẫu 4 — Công nhân trong khu vực làm việc", "worker-zone-detection.mp4"),
    ("Video mẫu 5 — Lối đi trong cửa hàng", "store-aisle-detection.mp4"),
    ("Video mẫu 6 — Phòng học", "classroom.mp4"),
    ("Video mẫu 7 — Người đi bộ (có khuôn mặt)", "face-demographics-walking.mp4"),
]


def _in(text: str) -> None:
    """In ra console. KHONG bao gio in mat khau."""
    print(text, flush=True)


# ------------------------------------------------------------------ trang thai
class _TrangThai:
    """Bien trang thai dung chung. Khoa CHI bao ve bien, khong giu khi tinh toan."""

    def __init__(self) -> None:
        # RLock: cho phep goi ham long nhau (them su kien trong khi dang giu khoa).
        self.khoa = threading.RLock()
        self.dang_chay = False
        self.yeu_cau_dung = False
        self.tieu_de = ""
        self.trang_thai = "Chưa chạy"          # chuoi tieng Viet cho nguoi dung
        self.phan_tram = 0.0
        self.khung_hinh = 0
        self.tong_khung_hinh = 0
        self.so_nguoi = 0
        self.so_mat = 0
        self.vao = 0
        self.ra = 0
        self.trong_vung = 0
        self.vi_pham = 0
        self.canh_lau = 0
        self.nhan_dien = ""
        self.nhat_dien: list[str] = []         # nguoi quen thay trong luc chay
        self.log: list[dict] = []
        self.ket_qua: dict | None = None
        self.thu_muc_ket_qua = ""
        self.bao_cao = "Chưa tạo báo cáo"
        self.dang_tao_bao_cao = False
        # --- v3.7 web: du lieu cho UI moi (may + dien thoai) ---
        self.su_kien: list[dict] = []          # su kien vao/ra/vi pham/canh lau
        self.xe = 0                            # so phuong tien phat hien
        self.fps_hien_tai = 0.0                # fps do duoc khi dang chay
        self.loai_nguon = ""                   # video | camera | anh | mang
        self.tep = ""                          # duong dan nguon vao
        self.loi = ""                          # loi cua lan chay gan nhat
        self.fps_thuoc = 0.0                   # fps that cua video nguon vao
        self.so_nguoi_cuoc = 0                 # dem vao/ra bang cach so sanh
        self.vi_pham_cuoc = 0
        self.canh_lau_cuoc = 0
        self.mau_fps: list[tuple[float, int]] = []   # (monotonic, frame) de do fps
        # --- v3.8 web: ket qua day du + danh sach (GET /api/ket-qua, ...) ---
        self.ket_qua_day_du: dict | None = None     # hop dong moi 17 truong
        self.anh_su_kien: list[dict] = []            # anh tu chup (duong dan + thoi gian)
        self.bien_so: list[dict] = []                # bien so doc duoc (text, tin_cay, frame)

    def dat(self, **nhat) -> None:
        with self.khoa:
            for k, v in nhat.items():
                setattr(self, k, v)

    def ghi_log(self, dong) -> None:
        muc = {
            "luc": datetime.now().strftime("%H:%M:%S"),
            "noi_dung": str(dong),
        }
        with self.khoa:
            self.log.append(muc)
            if len(self.log) > SO_DONG_NHAT_TOI_DA:
                del self.log[: len(self.log) - SO_DONG_NHAT_TOI_DA]

    def an(self) -> None:
        """Chuan hoa trang thai ve sau khi chay xong."""
        with self.khoa:
            self.dang_chay = False
            self.yeu_cau_dung = False
            if self.trang_thai == "Đang phân tích...":
                self.trang_thai = "Xong"

    def reset(self, tieu_de: str, thu_muc_kq: str = "") -> None:
        with self.khoa:
            self.dang_chay = True
            self.yeu_cau_dung = False
            self.tieu_de = tieu_de
            self.thu_muc_ket_qua = thu_muc_kq
            self.trang_thai = "Đang phân tích..."
            self.phan_tram = 0.0
            self.khung_hinh = 0
            self.tong_khung_hinh = 0
            self.so_nguoi = 0
            self.so_mat = 0
            self.vao = 0
            self.ra = 0
            self.trong_vung = 0
            self.vi_pham = 0
            self.canh_lau = 0
            self.nhan_dien = ""
            self.nhat_dien = []
            self.log = []
            self.ket_qua = None
            self.bao_cao = "Chưa tạo báo cáo"
            self.dang_tao_bao_cao = False
            # --- phan moi ---
            self.su_kien = []
            self.xe = 0
            self.fps_hien_tai = 0.0
            self.loi = ""
            self.so_nguoi_cuoc = 0
            self.vi_pham_cuoc = 0
            self.canh_lau_cuoc = 0
            self.mau_fps = []
            # --- phan moi ---
            self.ket_qua_day_du = None
            self.anh_su_kien = []
            self.bien_so = []

    def them_su_kien(self, loai: str, mo_ta: str, giay: float) -> None:
        """Ghi 1 su kien (vao/ra/vi pham/canh lau)."""
        muc = {
            "giay": round(float(giay), 2),
            "gio": datetime.now().strftime("%H:%M:%S"),
            "mo_ta": mo_ta,
            "loai": loai,
        }
        with self.khoa:
            self.su_kien.append(muc)
            if len(self.su_kien) > SO_DONG_TOI_DA * 5:
                del self.su_kien[: len(self.su_kien) - SO_DONG_TOI_DA * 5]

    def them_bien_so(self, muc: dict) -> None:
        """Ghi 1 bien so doc duoc (text, tin_cay, khung, frame)."""
        with self.khoa:
            self.bien_so.append(muc)
            if len(self.bien_so) > SO_DONG_TOI_DA:
                del self.bien_so[: len(self.bien_so) - SO_DONG_TOI_DA]

    def ban_trang_thai(self) -> dict:
        """Doc trang thai. Khoa giu RAT ngan, khong co tinh toan trong khoa."""
        with self.khoa:
            nhat_ky = [
                {
                    "gio": r.get("luc", ""),
                    "cap_do": _cap_do_log(r.get("noi_dung", "")),
                    "noi_dung": r.get("noi_dung", ""),
                }
                for r in self.log[-SO_DONG_TOI_DA:]
            ]
            return {
                # --- HOP DONG MOI (UI web moi + dien thoai) ---
                "busy": self.dang_chay,
                "xong": (not self.dang_chay) and (not self.loi),
                "loai_nguon": self.loai_nguon,
                "tep": self.tep,
                "dong": self.khung_hinh,
                "tong_khung": self.tong_khung_hinh,
                "fps_hien_tai": round(self.fps_hien_tai, 2),
                "nguoi": self.so_nguoi,
                "mat": self.so_mat,
                "nguoi_quen": len(self.nhat_dien),
                "vao": self.vao,
                "ra": self.ra,
                "trong_vung": self.trong_vung,
                "xe": self.xe,
                "su_kien": list(self.su_kien[-SO_DONG_TOI_DA:]),
                "nhat_ky": nhat_ky,
                "loi": self.loi,
                # --- HOP DONG CU (giao dien web cu - giu nguyen) ---
                "dang_chay": self.dang_chay,
                "trang_thai": self.trang_thai,
                "tieu_de": self.tieu_de,
                "phan_tram": round(self.phan_tram, 2),
                "khung_hinh": self.khung_hinh,
                "tong_khung_hinh": self.tong_khung_hinh,
                "so_nguoi": self.so_nguoi,
                "so_mat": self.so_mat,
                "vi_pham": self.vi_pham,
                "canh_lau": self.canh_lau,
                "nhan_dien": self.nhan_dien,
                "nhat_dien": list(self.nhat_dien),
                "log": list(self.log),
                "ket_qua": self.ket_qua,
                "bao_cao": self.bao_cao,
                "dang_tao_bao_cao": self.dang_tao_bao_cao,
            }


TT = _TrangThai()


def _cap_do_log(noi_dung: str) -> str:
    """Doan cap do cua 1 dong nhat ky: ERROR | WARN | INFO."""
    s = str(noi_dung or "")
    low = s.lower()
    if low.startswith("[loi]") or low.startswith("[lỗi]") or low.startswith("lỗi"):
        return "ERROR"
    if (
        low.startswith("[canh bao]")
        or low.startswith("[cảnh báo]")
        or low.startswith("[bao]")
        or low.startswith("[cảnh báo ")
    ):
        return "WARN"
    return "INFO"


# ------------------------------------------------------------------ anh nen
class _AnhNen:
    """Giu khung hinh JPEG moi nhat cho /api/anh-nen (dien thoai xem live view).

    Khung hinh do pipeline (cam_ai_core) gui ra qua frame_cb - da co overlay
    (khung nguoi, nhan ten, vung canh). Server KHONG giu file, chi giu bytes
    trong RAM nen moi nhat, roi resize ve <= 960px khi co request.
    """

    def __init__(self) -> None:
        self.khoa = threading.Lock()
        self.raw = b""            # JPEG nguyen ban vua pipeline
        self.ts = 0.0             # moc thoi gian cua khung hinh hien tai
        self.nho = b""            # ban da resize (cache)
        self.nho_ts = 0.0

    def dat(self, du_lieu: bytes) -> None:
        """Callback tu cam_ai_core (frame_cb): nhan bytes JPEG."""
        if not du_lieu:
            return
        with self.khoa:
            self.raw = du_lieu
            self.ts = time.time()

    def xoa(self) -> None:
        with self.khoa:
            self.raw = b""
            self.nho = b""
            self.ts = 0.0
            self.nho_ts = 0.0

    def lay(self) -> bytes:
        """Tra bytes JPEG da resize (toi da 960px, chat luong 70)."""
        with self.khoa:
            if not self.raw:
                return b""
            if self.nho and self.nho_ts == self.ts:
                return self.nho
            raw = self.raw
            ts = self.ts
        nho = _resize_jpeg(raw, KICH_THUOC_ANH_TOI_DA, CHAT_LUONG_ANH)
        with self.khoa:
            if self.ts == ts:            # khung hinh chua doi -> cache duoc
                self.nho = nho
                self.nho_ts = ts
        return nho


ANH_NEN = _AnhNen()
_ANH_PLACEHOLDER = b""


def _resize_jpeg(raw: bytes, max_px: int, chat_luong: int) -> bytes:
    """Giam kich thuoc anh JPEG (canh dai <= max_px) va nen lai chat luong."""
    try:
        import cv2
        import numpy as np

        anh = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if anh is None:
            return raw
        h, w = anh.shape[:2]
        canh = max(h, w)
        if canh > max_px:
            ti_le = max_px / float(canh)
            anh = cv2.resize(
                anh,
                (max(1, int(w * ti_le)), max(1, int(h * ti_le))),
                interpolation=cv2.INTER_AREA,
            )
        ok, buf = cv2.imencode(".jpg", anh, [int(cv2.IMWRITE_JPEG_QUALITY), chat_luong])
        if ok:
            return buf.tobytes()
    except Exception:                    # noqa: BLE001
        pass
    return raw


def _anh_placeholder() -> bytes:
    """Anh JPEG nho, tra khi chua co khung hinh nao (van hien thi duoc tren DT)."""
    global _ANH_PLACEHOLDER
    if _ANH_PLACEHOLDER:
        return _ANH_PLACEHOLDER
    du_lieu = b""
    try:
        from PIL import Image, ImageDraw

        anh = Image.new("RGB", (640, 360), (24, 28, 38))
        ve = ImageDraw.Draw(anh)
        ve.rectangle([0, 0, 639, 359], outline=(58, 68, 92), width=2)
        # Font mac dinh cua Pillow khong ve duoc dau tieng Viet -> chu khong dau.
        ve.text((248, 150), "CamAI", fill=(226, 232, 240))
        ve.text((212, 182), "Chua co khung hinh", fill=(138, 148, 168))
        buf = io.BytesIO()
        anh.save(buf, format="JPEG", quality=CHAT_LUONG_ANH)
        du_lieu = buf.getvalue()
    except Exception:                    # noqa: BLE001
        du_lieu = b""
    if du_lieu:
        _ANH_PLACEHOLDER = du_lieu
    return du_lieu


class _VideoCuoi:
    """Giu handle VideoCapture cua video ket qua de lay khung hinh gan nhat.

    Dung khi server vua khoi dong (chua co khung hinh live) hoac khi video ket
    qua da xong. Seek ve gan cuoi roi doc 1 khung hinh.
    """

    def __init__(self) -> None:
        self.khoa = threading.Lock()
        self.cap = None
        self.duong_dan = ""

    def dong(self) -> None:
        with self.khoa:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:            # noqa: BLE001
                    pass
            self.cap = None
            self.duong_dan = ""

    def lay(self, duong_dan: str) -> bytes:
        if not duong_dan or not os.path.isfile(duong_dan):
            return b""
        try:
            import cv2
        except Exception:                    # noqa: BLE001
            return b""
        with self.khoa:
            try:
                if self.cap is None or self.duong_dan != duong_dan:
                    if self.cap is not None:
                        try:
                            self.cap.release()
                        except Exception:    # noqa: BLE001
                            pass
                        self.cap = None
                    cap = cv2.VideoCapture(duong_dan)
                    if not cap.isOpened():
                        cap.release()
                        self.duong_dan = ""
                        return b""
                    self.cap = cap
                    self.duong_dan = duong_dan
                cap = self.cap
                tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                if tong > 1:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, tong - 1))
                ok, anh = cap.read()
                if not ok or anh is None:
                    return b""
                h, w = anh.shape[:2]
                canh = max(h, w)
                if canh > KICH_THUOC_ANH_TOI_DA:
                    ti_le = KICH_THUOC_ANH_TOI_DA / float(canh)
                    anh = cv2.resize(
                        anh,
                        (max(1, int(w * ti_le)), max(1, int(h * ti_le))),
                        interpolation=cv2.INTER_AREA,
                    )
                ok2, buf = cv2.imencode(
                    ".jpg", anh, [int(cv2.IMWRITE_JPEG_QUALITY), CHAT_LUONG_ANH]
                )
                if not ok2:
                    return b""
                return buf.tobytes()
            except Exception:                # noqa: BLE001
                return b""


VIDEO_CUOI = _VideoCuoi()


# ------------------------------------------------------------ phien dang nhap
class _Phien:
    def __init__(self) -> None:
        self.khoa = threading.Lock()
        # Mat khau chi nam trong bien moi truong, khong co gia tri mac dinh.
        # _kiem_tra_mat_khau() chay truoc khi phuc vu va tu choi khoi dong
        # neu bien nay rong hoac qua ngan.
        self.mat_khau = os.environ.get(TEN_BIEN_MAT_KHAU, "").strip()
        self.token: dict[str, float] = {}       # token -> het han (timestamp)
        self.sai: dict[str, dict] = {}           # ip -> {"sai": n, "khoa_den": ts}

    def co_hieu_luc(self, token) -> bool:
        if not token:
            return False
        with self.khoa:
            het = self.token.get(token)
            if het is None:
                return False
            if het < time.time():
                self.token.pop(token, None)
                return False
            return True

    def cap_phien(self) -> tuple[str, int]:
        token = secrets.token_urlsafe(32)
        giay = HET_HAN_PHIEN_GIO * 3600
        now = time.time()
        with self.khoa:
            self.token[token] = now + giay
            for t, h in list(self.token.items()):     # don rac
                if h < now:
                    self.token.pop(t, None)
        return token, giay

    def huy_phien(self, token) -> None:
        with self.khoa:
            if token:
                self.token.pop(token, None)

    def con_bi_khoa(self, ip: str) -> int:
        """Tra ve so giay con lai bi khoa (0 = khong bi khoa)."""
        with self.khoa:
            het = self.sai.get(ip, {}).get("khoa_den", 0)
        return max(0, int(het - time.time())) if het > time.time() else 0

    def ghi_sai(self, ip: str) -> tuple[int, int]:
        """Ghi 1 lan sai. Tra (so_lan_sai, so_giay_bi_khoa)."""
        with self.khoa:
            rec = self.sai.setdefault(ip, {"sai": 0, "khoa_den": 0})
            rec["sai"] += 1
            if rec["sai"] >= SO_LAN_SAI_TOI_DA:
                rec["sai"] = 0
                rec["khoa_den"] = time.time() + KHOA_SAI_GIO
                return SO_LAN_SAI_TOI_DA, KHOA_SAI_GIO
        return 0, 0

    def xoa_sai(self, ip: str) -> None:
        with self.khoa:
            self.sai.pop(ip, None)

    def khop_mat_khau(self, nhap) -> bool:
        """So sanh bang secrets.compare_dinh, khong so sanh truc tiep trong ma.

        str co dau (tieng Viet) se lam compare_dinh nem TypeError, nen
        chuyen ca hai ve byte UTF-8 truoc khi so sanh.
        """
        return secrets.compare_digest(
            str(nhap).encode("utf-8"), self.mat_khau.encode("utf-8")
        )


PHIEN = _Phien()


# ------------------------------------------------------------------ tien trinh
def _giay_cua_khung_hinh(frame_index: int) -> float:
    """Giay trong video cua khung hinh hien tai (dung fps that cua video nguon vao)."""
    fps = TT.fps_thuoc or TT.fps_hien_tai or 0.0
    if fps <= 0:
        return float(frame_index)
    return float(frame_index) / fps


def _tien_trinh(p) -> bool:
    """Callback tu cam_ai_core: cap nhat trang thai. Tra False = DUNG ngay."""
    with TT.khoa:
        TT.khung_hinh = p.frame_index
        TT.tong_khung_hinh = p.total_frames
        TT.phan_tram = p.percent
        TT.so_nguoi = p.so_nguoi
        TT.so_mat = p.so_mat
        TT.vao = p.vao
        TT.ra = p.ra
        TT.trong_vung = p.trong_vung
        TT.vi_pham = p.vi_pham
        TT.canh_lau = p.canh_lau
        TT.nhan_dien = p.nhan_dien
        for ten in str(p.nhan_dien).split("|"):
            ten = ten.strip()
            if ten and ten not in TT.nhat_dien:
                TT.nhat_dien.append(ten)

        # --- do fps thuc te (trong 2 giay gan nhat) ---
        luc = time.monotonic()
        TT.mau_fps.append((luc, p.frame_index))
        while TT.mau_fps and luc - TT.mau_fps[0][0] > 2.0:
            TT.mau_fps.pop(0)
        if len(TT.mau_fps) >= 2:
            t0, f0 = TT.mau_fps[0]
            t1, f1 = TT.mau_fps[-1]
            if t1 > t0:
                TT.fps_hien_tai = (f1 - f0) / (t1 - t0)

        # --- su kien: vao / ra / vi pham / canh lau (so sanh voi khung truoc) ---
        giay = _giay_cua_khung_hinh(p.frame_index)
        if p.so_nguoi > TT.so_nguoi_cuoc:
            for _ in range(min(20, p.so_nguoi - TT.so_nguoi_cuoc)):
                TT.them_su_kien("vao", "Người vào khu vực", giay)
        elif p.so_nguoi < TT.so_nguoi_cuoc:
            for _ in range(min(20, TT.so_nguoi_cuoc - p.so_nguoi)):
                TT.them_su_kien("ra", "Người ra khu vực", giay)
        if p.vi_pham > 0 and TT.vi_pham_cuoc <= 0:
            TT.them_su_kien("vi_pham", "Cảnh báo vượt quá số người cho phép", giay)
        if p.canh_lau > 0 and TT.canh_lau_cuoc <= 0:
            TT.them_su_kien("canh_lau", "Phát hiện người đứng lâu", giay)
        TT.so_nguoi_cuoc = p.so_nguoi
        TT.vi_pham_cuoc = p.vi_pham
        TT.canh_lau_cuoc = p.canh_lau
        dung = TT.yeu_cau_dung
    return not dung


# ------------------------------------------------------------------ chay phan tich
def _ten_tach_duong(duong_dan: str) -> str:
    ten = os.path.splitext(os.path.basename(duong_dan))[0]
    return "".join(c if c.isalnum() else "_" for c in ten)[:40] or "video"


DUOI_ANH = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")


def _loai_nguon_cua(duong_dan: str) -> str:
    """Loai nguon vao: video | camera | anh | mang (mirror cam_ai_core.loai_nguon).

    Ban sao rieng de /api/trang-thai khong phai import cam_ai_core (nang, cham).
    """
    goc = str(duong_dan or "").strip()
    if not goc:
        return "video"
    if goc == "0":
        return "camera"
    low = goc.lower()
    if low.startswith(("rtsp://", "rtmp://", "http://", "https://")):
        return "mang"
    if os.path.splitext(low)[1] in DUOI_ANH:
        return "anh"
    return "video"


def _fps_cua_video(duong_dan: str) -> float:
    """Doc fps that cua video nguon vao (dung de tinh giay cua su kien)."""
    try:
        import cv2

        cap = cv2.VideoCapture(duong_dan)
        if not cap.isOpened():
            cap.release()
            return 0.0
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        cap.release()
        return fps if fps > 0 else 0.0
    except Exception:                        # noqa: BLE001
        return 0.0


def _don_dep(giu=GIU_LAN_CHAY_BAO_NHIEU) -> None:
    """Giu vai lan chay gan nhat, xoa phan con lai de khong day dia."""
    try:
        if not os.path.isdir(THU_MUC_KET_QUA):
            return
        cac = [
            os.path.join(THU_MUC_KET_QUA, ten)
            for ten in os.listdir(THU_MUC_KET_QUA)
            if os.path.isdir(os.path.join(THU_MUC_KET_QUA, ten))
        ]
        cac.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for cu in cac[giu:]:
            shutil.rmtree(cu, ignore_errors=True)
    except Exception:
        pass


def _xoa_tam(duong_dan) -> None:
    """Chi xoa tep tam do CAMAI tu tai len. KHONG bao gio xoa video mau/goc."""
    try:
        if not duong_dan:
            return
        goc = os.path.abspath(str(duong_dan))
        if goc.startswith(os.path.abspath(THU_MUC_UPLOAD) + os.sep) and os.path.isfile(goc):
            os.remove(goc)
            with _KHOA_UPLOAD:
                _TEP_DA_UPLOAD.discard(goc)
    except Exception:
        pass


def _don_tap_tam(gio_tuoi: int = 6) -> None:
    """Tep tai len ma user tai len roi bo qua se ton tai. Quet khi bat dau server."""
    try:
        if not os.path.isdir(THU_MUC_UPLOAD):
            return
        han = time.time() - gio_tuoi * 3600
        for ten in os.listdir(THU_MUC_UPLOAD):
            duong_dan = os.path.join(THU_MUC_UPLOAD, ten)
            if os.path.isfile(duong_dan) and os.path.getmtime(duong_dan) < han:
                _xoa_tam(duong_dan)
    except Exception:
        pass


# ------------------------------------------------------------------ cau hinh API
# MO TA TOAN BO THAM SO CUA `cam_ai_core.AnalysisConfig` CHO UI WEB.
#
# NGUON SU THAT:
#   - Ten field + gia tri mac dinh: doc tu `AnalysisConfig.__dataclass_fields__`
#     (neu cam_ai_core da import roi) hooc doc truc tiep file cam_ai_core.py
#     bang AST (KHONG import -> khong treo ~9 giay vi torch).
#   - Nhan tieng Viet + khoang gioi han + nhom: bang tra cuu ben duoi.
#
# THEM FIELD MOI vao cam_ai_core.py -> GET /api/cau-hinh tu co field do,
# chi can them 1 dong o bang `_KHOA_CAU_HINH` (khong doi code Python khac).
#
# Moi truong trong bang: "nhan" (nhan tieng Viet), "mo_ta", "kieu"
# (bool | so | chuoi | duong_dan), va voi kieu="so" them
# "toi_thieu", "toi_da", "buoc".
_KHOA_CAU_HINH: dict[str, dict] = {
    "input": {
        "nhan": "Video cần phân tích",
        "mo_ta": "Đường dẫn video hoặc ảnh trên máy này.",
        "kieu": "duong_dan",
    },
    "output": {
        "nhan": "Thư mục lưu kết quả",
        "mo_ta": "Nơi lưu video kết quả và báo cáo. Phần mềm tự thêm đuôi "
                 "_ket_qua.mp4 và _bao_cao.csv.",
        "kieu": "duong_dan",
    },
    "no_face": {
        "nhan": "Nhận diện khuôn mặt",
        "mo_ta": "Bật = biết người đó là ai, ước lượng tuổi và giới tính. "
                 "Tắt = chỉ đếm người (nhanh hơn khoảng 2-2,5 lần).",
        "kieu": "bool",
    },
    "faces_dir": {
        "nhan": "Thư mục ảnh đã học",
        "mo_ta": "Cấu trúc: known_faces / <Tên> / *.jpg — mỗi người một thư mục con.",
        "kieu": "duong_dan",
    },
    "model": {
        "nhan": "Mô hình nhận diện",
        "mo_ta": "yolo11n.pt nhẹ và nhanh nhất, yolo11s/m/l chính xác hơn nhưng "
                 "nặng hơn. Không rành thì để yolo11n.pt.",
        "kieu": "chuoi",
    },
    "thiet_bi": {
        "nhan": "Chạy bằng",
        "mo_ta": "auto = tự chọn (có GPU thì GPU, không thì CPU); cuda = ép GPU; "
                 "cpu = ép CPU.",
        "kieu": "chuoi",
    },
    "conf": {
        "nhan": "Ngưỡng tin cậy",
        "mo_ta": "0,25 = mặc định. Hạ xuống sẽ bắt được cả người ở xa, "
                 "nhưng nhiều khi bắt nhầm.",
        "kieu": "so",
        "toi_thieu": 0.05,
        "toi_da": 1.0,
        "buoc": 0.05,
    },
    "face_every": {
        "nhan": "Quét mặt mỗi (khung hình)",
        "mo_ta": "Quét mặt sau mỗi N khung hình. Số càng lớn càng nhanh nhưng "
                 "dễ bỏ sót người quen đi nhanh.",
        "kieu": "so",
        "toi_thieu": 1,
        "toi_da": 100,
        "buoc": 1,
    },
    "face_threshold": {
        "nhan": "Ngưỡng giống mặt",
        "mo_ta": "Cao hơn = dễ nhận nhầm người khác. Thấp hơn = dễ không nhận ra "
                 "người quen. Mặc định 0,40.",
        "kieu": "so",
        "toi_thieu": 0.1,
        "toi_da": 0.9,
        "buoc": 0.05,
    },
    "min_face": {
        "nhan": "Bỏ qua mặt nhỏ hơn (px)",
        "mo_ta": "Mặt nhỏ hơn cỡ này thì bỏ qua, không hỏi ai. Để 0 = không bỏ.",
        "kieu": "so",
        "toi_thieu": 0,
        "toi_da": 2000,
        "buoc": 1,
    },
    "pixelate": {
        "nhan": "Làm mờ nền, giữ rõ chỗ có người",
        "mo_ta": "Làm mờ nền để dễ nhìn thấy người.",
        "kieu": "bool",
    },
    "vung": {
        "nhan": "File vùng (.txt)",
        "mo_ta": "Khoanh vùng trong khung hình rồi cảnh báo khi có người vào "
                 "vùng đó. Để trống = không canh vùng.",
        "kieu": "duong_dan",
    },
    "vung_nhay": {
        "nhan": "Chỉ cần một phần chân vào vùng là bị báo",
        "mo_ta": "Tắt = chặt: cả người phải nằm hẳn trong vùng mới báo. "
                 "Bật = nhạy: thân chạm vùng là báo ngay.",
        "kieu": "bool",
    },
    "vung_max": {
        "nhan": "Cảnh báo khi vượt quá (người)",
        "mo_ta": "Số người tối đa trong vùng. Nhập 0 để tắt cảnh báo này.",
        "kieu": "so",
        "toi_thieu": 0,
        "toi_da": 10000,
        "buoc": 1,
    },
    "canh_lau": {
        "nhan": "Cảnh báo khi người đứng lâu (giây)",
        "mo_ta": "Đứng lâu hơn số giây này thì báo. Nhập 0 để tắt.",
        "kieu": "so",
        "toi_thieu": 0.0,
        "toi_da": 3600.0,
        "buoc": 0.5,
    },
    "tu_luu_clip": {
        "nhan": "Thư mục lưu clip",
        "mo_ta": "Tự cắt và lưu đoạn video quanh lúc có sự kiện. "
                 "Để trống = tắt tính năng lưu clip.",
        "kieu": "duong_dan",
    },
    "clip_giay": {
        "nhan": "Tổng thời lượng 1 clip (giây)",
        "mo_ta": "Chia đôi: một nửa trước sự kiện, một nửa sau sự kiện.",
        "kieu": "so",
        "toi_thieu": 2.0,
        "toi_da": 600.0,
        "buoc": 1,
    },
    "clip_ghi_tat_ca": {
        "nhan": "Ghi clip cả khi không bật canh vùng",
        "mo_ta": "Mặc định chỉ ghi clip khi có chuyện trong vùng canh. Bật ô "
                 "này thì thấy người là ghi luôn.",
        "kieu": "bool",
    },
    "nhan_vat_the": {
        "nhan": "Thêm vật thể khác",
        "mo_ta": "Ngoài người, còn vẽ khung và đếm các vật thể khác (xe, chó, mèo).",
        "kieu": "bool",
    },
    "lop": {
        "nhan": "Danh sách lớp cần nhận",
        "mo_ta": "Gõ lớp cần nhận, cách nhau bằng dấu phẩy. Nhận được cả tiếng "
                 "Việt (ô tô, xe máy, chó, mèu) và tiếng Anh. "
                 "Để trống = nhóm lớp mặc định, gõ all = mọi lớp trừ người.",
        "kieu": "chuoi",
    },
    "tach_o": {
        "nhan": "Nhận người ở xa (chậm hơn)",
        "mo_ta": "Chia khung hình thành các ô nhỏ để dò kỹ hơn. CHẬM HƠN "
                 "KHOẢNG 5 LẦN nên xem chậm hơn — chỉ bật khi thật sự cần.",
        "kieu": "bool",
    },
    "bat_canh_bao": {
        "nhan": "Cảnh báo (gửi tin ra ngoài)",
        "mo_ta": "Khi có sự kiện thì báo ra ngoài máy này (chuông / hộp thoại / "
                 "Telegram). Mặc định TẮT.",
        "kieu": "bool",
    },
    "canh_bao_mo_phong": {
        "nhan": "Chỉ thử (không gửi thật)",
        "mo_ta": "Bỏ chọn ô này thì cảnh báo sẽ KÊU CHUÔNG và MỞ HỘP THOẠI "
                 "ngay trên máy này.",
        "kieu": "bool",
    },
    "canh_bao_go": {
        "nhan": "Gộp tin (giây)",
        "mo_ta": "Gộp tin cùng loại trong bao nhiêu giây thì gửi 1 lần.",
        "kieu": "so",
        "toi_thieu": 0.0,
        "toi_da": 3600.0,
        "buoc": 5,
    },
    "canh_bao_gioi_han": {
        "nhan": "Giới hạn (tin/phút)",
        "mo_ta": "Tối đa bao nhiêu tin cảnh báo trong một phút.",
        "kieu": "so",
        "toi_thieu": 1,
        "toi_da": 1000,
        "buoc": 1,
    },
    "show_box": {
        "nhan": "Vẽ khung người",
        "mo_ta": "Vẽ khung quanh mỗi người trong khung hình.",
        "kieu": "bool",
    },
    "show_label": {
        "nhan": "Vẽ nhãn tên",
        "mo_ta": "Ghi tên lên khung nếu nhận diện được người quen.",
        "kieu": "bool",
    },
    "show_line": {
        "nhan": "Vẽ vạch đếm ra vào",
        "mo_ta": "Vạch nằm ở giữa khung hình, đếm người đi qua vạch theo "
                 "hướng vào / ra.",
        "kieu": "bool",
    },
    "doc_bien_so": {
        "nhan": "Đọc biển số xe",
        "mo_ta": "Đọc chữ trên biển số xe Việt Nam bằng RapidOCR — chạy 100% "
                 "trên máy này, không gửi ảnh ra ngoài.",
        "kieu": "bool",
    },
    "bien_so_dir": {
        "nhan": "Thư mục lưu ảnh biển số",
        "mo_ta": "Nơi lưu ảnh crop biển số đọc được.",
        "kieu": "duong_dan",
    },
    "bien_so_tin_cay": {
        "nhan": "Ngưỡng tin cậy đọc biển số",
        "mo_ta": "Chỉ nhận biển số khi OCR tin cậy từ mức này trở lên.",
        "kieu": "so",
        "toi_thieu": 0.0,
        "toi_da": 1.0,
        "buoc": 0.05,
    },
    "bien_so_nhoan_lai_giay": {
        "nhan": "Nghỉ giữa 2 lần (giây)",
        "mo_ta": "Cùng một biển số chỉ được lưu ảnh 1 lần trong khoảng nghỉ "
                 "ở trên.",
        "kieu": "so",
        "toi_thieu": 0.0,
        "toi_da": 3600.0,
        "buoc": 1,
    },
    "vung_bien_so": {
        "nhan": "Vùng cần quét (x1,y1,x2,y2)",
        "mo_ta": "Để trống = phần mềm tự tìm biển số trong cả khung hình. "
                 "Gõ 4 số để chỉ quét một vùng.",
        "kieu": "chuoi",
    },
    "tu_chup_dir": {
        "nhan": "Thư mục lưu ảnh sự kiện",
        "mo_ta": "Khi có người đông, vượt vùng hoặc thấy người quen thì chụp "
                 "lại khung hình. Để trống = tắt tính năng tự chụp.",
        "kieu": "duong_dan",
    },
    "tu_chup_nhoan_lai_giay": {
        "nhan": "Nghỉ giữa 2 lần (giây)",
        "mo_ta": "Mỗi loại sự kiện chỉ chụp 1 lần trong khoảng nghỉ ở trên.",
        "kieu": "so",
        "toi_thieu": 0.0,
        "toi_da": 3600.0,
        "buoc": 1,
    },
    "dem_phuong_tien": {
        "nhan": "Đếm phương tiện",
        "mo_ta": "Đếm số xe (ô tô, xe máy...) đi qua. Tách khỏi số người.",
        "kieu": "bool",
    },
    "lop_phuong_tien": {
        "nhan": "Lớp phương tiện cần đếm",
        "mo_ta": "Gõ lớp cần đếm, cách nhau bằng dấu phẩy (ô tô, xe máy). "
                 "Để trống = dùng nhóm lớp phương tiện mặc định.",
        "kieu": "chuoi",
    },
}

# 12 NHOM CON - giong het 12 muc con cua GUI (gui.py, `_khung_tinh_nang`).
# Thu tu field trong moi nhom = thu tu control trong GUI.
# `input` va `output` nam o muc "NGUON" cua GUI (khong phai muc con) -> dua
# vao nhom 1 de moi field luon xuat hien dung 1 lan.
_NHOM_CAU_HINH: list[dict] = [
    {
        "ten": "Phát hiện người",
        "mo_ta": "Đếm có bao nhiêu người trong khung hình. Đây là bước đầu tiên, "
                 "mọi tính năng khác đều dựa vào nó.",
        "truong": [
            "input", "output", "conf", "model", "thiet_bi",
            "show_box", "show_label", "pixelate",
        ],
    },
    {
        "ten": "Nhận diện khuôn mặt",
        "mo_ta": "Dùng để biết người đó là ai. Cần có ảnh đăng ký trước trong "
                 "thư mục known_faces.",
        "truong": ["no_face", "face_threshold", "min_face", "face_every",
                   "faces_dir"],
    },
    {
        "ten": "Đếm ra vào",
        "mo_ta": "Vạch nằm ở giữa khung hình, đếm người đi qua vạch theo hướng "
                 "vào / ra.",
        "truong": ["show_line"],
    },
    {
        "ten": "Canh vùng",
        "mo_ta": "Khoanh một vùng trong khung hình rồi cảnh báo khi có người vào "
                 "vùng đó.",
        "truong": ["vung", "vung_nhay", "vung_max", "canh_lau"],
    },
    {
        "ten": "Lưu clip khi có sự kiện",
        "mo_ta": "Tự cắt và lưu đoạn video quanh lúc có chuyện. Để trống thư mục "
                 "= tắt để cho máy chạy nhẹ.",
        "truong": ["tu_luu_clip", "clip_giay", "clip_ghi_tat_ca"],
    },
    {
        "ten": "Thêm vật thể khác",
        "mo_ta": "Ngoài người, còn vẽ khung và đếm các vật thể khác (xe, chó, mèo).",
        "truong": ["nhan_vat_the", "lop", "dem_phuong_tien", "lop_phuong_tien"],
    },
    {
        "ten": "Nhận người ở xa (chậm hơn)",
        "mo_ta": "Video quay xa, người nhỏ như hạt thì CamAI hay bỏ sót. Bật lên "
                 "phần mềm sẽ chia khung hình thành các ô nhỏ để dò kỹ hơn.",
        "truong": ["tach_o"],
    },
    {
        "ten": "Đọc biển số xe",
        "mo_ta": "Đọc chữ trên biển số xe Việt Nam bằng RapidOCR — chạy 100% "
                 "trên máy này, không gửi ảnh ra ngoài.",
        "truong": ["doc_bien_so", "bien_so_dir", "vung_bien_so",
                   "bien_so_nhoan_lai_giay", "bien_so_tin_cay"],
    },
    {
        "ten": "Tự chụp ảnh khi có sự kiện",
        "mo_ta": "Khi có người đông, vượt vùng hoặc thấy người quen thì chụp lại "
                 "khung hình lưu thành ảnh.",
        "truong": ["tu_chup_dir", "tu_chup_nhoan_lai_giay"],
    },
    {
        "ten": "Cảnh báo (gửi tin ra ngoài)",
        "mo_ta": "Khi có sự kiện thì báo ra ngoài máy này (chuông / hộp thoại / "
                 "Telegram).",
        "truong": ["bat_canh_bao", "canh_bao_mo_phong", "canh_bao_go",
                   "canh_bao_gioi_han"],
    },
    {
        "ten": "Thông tin mô hình AI",
        "mo_ta": "Chỉ hiển thị thông tin: phần mềm đang dùng model nào, nặng bao "
                 "nhiêu, chạy trên GPU hay CPU. Lựa chọn model nằm ở nhóm "
                 "'Phát hiện người'.",
        "truong": [],
    },
    {
        "ten": "Máy này chạy bằng gì",
        "mo_ta": "Chỉ hiển thị thông tin: máy có GPU hay không, đang chọn chạy "
                 "bằng gì. Lựa chọn 'Chạy bằng' nằm ở nhóm 'Phát hiện người'.",
        "truong": [],
    },
]

# Tu khoa de gan field MOI (chua co trong _NHOM_CAU_HINH) vao nhom phu hop.
_TU_KHOA_NHOM: list[tuple[str, int]] = [
    ("bien_so", 7), ("canh_bao", 9), ("vung", 3), ("clip", 4),
    ("tu_chup", 8), ("face", 1), ("min_face", 1), ("no_face", 1),
    ("show_", 0), ("pixelate", 0), ("conf", 0), ("model", 0),
    ("thiet_bi", 0), ("input", 0), ("output", 0),
]


def _doc_field_analysis_config_ast() -> dict[str, dict]:
    """Doc ten + gia tri mac dinh + kieu cua field trong AnalysisConfig (KHONG import).

    `import cam_ai_core` mat ~9 giay (torch). Route /api/cau-hinh phai tra loi
    ngay -> doc truc tiep file cam_ai_core.py bang AST thay vi import.
    """
    duong_dan = os.path.join(APP_DIR, "cam_ai_core.py")
    try:
        with open(duong_dan, "r", encoding="utf-8") as f:
            cay = ast.parse(f.read(), filename=duong_dan)
    except Exception:                                     # noqa: BLE001
        return {}

    # Hang muc gan = 1 -> giai ma duoc gia tri mac dinh khong phai literal
    # (vd CLIP_MAC_DINH_GIAY = 10.0).
    hang: dict = {}
    for node in cay.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            try:
                hang[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:                             # noqa: BLE001
                pass

    lop = None
    for node in cay.body:
        if isinstance(node, ast.ClassDef) and node.name == "AnalysisConfig":
            lop = node
            break
    if lop is None:
        return {}

    ket_qua: dict[str, dict] = {}
    for node in lop.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        ten = node.target.id
        try:
            kieu_goc = ast.unparse(node.annotation) if node.annotation else ""
        except Exception:                                 # noqa: BLE001
            kieu_goc = ""
        mac_dinh = None
        co_mac_dinh = False
        if node.value is not None:
            co_mac_dinh = True
            try:
                mac_dinh = ast.literal_eval(node.value)
            except Exception:                             # noqa: BLE001
                mac_dinh = hang.get(getattr(node.value, "id", ""), None)
        ket_qua[ten] = {
            "kieu_goc": kieu_goc,
            "gia_tri_mac_dinh": mac_dinh,
            "co_mac_dinh": co_mac_dinh,
        }
    return ket_qua


def _truong_analysis_config() -> dict[str, dict]:
    """{ten_field: {...}} cho MOI field cua `AnalysisConfig`.

    Uu tien `AnalysisConfig.__dataclass_fields__` (da co trong RAM - nguon su
    that). Chua co -> doc bang AST (xem ham tren).
    """
    mod = sys.modules.get("cam_ai_core")
    if mod is not None:
        lop = getattr(mod, "AnalysisConfig", None)
        if lop is not None:
            try:
                ket_qua: dict[str, dict] = {}
                for ten, f in lop.__dataclass_fields__.items():
                    mac_dinh = f.default
                    co = mac_dinh is not dataclasses.MISSING
                    ket_qua[ten] = {
                        "kieu_goc": str(f.type),
                        "gia_tri_mac_dinh": mac_dinh if co else None,
                        "co_mac_dinh": co,
                    }
                return ket_qua
            except Exception:                             # noqa: BLE001
                pass
    return _doc_field_analysis_config_ast()


def _suy_kieu(kieu_goc: str) -> str:
    """Suy kieu cho UI tu kieu goc cua dataclass: bool | so | chuoi | duong_dan."""
    g = str(kieu_goc or "").lower()
    if "bool" in g:
        return "bool"
    if "int" in g or "float" in g:
        return "so"
    return "chuoi"


def _mo_ta_field(ten: str, thong_tin: dict) -> dict:
    """Mo ta 1 field cho UI (ten, nhan, mo_ta, kieu, gia tri mac dinh, gioi han)."""
    meta = _KHOA_CAU_HINH.get(ten, {})
    kieu = meta.get("kieu") or _suy_kieu(thong_tin.get("kieu_goc", ""))
    out = {
        "ten": ten,
        "nhan": meta.get("nhan") or ten,
        "mo_ta": meta.get("mo_ta", ""),
        "kieu": kieu,
        "gia_tri_mac_dinh": thong_tin.get("gia_tri_mac_dinh"),
    }
    if kieu == "so":
        for k in ("toi_thieu", "toi_da", "buoc"):
            if k in meta:
                out[k] = meta[k]
    return out


def _mo_ta_cau_hinh() -> list[dict]:
    """Dung danh sach 12 nhom + field de UI tu dung control."""
    truong = _truong_analysis_config()
    nhom_out: list[dict] = []
    da_dung: set[str] = set()
    for nhom in _NHOM_CAU_HINH:
        ds = []
        for ten in nhom["truong"]:
            if ten not in truong:
                continue                       # field da bi xoa -> bo qua
            da_dung.add(ten)
            ds.append(_mo_ta_field(ten, truong[ten]))
        nhom_out.append({"ten": nhom["ten"], "mo_ta": nhom["mo_ta"], "truong": ds})

    # Field MOI them vao dataclass ma chua gan nhom -> gan theo tu khoa,
    # khong gan duoc -> nhom dau tien. Moi field luon xuat hien DUNG 1 LAN.
    thieu = [t for t in truong if t not in da_dung]
    for ten in thieu:
        chi_so = 0
        for tu_khoa, muc in _TU_KHOA_NHOM:
            if tu_khoa in ten:
                chi_so = muc
                break
        if chi_so >= len(nhom_out):
            chi_so = 0
        nhom_out[chi_so]["truong"].append(_mo_ta_field(ten, truong[ten]))
    if thieu:
        _in("[web] cau hinh: %d field chua gan nhom -> gan tu dong: %s"
            % (len(thieu), ", ".join(thieu)))
    return nhom_out


# ------------------------------------------------------------------ ep kieu
def _ep_bool(gia_tri):
    """True/False tu nhieu kieu du lieu. None = khong ep duoc."""
    if isinstance(gia_tri, bool):
        return gia_tri
    if isinstance(gia_tri, (int, float)):
        return bool(gia_tri)
    if isinstance(gia_tri, str):
        s = gia_tri.strip().lower()
        if s in ("1", "true", "yes", "on", "co", "có"):
            return True
        if s in ("0", "false", "no", "off", "khong", "không"):
            return False
    return None


def _ep_int(gia_tri):
    """int tu nhieu kieu du lieu. None = khong ep duoc.

    bool KHONG duoc ep thanh int (True -> 1) de khong giu mot gia tri sai.
    """
    if isinstance(gia_tri, bool):
        return None
    if isinstance(gia_tri, int):
        return gia_tri
    if isinstance(gia_tri, float):
        return int(gia_tri)
    if isinstance(gia_tri, str):
        try:
            return int(float(gia_tri.strip()))
        except Exception:                                 # noqa: BLE001
            return None
    return None


def _ep_float(gia_tri):
    """float tu nhieu kieu du lieu. None = khong ep duoc.

    bool KHONG duoc ep thanh float (True -> 1.0) de khong giu mot gia tri sai.
    """
    if isinstance(gia_tri, bool):
        return None
    if isinstance(gia_tri, (int, float)):
        return float(gia_tri)
    if isinstance(gia_tri, str):
        try:
            return float(gia_tri.strip())
        except Exception:                                 # noqa: BLE001
            return None
    return None


def _ep_chuoi(gia_tri):
    """str tu nhieu kieu du lieu. None = khong ep duoc."""
    if isinstance(gia_tri, str):
        return gia_tri
    if isinstance(gia_tri, (int, float)) and not isinstance(gia_tri, bool):
        return str(gia_tri)
    return None


# Hop dong CU (UI web truoc) -> field moi cua AnalysisConfig.
# "bien_nghich" = True -> gia tri cu la NGUOC voi gia tri field.
_KHOA_CU: dict[str, tuple[str, bool]] = {
    "nhan_mat": ("no_face", True),
    "dem_ra_vao": ("show_line", False),
    "vat_the": ("nhan_vat_the", False),
    "ve_khung": ("show_box", False),
    "ve_nhan": ("show_label", False),
    "lam_mo": ("pixelate", False),
}
# Khoa cu chi dua vao 1 field so (khong doi dau).
_KHOA_CU_SO: dict[str, str] = {
    "nguong_mat": "face_threshold",
}
# Mac dinh cua hop dong CU - chi dung khi body LA hop dong CU.
_MAC_DINH_CU: dict = {
    "nhan_mat": True,
    "dem_ra_vao": False,
    "luu_clip": False,
    "vat_the": False,
    "canh_vung": False,
    "ve_khung": True,
    "ve_nhan": True,
    "lam_mo": False,
    "nguong_mat": 0.40,
    "vung_max": 2,
    "canh_lau": 3.0,
    "clip_giay": 10.0,
}
# Khoa CU rieng (khong trung ten voi field moi cua AnalysisConfig).
_KHOA_CU_RIENG = (
    "duong_dan", "nhan_mat", "dem_ra_vao", "luu_clip", "vat_the",
    "canh_vung", "ve_khung", "ve_nhan", "lam_mo", "nguong_mat", "file_vung",
)
# Khoa vua la hop dong CU vua la field moi -> gui len thi co y nghia moi.
_KHOA_CHIA = ("vung_max", "canh_lau", "clip_giay", "lop")


def _tham_so_from_body(body: dict, duong_dan: str, thu_muc_kq: str) -> tuple[dict, list[str]]:
    """Bien body JSON thanh tham so de tao `AnalysisConfig`.

    Tra (tham_so, danh_sach_canh_bao).
    - Field LA (khong co trong dataclass) -> bo qua, ghi canh bao.
    - Sai kieu -> ep kieu hop le, hoac bo qua + ghi canh bao.
    - Hop dong CU (UI web truoc) -> van dung y nguyen (ke ca mac dinh cu).
    """
    canh_bao: list[str] = []
    truong = _truong_analysis_config()

    # --- 0. Gia tri mac dinh cua dataclass ---
    gia_tri: dict = {}
    for ten, th in truong.items():
        if th.get("co_mac_dinh"):
            gia_tri[ten] = th["gia_tri_mac_dinh"]

    # Body co phai hop dong CU khong? (co khoa CU rieng va KHONG co khoa field
    # moi rieng) -> dung them mac dinh cu cho truong client khong gui.
    khoa_moi_rieng = [t for t in truong if t not in _KHOA_CHIA]
    la_legacy = (
        any(k in body for k in _KHOA_CU_RIENG)
        and not any(k in body for k in khoa_moi_rieng)
    )

    # --- 1. Hop dong CU: chi dung khi client KHONG gui field moi ---
    for ten_cu, (ten_field, bien_nghich) in _KHOA_CU.items():
        if ten_field in body:
            continue                       # field moi duoc gui -> uu tien field moi
        if ten_cu in body:
            gia_tri_cu = _ep_bool(body.get(ten_cu))
            if gia_tri_cu is None:
                canh_bao.append("%s: sai kieu -> bo qua" % ten_cu)
                continue
            gia_tri[ten_field] = (not gia_tri_cu) if bien_nghich else gia_tri_cu
        elif la_legacy:
            mac_dinh = _MAC_DINH_CU[ten_cu]
            gia_tri[ten_field] = (not mac_dinh) if bien_nghich else mac_dinh
    for ten_cu, ten_field in _KHOA_CU_SO.items():
        if ten_field in body:
            continue
        if ten_cu in body:
            gia_tri_so = _ep_float(body.get(ten_cu))
            if gia_tri_so is None:
                canh_bao.append("%s: sai kieu -> bo qua" % ten_cu)
                continue
            gia_tri[ten_field] = gia_tri_so
        elif la_legacy:
            gia_tri[ten_field] = _MAC_DINH_CU[ten_cu]
    # Mac dinh CU cho 3 khoa vua cu vua moi (client CU khong gui -> giu y cu).
    if la_legacy:
        for ten_cu in _KHOA_CHIA:
            if ten_cu in body or ten_cu not in truong:
                continue
            if ten_cu == "lop":
                gia_tri[ten_cu] = ""
            elif ten_cu == "vung_max":
                gia_tri[ten_cu] = int(_MAC_DINH_CU[ten_cu])
            else:
                gia_tri[ten_cu] = float(_MAC_DINH_CU[ten_cu])
    # "vat_the" cu -> dem phuong tien + lop phuong tien (giai hanh cu)
    if "vat_the" in body and "dem_phuong_tien" not in body:
        gia_tri_vat_the = _ep_bool(body.get("vat_the"))
        if gia_tri_vat_the is not None:
            gia_tri["dem_phuong_tien"] = gia_tri_vat_the
    if "vat_the" in body and "lop_phuong_tien" not in body:
        gia_tri_vat_the = _ep_bool(body.get("vat_the"))
        if gia_tri_vat_the is not None:
            gia_tri["lop_phuong_tien"] = str(body.get("lop") or "") if gia_tri_vat_the else ""
    # Hop dong moi: client chi gui `lop` + `dem_phuong_tien` -> dem phuong tien
    # theo lop do (cung y nghia voi hop dong cu: bat "vat the" + "lop").
    if ("lop_phuong_tien" not in body and str(body.get("lop") or "").strip()
            and _ep_bool(body.get("dem_phuong_tien"))):
        gia_tri["lop_phuong_tien"] = str(body.get("lop") or "")
    # canh_vung + file_vung -> vung
    if "vung" not in body:
        gia_tri["vung"] = (str(body.get("file_vung") or "").strip() or FILE_VUNG_MAC_DINH) \
            if _ep_bool(body.get("canh_vung")) else None
    # luu_clip -> tu_luu_clip (thu muc luu clip)
    if "tu_luu_clip" not in body:
        gia_tri["tu_luu_clip"] = thu_muc_kq if _ep_bool(body.get("luu_clip")) else ""
    # Nguon vao + noi luu (route da kiem tra duong dan roi)
    gia_tri["input"] = duong_dan
    gia_tri["output"] = os.path.join(thu_muc_kq, _ten_tach_duong(duong_dan))

    # --- 2. Hop dong MOI: body phang chua field cua AnalysisConfig ---
    for ten, gia_tri_body in body.items():
        if ten not in truong:
            continue
        if gia_tri_body is None:
            continue                           # None = khong dat gia tri nay
        if ten == "input":
            continue                           # da kiem tra o route
        meta = _KHOA_CAU_HINH.get(ten, {})
        kieu = meta.get("kieu") or _suy_kieu(truong[ten].get("kieu_goc", ""))
        kieu_goc = str(truong[ten].get("kieu_goc", "")).lower()
        la_int = "int" in kieu_goc and "float" not in kieu_goc
        if not kieu_goc:
            buoc = meta.get("buoc")
            la_int = isinstance(buoc, (int, float)) and float(buoc) >= 1
        if kieu == "bool":
            val = _ep_bool(gia_tri_body)
        elif kieu == "so":
            val = _ep_int(gia_tri_body) if la_int else _ep_float(gia_tri_body)
        else:
            val = _ep_chuoi(gia_tri_body)
        if val is None:
            canh_bao.append("%s: sai kieu (%r) -> bo qua" % (ten, gia_tri_body))
            continue
        if kieu == "so":
            toi_thieu = meta.get("toi_thieu")
            toi_da = meta.get("toi_da")
            if toi_thieu is not None and val < toi_thieu:
                canh_bao.append("%s: %s < %s -> lay %s"
                                % (ten, val, toi_thieu, toi_thieu))
                val = toi_thieu
            if toi_da is not None and val > toi_da:
                canh_bao.append("%s: %s > %s -> lay %s" % (ten, val, toi_da, toi_da))
                val = toi_da
        gia_tri[ten] = val

    # --- 3. Field la trong body -> bo qua (khong crash) ---
    la = [t for t in body if t not in truong and t not in _KHOA_CU
          and t not in _KHOA_CU_SO and t not in (
              "duong_dan", "canh_vung", "file_vung", "luu_clip")]
    if la:
        canh_bao.append("bo qua %d field la: %s" % (len(la), ", ".join(sorted(la)[:20])))
    return gia_tri, canh_bao


def _tao_cau_hinh(body: dict, duong_dan: str, thu_muc_kq: str):
    """Tao AnalysisConfig. GOI TRONG THREAD NEN (import cam_ai_core cham ~8s)."""
    from cam_ai_core import AnalysisConfig

    gia_tri, canh_bao = _tham_so_from_body(body, duong_dan, thu_muc_kq)
    for dong in canh_bao:
        TT.ghi_log("[web] " + dong)
        _in("[web] " + dong)
    # Chi lay field co THAT trong dataclass -> field la khong lam hong.
    co_that = {k: v for k, v in gia_tri.items() if k in AnalysisConfig.__dataclass_fields__}
    cfg = AnalysisConfig(**co_that)
    # In config da dung -> coordinator doi chieu voi GUI.
    for ten in AnalysisConfig.__dataclass_fields__:
        _in("[web] cfg: %s = %s" % (ten, getattr(cfg, ten)))
    TT.ghi_log(
        "[web] Cấu hình: "
        + ", ".join("%s=%s" % (t, getattr(cfg, t))
                    for t in AnalysisConfig.__dataclass_fields__)
    )
    return cfg


# Ket qua rong (chua chay gi) - cung dung 17 truong nhu hop dong moi.
_KET_QUA_RONG: dict = {
    "so_nguoi_max": 0,
    "so_mat_max": 0,
    "ten_da_nhan": [],
    "nam": 0,
    "nu": 0,
    "tuoi_tb": 0,
    "phuong_tien": {},
    "bien_so": [],
    "so_vi_pham": 0,
    "so_crowd": 0,
    "so_loiter": 0,
    "thoi_luong_clip": 0.0,
    "so_khung": 0,
    "fps": 0.0,
    "duong_dan_video": "",
    "duong_dan_bao_cao": "",
    "so_su_kien": 0,
}


def _boc_dich_bien_so():
    """Boc `bien_so.BoDocBienSo.doc` de lay tin cay OCR + khung cua tung bien so.

    `AnalysisResult.bien_so` chi giu CHUOI bien so (string). UI can them tin cay
    + so khung hinh -> boc 1 ham nay (chi trong RAM, KHONG sua file bien_so.py).
    Tra ve (lop, ham_goc) de khoi lai, hoac None neu khong boc duoc.
    """
    try:
        import bien_so

        lop = bien_so.BoDocBienSo
        goc = lop.doc
    except Exception:                                     # noqa: BLE001
        return None

    def doc(self, anh_bgr, detections=None, so_mat_rang=0, khuon_mat=None):
        ket = goc(self, anh_bgr, detections=detections, so_mat_rang=so_mat_rang,
                  khuon_mat=khuon_mat)
        try:
            with TT.khoa:
                khung_hinh = TT.khung_hinh
            for r in ket or []:
                TT.them_bien_so(
                    {
                        "text": str(getattr(r, "chuoi", "") or ""),
                        "confidence": round(float(getattr(r, "tin_cay", 0.0) or 0.0), 3),
                        "frame": int(khung_hinh),
                        "khung": list(getattr(r, "khung", (0, 0, 0, 0)) or (0, 0, 0, 0)),
                    }
                )
        except Exception:                                 # noqa: BLE001
            pass
        return ket

    try:
        lop.doc = doc
    except Exception:                                     # noqa: BLE001
        return None
    return lop, goc


def _khoi_boc_dich_bien_so(ghi) -> None:
    """Khoi lai ham doc bien so da boc (giu dung ban goc)."""
    if not ghi:
        return
    lop, goc = ghi
    try:
        lop.doc = goc
    except Exception:                                     # noqa: BLE001
        pass


def _ket_qua_day_du(ket_qua) -> dict:
    """Ket qua cuoi cung theo hop dong moi (GET /api/ket-qua)."""
    phuong_tien: dict = {}
    for ten_lop, du_lieu in (getattr(ket_qua, "phuong_tien", {}) or {}).items():
        du_lieu = du_lieu if isinstance(du_lieu, dict) else {}
        phuong_tien[str(ten_lop)] = {
            "ten_viet": str(du_lieu.get("ten_viet", "")),
            "ten_anh": str(du_lieu.get("ten_anh", "")),
            "tong": int(du_lieu.get("tong", 0) or 0),
            "max_cung_luc": int(du_lieu.get("max_cung_luc", 0) or 0),
        }
    so_vi_pham = int(getattr(ket_qua, "violation_events", 0) or 0)
    so_crowd = int(getattr(ket_qua, "crowd_events", 0) or 0)
    so_loiter = int(getattr(ket_qua, "loiter_events", 0) or 0)
    try:
        thoi_luong = round(float(ket_qua.duration.total_seconds()), 2)
    except Exception:                                     # noqa: BLE001
        thoi_luong = 0.0
    return {
        "so_nguoi_max": int(getattr(ket_qua, "max_people", 0) or 0),
        "so_mat_max": int(getattr(ket_qua, "max_faces", 0) or 0),
        "ten_da_nhan": [str(x) for x in (getattr(ket_qua, "seen_names", []) or [])],
        "nam": int(getattr(ket_qua, "males", 0) or 0),
        "nu": int(getattr(ket_qua, "females", 0) or 0),
        "tuoi_tb": int(getattr(ket_qua, "avg_age", 0) or 0),
        "phuong_tien": phuong_tien,
        "bien_so": [str(x) for x in (getattr(ket_qua, "bien_so", []) or [])],
        "so_vi_pham": so_vi_pham,
        "so_crowd": so_crowd,
        "so_loiter": so_loiter,
        "thoi_luong_clip": thoi_luong,
        "so_khung": int(getattr(ket_qua, "frames", 0) or 0),
        "fps": round(float(getattr(ket_qua, "fps", 0.0) or 0.0), 2),
        "duong_dan_video": str(getattr(ket_qua, "out_path", "") or ""),
        "duong_dan_bao_cao": str(getattr(ket_qua, "report_path", "") or ""),
        "so_su_kien": so_vi_pham + so_crowd + so_loiter,
    }


def _danh_sach_anh_su_kien(ket_qua) -> list[dict]:
    """Danh sach anh tu chup da luu (duong dan + thoi gian)."""
    danh_sach: list[dict] = []
    for duong_dan in (getattr(ket_qua, "anh_su_kien", []) or []):
        duong_dan = str(duong_dan)
        thoi_diem = ""
        try:
            thoi_diem = datetime.fromtimestamp(
                os.path.getmtime(duong_dan)
            ).strftime("%Y-%m-%d %H:%M:%S")
        except OSError:
            thoi_diem = ""
        danh_sach.append(
            {
                "duong_dan": duong_dan,
                "ten": os.path.basename(duong_dan),
                "thoi_diem": thoi_diem,
            }
        )
    return danh_sach


def _danh_sach_bien_so(ket_qua) -> list[dict]:
    """Danh sach bien so doc duoc (text, confidence, frame)."""
    with TT.khoa:
        chi_tiet = list(TT.bien_so)
    if chi_tiet:
        return chi_tiet
    # Khong boc duoc ham doc bien so -> chi tra duoc chuoi bien so.
    return [
        {"text": str(x), "confidence": None, "frame": None}
        for x in (getattr(ket_qua, "bien_so", []) or [])
    ]


def _chay_phan_tich(duong_dan: str, thu_muc_kq: str, body: dict) -> None:
    """CHAY TRONG THREAD NEN. Khong bao gio chay trong luong xu ly FastAPI.

    Import cam_ai_core + tao AnalysisConfig O DAY (khong o route) -> route
    /api/phan-tich tra ve NGAY, dien thoai khong bi treo ~8-30 giay cho
    viec load torch. Loi (vd lop vật thể sai) se lo ra qua TT.loi.
    """
    from cam_ai_core import CamAIError, run_analysis

    bat_dau = time.perf_counter()
    goc_doc = None
    TT.dat(thu_muc_ket_qua=thu_muc_kq)
    try:
        # Do fps that cua video (dung de tinh giay cua su kien) - o thread nen.
        TT.dat(fps_thuoc=_fps_cua_video(duong_dan))
        cfg = _tao_cau_hinh(body, duong_dan, thu_muc_kq)
        # Doc bien so: boc ham de lay tin_cay + khung (AnalysisResult chi giu chuoi)
        if cfg.doc_bien_so:
            goc_doc = _boc_dich_bien_so()
        # frame_cb -> luu khung hinh moi nhat cho /api/anh-nen (dien thoai xem live).
        # interval 0.2s = 5 khung/s: du cho dien thoai, chi +~2% chi phi pipeline.
        ket_qua = run_analysis(
            cfg,
            progress_cb=_tien_trinh,
            log=TT.ghi_log,
            frame_cb=ANH_NEN.dat,
            frame_cb_interval=KHOA_FRAME_MOI_NHAT,
        )
        TT.dat(
            ket_qua={
                "video_ket_qua": os.path.basename(ket_qua.out_path),
                "file_bao_cao": os.path.basename(ket_qua.report_path),
                "khung_hinh": ket_qua.frames,
                "fps": round(ket_qua.fps, 2),
                "thoi_luong": round(ket_qua.duration.total_seconds(), 1),
                "max_nguoi": ket_qua.max_people,
                "max_mat": ket_qua.max_faces,
                "nguoi_quen": ket_qua.seen_names,
                "nam": ket_qua.males,
                "nu": ket_qua.females,
                "tuoi_tb": ket_qua.avg_age,
                "co_mat": ket_qua.used_face,
                "peak_vung": ket_qua.peak_zone,
                "su_kien_vung": ket_qua.violation_events,
                "su_kien_qua_dong": ket_qua.crowd_events,
                "su_kien_dung_lau": ket_qua.loiter_events,
                "dung_lau_lau_nhat": round(ket_qua.longest_loiter, 1),
                "so_clip": len(ket_qua.clips),
                "da_dung": ket_qua.stopped,
                "xe": int(getattr(ket_qua, "tong_phuong_tien", 0) or 0),
                "max_xe": int(getattr(ket_qua, "max_phuong_tien", 0) or 0),
            }
        )
        # Hop dong moi: ket qua day du + anh su kien + bien so.
        TT.dat(ket_qua_day_du=_ket_qua_day_du(ket_qua))
        TT.dat(anh_su_kien=_danh_sach_anh_su_kien(ket_qua))
        TT.dat(bien_so=_danh_sach_bien_so(ket_qua))
        TT.dat(xe=int(getattr(ket_qua, "tong_phuong_tien", 0) or 0))
        TT.dat(trang_thai="Đã dừng theo yêu cầu" if ket_qua.stopped else "Xong")
        TT.ghi_log("[web] Xong trong %.1f giây." % (time.perf_counter() - bat_dau))
    except CamAIError as exc:
        TT.dat(trang_thai="Lỗi: " + str(exc), loi=str(exc))
        TT.ghi_log("[loi] " + str(exc))
        _in("[LOI] %s" % exc)
    except Exception as exc:                        # noqa: BLE001
        TT.dat(trang_thai="Lỗi: " + str(exc), loi=str(exc))
        TT.ghi_log("[loi] " + str(exc))
        _in("[LOI] %s" % exc)
        _in(traceback.format_exc())
    finally:
        _khoi_boc_dich_bien_so(goc_doc)
        TT.an()
        _xoa_tam(duong_dan)
        _don_dep()


def _tao_bao_cao(duong_csv: str, duong_video: str) -> None:
    """CHAY TRONG THREAD NEN: goi bao_cao_tong_ket.chay() da co san."""
    try:
        import bao_cao_tong_ket

        TT.dat(dang_tao_bao_cao=True, bao_cao="Đang tạo báo cáo...")
        tt = TT.thu_muc_ket_qua
        bao_cao_tong_ket.chay(
            ["--csv", duong_csv, "--video", duong_video, "--xuat", tt]
        )
        goc = os.path.splitext(os.path.basename(duong_csv))[0]
        if goc.endswith("_bao_cao"):
            goc = goc[: -len("_bao_cao")]
        co_xlsx = os.path.isfile(os.path.join(tt, goc + "_tong_ket.xlsx"))
        co_html = os.path.isfile(os.path.join(tt, goc + "_xem_lai.html"))
        TT.dat(
            dang_tao_bao_cao=False,
            bao_cao="Đã tạo báo cáo" if (co_xlsx or co_html) else "Không tạo được báo cáo",
        )
        TT.ghi_log("[web] " + TT.bao_cao)
    except Exception as exc:                        # noqa: BLE001
        TT.dat(dang_tao_bao_cao=False, bao_cao="Lỗi: " + str(exc))
        TT.ghi_log("[loi] bao cao: " + str(exc))
        _in("[LOI] bao cao: %s" % exc)


# ------------------------------------------------------------------ giao dien web
HTML_TRANG = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CamAI — Phân tích video</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:__NEN__;color:__CHU__;
     font-family:"Segoe UI",Tahoma,Arial,sans-serif;font-size:15px;line-height:1.5}
.man{padding:16px;max-width:1100px;margin:0 auto}
.an{display:none !important}
.the{background:__THE__;border:1px solid __VIEN__;border-radius:10px;
     padding:16px;margin-bottom:12px}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:17px;margin:0 0 12px}
.tieu-de{display:flex;justify-content:space-between;align-items:center;
         gap:12px;flex-wrap:nowrap;margin-bottom:12px}
.tieu-de>div{flex:1 1 auto;min-width:0}
.tieu-de>button{flex:0 0 auto}
.nho{color:__CHU_PHU__;font-size:13px;margin:6px 0 0}
.hang{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.cot{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}
button{font-family:inherit;font-size:14px;border:none;border-radius:10px;
       padding:10px 14px;cursor:pointer;transition:background .15s,color .15s}
.nut-chinh{background:__NUT_CHINH__;color:__CANH__}
.nut-chinh:hover{background:__VIEN_CHINH__;color:__CHU__}
.nut-phu{background:__NUT_PHU__;color:__CHU__}
.nut-phu:hover{background:__VIEN__;color:__CHU__}
.nut-loi{background:__LOI__;color:__CHU__}
.nut-loi:hover{background:__VIEN_LOI__}
button:disabled{opacity:.45;cursor:not-allowed}
input[type=text],input[type=number],input[type=password],input[type=file]{
  background:__CANH__;color:__CHU__;border:1px solid __VIEN__;border-radius:10px;
  padding:10px;font-family:inherit;font-size:14px;width:100%}
input:focus{outline:2px solid __NUT_CHINH__;outline-offset:1px}
label.opt{display:flex;gap:8px;align-items:flex-start;background:__CANH__;
  border:1px solid __VIEN__;border-radius:10px;padding:10px;cursor:pointer}
label.opt input{margin-top:3px;width:18px;height:18px;accent-color:__NUT_CHINH__}
label.opt.khoa{opacity:.75;cursor:default}
.nut-mau{width:100%;text-align:left;background:__NUT_PHU__;color:__CHU__}
.nut-mau:hover{background:__NUT_CHINH__;color:__CANH__}
.thanh{height:18px;background:__CANH__;border-radius:10px;overflow:hidden;
       border:1px solid __VIEN__}
.thanh>div{height:100%;width:0;background:__NUT_CHINH__;transition:width .3s}
.luoi{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;
      margin-top:12px}
.o{background:__CANH__;border:1px solid __VIEN__;border-radius:10px;padding:10px}
.o b{display:block;font-size:22px}
.o span{color:__CHU_PHU__;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid __VIEN__;
      white-space:nowrap}
th{color:__CHU_PHU__;position:sticky;top:0;background:__THE__}
.khung-nhat{height:300px;overflow:auto;border:1px solid __VIEN__;border-radius:10px}
#hop-thong-bao{position:sticky;top:0;z-index:9}
#noi_dung_thong_bao{border-radius:10px;padding:10px 12px;font-size:14px}
.tt-ok{background:__CANH_CHINH__;border:1px solid __NUT_CHINH__;color:__CHU__}
.tt-loi{background:__VIEN_LOI__;border:1px solid __LOI__;color:__CHU__}
#man_dang_nhap{display:flex;align-items:center;justify-content:center;min-height:100vh}
#the_dang_nhap{width:100%;max-width:380px}
.center{text-align:center}
@media (max-width:640px){.man{padding:10px}.the{padding:12px}h1{font-size:19px}}
</style>
</head>
<body>

<!-- ============================ DANG NHAP ============================ -->
<div id="man_dang_nhap">
  <div class="the" id="the_dang_nhap">
    <h1>CamAI</h1>
    <p class="nho">Nhập mật khẩu để vào phần mềm.</p>
    <form id="form_dang_nhap" style="margin-top:12px">
      <input type="password" id="o_mat_khauu" placeholder="Mật khẩu"
             autocomplete="current-password" autofocus required>
      <button class="nut-chinh" type="submit"
              style="width:100%;margin-top:8px">Vào phần mềm</button>
    </form>
    <div id="loi_dang_nhap" class="tt-loi an"
         style="margin-top:10px"></div>
    <p class="nho">Toàn bộ hình ảnh và video được xử lý ngay trên máy này,
      không gửi lên Internet.</p>
  </div>
</div>

<!-- ============================ TRANG CHINH ============================ -->
<div id="man_chinh" class="man an">
  <div class="tieu_de">
    <div>
      <h1>CamAI</h1>
      <p class="nho">Phân tích video camera — chạy trên máy này, không lên cloud.</p>
    </div>
    <button class="nut-phu" id="nut_dang_xuat">Đăng xuất</button>
  </div>

  <div id="hop-thong-bao"><div id="noi_dung_thong_bao" class="an"></div></div>

  <!-- 1. chon video -->
  <div class="the">
    <h2>1. Chọn video</h2>
    <div class="cot">
      <div>
        <label class="nho" for="o_file">Tải video từ máy/điện thoại</label>
        <input type="file" id="o_file"
               accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/webm">
      </div>
      <div>
        <label class="nho" for="o_duong_dan">Đường dẫn video trên máy chủ</label>
        <input type="text" id="o_duong_dan" placeholder="Chọn video mẫu bên dưới">
      </div>
    </div>
    <p class="nho" id="dong_tai_len"></p>
    <p class="nho"><b>Video mẫu có sẵn</b> — bấm để điền vào ô đường dẫn
      (chưa chạy, muốn chạy thì bấm “Bắt đầu phân tích”).</p>
    <div class="cot" id="luoi_video_mau" style="margin-top:8px"></div>
  </div>

  <!-- 2. tuy chon -->
  <div class="the">
    <h2>2. Tuỳ chọn</h2>
    <div class="cot">
      <label class="opt"><input type="checkbox" id="c_mat" checked>
        <span>Nhận diện khuôn mặt</span></label>
      <label class="opt khoa"><input type="checkbox" checked disabled>
        <span>Ước lượng tuổi và giới tính (luôn bật khi nhận diện mặt)</span></label>
      <label class="opt"><input type="checkbox" id="c_dem_ra_vao">
        <span>Đếm người ra / vào</span></label>
      <label class="opt"><input type="checkbox" id="c_clip">
        <span>Tự lưu clip khi có sự kiện</span></label>
      <label class="opt"><input type="checkbox" id="c_vat_the">
        <span>Nhận vật thể khác (xe, ba lô, điện thoại…)</span></label>
      <label class="opt"><input type="checkbox" id="c_vung">
        <span>Cảnh vùng</span></label>
      <label class="opt"><input type="checkbox" id="c_khung" checked>
        <span>Vẽ khung người</span></label>
      <label class="opt"><input type="checkbox" id="c_nhan" checked>
        <span>Vẽ nhãn tên</span></label>
      <label class="opt"><input type="checkbox" id="c_lam_mo">
        <span>Làm mờ nền, giữ rõ chỗ có người</span></label>
    </div>
    <div class="cot" style="margin-top:8px">
      <div><label class="nho" for="o_nguong">Ngưỡng giống mặt (mặc định 0.40)</label>
        <input type="number" id="o_nguong" step="0.01" min="0.1" max="0.9" value="0.40"></div>
      <div><label class="nho" for="o_vung_file">File vùng (.txt)</label>
        <input type="text" id="o_vung_file"></div>
      <div><label class="nho" for="o_vung_max">Cảnh báo vượt quá (người)</label>
        <input type="number" id="o_vung_max" min="0" value="2"></div>
      <div><label class="nho" for="o_canh_lau">Cảnh báo đứng lâu (giây)</label>
        <input type="number" id="o_canh_lau" min="0" step="0.5" value="3"></div>
      <div><label class="nho" for="o_clip_giay">Thời lượng 1 clip (giây)</label>
        <input type="number" id="o_clip_giay" min="2" step="1" value="10"></div>
      <div><label class="nho" for="o_lop">Lớp vật thể (cách nhau bằng dấu phẩy)</label>
        <input type="text" id="o_lop" placeholder="để trống = nhóm phổ biến"></div>
    </div>
  </div>

  <!-- 3. chay -->
  <div class="the">
    <h2>3. Chạy phân tích</h2>
    <div class="hang">
      <button class="nut-chinh" id="nut_chay">Bắt đầu phân tích</button>
      <button class="nut-loi" id="nut_dung" disabled>Dừng</button>
      <span id="dong_trang_thai" class="nho">Chưa chạy</span>
    </div>
    <div class="thanh" style="margin-top:12px"><div id="thanhtien"></div></div>
    <p class="nho" id="dong_khung_hinh"></p>
    <div class="luoi">
      <div class="o"><b id="s_nguoi">0</b><span>Người trong khung hình</span></div>
      <div class="o"><b id="s_mat">0</b><span>Khuôn mặt thấy</span></div>
      <div class="o"><b id="s_vao">0</b><span>Người vào</span></div>
      <div class="o"><b id="s_ra">0</b><span>Người ra</span></div>
      <div class="o"><b id="s_vung">0</b><span>Trong vùng cảnh giám</span></div>
      <div class="o"><b id="s_vi_pham">0</b><span>Vi phạm</span></div>
    </div>
  </div>

  <!-- 4. ket qua -->
  <div class="the an" id="the_ket_qua">
    <h2>4. Kết quả</h2>
    <p class="nho" id="dong_ket_qua"></p>
    <div class="hang" style="margin-top:8px">
      <button class="nut-phu" id="nut_csv">Tải CSV</button>
      <button class="nut-phu" id="nut_video">Tải video có khung</button>
      <button class="nut-phu" id="nut_bao_cao">Tạo báo cáo Excel + HTML</button>
      <a id="link_xlsx" class="nut-phu an"
         style="text-decoration:none;padding:10px 14px;border-radius:10px"
         href="#">Tải Excel</a>
      <a id="link_html" class="nut-phu an"
         style="text-decoration:none;padding:10px 14px;border-radius:10px"
         href="#">Mở trang xem lại</a>
    </div>
    <p class="nho" id="dong_bao_cao"></p>
  </div>

  <!-- 5. nhat ky -->
  <div class="the">
    <h2>5. Nhật ký tiến trình</h2>
    <div class="khung-nhat">
      <table><thead><tr><th>Giờ</th><th>Nội dung</th></tr></thead>
        <tbody id="bang_log"></tbody></table>
    </div>
  </div>
</div>

<script>
const VIDEO_MAU = __VIDEO_MAU_JSON__;
const $ = (id) => document.getElementById(id);

function thong_bao(nd, ok) {
  const o = $('noi_dung_thong_bao');
  o.className = ok ? 'tt-ok' : 'tt-loi';
  o.textContent = nd;
}

async function api(duong, tuy_chon) {
  const goi = Object.assign({credentials: 'same-origin'}, tuy_chon || {});
  const res = await fetch(duong, goi);
  let duLieu = null;
  try { duLieu = await res.json(); } catch (e) { duLieu = null; }
  return {ok: res.ok, status: res.status, du_lieu: duLieu};
}

// ------------------------------------------------------------ ve video mau
function ve_video_mau() {
  const luoi = $('luoi_video_mau');
  luoi.innerHTML = '';
  VIDEO_MAU.forEach((v) => {
    const b = document.createElement('button');
    b.className = 'nut-mau';
    b.type = 'button';
    b.textContent = v.ten;
    b.onclick = () => {
      $('o_duong_dan').value = v.duong_dan;
      thong_bao('Đã chọn ' + v.ten + '. Bấm “Bắt đầu phân tích” để chạy.', true);
    };
    luoi.appendChild(b);
  });
}

// ------------------------------------------------------------ dang nhap
$('form_dang_nhap').onsubmit = async (e) => {
  e.preventDefault();
  const loi = $('loi_dang_nhap');
  loi.className = 'tt-loi an';
  const r = await api('/api/dang-nhap', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mat_khauu: $('o_mat_khauu').value})
  });
  if (r.ok && r.du_lieu && r.du_lieu.ok) {
    $('o_mat_khauu').value = '';
    mo_trang_chinh();
    poll();
  } else {
    loi.textContent = (r.du_lieu && r.du_lieu.loi) || 'Đăng nhập không thành công.';
    loi.className = 'tt-loi';
  }
};

function mo_trang_chinh() {
  if ($('man_chinh').classList.contains('an')) ve_video_mau();
  $('man_dang_nhap').classList.add('an');
  $('man_chinh').classList.remove('an');
  $('man_chinh').classList.add('man');
}

$('nut_dang_xuat').onclick = async () => {
  await api('/api/dang-xuat', {method: 'POST'});
  $('man_chinh').classList.add('an');
  $('man_dang_nhap').classList.remove('an');
  if (bo_dong) {clearInterval(bo_dong); bo_dong = null;}
};

// ------------------------------------------------------------ tai video
$('o_file').onchange = async () => {
  const f = $('o_file').files[0];
  $('dong_tai_len').textContent = '';
  if (!f) return;
  const dl = new FormData();
  dl.append('file', f);
  thong_bao('Đang tải video lên máy chủ...', true);
  const r = await api('/api/tai-video', {method: 'POST', body: dl});
  if (r.ok && r.du_lieu && r.du_lieu.ok) {
    $('o_duong_dan').value = r.du_lieu.duong_dan;
    $('dong_tai_len').textContent =
      'Đã tải xong: ' + r.du_lieu.ten + ' (' + r.du_lieu.dung_luong_mb + ' MB).';
    thong_bao('Tải video xong. Bấm “Bắt đầu phân tích” để chạy.', true);
  } else {
    thong_bao((r.du_lieu && r.du_lieu.loi) || 'Tải video thất bại.', false);
  }
};

// ------------------------------------------------------------ chay / dung
$('nut_chay').onclick = async () => {
  const duong = $('o_duong_dan').value.trim();
  if (!duong) {thong_bao('Chưa chọn video.', false); return;}
  thong_bao('Đang bắt đầu...', true);
  const r = await api('/api/phan-tich', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      duong_dan: duong,
      nhan_mat: $('c_mat').checked,
      dem_ra_vao: $('c_dem_ra_vao').checked,
      luu_clip: $('c_clip').checked,
      vat_the: $('c_vat_the').checked,
      canh_vung: $('c_vung').checked,
      ve_khung: $('c_khung').checked,
      ve_nhan: $('c_nhan').checked,
      lam_mo: $('c_lam_mo').checked,
      nguong_mat: parseFloat($('o_nguong').value || '0.40'),
      file_vung: $('o_vung_file').value.trim(),
      vung_max: parseInt($('o_vung_max').value || '0', 10),
      canh_lau: parseFloat($('o_canh_lau').value || '0'),
      clip_giay: parseFloat($('o_clip_giay').value || '10'),
      lop: $('o_lop').value.trim()
    })
  });
  if (!(r.ok && r.du_lieu && r.du_lieu.ok)) {
    thong_bao((r.du_lieu && r.du_lieu.loi) || 'Không chạy được.', false);
    return;
  }
  thong_bao('Đang phân tích...', true);
  $('the_ket_qua').classList.add('an');
  poll();
};

$('nut_dung').onclick = async () => {
  thong_bao('Đang yêu cầu dừng...', true);
  const r = await api('/api/dung', {method: 'POST'});
  if (r.du_lieu && !r.du_lieu.ok) {
    thong_bao((r.du_lieu && r.du_lieu.loi) || 'Không dừng được.', false);
  }
};

// ------------------------------------------------------------ tai ket qua
$('nut_csv').onclick = () => {
  window.location.href = '/api/tai-ket-qua?loai=csv';
};
$('nut_video').onclick = () => {
  window.location.href = '/api/tai-ket-qua?loai=video';
};
$('nut_bao_cao').onclick = async () => {
  thong_bao('Đang tạo báo cáo, chờ vài giây...', true);
  const r = await api('/api/tao-bao-cao', {method: 'POST'});
  thong_bao((r.du_lieu && r.du_lieu.loi) || 'Đã gửi yêu cầu tạo báo cáo.', true);
};

// ------------------------------------------------------------ poll trang thai
let bo_dong = null;
let so_dong_cu = 0;

function ve_trang_thai(d) {
  $('nut_chay').disabled = d.dang_chay;
  $('nut_dung').disabled = !d.dang_chay;
  $('dong_trang_thai').textContent = d.trang_thai + (d.tieu_de ? ' — ' + d.tieu_de : '');
  $('thanhtien').style.width = d.phan_tram + '%';
  $('dong_khung_hinh').textContent =
    'Khung hình ' + d.khung_hinh + ' / ' + (d.tong_khung_hinh || '?') +
    '  (' + d.phan_tram + '%)' +
    (d.nhan_dien ? '  —  Người quen: ' + d.nhan_dien : '');
  $('s_nguoi').textContent = d.so_nguoi;
  $('s_mat').textContent = d.so_mat;
  $('s_vao').textContent = d.vao;
  $('s_ra').textContent = d.ra;
  $('s_vung').textContent = d.trong_vung;
  $('s_vi_pham').textContent = d.vi_pham;

  const tb = $('bang_log');
  if (d.log.length !== so_dong_cu) {
    so_dong_cu = d.log.length;
    tb.innerHTML = '';
    d.log.forEach((r) => {
      const tr = document.createElement('tr');
      const td1 = document.createElement('td');
      td1.textContent = r.luc;
      const td2 = document.createElement('td');
      td2.textContent = r.noi_dung;
      td2.style.whiteSpace = 'pre-wrap';
      tr.appendChild(td1); tr.appendChild(td2);
      tb.appendChild(tr);
    });
    const khung = tb.parentElement.parentElement;
    khung.scrollTop = khung.scrollHeight;
  }

  const k = d.ket_qua;
  if (k) {
    $('the_ket_qua').classList.remove('an');
    $('dong_ket_qua').textContent =
      'Video: ' + d.tieu_de + ' — ' + k.khung_hinh + ' khung hình, ' +
      k.thoi_luong + ' giây, ' + k.fps + ' fps. ' +
      'Nhiều nhất 1 khung hình: ' + k.max_nguoi + ' người, ' + k.max_mat + ' mặt. ' +
      'Giới tính: ' + k.nam + ' nam, ' + k.nu + ' nữ. ' +
      'Tuổi trung bình: ' + (k.co_mat ? k.tuoi_tb + ' tuổi' : 'không có nhận diện mặt') +
      (k.nguoi_quen && k.nguoi_quen.length
        ? ' — Đã nhận ra: ' + k.nguoi_quen.join(', ') : '');
  }
  $('dong_bao_cao').textContent = d.bao_cao;
  const co_bao_cao = d.bao_cao.indexOf('Đã tạo') === 0;
  $('link_xlsx').classList.toggle('an', !co_bao_cao);
  $('link_html').classList.toggle('an', !co_bao_cao);
  $('link_xlsx').href = '/api/tai-ket-qua?loai=xlsx';
  $('link_html').href = '/api/tai-ket-qua?loai=html';
}

async function poll() {
  const r = await api('/api/trang-thai');
  if (r.status === 401) {
    if (bo_dong) {clearInterval(bo_dong); bo_dong = null;}
    $('man_chinh').classList.add('an');
    $('man_dang_nhap').classList.remove('an');
    return;
  }
  // Cookie con hieu luc -> hien trang chinh ngay, ke ca khi tai lai trang.
  if (r.ok && r.du_lieu) {ve_trang_thai(r.du_lieu); mo_trang_chinh();}
  if (!bo_dong) bo_dong = setInterval(poll, 1500);
}

poll();
</script>
</body>
</html>
"""


def _do_mau(html: str) -> str:
    """The mau sac tu dict MAU vao HTML. Khong co hex nao viet tay trong HTML."""
    for ten, mau in MAU.items():
        html = html.replace("__%s__" % ten.upper(), mau)
    return html


def _trang_web() -> str:
    import json

    danh_sach = [
        {"ten": ten, "file": ten_file, "duong_dan": os.path.join(THU_MUC_VIDEO_MAU, ten_file)}
        for ten, ten_file in VIDEO_MAU
        if os.path.isfile(os.path.join(THU_MUC_VIDEO_MAU, ten_file))
    ]
    html = HTML_TRANG.replace("__VIDEO_MAU_JSON__", json.dumps(danh_sach, ensure_ascii=False))
    return _do_mau(html)


# ------------------------------------------------------------------ dinh nghia web
from fastapi import FastAPI, Request, UploadFile, File          # noqa: E402
from fastapi.responses import (                                # noqa: E402
    HTMLResponse,
    JSONResponse,
    FileResponse,
    Response,
    StreamingResponse,
)
from pydantic import BaseModel                                # noqa: E402

app = FastAPI(title="CamAI Web", docs_url=None, redoc_url=None)

# Cac tep da upload duoc phep dung (ten sinh tu UUID, khong dung ten nguoi gui).
_TEP_DA_UPLOAD: set[str] = set()
_KHOA_UPLOAD = threading.Lock()


def _ip(request: Request) -> str:
    return request.client.host if request.client else "khong-ro"


def _lay_token(request: Request) -> str:
    """Lay token phien tu cookie / header / query string.

    - Cookie `camai_phien`: giao dien web CU (giu nguyen).
    - Header `X-Camai-Token` hoac `Authorization: Bearer <token>`: UI moi.
    - Query `?token=...`: de <img>/<video> tren dien thoai tai duoc.
    """
    tok = request.cookies.get(TEN_COOKIE)
    if tok:
        return tok
    for ten in ("x-camai-token", "x-auth-token", "x-token", "token"):
        val = request.headers.get(ten)
        if val:
            val = val.strip()
            if val:
                return val
    auth = (request.headers.get("authorization") or "").strip()
    if auth:
        if auth.lower().startswith("bearer "):
            auth = auth[7:].strip()
        if auth:
            return auth
    val = request.query_params.get("token")
    if val:
        return val.strip()
    return ""


def _can_dang_nhap(request: Request):
    """Tra ve (token, phien_hop_le)."""
    token = _lay_token(request)
    return token, PHIEN.co_hieu_luc(token)


def _loi(noi_dung: str, ma: int = 400):
    return JSONResponse({"ok": False, "loi": noi_dung}, status_code=ma)


# ------------------------------------------------------------------ nguoi quen
# Ten nguoi quen duoc dung de TAO THU MUC (known_faces/<Ten>) => phai chan
# path traversal that, khong chi tin vao viec sanitize roi.
# Chi cho phep: chu cai (A-Z a-z), so (0-9), khoang trang, gach duoi.
# Dai 1-40 ky tu, ky tu dau khong phai khoang trang.
_TEN_NGUOI_QUEN_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_ ]{0,39}$")

# FaceEngine da nap trong phien (dung cho lenh reload_known).
_KHOA_ENGINE = threading.Lock()
_ENGINE = {"gia_tri": None, "dang_nap": False, "xong": False, "loi": ""}


def _ten_nguoi_quen_hop_le(ten: str) -> tuple[bool, str]:
    """Kiem tra ten nguoi quen (dung de tao thu muc).
    Tra (hop_le, thong_bao tieng Viet).
    """
    ten = (ten or "").strip()
    if not ten:
        return False, "Chưa nhập tên người quen."
    if len(ten) > 40:
        return False, "Tên người quen quá dài (tối đa 40 ký tự)."
    if ".." in ten or "/" in ten or "\\" in ten or "\x00" in ten:
        return False, (
            "Tên người quen không được chứa '..', dấu '/' hoặc dấu '\\'."
        )
    if not _TEN_NGUOI_QUEN_RE.match(ten):
        return False, (
            "Tên người quen chỉ được dùng chữ cái, số, khoảng trắng và gạch dưới "
            "(1–40 ký tự)."
        )
    if not any(c.isascii() and c.isalnum() for c in ten):
        return False, "Tên người quen phải có ít nhất một chữ cái hoặc số."
    return True, ""


def _thu_muc_nguoi_quen(ten: str) -> str:
    """Tra thu muc known_faces/<ten> sau khi kiem tra duong dan that.
    Nem ValueError neu duong dan tro ra ngoai known_faces.
    """
    goc = os.path.abspath(THU_MUC_KHUON_MAT)
    thu_muc = os.path.abspath(os.path.join(goc, ten))
    # 1) ten phai la mot thanh phu don le
    if os.path.basename(thu_muc) != ten:
        raise ValueError("Tên người quen chứa đường dẫn (không hợp lệ).")
    # 2) cha cua thu muc phai dung known_faces
    if os.path.dirname(thu_muc) != goc:
        raise ValueError("Tên người quen trỏ ra ngoài thư mục known_faces.")
    # 3) kiem tra lai bang chuoi tien to (defense in depth)
    if not thu_muc.startswith(goc + os.sep):
        raise ValueError("Tên người quen trỏ ra ngoài thư mục known_faces.")
    return thu_muc


def _duoi_anh_tu_noi_dung(du_lieu: bytes) -> str:
    """Doan duoi tep tu magic bytes. Tra '' neu khong phai anh."""
    if du_lieu[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if du_lieu[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if du_lieu[:2] == b"BM":
        return ".bmp"
    if du_lieu[:4] == b"RIFF" and du_lieu[8:12] == b"WEBP":
        return ".webp"
    return ""


def _danh_sach_nguoi_quen() -> list[dict]:
    """Danh sach nguoi da hoc (thu muc con trong known_faces)."""
    ds: list[dict] = []
    if not os.path.isdir(THU_MUC_KHUON_MAT):
        return ds
    for ten in sorted(os.listdir(THU_MUC_KHUON_MAT)):
        thu_muc = os.path.join(THU_MUC_KHUON_MAT, ten)
        if not os.path.isdir(thu_muc):
            continue
        anh = [
            f for f in sorted(os.listdir(thu_muc))
            if os.path.splitext(f)[1].lower() in DUOI_ANH_CHAP_NHAN
        ]
        ds.append(
            {
                "ten": ten,
                "so_anh": len(anh),
                "thu_muc": thu_muc,
                "anh": anh,
            }
        )
    return ds


def _engine_khuon_mat():
    """Tra FaceEngine da nap trong phien (None neu chua nap)."""
    with _KHOA_ENGINE:
        return _ENGINE["gia_tri"]


def _nap_engine_khuon_mat() -> bool:
    """Nap FaceEngine 1 lan (thread nen) de dung lenh reload_known trong phien.
    Tra True neu da nap xong, False neu vua bat dau nap.
    """
    with _KHOA_ENGINE:
        if _ENGINE["gia_tri"] is not None:
            return True
        if _ENGINE["dang_nap"]:
            return False
        _ENGINE["dang_nap"] = True
        _ENGINE["loi"] = ""

    def _viec() -> None:
        try:
            import face_engine

            engine = face_engine.FaceEngine(faces_dir=THU_MUC_KHUON_MAT)
            with _KHOA_ENGINE:
                _ENGINE["gia_tri"] = engine
                _ENGINE["xong"] = True
        except Exception as exc:                     # noqa: BLE001
            with _KHOA_ENGINE:
                _ENGINE["loi"] = str(exc)
        finally:
            with _KHOA_ENGINE:
                _ENGINE["dang_nap"] = False

    threading.Thread(
        target=_viec, daemon=True, name="camai-web-engine"
    ).start()
    return False


def _cho_engine_khuon_mat(giay_toi_da: float = 120.0) -> bool:
    """Cho mot lan nap FaceEngine hoan tat. Tra True neu thanh cong."""
    het = time.time() + giay_toi_da
    while time.time() < het:
        if _engine_khuon_mat() is not None:
            return True
        with _KHOA_ENGINE:
            loi = _ENGINE["loi"]
        if loi:
            return False
        time.sleep(0.4)
    return False


def _reload_nguoi_quen(cho_nap: bool = True) -> tuple[int, str]:
    """Doc lai danh sach nguoi quen cho model.
    - model da nap  -> goi face_engine.reload_known() that.
    - model chua nap -> chi ghi nhan (lan phan tich sau se nap).
    Tra (so_nguoi, thong_bao tieng Viet).
    """
    if _engine_khuon_mat() is None:
        if not cho_nap:
            return len(_danh_sach_nguoi_quen()), (
                "Đã lưu ảnh. Model chưa nạp nên người mới sẽ được nhận diện "
                "ở lần phân tích sau."
            )
        _nap_engine_khuon_mat()
        if not _cho_engine_khuon_mat(120.0):
            with _KHOA_ENGINE:
                loi = _ENGINE["loi"]
            return len(_danh_sach_nguoi_quen()), (
                "Không nạp được model nhận diện (%s). Người mới sẽ được nạp "
                "ở lần phân tích sau." % (loi or "hết thời gian chờ")
            )
    engine = _engine_khuon_mat()
    try:
        engine.reload_known(THU_MUC_KHUON_MAT)
    except Exception as exc:                         # noqa: BLE001
        return len(_danh_sach_nguoi_quen()), (
            "Không đọc lại được danh sách người quen: %s" % exc
        )
    return len(engine.known), (
        "Đã đọc lại %d người trong model." % len(engine.known)
    )


# ---------------------------------------------------------------------- vung
def _kich_thuoc_video(duong_dan: str) -> tuple[int, int]:
    """Tra (rong, cao) cua video theo khung hinh that. (0, 0) neu khong doc duoc."""
    if not duong_dan or not os.path.isfile(duong_dan):
        return 0, 0
    try:
        import cv2
    except Exception:                                # noqa: BLE001
        return 0, 0
    cap = cv2.VideoCapture(duong_dan)
    try:
        if not cap.isOpened():
            return 0, 0
        rong = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        cao = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        return rong, cao
    finally:
        cap.release()


def _ghi_file_vung(x1: float, y1: float, x2: float, y2: float) -> str:
    """Ghi vung.txt theo DUNG format cam_ai_core.load_zone doc:
       - bo qua dong rong va dong bat dau bang '#'
       - dong du lieu: 4 so thuc tach nhau bang dau cach
       - toa do TUONG DOI 0..1 (core tu doi sang pixel theo khung hinh)
    """
    noi_dung = (
        "# CamAI - vung canh (ve tren man hinh web)\n"
        "# Toa do tuong doi 0.0 - 1.0, dung chung cho moi video\n"
        "%.4f %.4f %.4f %.4f\n" % (x1, y1, x2, y2)
    )
    with open(FILE_VUNG_MAC_DINH, "w", encoding="utf-8", newline="\n") as f:
        f.write(noi_dung)
    return noi_dung


def _doc_file_vung(duong_dan: str) -> tuple[float, float, float, float] | None:
    """Doc vung.txt y giong het cam_ai_core.load_zone (tuong doi 0..1)."""
    if not os.path.isfile(duong_dan):
        return None
    with open(duong_dan, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 4:
            continue
        try:
            x1, y1, x2, y2 = (float(v) for v in parts)
        except ValueError:
            continue
        return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
    return None



def _tra_file_range(
    request: Request,
    duong_dan: str,
    ten: str,
    kieu: str,
    inline: bool = False,
):
    """Tra file, co ho tro Range (206 Partial Content).

    Safari/iOS CHI phat video khi server tra 206 + header Content-Range.
    Khong co Range -> tra 200 binh thuong nhung van giu header Accept-Ranges.
    """
    if not os.path.isfile(duong_dan):
        return _loi("Không tìm thấy tệp: " + ten)
    kich_thuoc = os.path.getsize(duong_dan)
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
        "Content-Disposition": '%s; filename="%s"'
        % ("inline" if inline else "attachment", ten),
    }
    yeu_cau = request.headers.get("range") or ""
    yeu_cau = yeu_cau.strip()
    mau = re.match(r"^bytes=(\d*)-(\d*)$", yeu_cau) if yeu_cau else None
    if mau:
        dau = mau.group(1)
        cuoi = mau.group(2)
        if dau == "" and cuoi == "":
            mau = None
        else:
            if dau == "":
                do_dai = int(cuoi)
                dau = max(0, kich_thuoc - do_dai)
                cuoi = kich_thuoc - 1
            else:
                dau = int(dau)
                cuoi = int(cuoi) if cuoi != "" else kich_thuoc - 1
            if dau >= kich_thuoc or dau < 0:
                return Response(
                    status_code=416,
                    headers={"Content-Range": "bytes */%d" % kich_thuoc},
                )
            cuoi = min(cuoi, kich_thuoc - 1)
            do_dai = cuoi - dau + 1
            headers["Content-Range"] = "bytes %d-%d/%d" % (dau, cuoi, kich_thuoc)
            headers["Content-Length"] = str(do_dai)

            def dong_luong():
                with open(duong_dan, "rb") as f:
                    f.seek(dau)
                    con = do_dai
                    while con > 0:
                        khoi = f.read(min(262144, con))
                        if not khoi:
                            break
                        con -= len(khoi)
                        yield khoi

            return StreamingResponse(
                dong_luong(), status_code=206, media_type=kieu, headers=headers
            )
    return FileResponse(duong_dan, media_type=kieu, headers=headers)


def _duong_dan_an_toan(duong_dan: str) -> tuple[bool, str]:
    """Chi cho phep doc video nam trong thu muc ung dung hoac tep da upload."""
    duong_dan = str(duong_dan or "").strip()
    if not duong_dan:
        return False, "Chưa chọn video."
    if str(duong_dan).strip() == "0":
        return False, "Web không dùng webcam được, hãy chọn video."
    if os.path.isabs(duong_dan):
        duong_dan = os.path.normpath(duong_dan)
    else:
        duong_dan = os.path.normpath(os.path.join(APP_DIR, duong_dan))
    with _KHOA_UPLOAD:
        da_upload = os.path.abspath(duong_dan) in _TEP_DA_UPLOAD
    goc = os.path.abspath(duong_dan)
    if not da_upload and not goc.startswith(os.path.abspath(APP_DIR) + os.sep):
        return False, "Đường dẫn video không nằm trong thư mục phần mềm."
    if not os.path.isfile(goc):
        return False, "Không tìm thấy video: " + os.path.basename(goc)
    return True, goc


class _DangNhap(BaseModel):
    mat_khauu: str = ""


# HOP DONG BODY CUA POST /api/phan-tich
# --------------------------------------
# MOI (web-first): body JSON PHANG chua BAT KY field nao cua
# `cam_ai_core.AnalysisConfig` (xem GET /api/cau-hinh de lay danh sach day du):
#   input, output, no_face, faces_dir, model, thiet_bi, conf, face_every,
#   face_threshold, min_face, pixelate, vung, vung_nhay, vung_max, canh_lau,
#   tu_luu_clip, clip_giay, clip_ghi_tat_ca, nhan_vat_the, lop, tach_o,
#   bat_canh_bao, canh_bao_mo_phong, canh_bao_go, canh_bao_gioi_han,
#   show_box, show_label, show_line, doc_bien_so, bien_so_dir, bien_so_tin_cay,
#   bien_so_nhoan_lai_giay, vung_bien_so, tu_chup_dir, tu_chup_nhoan_lai_giay,
#   dem_phuong_tien, lop_phuong_tien.
#   Field la -> bo qua (khong crash). Sai kieu -> ep kieu hop le hoac bo qua.
#
# CU (UI web truoc) -> VAN CHAY NGUYEN:
#   duong_dan, nhan_mat, dem_ra_vao, luu_clip, vat_the, canh_vung, ve_khung,
#   ve_nhan, lam_mo, nguong_mat, file_vung, vung_max, canh_lau, clip_giay, lop.
#   (mapping xem `_KHOA_CU` va `_KHOA_CU_SO` trong file nay)


# ------------------------------------------------------------------ trang
def _html_giao_dien_web() -> str:
    """Tra HTML cua UI moi (giao_dien_web/index.html) neu co; khong co -> UI cu."""
    duong_dan = os.path.join(THU_MUC_GIAO_DIEN_WEB, "index.html")
    if os.path.isfile(duong_dan):
        try:
            with open(duong_dan, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            pass
    return _trang_web()


@app.get("/", response_class=HTMLResponse)
def trang_chinh(request: Request):
    # Khong cho trinh duyet cache lai trang: luon tai ban moi nhat.
    response = HTMLResponse(_html_giao_dien_web(), headers={"Cache-Control": "no-store"})
    return response


@app.get("/giao-dien-cu", response_class=HTMLResponse)
def trang_giao_dien_cu(request: Request):
    """UI WEB CU (HTML_TRANG) - giu de khong pha lien ket cua ban da dung.

    API cu van chay nguyen tren cac route goc.
    """
    response = HTMLResponse(_trang_web(), headers={"Cache-Control": "no-store"})
    return response


@app.get("/api/trang-thai")
def api_trang_thai(request: Request):
    """Endpoint nhanh: chi doc bien, khong cham vao pipeline."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return JSONResponse({"ok": False, "loi": "Chưa đăng nhập."}, status_code=401)
    du_lieu = TT.ban_trang_thai()
    du_lieu["ok"] = True
    return JSONResponse(du_lieu)


@app.get("/api/cau-hinh")
def api_cau_hinh(request: Request):
    """Mo ta TOAN BO tham so cua `AnalysisConfig` cho UI tu dung control.

    Tra ve 12 nhom (giong 12 muc con cua GUI) + moi field: ten, nhan, mo_ta,
    kieu (bool | so | chuoi | duong_dan), gia tri mac dinh, va toi_thieu /
    toi_da / buc voi field so.
    """
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    return JSONResponse({"ok": True, "nhom": _mo_ta_cau_hinh()})


@app.get("/api/ket-qua")
def api_ket_qua(request: Request):
    """Ket qua cuoi cung cua lan phan tich vua roi (hop dong moi 17 truong)."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        ket_qua = TT.ket_qua_day_du
    co_ket_qua = bool(ket_qua)
    du_lieu = {"ok": True, "co_ket_qua": co_ket_qua}
    du_lieu.update(ket_qua if ket_qua else _KET_QUA_RONG)
    return JSONResponse(du_lieu)


@app.get("/api/anh-su-kien")
def api_anh_su_kien(request: Request):
    """Danh sach anh tu chup da luu (duong dan + thoi gian)."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        danh_sach = list(TT.anh_su_kien)
    return JSONResponse(
        {"ok": True, "danh_sach": danh_sach, "so_anh": len(danh_sach)}
    )


@app.get("/api/bien-so")
def api_bien_so(request: Request):
    """Danh sach bien so da doc duoc (text, confidence, frame)."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        danh_sach = list(TT.bien_so)
        if not danh_sach and TT.ket_qua_day_du:
            danh_sach = [
                {"text": str(x), "confidence": None, "frame": None}
                for x in (TT.ket_qua_day_du.get("bien_so") or [])
            ]
    return JSONResponse(
        {"ok": True, "danh_sach": danh_sach, "so_bien_so": len(danh_sach)}
    )


@app.get("/api/video-mau")
def api_video_mau(request: Request):
    token, ok = _can_dang_nhap(request)
    if not ok:
        return JSONResponse({"ok": False, "loi": "Chưa đăng nhập."}, status_code=401)
    danh_sach = [
        {
            "ten": ten,
            "file": ten_file,
            "duong_dan": os.path.join(THU_MUC_VIDEO_MAU, ten_file),
            "co_that": os.path.isfile(os.path.join(THU_MUC_VIDEO_MAU, ten_file)),
        }
        for ten, ten_file in VIDEO_MAU
    ]
    return JSONResponse({"ok": True, "video_mau": danh_sach})


@app.get("/api/anh-nen")
def api_anh_nen(request: Request):
    """Khung hinh moi nhat (image/jpeg) - de dien thoai xem live view.

    Thu tu: khung hinh pipeline (frame_cb) -> video ket qua -> anh placeholder.
    """
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    du_lieu = ANH_NEN.lay()
    if not du_lieu:
        with TT.khoa:
            duong_dan = ""
            if TT.ket_qua and TT.thu_muc_ket_qua:
                duong_dan = os.path.join(TT.thu_muc_ket_qua, TT.ket_qua.get("video_ket_qua", ""))
        if duong_dan:
            du_lieu = VIDEO_CUOI.lay(duong_dan)
    if not du_lieu:
        du_lieu = _anh_placeholder()
    if not du_lieu:
        return _loi("Không tạo được ảnh nền.", 500)
    return Response(
        content=du_lieu,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store", "Content-Length": str(len(du_lieu))},
    )


@app.get("/api/quet-camera")
def api_quet_camera(request: Request):
    """Quet camera tren may (dung cam_ai_core.quet_camera)."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    danh_sach: list[dict] = []
    try:
        from cam_ai_core import quet_camera

        for muc in quet_camera():
            rong = bool(muc.get("mo_duoc"))
            danh_sach.append(
                {
                    "index": int(muc.get("index", 0) or 0),
                    "ten": str(muc.get("ten", "") or ""),
                    "do_phan_giai": (
                        "%dx%d" % (int(muc.get("width", 0) or 0), int(muc.get("height", 0) or 0))
                        if rong
                        else ""
                    ),
                    "mo_duoc": rong,
                    "width": int(muc.get("width", 0) or 0),
                    "height": int(muc.get("height", 0) or 0),
                    "fps": round(float(muc.get("fps", 0.0) or 0.0), 2),
                    "backend": str(muc.get("backend", "") or ""),
                }
            )
    except Exception as exc:                        # noqa: BLE001
        _in("[LOI] quet camera: %s" % exc)
    return JSONResponse({"ok": True, "danh_sach": danh_sach})


@app.get("/api/lop-viet")
def api_lop_viet(request: Request):
    """Danh sach 80 lop COCO (id, ten tieng Anh, ten tieng Viet)."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    danh_sach: list[dict] = []
    try:
        from lop_viet import DANH_SACH_LOP_VIET

        for cid, ten_anh, ten_viet in DANH_SACH_LOP_VIET():
            danh_sach.append(
                {"id": int(cid), "ten_anh": str(ten_anh), "ten_viet": str(ten_viet)}
            )
    except Exception as exc:                        # noqa: BLE001
        _in("[LOI] doc lop viet: %s" % exc)
    return JSONResponse({"ok": True, "danh_sach": danh_sach})


@app.post("/api/dang-nhap")
def api_dang_nhap(request: Request, du_lieu: _DangNhap):
    ip = _ip(request)
    con_khoa = PHIEN.con_bi_khoa(ip)
    if con_khoa:
        return _loi(
            "Bạn đã nhập sai mật khẩu quá nhiều lần. Vui lòng thử lại sau %d giây."
            % con_khoa,
            429,
        )
    if not PHIEN.khop_mat_khau(du_lieu.mat_khauu):
        so_lan, giay = PHIEN.ghi_sai(ip)
        if so_lan:
            _in(
                "[BAO] Dung %s thử sai mật khẩu %d lần liên tiếp. "
                "Khoá đăng nhập trong %d phút." % (ip, so_lan, giay // 60)
            )
            return _loi(
                "Sai mật khẩu %d lần. Tài khoản bị khoá trong %d phút."
                % (so_lan, giay // 60),
                429,
            )
        return _loi("Mật khẩu không đúng.")
    PHIEN.xoa_sai(ip)
    token, giay = PHIEN.cap_phien()
    _in("[OK] %s đã đăng nhập." % ip)
    # Tra them `token` de UI moi (dien thoai) luu vao localStorage roi gui
    # kem vao request sau. Cookie van duoc dat nhu cu (UI cu van chay).
    response = JSONResponse(
        {"ok": True, "token": token, "het_han_gio": HET_HAN_PHIEN_GIO}
    )
    response.set_cookie(
        TEN_COOKIE, token, max_age=giay, httponly=True, samesite="lax", path="/"
    )
    return response


@app.post("/api/dang-xuat")
def api_dang_xuat(request: Request):
    PHIEN.huy_phien(request.cookies.get(TEN_COOKIE))
    response = JSONResponse({"ok": True})
    response.delete_cookie(TEN_COOKIE, path="/")
    return response


@app.post("/api/tai-video")
async def api_tai_video(request: Request, file: UploadFile = File(...)):
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)

    ten_goc = os.path.basename(file.filename or "")
    duoi = os.path.splitext(ten_goc)[1].lower()
    if duoi not in DUOI_VIDEO_CHAP_NHAN:
        return _loi(
            "Định dạng tệp không hợp lệ (chỉ nhận %s)."
            % ", ".join(d[1:] for d in DUOI_VIDEO_CHAP_NHAN)
        )

    os.makedirs(THU_MUC_UPLOAD, exist_ok=True)
    # Ten file sinh tu UUID: KHONG dung ten nguoi gui len (tranh path traversal).
    duong_dan = os.path.join(THU_MUC_UPLOAD, uuid.uuid4().hex + duoi)
    kich_thuoc = 0
    with open(duong_dan, "wb") as f:
        while True:
            khoi = await file.read(1024 * 1024)
            if not khoi:
                break
            kich_thuoc += len(khoi)
            if kich_thuoc > KICH_THUOC_TAI_TOI_DA:
                f.close()
                _xoa_tam(duong_dan)
                return _loi(
                    "Tệp quá lớn (tối đa %d MB)."
                    % (KICH_THUOC_TAI_TOI_DA // (1024 * 1024))
                )
            f.write(khoi)

    if kich_thuoc == 0:
        _xoa_tam(duong_dan)
        return _loi("Tệp rỗng, không có dữ liệu video.")

    # Kiem tra co that la video khong (OpenCV doc duoc hay khong).
    import cv2

    cap = cv2.VideoCapture(duong_dan)
    duoc = bool(cap.isOpened())
    if duoc:
        duoc = cap.read()[0]
    cap.release()
    if not duoc:
        _xoa_tam(duong_dan)
        return _loi("Tệp tải lên không phải video hợp lệ (không đọc được khung hình).")

    with _KHOA_UPLOAD:
        _TEP_DA_UPLOAD.add(os.path.abspath(duong_dan))
    return JSONResponse(
        {
            "ok": True,
            "duong_dan": duong_dan,
            "ten": os.path.basename(ten_goc),
            "dung_luong_mb": round(kich_thuoc / (1024 * 1024), 2),
        }
    )


# ------------------------------------------------------------------ nguoi quen
@app.get("/api/nguoi-quen")
def api_danh_sach_nguoi_quen(request: Request):
    """Danh sach nguoi da hoc (thu muc con trong known_faces)."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    ds = _danh_sach_nguoi_quen()
    return JSONResponse(
        {
            "ok": True,
            "so_nguoi": len(ds),
            "danh_sach": ds,
            "model_da_nap": _engine_khuon_mat() is not None,
        }
    )


@app.post("/api/nguoi-quen")
async def api_dang_ky_nguoi_quen(
    request: Request,
    ten: str = File(default=""),
    anh: UploadFile | None = File(default=None),
):
    """Dang ky nguoi quen. multipart/form-data: `ten` (text) + `anh` (file anh).

    Anh duoc luu vao known_faces/<Ten>/<gio>.jpg va model duoc doc lai
    (face_engine.reload_known) neu model da nap trong phien.
    """
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)

    ten = (ten or "").strip()
    hop_le, loi = _ten_nguoi_quen_hop_le(ten)
    if not hop_le:
        return _loi(loi, 400)
    if anh is None:
        return _loi("Chưa chọn ảnh khuôn mặt.", 400)
    try:
        thu_muc = _thu_muc_nguoi_quen(ten)
    except ValueError as exc:
        return _loi(str(exc), 400)

    du_lieu = await anh.read(KICH_THUOC_ANH_NGUOI_QUEN_TOI_DA + 1)
    if not du_lieu:
        return _loi("Tệp ảnh rỗng, không có dữ liệu.", 400)
    if len(du_lieu) > KICH_THUOC_ANH_NGUOI_QUEN_TOI_DA:
        return _loi(
            "Ảnh quá lớn (tối đa %d MB)."
            % (KICH_THUOC_ANH_NGUOI_QUEN_TOI_DA // (1024 * 1024)),
            400,
        )
    duoi = _duoi_anh_tu_noi_dung(du_lieu)
    if not duoi:
        return _loi(
            "Tệp tải lên không phải ảnh hợp lệ (jpg/png/bmp/webp).", 400
        )

    if (
        not os.path.isdir(thu_muc)
        and len(_danh_sach_nguoi_quen()) >= SO_NGUOI_QUEN_TOI_DA
    ):
        return _loi(
            "Đã đạt giới hạn %d người quen." % SO_NGUOI_QUEN_TOI_DA, 400
        )

    os.makedirs(thu_muc, exist_ok=True)
    ten_anh = "%s_%s%s" % (
        datetime.now().strftime("%Y%m%d_%H%M%S"),
        uuid.uuid4().hex[:6],
        duoi,
    )
    duong_dan = os.path.join(thu_muc, ten_anh)
    # Kiem tra lai duong dan (defense in depth): phai nam trong thu muc nguoi quen
    if os.path.dirname(os.path.abspath(duong_dan)) != os.path.abspath(thu_muc):
        return _loi("Không lưu được ảnh (đường dẫn không hợp lệ).", 400)
    with open(duong_dan, "wb") as f:
        f.write(du_lieu)

    so_anh = len(
        [
            f for f in os.listdir(thu_muc)
            if os.path.splitext(f)[1].lower() in DUOI_ANH_CHAP_NHAN
        ]
    )
    # Neu model chua nap: chi ghi nhan, lan phan tich sau se nap (khong block UI).
    so_nguoi, thong_bao = _reload_nguoi_quen(cho_nap=False)
    if _engine_khuon_mat() is None:
        _nap_engine_khuon_mat()
    TT.ghi_log("[web] Đăng ký người quen '%s' (%d ảnh)." % (ten, so_anh))
    return JSONResponse(
        {
            "ok": True,
            "ten": ten,
            "so_anh": so_anh,
            "thu_muc": thu_muc,
            "file_anh": ten_anh,
            "so_nguoi": so_nguoi,
            "thong_bao": thong_bao,
        }
    )


@app.post("/api/nguoi-quen-tai-lai")
def api_doc_lai_nguoi_quen(request: Request):
    """Doc lai nguoi da hoc: nap lai model (face_engine.reload_known) roi tra danh sach."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    so_nguoi, thong_bao = _reload_nguoi_quen(cho_nap=True)
    ds = _danh_sach_nguoi_quen()
    return JSONResponse(
        {
            "ok": True,
            "so_nguoi": so_nguoi,
            "danh_sach": ds,
            "thong_bao": thong_bao,
            "model_da_nap": _engine_khuon_mat() is not None,
        }
    )


# ---------------------------------------------------------------------- vung
@app.post("/api/vung")
async def api_luu_vung(request: Request):
    """Luu vung canh ve tren man hinh.

    Body JSON: {"x1":.., "y1":.., "x2":.., "y2":..} (toa do tuong doi 0..1)
    hoac {"vung": "x1,y1,x2,y2"}.
    Ghi vao vung.txt theo dung format cam_ai_core.load_zone doc.
    """
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    try:
        body = await request.json()
    except Exception:                                 # noqa: BLE001
        body = {}
    if not isinstance(body, dict):
        body = {}

    gia_tri = [body.get("x1"), body.get("y1"), body.get("x2"), body.get("y2")]
    if any(v is None for v in gia_tri):
        chuoi = str(body.get("vung") or "").strip()
        if chuoi:
            gia_tri = [
                p for p in chuoi.replace(";", ",").split(",") if p.strip() != ""
            ]
    if len(gia_tri) != 4:
        return _loi("Cần đủ 4 toạ độ x1, y1, x2, y2 (từ 0 đến 1).", 400)
    try:
        x1, y1, x2, y2 = (float(v) for v in gia_tri)
    except (TypeError, ValueError):
        return _loi("Toạ độ phải là số.", 400)
    for gia in (x1, y1, x2, y2):
        if gia < 0.0 or gia > 1.0:
            return _loi("Toạ độ phải nằm trong khoảng 0 đến 1.", 400)
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    if x2 - x1 < 0.01 or y2 - y1 < 0.01:
        return _loi("Vùng quá nhỏ, hãy vẽ vùng lớn hơn.", 400)

    # Video tham chieu: body -> video dang chay -> video mau.
    ten_video = str(body.get("video") or body.get("input") or "").strip()
    duong_video = ""
    if ten_video:
        hieu_luc, duong_video = _duong_dan_an_toan(ten_video)
        if not hieu_luc:
            duong_video = ""
    if not duong_video:
        with TT.khoa:
            duong_video = TT.tep or ""
    if not duong_video or not os.path.isfile(duong_video):
        duong_video = os.path.join(THU_MUC_VIDEO_MAU, "people-detection.mp4")
    rong, cao = _kich_thuoc_video(duong_video)

    noi_dung = _ghi_file_vung(x1, y1, x2, y2)
    doc_duoc = _doc_file_vung(FILE_VUNG_MAC_DINH)
    toa_do_px = {}
    if rong > 0 and cao > 0:
        toa_do_px = {
            "x1": int(x1 * rong), "y1": int(y1 * cao),
            "x2": int(x2 * rong), "y2": int(y2 * cao),
        }
    TT.ghi_log(
        "[web] Lưu vùng: %.4f,%.4f -> %.4f,%.4f (file %s)"
        % (x1, y1, x2, y2, os.path.basename(FILE_VUNG_MAC_DINH))
    )
    return JSONResponse(
        {
            "ok": True,
            "vung_file": FILE_VUNG_MAC_DINH,
            "toa_do_px": toa_do_px,
            "toa_do_tuong_doi": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "kich_thuoc_video": {"rong": rong, "cao": cao},
            "video": duong_video,
            "noi_dung_file": noi_dung,
            "doc_duoc": list(doc_duoc) if doc_duoc else None,
            "thong_bao": (
                "Đã lưu vùng vào %s." % os.path.basename(FILE_VUNG_MAC_DINH)
            ),
        }
    )


# ------------------------------------------------------------------ canh bao
@app.post("/api/thu-canh-bao")
def api_thu_canh_bao(request: Request):
    """Thu 1 canh bao o che do CHI THU (mo_phong=True) -> KHONG gui ra ngoai."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    try:
        from canh_bao import CanhBao
    except Exception as exc:                         # noqa: BLE001
        return _loi("Không nạp được module cảnh báo: %s" % exc, 500)

    # mo_phong=True + tat het kenh -> chi tao noi_dung, khong gui gi ra ngoai.
    cb = CanhBao(
        mo_phong=True,
        bat_telegram=False,
        bat_chuong=False,
        hien_hop_thoai=False,
        in_thong_bao=False,
    )
    chi_tiet = {
        "video": "Thử cảnh báo từ giao diện web",
        "so_nguoi": 3,
        "mo_ta": "Đây là cảnh báo thử nghiệm (không gửi ra ngoài).",
    }
    thanh_cong = cb.guii("co_nguoi_vao_vung", chi_tiet)
    ket_qua = getattr(cb, "ket_qua_gan_nhat", {}) or {}
    noi_dung = str(ket_qua.get("noi_dung") or "")
    return JSONResponse(
        {
            "ok": True,
            "noi_dung": noi_dung,
            "mo_phong": True,
            "da_gui_thuc": False,
            "hanh_dong": str(ket_qua.get("hanh_dong") or ""),
            "thanh_cong": bool(thanh_cong),
            "thong_bao": "Đã tạo cảnh báo thử (không gửi ra ngoài).",
        }
    )


# ------------------------------------------------------------- thong tin may
def _ram_may() -> dict:
    """RAM dang dung. Dung psutil neu co, khong co thi dung Windows API."""
    try:
        import psutil

        bo = psutil.virtual_memory()
        return {
            "tong_mb": int(bo.total / (1024 * 1024)),
            "dung_mb": int(bo.used / (1024 * 1024)),
            "con_trong_mb": int(bo.available / (1024 * 1024)),
            "ty_le": int(bo.percent),
        }
    except Exception:                                # noqa: BLE001
        pass
    try:
        import ctypes

        class _TrangThai(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        tt = _TrangThai()
        tt.dwLength = ctypes.sizeof(_TrangThai)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(tt))
        return {
            "tong_mb": int(tt.ullTotalPhys / (1024 * 1024)),
            "dung_mb": int((tt.ullTotalPhys - tt.ullAvailPhys) / (1024 * 1024)),
            "con_trong_mb": int(tt.ullAvailPhys / (1024 * 1024)),
            "ty_le": int(tt.dwMemoryLoad),
        }
    except Exception:                                # noqa: BLE001
        return {}


def _ten_gpu() -> tuple[str, int]:
    """Ten GPU + VRAM (MB). Uu tien torch da nap, khong co thi dung nvidia-smi."""
    torch = sys.modules.get("torch")
    if torch is not None:
        try:
            if torch.cuda.is_available():
                return (
                    torch.cuda.get_device_name(0),
                    int(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)),
                )
        except Exception:                            # noqa: BLE001
            pass
    try:
        import subprocess

        ket = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
        dong = (ket.stdout or "").strip().splitlines()
        if dong:
            ten, _, vram = dong[0].partition(",")
            return ten.strip(), int(float(vram.strip() or 0))
    except Exception:                                # noqa: BLE001
        pass
    return "", 0


@app.get("/api/thong-tin-model")
def api_thong_tin_model(request: Request):
    """Thong tin model AI dang dung (dung lai dung ham cua model_info)."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    try:
        # Nap face_engine TRUOC model_info: face_engine chuan bi DLL CUDA cho
        # torch, onnxruntime phai duoc import sau de dung duoc GPU.
        import face_engine                          # noqa: F401
        import model_info
    except Exception as exc:                         # noqa: BLE001
        return _loi("Không nạp được thông tin model: %s" % exc, 500)
    try:
        bang = model_info.bang_tt_tong_hop()
        phien_ban = model_info.lay_phien_ban()
    except Exception as exc:                         # noqa: BLE001
        return _loi("Không lấy được thông tin model: %s" % exc, 500)
    return JSONResponse(
        {
            "ok": True,
            "models": bang,
            "phien_ban": phien_ban,
            "so_model": len(bang),
            "co_gpu": bool(phien_ban.get("cuda")),
        }
    )


@app.get("/api/thong-tin-thiet-bi")
def api_thong_tin_thiet_bi(request: Request):
    """CPU / GPU / RAM cua may dang chay phan mem."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    import platform

    try:
        import face_engine                          # noqa: F401
        import model_info

        phien_ban = model_info.lay_phien_ban()
    except Exception:                                # noqa: BLE001
        phien_ban = {}
    ten_gpu, vram = _ten_gpu()
    providers = []
    ort = sys.modules.get("onnxruntime")
    if ort is not None:
        try:
            providers = list(ort.get_available_providers())
        except Exception:                            # noqa: BLE001
            providers = []
    return JSONResponse(
        {
            "ok": True,
            "he_dieu_hanh": platform.system() + " " + platform.release(),
            "may": platform.machine(),
            "bo_vi_xu_lien": platform.processor() or "Không rõ",
            "so_lan_cpu": os.cpu_count() or 1,
            "python": platform.python_version(),
            "ram": _ram_may(),
            "gpu": {
                "co_gpu": bool(phien_ban.get("cuda")) or bool(ten_gpu),
                "ten_gpu": ten_gpu,
                "vram_mb": vram,
                "providers": providers,
            },
            "phien_ban": phien_ban,
        }
    )


@app.post("/api/phan-tich")
async def api_phan_tich(request: Request):
    """Bat dau phan tich. Body JSON phang chua field cua `AnalysisConfig`.

    HOP DONG MOI (web-first): gui BAT KY field nao cua `AnalysisConfig`
    (`conf`, `nhan_vat_the`, `lop`, `doc_bien_so`, `dem_phuong_tien`,
    `vung_max`, `canh_lau`, `tu_luu_clip`, `face_threshold`, `clip_giay`...).
    Field la -> bo qua (khong crash). Sai kieu -> ep kieu hop le hoac bo qua.
    HOP DONG CU (UI web truoc): `duong_dan`, `nhan_mat`, `dem_ra_vao`,
    `luu_clip`, `vat_the`, `canh_vung`, `ve_khung`, `ve_nhan`, `lam_mo`,
    `nguong_mat`, `file_vung`, `vung_max`, `canh_lau`, `clip_giay`, `lop`
    -> VAN CHAY NGUYEN.

    Route tra ve NGAY; phan nang (import torch + pipeline) chay o thread nen.
    """
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)

    try:
        body = await request.json()
    except Exception:                                     # noqa: BLE001
        body = {}
    if not isinstance(body, dict):
        return _loi("Body phải là JSON object.")

    with TT.khoa:
        if TT.dang_chay:
            return _loi(
                "Phần mềm đang phân tích video '%s'. "
                "Vui lòng đợi xong hoặc bấm “Dừng” trước khi chạy video mới."
                % TT.tieu_de,
                409,
            )

    # Nguon vao: field moi `input` hoac khoa cu `duong_dan`.
    ten_nguon = str(body.get("input") or body.get("duong_dan") or "").strip()
    hieu_luc, duong_dan = _duong_dan_an_toan(ten_nguon)
    if not hieu_luc:
        return _loi(duong_dan)

    thu_muc_kq = os.path.join(THU_MUC_KET_QUA, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(thu_muc_kq, exist_ok=True)

    # File vung: khoa cu (canh_vung + file_vung) hoac field moi `vung`.
    # Tu dong gan file vung da luu (nguoi dung vua ve vung tren man hinh web)
    # khi body KHONG noi ro gi ve vung.
    if (
        not str(body.get("vung") or "").strip()
        and not str(body.get("file_vung") or "").strip()
        and "canh_vung" not in body
        and os.path.isfile(FILE_VUNG_MAC_DINH)
    ):
        body = dict(body)
        body["vung"] = FILE_VUNG_MAC_DINH
        body.pop("canh_vung", None)
        TT.ghi_log(
            "[web] Tự động gắn vùng đã lưu: %s"
            % os.path.basename(FILE_VUNG_MAC_DINH)
        )
    if "vung" in body:
        file_vung = str(body.get("vung") or "").strip()
        co_vung = bool(file_vung)
    else:
        file_vung = str(body.get("file_vung") or "").strip() or FILE_VUNG_MAC_DINH
        co_vung = bool(_ep_bool(body.get("canh_vung")))
    if co_vung:
        duong_vung = (
            file_vung if os.path.isabs(file_vung)
            else os.path.join(APP_DIR, file_vung)
        )
        if not os.path.isfile(duong_vung):
            _xoa_tam(duong_dan)
            return _loi(
                "Bật cảnh vùng nhưng không thấy file vùng: "
                + os.path.basename(file_vung)
            )
        # Dung duong dan TUYET DOI cho cam_ai_core: khong phu thuoc thu muc
        # lam viec cua may chu khi doc file vung.txt.
        body = dict(body)
        body["vung"] = duong_vung

    # KHONG import cam_ai_core o day (torch nang, ~8-30 giay) -> nut "Bat dau"
    # tren dien thoai se bi treo khong phan hoi. Import + tao config chuyen
    # sang thread nen; route tra ve ngay, UI thay busy=true ngay lap tuc.
    TT.reset(os.path.basename(duong_dan), thu_muc_kq)
    TT.dat(
        tep=duong_dan,
        loai_nguon=_loai_nguon_cua(duong_dan),
    )
    ANH_NEN.xoa()
    TT.ghi_log("[web] Bắt đầu: %s" % duong_dan)
    _in("[CHAY] %s" % duong_dan)

    # THREAD NEN: pipeline khong chay trong luong xu ly FastAPI.
    threading.Thread(
        target=_chay_phan_tich,
        args=(duong_dan, thu_muc_kq, body),
        daemon=True,
        name="camai-web-phan-tich",
    ).start()
    return JSONResponse(
        {
            "ok": True,
            "thong_bao": "Đã bắt đầu phân tích: " + os.path.basename(duong_dan),
        }
    )


@app.post("/api/dung")
def api_dung(request: Request):
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        if not TT.dang_chay:
            return _loi("Không có video nào đang chạy.")
        TT.yeu_cau_dung = True
    TT.ghi_log("[web] Người dùng bấm Dừng.")
    return JSONResponse({"ok": True})


@app.post("/api/tao-bao-cao")
def api_tao_bao_cao(request: Request):
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        if TT.dang_chay:
            return _loi("Đang phân tích, xong hãy tạo báo cáo.")
        if not TT.ket_qua or not TT.thu_muc_ket_qua:
            return _loi("Chưa có kết quả để tạo báo cáo.")
        csv_path = os.path.join(TT.thu_muc_ket_qua, TT.ket_qua["file_bao_cao"])
        video_path = os.path.join(TT.thu_muc_ket_qua, TT.ket_qua["video_ket_qua"])
        thu_muc = TT.thu_muc_ket_qua
        dang = TT.dang_tao_bao_cao
    if dang:
        return _loi("Báo cáo đang được tạo, vui lòng đợi.")
    if not os.path.isfile(csv_path):
        return _loi("Không tìm thấy file CSV kết quả.")
    TT.dat(dang_tao_bao_cao=True, bao_cao="Đang tạo báo cáo...")
    threading.Thread(
        target=_tao_bao_cao, args=(csv_path, video_path), daemon=True,
        name="camai-web-bao-cao",
    ).start()
    return JSONResponse({"ok": True})


@app.get("/api/tao-bao-cao")
def api_tao_bao_cao_get(request: Request):
    """Tra file bao cao (HTML xem lai truoc, neu co) - POST cu van giu nguyen."""
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        if not TT.ket_qua or not TT.thu_muc_ket_qua:
            return _loi("Chưa có kết quả để tải báo cáo.")
        thu_muc = TT.thu_muc_ket_qua
        goc_csv = os.path.splitext(TT.ket_qua.get("file_bao_cao", ""))[0]
    if goc_csv.endswith("_bao_cao"):
        goc_csv = goc_csv[: -len("_bao_cao")]
    html = os.path.join(thu_muc, goc_csv + "_xem_lai.html")
    xlsx = os.path.join(thu_muc, goc_csv + "_tong_ket.xlsx")
    if os.path.isfile(html):
        return _tra_file_range(
            request, html, os.path.basename(html), "text/html", inline=True
        )
    if os.path.isfile(xlsx):
        return _tra_file_range(
            request,
            xlsx,
            os.path.basename(xlsx),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            inline=True,
        )
    return _loi("Chưa có báo cáo. Bấm “Tạo báo cáo Excel + HTML” trước.")


@app.get("/api/tai-video")
def api_tai_video_get(request: Request):
    """Video ket qua (mp4) - co Range -> phat duoc tren Safari/iOS.

    POST /api/tai-video (tai video len) van giu nguyen.
    """
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        if not TT.ket_qua or not TT.thu_muc_ket_qua:
            return _loi("Chưa có kết quả để tải.")
        duong_dan = os.path.join(TT.thu_muc_ket_qua, TT.ket_qua.get("video_ket_qua", ""))
        ten = TT.ket_qua.get("video_ket_qua", "video.mp4")
    return _tra_file_range(request, duong_dan, ten, "video/mp4", inline=True)


@app.get("/api/tai-ket-qua")
def api_tai_ket_qua(request: Request, loai: str = "csv"):
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)
    with TT.khoa:
        if not TT.ket_qua or not TT.thu_muc_ket_qua:
            return _loi("Chưa có kết quả để tải.")
        thu_muc = TT.thu_muc_ket_qua
        csv_name = TT.ket_qua["file_bao_cao"]
        video_name = TT.ket_qua["video_ket_qua"]

    duoi_video = os.path.splitext(video_name)[0]
    # bao_cao_tong_ket lay ten file bao cao tu STEM CUA CSV (khong phai ten video).
    goc_csv = os.path.splitext(csv_name)[0]
    if goc_csv.endswith("_bao_cao"):
        goc_csv = goc_csv[: -len("_bao_cao")]
    bang = {
        "csv": (os.path.join(thu_muc, csv_name), csv_name, "text/csv"),
        "video": (os.path.join(thu_muc, video_name), video_name, "video/mp4"),
        "xlsx": (
            os.path.join(thu_muc, goc_csv + "_tong_ket.xlsx"),
            goc_csv + "_tong_ket.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "html": (
            os.path.join(thu_muc, goc_csv + "_xem_lai.html"),
            goc_csv + "_xem_lai.html",
            "text/html",
        ),
    }
    if loai not in bang:
        return _loi("Loại tệp không hợp lệ (csv, video, xlsx, html).")
    duong_dan, ten, kieu = bang[loai]
    if not os.path.isfile(duong_dan):
        return _loi(
            "Chưa có tệp %s. Bấm “Tạo báo cáo Excel + HTML” trước." % ten
            if loai in ("xlsx", "html")
            else "Không tìm thấy tệp: " + ten
        )
    return FileResponse(duong_dan, media_type=kieu, filename=ten)


# ------------------------------------------------------------------ chay
def _chuan_bi_thu_muc() -> None:
    for thu_muc in (THU_MUC_TAM, THU_MUC_UPLOAD, THU_MUC_KET_QUA):
        os.makedirs(thu_muc, exist_ok=True)


def _kiem_tra_mat_khau() -> bool:
    """Fail closed: thieu hoac qua ngan mat khau -> tu choi khoi dong.

    KHONG tu sinh mat khau yeu. KHONG in gia tri mat khau ra man hinh.
    """
    mk = os.environ.get(TEN_BIEN_MAT_KHAU, "").strip()
    if not mk:
        _in("=" * 66)
        _in("  KHÔNG KHỞI ĐỘNG ĐƯỢC: chưa đặt biến môi trường %s." % TEN_BIEN_MAT_KHAU)
        _in("  Phần mềm bắt buộc có mật khẩu riêng, không dùng mật khẩu mặc định.")
        _in("")
        _in("  Đặt mật khẩu trước khi chạy (PowerShell):")
        _in('      $env:%s = "mat-khau-cua-ban-it-nhat-8-ky-tu"' % TEN_BIEN_MAT_KHAU)
        _in("")
        _in("  Hoặc đặt vĩnh viễn cho tài khoản Windows (đổi tên user nếu cần):")
        _in(
            '      [Environment]::SetEnvironmentVariable("%s", '
            '"mat-khau-cua-ban-it-nhat-8-ky-tu", "User")' % TEN_BIEN_MAT_KHAU
        )
        _in("")
        _in("=" * 66)
        return False
    if len(mk) < DO_DAI_MAT_KHAU_TOI_THIEU:
        _in("=" * 66)
        _in("  KHÔNG KHỞI ĐỘNG ĐƯỢC: mật khẩu quá ngắn.")
        _in(
            "  Mật khẩu phải có ít nhất %d ký tự."
            % DO_DAI_MAT_KHAU_TOI_THIEU
        )
        _in("  Hãy đặt mật khẩu dài hơn:")
        _in('      $env:%s = "mat-khau-dai-hon-8-ky-tu"' % TEN_BIEN_MAT_KHAU)
        _in("")
        _in("  (Không in nội dung mật khẩu ra màn hình.)")
        _in("=" * 66)
        return False
    return True


def _canh_bao_mat_khau() -> None:
    """Chỉ in TÊN biến môi trường, không in giá trị mật khẩu."""
    _in("=" * 66)
    _in(
        "  Mật khẩu đăng nhập được lấy từ biến môi trường %s."
        % TEN_BIEN_MAT_KHAU
    )
    _in(
        "  (đã kiểm tra độ dài tối thiểu %d ký tự)"
        % DO_DAI_MAT_KHAU_TOI_THIEU
    )
    _in("  Không in mật khẩu ra màn hình, không lưu mật khẩu vào tệp.")
    _in("=" * 66)


def _ip_lan() -> str:
    """Dia chi IP cua may trong mang LAN (khong can Internet).

    UDP connect chi CHON route (khong gui du lieu len dau) -> an toan.
    """
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:                    # noqa: BLE001
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        try:
            s.connect(("10.255.255.255", 1))     # chi chon route, KHONG gui du lieu
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
        finally:
            s.close()
    except Exception:                    # noqa: BLE001
        pass
    return "127.0.0.1"


def _co_giao_dien_web() -> bool:
    return os.path.isfile(os.path.join(THU_MUC_GIAO_DIEN_WEB, "index.html"))


_DA_GAN_MOUNT_UI = False


def _gan_mount_ui() -> None:
    """Gan StaticFiles cho thu muc giao_dien_web (trang co the tai CSS/JS rieng)."""
    global _DA_GAN_MOUNT_UI
    if _DA_GAN_MOUNT_UI:
        return
    if not os.path.isdir(THU_MUC_GIAO_DIEN_WEB):
        return
    try:
        from fastapi.staticfiles import StaticFiles

        app.mount(
            "/",
            StaticFiles(directory=THU_MUC_GIAO_DIEN_WEB, html=True),
            name="giao_dien_web",
        )
        _DA_GAN_MOUNT_UI = True
        _in("[OK] Da gan thu muc giao dien web: %s" % THU_MUC_GIAO_DIEN_WEB)
    except Exception as exc:            # noqa: BLE001
        _in("[LOI] khong gan duoc thu muc giao dien web: %s" % exc)


def _thong_bao_khoi_dong(host: str, cong: int) -> None:
    ip_lan = _ip_lan()
    _in("")
    _in("=" * 66)
    _in("  CamAI - giao dien WEB da chay.")
    _in("  Tren may nay:     http://127.0.0.1:%d" % cong)
    _in("  Tren dien thoai:  http://%s:%d" % (ip_lan, cong))
    _in("")
    _in("  * MAY TINH + DIEN THOAI PHAI CUNG WI-FI (cung mot mang LAN).")
    _in("  * KHONG mo ra Internet - server chi nghe trong mang LAN noi bo.")
    _in("  * Dien thoai khong vao duoc? Cho phep Python trong Windows")
    _in("    Defender Firewall (mang Private).")
    if not _co_giao_dien_web():
        _in("")
        _in("  [!] CHUA CO giao_dien_web/ - dang dung UI CU (tuong thich nguoc).")
    _in("  Nhan Ctrl+C de tat.")
    _in("=" * 66)
    _in("")


def main() -> None:
    import uvicorn

    ctl = argparse.ArgumentParser(description="CamAI - giao dien web chay local")
    ctl.add_argument("--port", type=int, default=8787, help="cong (mac dinh 8787)")
    ctl.add_argument(
        "--host",
        default="0.0.0.0",
        help="dia chi (mac dinh 0.0.0.0 = cho dien thoai cung LAN truy cap)",
    )
    args = ctl.parse_args()

    # Fail closed: khong co mat khau hop le -> khong phuc vu.
    if not _kiem_tra_mat_khau():
        sys.exit(2)

    _chuan_bi_thu_muc()
    _canh_bao_mat_khau()
    _don_tap_tam()
    _don_dep()
    _gan_mount_ui()
    _thong_bao_khoi_dong(args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()