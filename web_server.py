"""
CamAI - giao dien WEB chay hoan toan tren may nay (khong gui hinh/video len cloud).

Chay:
    .venv\\Scripts\\python.exe web_server.py
    .venv\\Scripts\\python.exe web_server.py --port 8787

Mo trinh duyet: http://127.0.0.1:8787

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
import os
import secrets
import shutil
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
        self.khoa = threading.Lock()
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

    def ban_trang_thai(self) -> dict:
        """Doc trang thai. Khoa giu RAT ngan, khong co tinh toan trong khoa."""
        with self.khoa:
            return {
                "dang_chay": self.dang_chay,
                "trang_thai": self.trang_thai,
                "tieu_de": self.tieu_de,
                "phan_tram": round(self.phan_tram, 2),
                "khung_hinh": self.khung_hinh,
                "tong_khung_hinh": self.tong_khung_hinh,
                "so_nguoi": self.so_nguoi,
                "so_mat": self.so_mat,
                "vao": self.vao,
                "ra": self.ra,
                "trong_vung": self.trong_vung,
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
        dung = TT.yeu_cau_dung
    return not dung


# ------------------------------------------------------------------ chay phan tich
def _ten_tach_duong(duong_dan: str) -> str:
    ten = os.path.splitext(os.path.basename(duong_dan))[0]
    return "".join(c if c.isalnum() else "_" for c in ten)[:40] or "video"


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


def _chay_phan_tich(cfg, thu_muc_kq: str, duong_dan_tai_len: str) -> None:
    """CHAY TRONG THREAD NEN. Khong bao gio chay trong luong xu ly FastAPI."""
    from cam_ai_core import CamAIError, run_analysis

    bat_dau = time.perf_counter()
    TT.dat(thu_muc_ket_qua=thu_muc_kq)
    try:
        ket_qua = run_analysis(cfg, progress_cb=_tien_trinh, log=TT.ghi_log)
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
            }
        )
        TT.dat(trang_thai="Đã dừng theo yêu cầu" if ket_qua.stopped else "Xong")
        TT.ghi_log("[web] Xong trong %.1f giây." % (time.perf_counter() - bat_dau))
    except CamAIError as exc:
        TT.dat(trang_thai="Lỗi: " + str(exc))
        TT.ghi_log("[loi] " + str(exc))
        _in("[LOI] %s" % exc)
    except Exception as exc:                        # noqa: BLE001
        TT.dat(trang_thai="Lỗi: " + str(exc))
        TT.ghi_log("[loi] " + str(exc))
        _in("[LOI] %s" % exc)
        _in(traceback.format_exc())
    finally:
        TT.an()
        _xoa_tam(duong_dan_tai_len)
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
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse  # noqa: E402
from pydantic import BaseModel                                # noqa: E402

app = FastAPI(title="CamAI Web", docs_url=None, redoc_url=None)

# Cac tep da upload duoc phep dung (ten sinh tu UUID, khong dung ten nguoi gui).
_TEP_DA_UPLOAD: set[str] = set()
_KHOA_UPLOAD = threading.Lock()


def _ip(request: Request) -> str:
    return request.client.host if request.client else "khong-ro"


def _can_dang_nhap(request: Request):
    """Tra ve (token, phien_hop_le)."""
    return request.cookies.get(TEN_COOKIE), PHIEN.co_hieu_luc(request.cookies.get(TEN_COOKIE))


def _loi(noi_dung: str, ma: int = 400):
    return JSONResponse({"ok": False, "loi": noi_dung}, status_code=ma)


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


class _PhanTich(BaseModel):
    duong_dan: str = ""
    nhan_mat: bool = True
    dem_ra_vao: bool = False
    luu_clip: bool = False
    vat_the: bool = False
    canh_vung: bool = False
    ve_khung: bool = True
    ve_nhan: bool = True
    lam_mo: bool = False
    nguong_mat: float = 0.40
    file_vung: str = ""
    vung_max: int = 2
    canh_lau: float = 3.0
    clip_giay: float = 10.0
    lop: str = ""


# ------------------------------------------------------------------ trang
@app.get("/", response_class=HTMLResponse)
def trang_chinh(request: Request):
    # Khong cho trinh duyet cache lai trang: luon tai ban moi nhat.
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
    response = JSONResponse({"ok": True, "het_han_gio": HET_HAN_PHIEN_GIO})
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


@app.post("/api/phan-tich")
def api_phan_tich(request: Request, yeu_cau: _PhanTich):
    token, ok = _can_dang_nhap(request)
    if not ok:
        return _loi("Chưa đăng nhập.", 401)

    with TT.khoa:
        if TT.dang_chay:
            return _loi(
                "Phần mềm đang phân tích video '%s'. "
                "Vui lòng đợi xong hoặc bấm “Dừng” trước khi chạy video mới."
                % TT.tieu_de,
                409,
            )

    hieu_luc, duong_dan = _duong_dan_an_toan(yeu_cau.duong_dan)
    if not hieu_luc:
        return _loi(duong_dan)

    thu_muc_kq = os.path.join(THU_MUC_KET_QUA, datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(thu_muc_kq, exist_ok=True)

    file_vung = yeu_cau.file_vung.strip() or FILE_VUNG_MAC_DINH
    vung = None
    if yeu_cau.canh_vung:
        if not os.path.isfile(file_vung):
            _xoa_tam(duong_dan)
            return _loi(
                "Bật cảnh vùng nhưng không thấy file vùng: "
                + os.path.basename(file_vung)
            )
        vung = file_vung

    from cam_ai_core import AnalysisConfig

    cfg = AnalysisConfig(
        input=duong_dan,
        output=os.path.join(thu_muc_kq, _ten_tach_duong(duong_dan)),
        no_face=not yeu_cau.nhan_mat,
        faces_dir=THU_MUC_KHUON_MAT,
        model=MODEL_YOLO,
        conf=0.25,
        face_every=1,
        face_threshold=min(0.9, max(0.1, float(yeu_cau.nguong_mat or 0.40))),
        min_face=0,
        pixelate=yeu_cau.lam_mo,
        vung=vung,
        vung_nhay=False,
        vung_max=max(0, int(yeu_cau.vung_max or 0)),
        canh_lau=max(0.0, float(yeu_cau.canh_lau or 0.0)),
        tu_luu_clip=thu_muc_kq if yeu_cau.luu_clip else "",
        clip_giay=max(2.0, float(yeu_cau.clip_giay or 10.0)),
        clip_ghi_tat_ca=False,
        nhan_vat_the=yeu_cau.vat_the,
        lop=yeu_cau.lop.strip(),
        show_box=yeu_cau.ve_khung,
        show_label=yeu_cau.ve_nhan,
        show_line=yeu_cau.dem_ra_vao,
    )

    TT.reset(os.path.basename(duong_dan), thu_muc_kq)
    TT.ghi_log("[web] Bắt đầu: %s" % duong_dan)
    _in("[CHAY] %s" % duong_dan)

    # THREAD NEN: pipeline khong chay trong luong xu ly FastAPI.
    threading.Thread(
        target=_chay_phan_tich,
        args=(cfg, thu_muc_kq, duong_dan),
        daemon=True,
        name="camai-web-phan-tich",
    ).start()
    return JSONResponse({"ok": True})


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


def _thong_bao_khoi_dong(host: str, cong: int) -> None:
    _in("")
    _in("=" * 66)
    _in("  CamAI - giao dien WEB da chay.")
    _in("  Mo trinh duyet tai: http://%s:%d" % (host, cong))
    _in("  (Tu dien thoai trong cung mang, dung dia chi may may)")
    _in("  Nhan Ctrl+C de tat.")
    _in("=" * 66)
    _in("")


def main() -> None:
    import uvicorn

    ctl = argparse.ArgumentParser(description="CamAI - giao dien web chay local")
    ctl.add_argument("--port", type=int, default=8787, help="cong (mac dinh 8787)")
    ctl.add_argument("--host", default="127.0.0.1", help="dia chi (mac dinh 127.0.0.1)")
    args = ctl.parse_args()

    # Fail closed: khong co mat khau hop le -> khong phuc vu.
    if not _kiem_tra_mat_khau():
        sys.exit(2)

    _chuan_bi_thu_muc()
    _canh_bao_mat_khau()
    _don_tap_tam()
    _don_dep()
    _thong_bao_khoi_dong(args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()