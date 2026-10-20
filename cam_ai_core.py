"""
CamAI - loi phan tich video (dung chung cho app.py va gui.py).

Tach ra tu app.py de GUI goi duoc ma khong phai sua lai pipeline.
KHONG doi bat ky hanh vi nao so voi ban CLI cu: van toa do, ve khung,
ve duong dem, canh vung (chac/nhay), canh bao dong, canh bao dung lau,
lam mo nen, nhan dien mat + tuoi/gioi tinh, ghi video ket qua, ghi CSV 10 cot,
va khoi tong ket in ra console.

Dung:
    from cam_ai_core import AnalysisConfig, run_analysis

    run_analysis(AnalysisConfig(input="video.mp4"), log=print)

GUI:
    def tien_trinh(p):           # p la doi tuong Progress
        hien_thanh(p.frame_index, p.total_frames)
        return True              # tra False = yeu cau DUNG

    run_analysis(cfg, progress_cb=tien_trinh, log=ghi_log)
"""

from __future__ import annotations

import csv
import difflib
import os
import signal
import tempfile
import time
import warnings
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Iterator

import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO

from duong_dan import chuan_hoa_duong_dan

warnings.filterwarnings("ignore", category=FutureWarning)

PERSON_CLASS_ID = 0
VERSION = "3.4"

# --- v3.2: chat luong JPEG cua khung hinh gui ra GUI (che do phan tich theo lo)
JPEG_CHAT_LUONG = 80                    # 0-100; 80 = rat kho cho mat, nho hon 85

# thiet bi chay model: "auto" = tu chon (giam nhip), "cuda"/"cpu" = ep
THIET_BI_MAC_DINH = "auto"
THIET_BI_CHON = ("auto", "cuda", "cpu")

# --- tach o (tile): chua MOT phuong an de nhan nguoi o xa. MAC DINH TAT.
# Do that 2026-10-19 (xem _kk_bench_nang_cao.py, _kk_bench_gop.py):
#   chi tach o            -> LAM HONG video gan (9.4 -> 4.5 nguoi/khung)
#   phong to x2           -> vô dung (ultralytics tu resize ve 640px)
#   yolo11s thay yolo11n  -> khong giup, dam-dong con te hon
#   TOAN KHUH + o 2x2     -> tot nhat: dam-dong 3.0->6.5, xe-co 1.0->6.8,
#                           video gan khong hoi quat (9.4->10.0)
#   nhung cham hon 5.3 lan (~170 ms/khung) nen mac dinh TAT de giu muc tieu 1
#   (live view >=10 fps). Chi bat khi phan tich video quay san o cu ly xa.
TACH_O_MAC_DINH = False
TACH_O_TRUNG = 0.35            # kich thuoc o = 35% chieu rong/khung, 2x2 co chong
# NMS CHI GOP TRUNG, KHONG DUOC LOAI BOI nhan.
# cv2.dnn.NMSBoxes(bboxes, scores, score_threshold, nms_threshold)
# -> score_threshold phai = 0. VI SAI O DAY (dat 0.45) se xoa sach moi
# nhan co conf < 0.45, trong khi nguong nhan goc la 0.25 => dem THIEU nang.
TACH_O_DIEM = 0.0              # score_threshold: 0 = khong loai nhan nao
TACH_O_IOU = 0.45              # nms_threshold: gop khi 2 khung trung nhau > 45%

CSV_FIELDS = [
    "giay", "so_nguoi", "so_mat", "nguoi_quen", "nam", "nu", "tuoi_tb",
    "trong_vung", "vi_pham", "canh_lau",
]

# --- bien so: cot them vao CUOI, CHI khi bat --doc-bien-so.
# QUY TAC CU: khi tinh nang tat, CSV van dung 10 cot cu (xem PROJECT_STATE.md
# muc 3 "CSV giu dung 10 cot"). Khong bao gio ghi 11/12 cot mac dinh.
CSV_FIELDS_BIEN_SO = ["bien_so", "so_bien_so"]

HEADER = "CamAI v{} - ArcFace (SCRFD + w600k_r50)"

# --- tu luu clip: cung codec voi video ket qua de mo duoc o moi noi
# GHI CHU (quan trong): mp4v = MPEG-4 Part 2. Chrome/Edge/Firefox KHONG phat
# duoc MPEG-4 Part 2 -> video trong file bao cao xem lai bao loi
# "Unable to play media" khach xem khong duoc. H.264 (avc1) thi moi trinh
# duyet deu phat duoc, nen ham _fourcc_ket_qua() se uu tien avc1.
# FOURCC_KET_QUA giu nguyen gia tri "mp4v" (co noi khac import no) - chi la
# phuong an DU PHONG khi may khong co encoder H.264.
FOURCC_KET_QUA = "mp4v"
_FOURCC_KET_QUA_CACHE = None      # cache ket qua kiem tra 1 lan cho ca tien trinh
CLIP_MAC_DINH_GIAY = 10.0
BO_NHO_VONG_DEM_MB = 300 * 1024 * 1024      # gioi han RAM cho vong dem khung hinh
BUU_HOI_MAT_DAU = 1.0        # giay - nguoi bi che mat dau, van giu dong bo dem
LY_DO_VAO_VUNG = "vao_vung"
LY_DO_VUOT_DONG = "vuot_nguong_dong"
LY_DO_DUNG_LAU = "dung_lau"
LY_DO_NGUOI_QUEN = "nguoi_quen"
LY_DO_CO_NGUOI = "co_nguoi"

# --- canh bao ngoai (canh_bao.py): gop tin + gioi han chong spam
CANH_BAO_MAC_DINH_GO = 60.0          # gop tin cung loai trong bao nhieu giay
CANH_BAO_MAC_DINH_GIOI_HAN = 5       # toi da bao nhieu tin / 60 giay

# --- vat the khac: chi ve khung + nhan + dem, KHONG tinh vao canh vung
VAT_THE_MAC_DINH = [
    "car", "motorcycle", "bicycle", "bus", "truck",
    "backpack", "handbag", "suitcase", "cell phone",
]
TEN_VAT_THE = {
    "car": "xe o to",
    "motorcycle": "xe may",
    "bicycle": "xe dap",
    "bus": "xe khach",
    "truck": "xe tai",
    "backpack": "ba loi",
    "handbag": "tui xach",
    "suitcase": "vali",
    "cell phone": "dien thoai",
    "boat": "thuyen",
    "bench": "ghe",
    "chair": "ghe",
    "potted plant": "cay",
    "tv": "tivi",
    "laptop": "may tinh",
    "bird": "chim",
    "cat": "meo",
    "dog": "cho",
    "bird nest": "to chim",
}


class CamAIError(Exception):
    """Loi co kiem soat: GUI hien thi len man hinh, CLI in ra roi dung.

    Khong dung SystemExit o day de GUI khong bi bay toan bo app.
    """


# ------------------------------------------------------------------ cau hinh

@dataclass
class AnalysisConfig:
    """Moi thu can de chay 1 lan phan tich. Gia tri mac dinh giong het app.py."""

    # nguon
    input: str = "video_test.mp4"          # duong dan video, hoac "0" = webcam
    output: str = "output.mp4"             # chi dung de dat ten file ket qua
    # nhan dien mat
    no_face: bool = False
    faces_dir: str = "known_faces"
    model: str = "yolo11n.pt"
    # "auto" = tu do torch chon (co GPU thi GPU, khong co thi CPU),
    # "cuda"/"cpu" = ep chay cai do.
    thiet_bi: str = THIET_BI_MAC_DINH
    # 0.25 = dung nguyen mac dinh cua ultralytics (predictor.py:155)
    # nen CLI chay y het nhu truoc khi tach file nay.
    conf: float = 0.25
    face_every: int = 1
    face_threshold: float = 0.40
    min_face: int = 0
    # hinh anh
    pixelate: bool = False
    # canh vung
    vung: str | None = None
    vung_nhay: bool = False
    vung_max: int = 0
    canh_lau: float = 0.0
    # tu luu clip (mac dinh TAT de khong doi hanh vi cu)
    tu_luu_clip: str = ""            # thu muc luu clip, rong = tat
    clip_giay: float = CLIP_MAC_DINH_GIAY
    clip_ghi_tat_ca: bool = False    # ghi ca khi khong co --vung
    # nhan vat the khac (chi ve khung + nhan + dem, mac dinh TAT)
    nhan_vat_the: bool = False
    lop: str = ""                    # "car,motorcycle", rong = nhom mac dinh
    # tach o: tach khung hinh thanh 2x2 o co chong de nhan nguoi o xa.
    # MAC DINH TAT: bat vao se cham hon ~5.3 lan, lam live view rut fps.
    tach_o: bool = TACH_O_MAC_DINH
    # canh bao ngoai (mac dinh TAT de hanh vi cu khong doi)
    bat_canh_bao: bool = False       # bao su kien vuot nguong / dung lau ra ngoai
    canh_bao_mo_phong: bool = False  # chi thu, KHONG gui tin ra ngoai
    canh_bao_go: float = CANH_BAO_MAC_DINH_GO
    canh_bao_gioi_han: int = CANH_BAO_MAC_DINH_GIOI_HAN
    # tu chon cho GUI, mac dinh giu nguyen hinh ve cua app.py
    show_box: bool = True
    show_label: bool = True
    show_line: bool = True
    # --- NHOM TINH NANG MOI (v3.0) ---
    # Dat CUOI dataclass de moi truong doi khong phai doi thu tu vi tri cu.
    # Doc bien so (bien_so.py): MAC DINH TAT. Bat vao them cot CSV o CUOI
    # (xem CSV_FIELDS_BIEN_SO) - khi tat van dung 10 cot nhu cu.
    doc_bien_so: bool = False
    bien_so_dir: str = "anh_bien_so"        # thu muc luu crop bien so
    bien_so_tin_cay: float = 0.5
    bien_so_nhoan_lai_giay: float = 30.0     # cung bien so chi luu 1 lan/30s
    vung_bien_so: str | None = None          # ROI "x1,y1,x2,y2" neu khong co class plate
    # Tu chup anh su kien (tu_chup.py): MAC DINH TAT (chuoi rong = tat).
    tu_chup_dir: str = ""
    tu_chup_nhoan_lai_giay: float = 10.0

    def __post_init__(self) -> None:
        """Chuan hoa duong dan tuong doi theo thu muc goc du an (duong_dan.py).

        CWD khac thu muc du an (double-click tu Explorer, chay tu shortcut,
        chay tu service/CI) thi duong dan tuong doi nhu "known_faces" hay
        "yolo11n.pt" se khong tim thay. Chuan hoa o day de CLI va GUI cung
        dung mot quy tac, va de chay app tu thu muc nao cung ra ket qua giong
        nhau.
        """
        self.faces_dir = chuan_hoa_duong_dan(self.faces_dir)
        self.model = chuan_hoa_duong_dan(self.model)


@dataclass
class Progress:
    """Trang thai sau moi khung hinh, gui cho callback de hien thi len GUI.

    Cung co __iter__ de unpack duoc dung thu tu:
        frame_index, total_frames, so_nguoi, so_mat, vao, ra,
        trong_vung, vi_pham, canh_lau, nhan_dien = progress
    """

    frame_index: int
    total_frames: int
    so_nguoi: int
    so_mat: int
    vao: int
    ra: int
    trong_vung: int
    vi_pham: int
    canh_lau: int
    nhan_dien: str          # "An | Binh" - nguoi quen thay trong khung hinh nay

    @property
    def percent(self) -> float:
        if not self.total_frames:
            return 0.0
        return min(100.0, self.frame_index * 100.0 / self.total_frames)

    def __iter__(self) -> Iterator:
        return iter((
            self.frame_index, self.total_frames, self.so_nguoi, self.so_mat,
            self.vao, self.ra, self.trong_vung, self.vi_pham,
            self.canh_lau, self.nhan_dien,
        ))


@dataclass
class AnalysisResult:
    """Ket qua sau khi chay xong. GUI doc .out_path / .report_path de mo file."""

    out_path: str = ""
    report_path: str = ""
    frames: int = 0
    fps: float = 0.0
    duration: timedelta = field(default_factory=timedelta)
    max_people: int = 0
    max_faces: int = 0
    seen_names: list = field(default_factory=list)
    males: int = 0
    females: int = 0
    avg_age: int = 0
    zone_px: tuple | None = None
    zone_mode: str = "chac"
    peak_zone: int = 0
    violation_events: int = 0
    crowd_events: int = 0
    loiter_events: int = 0
    longest_loiter: float = 0.0
    used_face: bool = False
    clips: list = field(default_factory=list)     # duong dan cac file clip da luu
    # --- v3.0: ket qua tinh nang moi (mac dinh rong, khong doi hanh vi cu) ---
    bien_so: list = field(default_factory=list)   # list[KetQuaBienSo] doc duoc
    anh_su_kien: list = field(default_factory=list)  # duong dan anh tu chup
    stopped: bool = False          # True = nguoi dung dung giua chung


# ------------------------------------------------- ghi video an toan (moov atom)

def _fourcc_ket_qua() -> str:
    """Tra fourcc de ghi video: 'avc1' (H.264) neu may co encoder, nguoc lai 'mp4v'.

    LY DO: mp4v = MPEG-4 Part 2. Chrome/Edge/Firefox KHONG phat duoc MPEG-4
    Part 2 -> video trong file bao cao xem lai bao loi "Unable to play media".
    H.264 (avc1) thi moi trinh duyet deu phat duoc.

    CACH KIEM TRA (chi 1 LAN cho ca tien trinh, ket qua duoc cache):
      1. Ghi 1 file mp4 tam (2 khung hinh 64x64 mau den) voi fourcc avc1.
      2. Doc ~4 KB dau file, tim chuoi b'avc1' (fourcc that trong box stsd).
      3. Co b'avc1' -> dung 'avc1'; khong co -> lui ve 'mp4v'.
    File probe LUON duoc xoa. Moi loi -> tra 'mp4v' (fail-safe, khong lam
    hong pipeline).
    """
    global _FOURCC_KET_QUA_CACHE
    if _FOURCC_KET_QUA_CACHE is not None:
        return _FOURCC_KET_QUA_CACHE

    fourcc = "mp4v"
    duong_dan_probe = ""
    try:
        # tempfile: file probe nam o thu muc tam cua he -> khong de rac
        # trong thu muc du an.
        fd, duong_dan_probe = tempfile.mkstemp(prefix="cam_ai_probe_", suffix=".mp4")
        os.close(fd)

        writer = None
        mo_duoc = False
        try:
            writer = cv2.VideoWriter(
                duong_dan_probe, cv2.VideoWriter_fourcc(*"avc1"), 10.0, (64, 64)
            )
            mo_duoc = bool(writer.isOpened())
            if mo_duoc:
                khung_hinh_den = np.zeros((64, 64, 3), np.uint8)
                writer.write(khung_hinh_den)
                writer.write(khung_hinh_den)
        finally:
            if writer is not None:
                try:
                    writer.release()
                except Exception:                            # noqa: BLE001
                    pass
                # Huy tham chu de dong han file that. Windows: file con bi
                # khoa thi os.remove() that bai -> de lai rac trong TEMP.
                del writer
                writer = None

        if mo_duoc and os.path.isfile(duong_dan_probe):
            kich_thuoc = os.path.getsize(duong_dan_probe)
            if kich_thuoc > 0:
                with open(duong_dan_probe, "rb") as f:
                    dau = f.read(4096)
                tim_thay = b"avc1" in dau
                if not tim_thay and kich_thuoc > len(dau):
                    # moov atom (chua box stsd) co the nam o CUOI file
                    f.seek(max(0, kich_thuoc - 65536))
                    tim_thay = b"avc1" in f.read()
                if tim_thay:
                    fourcc = "avc1"
    except Exception:                                        # noqa: BLE001
        fourcc = "mp4v"        # fail-safe: khong bao gio lam hong pipeline
    finally:
        # Xoa file probe (khong de lai rac). Thu them vai lan: Windows co
        # luc khoa file tam thoi (FFmpeg chua dong het) -> os.remove that bai.
        if duong_dan_probe:
            for _lan in range(5):
                try:
                    if os.path.isfile(duong_dan_probe):
                        os.remove(duong_dan_probe)
                    break
                except OSError:
                    continue

    _FOURCC_KET_QUA_CACHE = fourcc
    return fourcc


def duong_dan_tam(duong_dan: str) -> str:
    """'a_ket_qua.mp4' -> 'a_ket_qua.part.mp4' (ghi tam, xong moi doi ten)."""
    goc, duoi = os.path.splitext(duong_dan)
    return f"{goc}.part{duoi or '.mp4'}"


def chuyen_ten_sau_khi_dong(duong_dan_tam: str, duong_dan: str) -> bool:
    """Doi ten file tam -> ten that. PHAI goi sau khi VideoWriter da release().

    MP4 ghi ra co moov atom o CUOI file; bi taskkill /F giyet giua chung thi file
    .mp4 mang ten dung se ra 'moov atom not found'. Ghi ra .part.mp4 roi doi ten
    o day thi file hong khong bao gio xuat hien voi ten dung.
    Tra True neu doi xong; False neu khong co gi de doi (hoac loi - bo qua).
    """
    if not os.path.isfile(duong_dan_tam):
        return False
    try:
        if os.path.getsize(duong_dan_tam) <= 0:
            os.remove(duong_dan_tam)
            return False
        os.replace(duong_dan_tam, duong_dan)
        return True
    except OSError:
        return False


def don_file_tam(duong_dan_tam: str) -> bool:
    """Xoa 1 file .part.mp4 (con sot tu lan chay truoc)."""
    try:
        if os.path.isfile(duong_dan_tam):
            os.remove(duong_dan_tam)
            return True
    except OSError:
        pass
    return False


# --- file .part.mp4 DANG DUOC GHI (file tam cu video ket qua, cua clip, ...)
# Registry la LOP BAO VE THU HAI cho chuc "don file sot": VideoWriter giu
# file khi dang ghi, xoa file do giua chung se lam MAT video ket qua ma app
# van exit 0 (bug nghiem trong - xem ISSUE_LOG).
_FILE_DANG_GHI: set[str] = set()


def _khoa_duong_dan(duong_dan: str) -> str:
    """Chuan hoa duong dan de so sanh (Windows khong phan biet hoa/thuong)."""
    if not duong_dan:
        return ""
    try:
        return os.path.normcase(os.path.abspath(duong_dan))
    except (TypeError, ValueError):
        return os.path.normcase(str(duong_dan))


def dang_ghi_file(duong_dan: str) -> None:
    """Dang ky 1 file .part.mp4 dang duoc VideoWriter ghi (KHONG duoc xoa)."""
    khoa = _khoa_duong_dan(duong_dan)
    if khoa:
        _FILE_DANG_GHI.add(khoa)


def ngung_ghi_file(duong_dan: str) -> None:
    """Bo dang ky file .part.mp4 (sau khi ghi xong / dong lai)."""
    khoa = _khoa_duong_dan(duong_dan)
    if khoa:
        _FILE_DANG_GHI.discard(khoa)


def don_file_tam_trong_thu_muc(thu_muc: str, giu=()) -> list:
    """Xoa moi file *.part.mp4 trong thu muc (con sot sau khi bi kill cung).

    giu: iterable cac duong dan (tuyet doi) KHONG duoc xoa.
    File dang duoc VideoWriter ghi trong chinh tien trinh nay cung duoc bao ve
    (registry _FILE_DANG_GHI) - xoa file dang ghi giua chung se lam mat video
    ket qua ma app van exit 0.
    """
    giu_luon = {_khoa_duong_dan(p) for p in giu if p}
    da_xoa = []
    try:
        ten_files = os.listdir(thu_muc)
    except OSError:
        return da_xoa
    for ten in ten_files:
        if not ten.endswith(".part.mp4"):
            continue
        duong_dan = os.path.join(thu_muc, ten)
        khoa = _khoa_duong_dan(duong_dan)
        if khoa in giu_luon or khoa in _FILE_DANG_GHI:
            continue
        try:
            os.remove(duong_dan)
            da_xoa.append(ten)
        except OSError:
            # 1 file xoa khong duoc (dang mo) -> bo qua no, van don con lai
            continue
    return da_xoa


# ------------------------------------------------------------ tien ich / an toan

def _log_an_toan(log, dong: str, dong_khong_dau: str = "") -> None:
    """Log tieng Viet co dau; console cp1252 khong in duoc -> lui ve ban khong dau.

    Khong du con so la du, dong log KHONG bao gio lam chet luong phan tich.
    Xem ISSUE_LOG.md muc "Console Windows khong in duoc tieng Viet".
    """
    for noi_dung in ((dong, dong_khong_dau) if dong_khong_dau else (dong,)):
        try:
            log(noi_dung)
            return
        except UnicodeEncodeError:
            continue
        except Exception:
            return


def _goi_y_lop(ten_sai: list, id_lop: dict) -> str:
    """'mnay' -> "co phai la 'mootray'?" (chi doan nhac de bao loi, khong chan)."""
    goi_y = []
    for ten in ten_sai:
        gan = difflib.get_close_matches(ten, list(id_lop), n=1, cutoff=0.7)
        if gan:
            goi_y.append(f"'{ten}' co phai la '{gan[0]}'?")
    return "; ".join(goi_y)


def cai_tin_hieu_dung() -> dict:
    """Bat SIGTERM / SIGBREAK de DUNG MEM thay vi bi giet lap tuc.

    Windows: `taskkill` KHONG kem `/F` gui WM_CLOSE -> tien trinh nhan duoc tin
    hieu, dung vong lap, dong video (co moov atom) roi doi ten -> clip hop le.
    GIOI HAN: `taskkill /F` / Stop-Process -Force la GIET CUNG, khong cai dat
    nao bat duoc - xem ISSUE_LOG.md "Clip MP4 hong khi hard kill".

    Signal chi cai duoc o main thread (gui.py chay pipeline o thread nen bo qua
    o do). Tra dict {"flag": bool, "ten": str} de vong lap nhin thay doi.
    """
    trang_thai = {"flag": False, "ten": ""}

    def handler(so_tin_hieu, khung_hinh):       # noqa: ARG001 - chu ky signal
        trang_thai["flag"] = True

    for ten in ("SIGTERM", "SIGBREAK"):
        so_tin_hieu = getattr(signal, ten, None)
        if so_tin_hieu is None:
            continue
        try:
            signal.signal(so_tin_hieu, handler)
            trang_thai["ten"] = (
                f"{trang_thai['ten']}, {ten}" if trang_thai["ten"] else ten
            )
        except (ValueError, OSError, RuntimeError):
            pass
    return trang_thai


# ---------------------------------------------------------- noi canh_bao.py

class CanhBaoNoi:
    """Noi canh_bao.py vao pipeline (truoc day file co san nhung KHONG ai goi).

    - Chi bat khi AnalysisConfig.bat_canh_bao = True (mac dinh TAT).
    - Co 'chot' true -> false: mot su kien chi bao MOT LAN, phai ve binh thuong
      roi vi pham lai moi bao tiep (khong keu moi khung hinh).
    - Fail-safe: import hay gui that bai -> bao loi MOT LAN roi tu tat, phan
      tich van chay tiep chi mat canh bao.
    """

    def __init__(self, cfg: AnalysisConfig, log, ten_video: str = ""):
        self.cfg = cfg
        self.log = log
        self.ten_video = ten_video
        self.can_bao = None
        self.bat_duoc = False
        self.loi = ""
        self.chot: dict = {}
        self.so_su_kien = 0
        if not cfg.bat_canh_bao:
            return
        try:
            # import lai (lazy) + trong try: canh_bao.py hong thi cam_ai_core
            # van phai chay duoc binh thuong.
            from canh_bao import CanhBao

            self.can_bao = CanhBao(
                gioi_han=cfg.canh_bao_gioi_han,
                go=cfg.canh_bao_go,
                mo_phong=cfg.canh_bao_mo_phong,
            )
            self.bat_duoc = True
        except Exception as exc:              # noqa: BLE001 - fail-safe
            self.can_bao = None
            self.loi = f"{type(exc).__name__}: {exc}"
            log(f"[canh bao] KHONG bat duoc, chi mat canh bao: {self.loi}")

    def cap_nhat(self, loai_su_kien: str, dang_xay_ra: bool,
                 mo_ta: str = "", so_nguoi=None) -> None:
        """Cap nhat trang thai su kien; gui canh bao dung 1 lan cho 1 su kien."""
        if self.can_bao is None:
            return
        if not dang_xay_ra:
            self.chot[loai_su_kien] = False    # ve binh thuong -> cho phep bao lai
            return
        if self.chot.get(loai_su_kien):
            return                             # dang bao roi, im lang
        self.chot[loai_su_kien] = True
        self.so_su_kien += 1
        self.log(f"[canh bao] {datetime.now():%H:%M:%S} canh bao: {loai_su_kien}")
        try:
            self.can_bao.guii(loai_su_kien, {
                "video": self.ten_video,
                "so_nguoi": so_nguoi,
                "mo_ta": mo_ta,
                "gio": datetime.now().strftime("%H:%M:%S"),
            })
        except Exception as exc:              # noqa: BLE001 - fail-safe
            self.loi = f"{type(exc).__name__}: {exc}"
            self.can_bao = None
            self.log(f"[canh bao] gui that bai, TAT canh bao: {self.loi}")

    def dong(self) -> None:
        if self.can_bao is None:
            return
        try:
            self.can_bao.tat(in_tong_ket=False)
        except Exception:                      # noqa: BLE001 - fail-safe
            pass
        self.can_bao = None


# ------------------------------------------------------------- tu luu clip

class ClipRecorder:
    """Tu dong cat va luu clip ngan khi co su kien.

    Video chi ghi duoc 1 chieu, nen phan TRUOC su kien phai lay tu vong dem
    khung hinh (deque) giu ~n giay gan nhat - KHONG ghi ca video ra dia roi
    cat sau (cham + ton dia).
    Su kien moi khi dang ghi clip -> noi dai clip dang ghi, khong mo file moi.

    pre  = tong_giay / 2  (phia truoc su kien)
    post = tong_giay / 2  (phia sau su kien)
    """

    def __init__(self, thu_muc, tong_giay=CLIP_MAC_DINH_GIAY, fps=25.0, size=(0, 0)):
        self.thu_muc = thu_muc
        self.tong_giay = max(2.0, float(tong_giay))
        self.pre = self.tong_giay / 2.0
        self.post = self.tong_giay - self.pre
        self.fps = fps or 25.0
        self.size = size
        # Can bao dem: 1 khung hinh 1080p ~ 6 MB, giu qua se no RAM.
        can_ban_dinh = int(self.pre * self.fps) + 2
        can = can_ban_dinh
        width, height = size
        if width > 0 and height > 0:
            gioi_han = max(2, int(BO_NHO_VONG_DEM_MB // (width * height * 3)))
            can = min(can, gioi_han)
        self.so_khung_vong_dem = can
        self.bao_nho = can < can_ban_dinh
        self.buffer: deque = deque(maxlen=can)
        self.writer = None
        self.duong_dan = ""
        self.ly_do: list[str] = []
        self.nhan = ""
        self.ket_thuc_luc = 0.0
        self.khung_hinh_ghi = 0
        self.ket_qua: list[str] = []
        self.chi_tiet: list[str] = []

    # ------------------------------------------------------------ nap vao

    def feed(self, frame, t, reasons):
        """Dua khung hinh hien tai vao. reasons = ly do su kien (rong = im lang)."""
        if reasons:
            if self.writer is None:
                self._mo(t, reasons)
            else:
                self._noi_dai(t, reasons)
        if self.writer is not None:
            self.writer.write(frame)
            self.khung_hinh_ghi += 1
            if t >= self.ket_thuc_luc:
                self._dong()
        self.buffer.append((t, frame))

    def _mo(self, t, reasons):
        os.makedirs(self.thu_muc, exist_ok=True)
        self.nhan = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.ket_thuc_luc = t + self.post
        self.ly_do = list(dict.fromkeys(reasons))
        self.khung_hinh_ghi = 0
        self.duong_dan = os.path.join(
            self.thu_muc, f"clip_{self.nhan}_{self._ten_ly_do()}.mp4"
        )
        # Ghi ra .part.mp4: clip hong (moov atom chua ghi xong) khong bao gio
        # xuat hien voi ten .mp4 that. Xem chuyen_ten_sau_khi_dong().
        duong_tam = duong_dan_tam(self.duong_dan)
        don_file_tam(duong_tam)
        writer = cv2.VideoWriter(
            duong_tam,
            # avc1 (H.264) neu may co encoder, nguoc lai mp4v - xem
            # _fourcc_ket_qua(). mp4v thi trinh duyet khong phat duoc.
            cv2.VideoWriter_fourcc(*_fourcc_ket_qua()),
            self.fps, self.size,
        )
        if not writer.isOpened():
            self.duong_dan = ""
            self.ly_do = []
            return
        self.writer = writer
        # File clip dang ghi -> dang ky vao registry de "don file sot"
        # khong xoa nho (xem don_file_tam_trong_thu_muc).
        dang_ghi_file(duong_tam)
        for t0, f0 in self.buffer:                 # ghi phan TRUOC su kien
            if t0 > t - self.pre:
                self.writer.write(f0)
                self.khung_hinh_ghi += 1

    def _noi_dai(self, t, reasons):
        """Su kien moi trong luc dang ghi -> keo dai clip hien tai."""
        self.ket_thuc_luc = max(self.ket_thuc_luc, t + self.post)
        for r in reasons:
            if r not in self.ly_do:
                self.ly_do.append(r)

    def _ten_ly_do(self) -> str:
        return "+".join(self.ly_do) or "khong_ro"

    def _dong(self):
        if self.writer is None:
            return
        self.writer.release()
        self.writer = None
        # Da ghi xong -> bo dang ky file clip tam (xem don_file_tam_trong_thu_muc).
        ngung_ghi_file(duong_dan_tam(self.duong_dan))
        # Chi doi ten .part.mp4 -> .mp4 sau khi da release (da co moov atom).
        if not chuyen_ten_sau_khi_dong(duong_dan_tam(self.duong_dan), self.duong_dan):
            self.chi_tiet.append(f"BO QUA clip khong ghi duoc: {duong_dan_tam(self.duong_dan)}")
            self.duong_dan = ""
            self.ly_do = []
            self.khung_hinh_ghi = 0
            return
        ten_moi = f"clip_{self.nhan}_{self._ten_ly_do()}.mp4"
        if ten_moi != os.path.basename(self.duong_dan):
            duong_moi = os.path.join(self.thu_muc, ten_moi)
            try:
                os.replace(self.duong_dan, duong_moi)
                self.duong_dan = duong_moi
            except OSError:
                pass
        self.ket_qua.append(self.duong_dan)
        self.chi_tiet.append(
            f"{self.duong_dan} ({self.khung_hinh_ghi} khung hinh, "
            f"{self.khung_hinh_ghi / self.fps:.1f}s)"
        )
        self.duong_dan = ""
        self.ly_do = []
        self.khung_hinh_ghi = 0

    def ket_thuc(self):
        """Dong clip dang ghi va xoa vong dem (goi khi dung / xong video)."""
        if self.writer is not None:
            self._dong()
        self.buffer.clear()


def ten_vat_the(ten_lop: str) -> str:
    """'motorcycle' -> 'xe may' (nhan tieng Viet khong dau)."""
    return TEN_VAT_THE.get(ten_lop, ten_lop)


# ----------------------------------------------------------------- vung canh

def load_zone(path):
    """Doc vung.txt -> toa do tuong doi (x1, y1, x2, y2), hoac None."""
    if not os.path.exists(path):
        raise CamAIError(f"[loi] khong tim thay file vung: {path}")
    with open(path, encoding="utf-8") as file:
        lines = file.read().splitlines()
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
    raise CamAIError(f"[loi] file vung khong co du lieu hop le: {path}")


def person_inside(box, zone):
    """Che CHAT: nguoi phai nam trong vung moi tinh."""
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    return zone[0] <= cx <= zone[2] and zone[1] <= cy <= zone[3]


def person_touches(box, zone, min_ratio=0.05):
    """Che NHAY: chi can mot phan chan cham vao vung la tinh."""
    x1, y1, x2, y2 = box
    ix1, iy1 = max(x1, zone[0]), max(y1, zone[1])
    ix2, iy2 = min(x2, zone[2]), min(y2, zone[3])
    if ix2 <= ix1 or iy2 <= iy1:
        return False
    area = max(1.0, float(x2 - x1) * float(y2 - y1))
    return (ix2 - ix1) * (iy2 - iy1) / area >= min_ratio


def track_id_at(detections, index):
    """Lay id theo doi tai chi so, bo qua gia tri NaN."""
    ids = detections.tracker_id
    if ids is None:
        return None
    raw = float(ids[index])
    return None if raw != raw else int(raw)


def _boxes_cua(result):
    """Rut xyxy / conf / class_id tu 1 ket qua ultralytics, luon tra ve list."""
    if result is None or result.boxes is None or len(result.boxes) == 0:
        return [], [], []
    return (
        result.boxes.xyxy.tolist(),
        result.boxes.conf.tolist(),
        result.boxes.cls.tolist(),
    )


def detect_tach_o(detector, frame, conf):
    """Do 1 khung hinh theo kieu TOAN KHUH + 2x2 O CO CHONG, roi gop NMS.

    Vi sao phai gom ca toan khhang: neu chi tach o, nguoi o gan bi cat doi o
    ranh giua cac o nen mat so nguoi (do that: 9.4 -> 4.5 nguoi/khung).
    Giu toan khung thi nguoi o gan khong mat, ngui o xa duoc phong to.
    """
    h, w = frame.shape[:2]
    cw = max(1, int(w * TACH_O_TRUNG))
    ch = max(1, int(h * TACH_O_TRUNG))
    # 2 o moi canh 35% -> buoc = kich thuoc con lai (65%) de 2 o chong nhau
    # va PHU TOAN khung. Sai o day: dung buoc = cw se chi quet 70% khung hinh.
    buoc_x = max(1, w - cw)
    buoc_y = max(1, h - ch)

    xyxy, confs, cids = [], [], []

    r0 = detector(frame, verbose=False, conf=conf)[0]
    x0, c0, i0 = _boxes_cua(r0)
    xyxy += x0
    confs += c0
    cids += i0

    for iy in (0, 1):
        for ix in (0, 1):
            tx = min(ix * buoc_x, w - cw)
            ty = min(iy * buoc_y, h - ch)
            tx, ty = max(0, tx), max(0, ty)
            x1, y1 = min(tx + cw, w), min(ty + ch, h)
            if x1 - tx < 16 or y1 - ty < 16:
                continue
            o = frame[ty:y1, tx:x1]
            if o.size == 0:
                continue
            r = detector(o, verbose=False, conf=conf)[0]
            bx, bc, bi = _boxes_cua(r)
            for b in bx:
                xyxy.append([b[0] + tx, b[1] + ty, b[2] + tx, b[3] + ty])
            confs += bc
            cids += bi

    if not xyxy:
        return sv.Detections.empty()

    b = np.array(xyxy, dtype=np.float32)
    keep = cv2.dnn.NMSBoxes(
        [list(map(float, v)) for v in b],
        [float(v) for v in confs],
        TACH_O_DIEM,
        TACH_O_IOU,
    )
    if isinstance(keep, np.ndarray):
        idx = keep.flatten().tolist()
    elif isinstance(keep, (list, tuple)):
        idx = [int(k) for k in np.array(keep).flatten().tolist()]
    else:
        idx = []
    if not idx:
        return sv.Detections.empty()

    idx = np.array(idx, dtype=int)
    arr = np.ascontiguousarray(b[idx], dtype=np.float32)
    con = np.ascontiguousarray(
        np.array(confs, dtype=np.float32)[idx]
    )
    cla = np.ascontiguousarray(
        np.array(cids, dtype=np.float32)[idx]
    )
    return sv.Detections(xyxy=arr, confidence=con, class_id=cla)


def output_paths(output: str) -> tuple[str, str]:
    """'a.mp4' -> ('a_ket_qua.mp4', 'a_bao_cao.csv')."""
    stem = os.path.splitext(output)[0]
    return stem + "_ket_qua.mp4", stem + "_bao_cao.csv"


def tao_thu_muc_cha(duong_dan: str) -> str:
    """Tao thu muc cha cua 1 duong dan file neu chua co. Tra ve thu muc cha.

    VideoWriter KHONG tu tao thu muc -> thieu thu muc thi app chet ngay voi
    thong bao khong ro nguyen nhan. Day la noi sua do (xem ISSUE_LOG).
    Da co san -> tra ve luon. Khong tao duoc (khong co quyen ghi) -> tra ve
    chuoi rong, de loi bao o buoc sau noi ro thu muc cha la gi.
    """
    # abspath() bao dam dirname khong bao gio rong (duong dan tuong doi).
    thu_muc_cha = os.path.dirname(os.path.abspath(duong_dan))
    if not thu_muc_cha:
        return ""
    if os.path.isdir(thu_muc_cha):
        return thu_muc_cha
    try:
        os.makedirs(thu_muc_cha, exist_ok=True)
    except OSError:
        return ""
    return thu_muc_cha


def chon_thiet_bi(che: str) -> str:
    """Tra 'cuda' hoac 'cpu'. Che 'auto' se tu do bang torch."""
    if che == "cpu":
        return "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def chon_providers(che: str) -> list[str] | None:
    """Danh sach provider cua onnxruntime cho engine khuon mat.

    FaceEngine (insightface) TU chon CUDA neu may co GPU - no KHONG DOC
    AnalysisConfig.thiet_bi. Nem khong thi chon "CPU" tren GUI chi chuyen
    YOLO sang CPU con nhan dien mat van chay GPU.

    Tra None = de FaceEngine tu chon (giu nguyen hanh vi cu khi che='auto').
    """
    if che == "cpu":
        return ["CPUExecutionProvider"]
    if che == "cuda":
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return None


# --------------------------------------------------------------------- chay

def run_analysis(
    cfg: AnalysisConfig,
    progress_cb: Callable[[Progress], bool] | None = None,
    log: Callable[[str], None] = print,
    frame_cb: Callable[[bytes], None] | None = None,
    frame_cb_interval: float = 0.0,
) -> AnalysisResult:
    """Chay toan bo pipeline. Tra ve AnalysisResult.

    progress_cb(progress) -> True/None de tiep tuc, False de DUNG ngay.
    log(dong_chu) de in ra console (mac dinh) hoac dua len GUI.
    frame_cb(jpeg_bytes) -> GOI VOI KHUNG HINH DA VE OVERLAY (khung nguoi, nhan
        ten, vung canh, badge) de GUI hien thi khi phan tich theo lo.
        None = KHONG encode, KHONG ton them gi (CLI khong bi anh huong).
    frame_cb_interval > 0 -> chi goi frame_cb moi MOT KHUNG HINH sau moi
        khoang (giay) -> giam chi phi encode. 0 = moi khung hinh.

    CHI PHI (do that 2026-10-20, video 960x540, yolo11n + ArcFace, may nay):
        encode JPEG q=80 = 2.80 ms/khung (117 KB/khung).
        frame_cb_interval=0   -> +2.81 ms/khung (~+5% so voi pipeline).
        frame_cb_interval=0.1 -> +1.07 ms/khung (~+2%) -> GUI dung muc nay.
    """
    log(HEADER.format(VERSION))

    # --- VIEC 3: --lop ma quen --nhan-vat-the truoc day bi BO QUA IM LANG.
    # Bay: tu bat + bao ro, de nguoi dung khong tuong la mat cau hinh.
    if str(cfg.lop).strip() and not cfg.nhan_vat_the:
        cfg.nhan_vat_the = True
        _log_an_toan(
            log,
            f"[thong tin] Đã bật tự động nhận diện vật thể vì có dùng --lop "
            f"({cfg.lop.strip()})",
            f"[thong tin] Da bat tu dong nhan dien vat the vi co dung --lop "
            f"({cfg.lop.strip()})",
        )

    source = 0 if str(cfg.input).strip() == "0" else cfg.input
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise CamAIError(f"[loi] khong mo duoc video: {cfg.input}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    log(f"[video] {width}x{height} @ {fps:.0f}fps, {total_frames} frame")

    if cfg.tach_o:
        log(
            "[tach-o] DANG BAT: do toan khung + 2x2 o co chong de nhan tot hon "
            "nguoi o xa"
        )
        log(
            "[tach-o] CHAM HON ~5.3 lan. Live view se rut fps. "
            "Neu chi can do nhan nguoi o gan, hay bo co nay."
        )

    try:
        detector = YOLO(cfg.model).to(chon_thiet_bi(cfg.thiet_bi))
    except Exception as exc:
        cap.release()
        raise CamAIError(f"[loi] khong nap duoc model '{cfg.model}': {exc}") from exc

    # --- vat the khac: chi ve khung + nhan + dem, KHONG tinh vao canh vung.
    # Person van chay qua pipeline cu (dem ra/vao, canh vung, mat) nhu cu.
    id_lop = {}
    ten_lop = {}                 # class_id -> nhan tieng Viet khong dau
    vat_the_ids = np.array([], dtype=int)
    if cfg.nhan_vat_the:
        id_lop = {ten: cid for cid, ten in detector.names.items()}
        yeu_cau = [x.strip() for x in str(cfg.lop).split(",") if x.strip()]
        if not yeu_cau:
            chon = [ten for ten in VAT_THE_MAC_DINH if ten in id_lop]
        elif yeu_cau[0].lower() == "all":
            chon = [ten for ten in detector.names.values() if ten != "person"]
        else:
            chon = yeu_cau
        sai = [ten for ten in chon if ten not in id_lop]
        if sai:
            cap.release()
            goi_y = _goi_y_lop(sai, id_lop)
            raise CamAIError(
                f"[loi] khong co lop vat the nay: {', '.join(sai)}"
                f"{' (' + goi_y + ')' if goi_y else ''}. "
                f"Cac lop co san: {', '.join(sorted(detector.names.values()))}. "
                f"Kiem tra chinh ta; 'all' = tat ca lop tru nguoi."
            )
        vat_the_ids = np.array(
            sorted({id_lop[ten] for ten in chon if id_lop[ten] != PERSON_CLASS_ID}),
            dtype=int,
        )
        ten_lop = {cid: ten_vat_the(ten) for cid, ten in detector.names.items()}
        log(
            f"[vat the] nhan them {len(vat_the_ids)} lop: "
            f"{', '.join(ten_lop[int(i)] for i in vat_the_ids)}"
        )

    tracker = sv.ByteTrack()

    engine = None
    if not cfg.no_face:
        try:
            from face_engine import FaceEngine

            # QUAN TRONG: import FaceEngine o day (lazy), dung y app.py cu.
            # face_engine tu nap DLL CUDA cua torch truoc khi onnxruntime
            # duoc import. Chuyen import len dau file se lam GPU chay sai.
            engine = FaceEngine(
                faces_dir=cfg.faces_dir, threshold=cfg.face_threshold,
                providers=chon_providers(cfg.thiet_bi),
            )
        except CamAIError:
            raise
        except SystemExit as exc:          # face_engine nem SystemExit khi thieu model
            cap.release()
            raise CamAIError(str(exc)) from exc
        except Exception as exc:
            cap.release()
            raise CamAIError(f"[loi] khong khoi dong duoc nhan dien mat: {exc}") from exc
    else:
        log("[thong tin] tat nhan dien khuon mat (--no-face)")

    line_zone = sv.LineZone(
        start=sv.Point(width // 2, 0),
        end=sv.Point(width // 2, height),
    )

    # --- vung canh: toa do tuong doi -> pixel theo khung hinh nay
    zone_px = None
    zone_mode = "chac"
    if cfg.vung:
        try:
            rel = load_zone(cfg.vung)
        except CamAIError:
            cap.release()
            raise
        zone_px = (
            int(rel[0] * width), int(rel[1] * height),
            int(rel[2] * width), int(rel[3] * height),
        )
        zone_mode = "nhay" if cfg.vung_nhay else "chac"
        log(
            f"[vung] {zone_px[0]},{zone_px[1]} -> {zone_px[2]},{zone_px[3]} "
            f"| che do {zone_mode}"
            f"{' | toi da ' + str(int(cfg.vung_max)) + ' nguoi' if cfg.vung_max else ''}"
            f"{' | canh dung lau ' + str(cfg.canh_lau) + 's' if cfg.canh_lau else ''}"
        )

    out_path, report_path = output_paths(cfg.output)
    # Tao thu muc cha TRUOC khi mo VideoWriter va truoc khi ghi CSV.
    # VideoWriter khong tu tao thu muc: thieu thu muc thi app chet ngay.
    thu_muc_video = tao_thu_muc_cha(out_path)
    thu_muc_bao_cao = tao_thu_muc_cha(report_path)
    # GHI TAM (.part.mp4) -> DOI TEN khi dong video. File .mp4 hong (moov atom
    # chua ghi xong) thi KHONG bao gio xuat hien voi ten dung.
    out_path_tam = duong_dan_tam(out_path)
    if don_file_tam(out_path_tam):
        log(f"[video] da don file tam cu: {out_path_tam}")
    fourcc_dung = _fourcc_ket_qua()
    if fourcc_dung == "avc1":
        _log_an_toan(
            log,
            "[video] codec: H.264 (avc1) - trình duyệt phát được video",
            "[video] codec: H.264 (avc1) - trinh duyet phat duoc video",
        )
    else:
        _log_an_toan(
            log,
            "[video] codec: MPEG-4 Part 2 (mp4v) - máy này không có encoder H.264",
            "[video] codec: MPEG-4 Part 2 (mp4v) - may nay khong co encoder H.264",
        )
    writer = cv2.VideoWriter(
        out_path_tam, cv2.VideoWriter_fourcc(*fourcc_dung), fps, (width, height)
    )
    if not writer.isOpened():
        cap.release()
        don_file_tam(out_path_tam)
        raise CamAIError(
            f"[loi] khong gia duoc file video ket qua: {out_path}\n"
            "       Thu muc cha khong tao duoc hoac khong co quyen ghi: "
            f"{thu_muc_video or os.path.dirname(os.path.abspath(out_path))}"
        )
    # File tam dang duoc ghi -> dang ky vao registry de "don file sot" khong
    # bao gio xoa nho (xem don_file_tam_trong_thu_muc).
    dang_ghi_file(out_path_tam)

    # --- VIEC 2: dung mem tren Windows (taskkill KHONG kem /F).
    tin_hieu_dung = cai_tin_hieu_dung()
    if tin_hieu_dung["ten"]:
        log(
            f"[dung] da bat tin hieu {tin_hieu_dung['ten']}: "
            f"dung mem se dong video an toan (taskkill /F van khong bat duoc)"
        )

    # --- tu luu clip: mac dinh TAT, chi bat khi co --tu-luu-clip
    recorder = None
    if cfg.tu_luu_clip:
        # QUAN TRONG: giu file tam cu video ket qua (out_path_tam). Neu thu muc
        # clip TRUNG thu muc ghi video ket qua, "don file sot" se xoa dung file
        # dang duoc VideoWriter ghi -> mat video ket qua ma app van exit 0.
        don_con_sot = don_file_tam_trong_thu_muc(cfg.tu_luu_clip, giu=(out_path_tam,))
        if don_con_sot:
            log(f"[clip] da don {len(don_con_sot)} file .part.mp4 con sot lai")
        recorder = ClipRecorder(
            cfg.tu_luu_clip, tong_giay=cfg.clip_giay, fps=fps, size=(width, height)
        )
        log(
            f"[clip] tu luu clip vao: {cfg.tu_luu_clip}"
            f" | {cfg.clip_giay:.1f}s/clip = {cfg.clip_giay / 2:.1f}s truoc"
            f" + {cfg.clip_giay / 2:.1f}s sau"
            f"{' | ghi ca khi khong co --vung' if cfg.clip_ghi_tat_ca else ''}"
        )
        if recorder.bao_nho:
            log(
                f"[clip] anh pha gian: vong dem chi giu "
                f"{recorder.so_khung_vong_dem} khung hinh de khong no RAM"
            )

    report_rows: list[dict] = []
    # --- v3.0 bien so (bien_so.py): MAC DINH TAT, chi bat khi --doc-bien-so.
    # import LAZY + trong try: bien_so.py hong thi phan tich van chay binh
    # thuong, chi mat tinh nang doc bien so (fail-safe, giong CanhBaoNoi).
    bo_doc_bien_so = None
    csv_fields = CSV_FIELDS[:]          # mac dinh DUNG 10 cot nhu cu
    if cfg.doc_bien_so:
        csv_fields = CSV_FIELDS + CSV_FIELDS_BIEN_SO
        try:
            from bien_so import BoDocBienSo

            bo_doc_bien_so = BoDocBienSo(
                nguong_tin_cay=cfg.bien_so_tin_cay,
                thu_muc_luu=cfg.bien_so_dir or "",
                nhoan_lai_giay=cfg.bien_so_nhoan_lai_giay,
                vung=cfg.vung_bien_so,
                ten_lop=detector.names,
                log=log,
            )
            co_lop_bien_so = bool(bo_doc_bien_so.id_bien_so)
            log(
                f"[bien so] DANG BAT: doc bien so Viet Nam bang RapidOCR (100% tren may)"
                f"{' | class plate co san' if co_lop_bien_so else ''}"
                f"{' | vung ROI: ' + str(cfg.vung_bien_so) if cfg.vung_bien_so else ''}"
                f" | luu crop vao: {cfg.bien_so_dir or '(khong luu)'}"
                f" | cung bien so chi luu 1 lan/{cfg.bien_so_nhoan_lai_giay:.0f}s"
            )
        except Exception as exc:                            # noqa: BLE001 - fail-safe
            bo_doc_bien_so = None
            csv_fields = CSV_FIELDS[:]         # khong bat duoc -> van 10 cot
            log(
                f"[bien so] KHONG bat duoc, chi mat tinh nang doc bien so "
                f"(khong dung app): {type(exc).__name__}: {exc}"
            )

    # --- v3.0 tu chup anh (tu_chup.py): MAC DINH TAT (chuoi rong = tat)
    chup_anh = None
    if cfg.tu_chup_dir:
        try:
            from tu_chup import TuChupAnh

            chup_anh = TuChupAnh(cfg.tu_chup_dir,
                                 nhoan_lai_giay=cfg.tu_chup_nhoan_lai_giay,
                                 log=log)
            log(
                f"[tu chup] DANG BAT: luu anh su kien vao: {cfg.tu_chup_dir}"
                f" | moi loai su kien chup 1 lan/{cfg.tu_chup_nhoan_lai_giay:.0f}s"
            )
        except Exception as exc:                            # noqa: BLE001 - fail-safe
            chup_anh = None
            log(
                f"[tu chup] KHONG bat duoc, chi mat tu chup anh "
                f"({type(exc).__name__}: {exc})"
            )

    # --- canh bao ngoai: mac dinh TAT (chi bat khi --bat-canh-bao)
    canh_bao_noi = CanhBaoNoi(cfg, log, ten_video=str(cfg.input))
    seen_names: set[str] = set()
    max_people = 0
    max_faces = 0
    frame_index = 0
    stopped = False

    # --- dem su kien trong vung
    prev_zone_count = 0
    prev_over_crowd = False
    prev_people_count = 0
    prev_known: list[str] = []
    violation_events = 0
    crowd_events = 0
    loiter_events = 0
    longest_loiter = 0.0
    entered_at: dict[int, float] = {}
    last_seen: dict[int, float] = {}
    loiter_reported: set[int] = set()
    dem_vat_the: dict[int, list[int]] = {}      # class_id -> [so khung hinh, toi da]
    # --- v3.0: bien so + tu chup anh
    ds_bien_so: dict[str, int] = {}             # bien so -> so khung hinh thay
    bien_so_da_thay: list[str] = []             # bien so thay trong video (theo thu tu)

    # --- v3.2: gui khung hinh ra GUI (che do phan tich theo lo).
    # KHONG ton them gi khi frame_cb is None -> CLI y nguyen.
    lan_gui_hinh = 0.0                          # thoi diem gui khung hinh gan nhat
    bao_loi_gui_hinh = False                    # chi bao loi callback 1 lan

    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break

            # --- nguoi: chay moi khung hinh (YOLO tren GPU, rat nhanh)
            if cfg.tach_o:
                # TOAN KHUH + 2x2 o co chong, gop NMS.
                # Cham hon ~5.3 lan. MAC DINH TAT de giu live view >=10 fps.
                tat_ca = detect_tach_o(detector, frame, cfg.conf)
            else:
                result = detector(frame, verbose=False, conf=cfg.conf)[0]
                tat_ca = sv.Detections.from_ultralytics(result)
            detections = tat_ca[tat_ca.class_id == PERSON_CLASS_ID]
            detections = tracker.update_with_detections(detections)

            people_count = len(detections)
            max_people = max(max_people, people_count)

            # --- vat the khac: chi ve + dem, khong vao pipeline cua nguoi
            vat_the = None
            if vat_the_ids.size and len(tat_ca):
                vat_the = tat_ca[np.isin(tat_ca.class_id, vat_the_ids)]
                if len(vat_the):
                    for cid in np.unique(vat_the.class_id):
                        n = int((vat_the.class_id == cid).sum())
                        rec = dem_vat_the.setdefault(int(cid), [0, 0])
                        rec[0] += 1
                        rec[1] = max(rec[1], n)
                else:
                    vat_the = None
            elif vat_the_ids.size:
                vat_the = None

            # --- khuon mat: quet theo --face-every de tiet kiem thoi gian
            face_results = []
            if engine is not None and frame_index % max(1, cfg.face_every) == 0:
                face_results = engine.analyze(frame, min_face_px=cfg.min_face)

            face_count = len(face_results)
            max_faces = max(max_faces, face_count)

            for face in face_results:
                x1, y1, x2, y2 = face.box
                color = (0, 220, 0) if face.is_known else (0, 200, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                text = face.label if face.is_known else "Nguoi la"
                cv2.putText(
                    frame, text, (x1, max(y1 - 8, 14)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
                )
                if face.is_known:
                    seen_names.add(face.name)

            known_here = sorted({f.name for f in face_results if f.is_known})

            # --- v3.0 bien so: OCR tren KHUNG HINH GOC (truoc khi lam mo nen,
            # neu lam mo thi OCR khong doc duoc). Dung lai `tat_ca` cua YOLO
            # san co -> KHONG chay them 1 lan YOLO moi khung hinh.
            bs_frame: list = []
            if bo_doc_bien_so is not None:
                try:
                    bs_frame = bo_doc_bien_so.doc(
                        frame, detections=tat_ca, so_mat_rang=face_count,
                        khuon_mat=[f.box for f in face_results],
                    )
                    for r in bs_frame:
                        if r.duong_dan:
                            ds_bien_so[r.chuoi] = ds_bien_so.get(r.chuoi, 0) + 1
                        if r.chuoi not in bien_so_da_thay:
                            bien_so_da_thay.append(r.chuoi)
                except Exception as exc:                    # noqa: BLE001 - fail-safe
                    log(
                        f"[bien so] loi khi doc 1 khung hinh, tat nhac lai "
                        f"({type(exc).__name__}: {exc})"
                    )
                    bo_doc_bien_so = None

            # --- lam mo nen
            if cfg.pixelate and people_count:
                pixelated = sv.PixelateAnnotator(pixel_size=24).annotate(
                    scene=frame.copy(), detections=sv.Detections.empty()
                )
                for x1, y1, x2, y2 in detections.xyxy.astype(int):
                    x1, y1 = max(x1, 0), max(y1, 0)
                    x2, y2 = min(x2, width), min(y2, height)
                    if x2 > x1 and y2 > y1:
                        pixelated[y1:y2, x1:x2] = frame[y1:y2, x1:x2]
                frame = pixelated

            # --- canh vung: ai dang o trong vung, co bi canh bao khong
            now = frame_index / fps
            zone_count = 0
            loiter_count = 0
            if zone_px is not None:
                inside_ids: set[int] = set()
                boxes = detections.xyxy
                for i in range(people_count):
                    box = (
                        float(boxes[i][0]), float(boxes[i][1]),
                        float(boxes[i][2]), float(boxes[i][3]),
                    )
                    hit = (
                        person_touches(box, zone_px)
                        if zone_mode == "nhay"
                        else person_inside(box, zone_px)
                    )
                    if not hit:
                        continue
                    zone_count += 1
                    tid = track_id_at(detections, i)
                    if tid is not None:
                        inside_ids.add(tid)

                # Nguoi mat tam thoi (bi che): chi xoa sau khi qua thoi gian
                # cho. Neu hien lai cung id thi van dung dong bo dem cu,
                # khong reset - vi day la ly do phai dem theo tracker_id.
                for tid in [t for t in entered_at if t not in inside_ids]:
                    if now - last_seen.get(tid, now) > BUU_HOI_MAT_DAU:
                        del entered_at[tid]
                        last_seen.pop(tid, None)
                        loiter_reported.discard(tid)
                for tid in inside_ids:
                    entered_at.setdefault(tid, now)
                    last_seen[tid] = now
                    held = now - entered_at[tid]
                    # Cap nhat lien tuc: longest_loiter = thoi gian DUNG THAT
                    # dai nhat, do tu luc vao vung - khong phai ban bang nguong.
                    if held > longest_loiter:
                        longest_loiter = held
                    if cfg.canh_lau and held >= cfg.canh_lau and tid not in loiter_reported:
                        loiter_reported.add(tid)
                        loiter_events += 1
                        loiter_count += 1

            if zone_count > 0 and prev_zone_count == 0:
                violation_events += 1
            over_crowd = bool(cfg.vung_max and zone_count > cfg.vung_max)
            if over_crowd and not prev_over_crowd:
                crowd_events += 1

            # --- su kien de tu luu clip (chi tinh, khong doi so lieu o tren)
            su_kien: list[str] = []
            if recorder is not None:
                if zone_count > 0 and prev_zone_count == 0:
                    su_kien.append(LY_DO_VAO_VUNG)
                if over_crowd and not prev_over_crowd:
                    su_kien.append(LY_DO_VUOT_DONG)
                if loiter_count:
                    su_kien.append(LY_DO_DUNG_LAU)
                if known_here and known_here != prev_known:
                    su_kien.append(LY_DO_NGUOI_QUEN)
                if (cfg.clip_ghi_tat_ca and zone_px is None
                        and people_count > 0 and prev_people_count == 0):
                    su_kien.append(LY_DO_CO_NGUOI)
            # --- v3.0 tu chup anh su kien: dung CHUNG bo canh su kien voi
            # tu luu clip, nhung TINH RIENG (khong dung recorder) va chi chay
            # khi AnalysisConfig.tu_chup_dir co gia tri (mac dinh rong = TAT).
            if chup_anh is not None:
                loai_chup = ""
                if zone_count > 0 and prev_zone_count == 0:
                    loai_chup = LY_DO_VAO_VUNG
                elif over_crowd and not prev_over_crowd:
                    loai_chup = LY_DO_VUOT_DONG
                elif known_here and known_here != prev_known:
                    loai_chup = LY_DO_NGUOI_QUEN
                elif loiter_count:
                    loai_chup = LY_DO_DUNG_LAU
                if loai_chup:
                    so_nguoi_chup = zone_count if zone_px is not None else people_count
                    duong_anh = chup_anh.chup(
                        frame, loai_chup, so_nguoi=so_nguoi_chup, giay_trong_video=now
                    )
                    if duong_anh:
                        log(f"[tu chup] {loai_chup}: {duong_anh}")

            prev_known = known_here
            prev_people_count = people_count
            prev_zone_count = zone_count
            prev_over_crowd = over_crowd

            # --- canh bao ngoai (canh_bao.py): chi bat khi --bat-canh-bao.
            # CanhBaoNoi tu chot: moi su kien chi bao 1 lan cho toi khi ve binh
            # thuong, nen khong keu moi khung hinh.
            if cfg.bat_canh_bao:
                canh_bao_noi.cap_nhat(
                    LY_DO_VUOT_DONG,
                    over_crowd,
                    mo_ta=(
                        f"vung canh dang co {zone_count} nguoi, "
                        f"vuot nguong {cfg.vung_max} nguoi"
                    ),
                    so_nguoi=zone_count,
                )
                canh_bao_noi.cap_nhat(
                    LY_DO_DUNG_LAU,
                    bool(loiter_count),
                    mo_ta=(
                        f"co nguoi dung trong vung canh lau hon {cfg.canh_lau:g}s"
                    ),
                    so_nguoi=zone_count,
                )

            # --- khung nguoi + duong dem
            labels = [
                f"Nguoi {int(tid)}" if tid is not None else "Nguoi"
                for tid in (detections.tracker_id if people_count else [])
            ]
            if cfg.show_box:
                frame = sv.BoxAnnotator(thickness=2).annotate(
                    scene=frame, detections=detections
                )
            if cfg.show_label:
                frame = sv.LabelAnnotator().annotate(
                    scene=frame, detections=detections, labels=labels
                )

            # --- vat the khac: khung + nhan ten lop (khong vao dem nguoi)
            if vat_the is not None:
                if cfg.show_box:
                    frame = sv.BoxAnnotator(
                        thickness=2, color=sv.Color(r=255, g=180, b=0)
                    ).annotate(scene=frame, detections=vat_the)
                if cfg.show_label:
                    frame = sv.LabelAnnotator().annotate(
                        scene=frame, detections=vat_the,
                        labels=[ten_lop[int(c)] for c in vat_the.class_id],
                    )

            line_zone.trigger(detections)
            if cfg.show_line:
                frame = sv.LineZoneAnnotator(thickness=4).annotate(
                    frame=frame, line_counter=line_zone
                )

            if zone_px is not None:
                if over_crowd:
                    zcolor = (0, 0, 255)
                    zlabel = f"VUNG QUA {cfg.vung_max} NG"
                elif zone_count:
                    zcolor = (0, 0, 255)
                    zlabel = f"VUNG CANH: {zone_count} nguoi"
                else:
                    zcolor = (0, 200, 255)
                    zlabel = "VUNG CANH"
                zx1, zy1, zx2, zy2 = zone_px
                cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), zcolor, 3)
                cv2.putText(
                    frame, zlabel, (zx1 + 8, zy1 + 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, zcolor, 2,
                )
                if loiter_count:
                    cv2.putText(
                        frame, "CO NGUOI DUNG LAU", (zx1 + 8, zy2 - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2,
                    )

            header = (
                f"Nguoi: {people_count} | Mat: {face_count} "
                f"| Vao: {line_zone.in_count} | Ra: {line_zone.out_count}"
            )
            if zone_px is not None:
                header += f" | Trong vung: {zone_count}"
            cv2.rectangle(frame, (0, 0), (width, 34), (0, 0, 0), -1)
            cv2.putText(
                frame, header, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2,
            )

            # --- v3.0: ve chu tieng Viet co dau cho bien so (PIL, KHONG cv2.putText)
            if bo_doc_bien_so is not None and bs_frame:
                try:
                    from bien_so import ve_khung_bien_so

                    frame = ve_khung_bien_so(frame, bs_frame)
                except Exception:                           # noqa: BLE001 - fail-safe
                    pass    # khong ve overlay van chay tiep, khong dung app

            writer.write(frame)

            # --- v3.2: gui khung hinh cho GUI (che do phan tich theo lo).
            # Khung hinh o day DA CO overlay (khung nguoi, nhan ten, vung canh,
            # badge) nen hien thi y hinh pipeline, khac vo hinh tho.
            # CHI encode khi co frame_cb (GUI) -> CLI khong ton them gi.
            if frame_cb is not None:
                gui_duoc = True
                if frame_cb_interval > 0:
                    luc = time.monotonic()
                    if luc - lan_gui_hinh < frame_cb_interval:
                        gui_duoc = False
                    else:
                        lan_gui_hinh = luc
                if gui_duoc:
                    try:
                        ok_jpg, buf_jpg = cv2.imencode(
                            ".jpg", frame,
                            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_CHAT_LUONG],
                        )
                        if ok_jpg:
                            frame_cb(buf_jpg.tobytes())
                    except Exception as exc:                # noqa: BLE001
                        # Callback loi KHONG BAO GIO duoc lam chet pipeline.
                        if not bao_loi_gui_hinh:
                            bao_loi_gui_hinh = True
                            log(f"[canh bao] callback khung hinh loi: {exc}")

            # --- tu luu clip: giu vong dem + ghi khi co su kien
            if recorder is not None:
                recorder.feed(frame, now, su_kien)

            males = sum(1 for f in face_results if f.sex == "Nam")
            females = sum(1 for f in face_results if f.sex == "Nu")
            ages = [f.age for f in face_results if f.age]

            dong_bao_cao = {
                    "giay": round(frame_index / fps, 2),
                    "so_nguoi": people_count,
                    "so_mat": face_count,
                    "nguoi_quen": " | ".join(known_here),
                    "nam": males,
                    "nu": females,
                    "tuoi_tb": int(round(sum(ages) / len(ages))) if ages else "",
                    "trong_vung": zone_count,
                    "vi_pham": 1 if zone_count else 0,
                    "canh_lau": loiter_count,
                }
            # Cot bien so them o CUOI, chi khi --doc-bien-so bat.
            # Tat -> dung 10 cot nhu cu (khong doi bao gio).
            if bo_doc_bien_so is not None:
                dong_bao_cao["bien_so"] = " | ".join(r.chuoi for r in bs_frame)
                dong_bao_cao["so_bien_so"] = len(bs_frame)
            report_rows.append(dong_bao_cao)

            if frame_index % 50 == 0:
                log(f"  frame {frame_index}/{total_frames or '?'} | {header}")
            frame_index += 1

            if progress_cb is not None:
                progress = Progress(
                    frame_index=frame_index,
                    total_frames=total_frames,
                    so_nguoi=people_count,
                    so_mat=face_count,
                    vao=line_zone.in_count,
                    ra=line_zone.out_count,
                    trong_vung=zone_count,
                    vi_pham=1 if zone_count else 0,
                    canh_lau=loiter_count,
                    nhan_dien=" | ".join(known_here),
                )
                if progress_cb(progress) is False:
                    stopped = True
                    break

            # --- dung mem: nhan SIGTERM / SIGBREAK -> ket thuc co don dep
            if tin_hieu_dung["flag"]:
                stopped = True
                log("  [dung] nhan tin hieu dung -> dung mem, dong video an toan")
                break
    finally:
        cap.release()
        writer.release()
        if recorder is not None:
            recorder.ket_thuc()      # dong clip dang ghi + xoa vong dem
        if chup_anh is not None:
            chup_anh.dong()          # ghi CSV bang ke cac lan chup
        canh_bao_noi.dong()
        # Chi sau khi release() (da ghi xong moov atom) moi doi ten that.
        if not chuyen_ten_sau_khi_dong(out_path_tam, out_path):
            _log_an_toan(
                log,
                f"[video] ⚠ không ghi được video kết quả, xem {out_path_tam}",
                f"[video] khong gia duoc video ket qua, xem {out_path_tam}",
            )
        # Da ghi xong -> bo dang ky, tu lan sau moi duoc don file sot.
        ngung_ghi_file(out_path_tam)

    # Bao cao CSV: cung thu muc cha phai co, va loi phai ra ro rang.
    if not thu_muc_bao_cao:
        thu_muc_bao_cao = tao_thu_muc_cha(report_path)
    if not thu_muc_bao_cao:
        raise CamAIError(
            f"[loi] khong tao duoc thu muc cho file bao cao: {report_path}\n"
            "       Thu muc cha khong tao duoc hoac khong co quyen ghi: "
            f"{os.path.dirname(os.path.abspath(report_path))}"
        )
    try:
        with open(report_path, "w", newline="", encoding="utf-8-sig") as file:
            csv_writer = csv.DictWriter(file, fieldnames=csv_fields)
            csv_writer.writeheader()
            csv_writer.writerows(report_rows)
    except OSError as exc:
        raise CamAIError(
            f"[loi] khong ghi duoc file bao cao: {report_path}\n"
            f"       Thu muc cha khong co quyen ghi: {thu_muc_bao_cao} ({exc})"
        ) from exc

    all_males = sum(r["nam"] for r in report_rows)
    all_females = sum(r["nu"] for r in report_rows)
    all_ages = [r["tuoi_tb"] for r in report_rows if r["tuoi_tb"] != ""]

    duration = timedelta(seconds=len(report_rows) / fps)
    log("\n========== KET QUA ==========")
    log(f"Video ket qua : {out_path}")
    log(f"Bao cao       : {report_path}")
    log(f"Do dai        : {duration}")
    log(f"Nguoi nhieu nhat trong 1 khung hinh: {max_people}")
    if zone_px is not None:
        peak_zone = max((r["trong_vung"] for r in report_rows), default=0)
        log("\n--- CANH VUNG ---")
        log(
            f"Vung          : {zone_px[0]},{zone_px[1]} -> {zone_px[2]},{zone_px[3]}"
            f" (che do {zone_mode})"
        )
        log(f"So nguoi nhieu nhat trong vung: {peak_zone}")
        log(f"So lan co nguoi vao vung: {violation_events}")
        if cfg.vung_max:
            log(
                f"Nguong {cfg.vung_max} nguoi: vuot {crowd_events} lan"
                f"{' (CANH BAO)' if crowd_events else ''}"
            )
        if cfg.canh_lau:
            if loiter_events:
                log(
                    f"Dung lau hon {cfg.canh_lau}s: {loiter_events} lan"
                    f"{f', lan dai nhat {longest_loiter:.1f}s' if longest_loiter else ''}"
                )
            else:
                log(f"Dung lau hon {cfg.canh_lau}s: 0 lan, khong co")
            # Dong nay de kiem chung: so nay do that, khong phai ban nguong.
            log(f"Nguoi dung lao nhat: {longest_loiter:.1f}s")
    if engine is not None:
        log(f"Mat nhieu nhat trong 1 khung hinh: {max_faces}")
        log(f"Nguoi da hoc trong video: {sorted(seen_names) or 'khong co'}")
        log(f"Uoc luong gioi tinh: {all_females} nu, {all_males} nam")
        if all_ages:
            log(f"Uoc luong tuoi   : trung binh {int(round(np.mean(all_ages)))} tuoi")
    if cfg.nhan_vat_the:
        log("\n--- VAT THE KHAC ---")
        if dem_vat_the:
            for cid in sorted(dem_vat_the, key=lambda c: ten_lop.get(c, str(c))):
                so_khung, toi_da = dem_vat_the[cid]
                log(
                    f"{ten_lop.get(cid, cid):<12}: {so_khung} khung hinh,"
                    f" toi da {toi_da}"
                )
        else:
            log("khong phat hien vat the khac trong video nay")
    if recorder is not None:
        log("\n--- TU LUU CLIP ---")
        log(f"Clip da luu: {len(recorder.ket_qua)} file")
        for i, duong_dan in enumerate(recorder.ket_qua, 1):
            log(f"  {i}. {duong_dan}")
        for dong_bo in recorder.chi_tiet:
            if dong_bo.startswith("BO QUA"):
                log(f"  {dong_bo}")
    if cfg.bat_canh_bao:
        log("\n--- CANH BAO ---")
        if canh_bao_noi.bat_duoc:
            log(f"Su kien da canh bao: {canh_bao_noi.so_su_kien}")
        else:
            log(f"KHONG bat duoc canh bao: {canh_bao_noi.loi or 'khong ro'}")
            log("Phan tich van chay binh thuong, chi khong co canh bao.")
    # --- v3.0: ket qua bien so + tu chup anh (chi in khi bat) ---
    if cfg.doc_bien_so:
        log("\n--- BIEN SO ---")
        if bo_doc_bien_so is None:
            log("KHONG chay duoc doc bien so (xem dong canh bao o tren).")
        elif not bien_so_da_thay:
            log(
                "Khong doc duoc bien so nao trong video nay. "
                "Thu khoang trong khung hinh, hoac chon model co class 'plate'."
            )
        else:
            for chuoi, so_khung in sorted(ds_bien_so.items(), key=lambda kv: -kv[1]):
                log(f"  {chuoi:<14}: thay trong {so_khung} khung hinh")
            log(f"Tong so bien so khac nhau: {len(bien_so_da_thay)}")
            thong_ke = bo_doc_bien_so.thong_ke()
            log(
                f"Anh bien so da luu: {thong_ke['da_luu']} file "
                f"(bo qua vi co mat: {thong_ke['bo_qua_mat']}) | "
                f"{thong_ke['so_lan_doc']} lan doc, "
                f"{thong_ke['ms_trung_binh']:.0f} ms/anh"
            )
    if chup_anh is not None:
        log("\n--- TU CHUP ANH ---")
        if chup_anh.ket_qua:
            log(f"Anh da chup: {len(chup_anh.ket_qua)} file vao {chup_anh.thu_muc}")
            for i, dong in enumerate(chup_anh.ket_qua, 1):
                log(
                    f"  {i}. [{dong['thoi_diem']}] {dong['ten_hien_thi']}"
                    f" ({dong['so_nguoi']} nguoi) - {dong['duong_dan']}"
                )
        else:
            log("Khong co su kien nao duoc chup trong video nay.")
    log("==============================")

    return AnalysisResult(
        out_path=out_path,
        report_path=report_path,
        frames=len(report_rows),
        fps=fps,
        duration=duration,
        max_people=max_people,
        max_faces=max_faces,
        seen_names=sorted(seen_names),
        males=all_males,
        females=all_females,
        avg_age=int(round(float(np.mean(all_ages)))) if all_ages else 0,
        zone_px=zone_px,
        zone_mode=zone_mode,
        peak_zone=peak_zone if zone_px is not None else 0,
        violation_events=violation_events,
        crowd_events=crowd_events,
        loiter_events=loiter_events,
        longest_loiter=longest_loiter,
        used_face=engine is not None,
        clips=list(recorder.ket_qua) if recorder is not None else [],
        bien_so=list(bien_so_da_thay),
        anh_su_kien=[d["duong_dan"] for d in chup_anh.ket_qua] if chup_anh else [],
        stopped=stopped,
    )