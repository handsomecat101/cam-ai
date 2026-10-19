r"""DO THONG LUU THAT cua ban PHAN TICH FILE (khong phai ban xem truc tiep).

Khong sua cam_ai_core / app.py / gui.py / gui_khung.py / canh_bao.py.

Cach dung (chay tu thu muc cam-ai):
    .\.venv\Scripts\python.exe _kk_do_thong_luu.py <giai_doan> [so_video]
    giai_doan: decode | yolo | ad | e | f | g | h

Ket gia tung giai doan ghi ra _kk_out\do_thong_luu\<giai_doan><video>.json.

GHI CHU QUAN TRONG:
  - A-D do bang HAM SAN PHAM run_analysis() cua cam_ai_core (keo ca ve khung,
    ghi file mp4, ghi CSV) => do dung thoi gian nguoi dung phai chiu khi bam
    "BAT DAU" trong GUI.
  - E/F/G do bang VONG LAP TOI GIAN (doc video -> YOLO -> ByteTrack), KHONG ve
    khung, KHONG ghi video. Dung de do rieng dang gop cua YOLO nhu yeu cau.
    => So san A/B voi E(N=1) moi biet chi phi ve + ghi file la bao nhieu.
"""

from __future__ import annotations

import json
import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

OUT_DIR = os.path.join(APP_DIR, "_kk_out", "do_thong_luu")

VIDEO = [
    "video_test.mp4",
    os.path.join("video_mau", "moi", "nguoi-dung-cho.mp4"),
    os.path.join("video_mau", "moi", "xe-co-giao-thong.mp4"),
]
VIDEO_TEN = ["video_test", "nguoi-dung-cho", "xe-co-giao-thong"]

WARMUP = 1.0
DO_GIAY = 3.0


# ------------------------------------------------------------------ tien ich

def _luu(ten: str, du_lieu: dict) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    duong = os.path.join(OUT_DIR, ten + ".json")
    with open(duong, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(du_lieu, fh, ensure_ascii=False, indent=2)
    print(f"[luu] {duong}", flush=True)


def _bo_nho_gpu() -> None:
    try:
        import torch

        torch.cuda.empty_cache()
    except Exception:                                   # noqa: BLE001
        pass


class Dem:
    """Dem khung trong 1s warm-up roi DO 3s, dung chung cho moi phep do."""

    def __init__(self) -> None:
        self.t0 = None
        self.t_do = None
        self.n_warm = 0
        self.n = 0
        self.people: list[int] = []
        self.giay_do = 0.0

    def cb(self, p) -> bool:
        if self.t0 is None:
            self.t0 = time.perf_counter()
            return True
        if self.t_do is None:
            if time.perf_counter() - self.t0 < WARMUP:
                self.n_warm = p.frame_index
                return True
            self.t_do = time.perf_counter()
            self.n_warm = p.frame_index
            return True
        self.people.append(int(p.so_nguoi))
        if time.perf_counter() - self.t_do >= DO_GIAY:
            self.giay_do = time.perf_counter() - self.t_do
            self.n = int(p.frame_index) - self.n_warm
            return False
        return True

    @property
    def fps(self) -> float:
        return (self.n / self.giay_do) if self.giay_do > 0 else 0.0

    @property
    def nguoi_tb(self) -> float:
        return (sum(self.people) / len(self.people)) if self.people else 0.0


# ------------------------------------------------------- giai doan: doc video

def giai_doan_decode(iv: int) -> dict:
    """Chi giai ma video, khong YOLO. Do rieng chi phi giai ma."""
    import cv2

    duong = VIDEO[iv]
    cap = cv2.VideoCapture(duong)
    if not cap.isOpened():
        return {"video": VIDEO_TEN[iv], "loi": "khong mo duoc video"}
    dem = Dem()
    n = 0
    t0 = None
    t_do = None
    n_warm = 0
    # video_test.mp4 chi 10s: giai ma nhanh hon ca cua so do (4s > 10s video
    # mau o ~670 fps se het file). KHUYEN VIDEO VE DAU khi het de do du 3s.
    so_lan_quay = 0
    while True:
        ok, _ = cap.read()
        if not ok:
            so_lan_quay += 1
            cap.release()
            cap = cv2.VideoCapture(duong)
            ok, _ = cap.read()
            if not ok:
                break
        n += 1
        if t0 is None:
            t0 = time.perf_counter()
            continue
        if t_do is None:
            if time.perf_counter() - t0 < WARMUP:
                n_warm = n
                continue
            t_do = time.perf_counter()
            n_warm = n
            continue
        if time.perf_counter() - t_do >= DO_GIAY:
            dem.giay_do = time.perf_counter() - t_do
            dem.n = n - n_warm
            break
    cap.release()
    return {
        "video": VIDEO_TEN[iv],
        "khung": dem.n,
        "giay": round(dem.giay_do, 3),
        "fps_doc": round(dem.fps, 2),
    }


def giai_doan_yolo(iv: int) -> dict:
    """Chi chay YOLO tren khung da doc san. Do rieng chi phi suy luan."""
    import cv2
    from ultralytics import YOLO

    duong = VIDEO[iv]
    cap = cv2.VideoCapture(duong)
    khung = []
    while len(khung) < 200:
        ok, fr = cap.read()
        if not ok:
            cap.release()
            if len(khung) < 5:
                return {"video": VIDEO_TEN[iv], "loi": "video qua ngan"}
            break
        khung.append(fr)
    cap.release()

    mo = YOLO("yolo11n.pt")
    if not mo.predict(khung[0], verbose=False, conf=0.25, imgsz=640):
        return {"video": VIDEO_TEN[iv], "loi": "yolo that bai"}

    dem = Dem()
    i = 0
    t0 = None
    t_do = None
    n_warm = 0
    n = 0
    dem_nguoi = 0
    while True:
        fr = khung[i % len(khung)]
        res = mo(fr, verbose=False, conf=0.25)[0]
        dem_nguoi += int((res.boxes.cls == 0).sum()) if res.boxes is not None else 0
        i += 1
        n += 1
        if t0 is None:
            t0 = time.perf_counter()
            continue
        if t_do is None:
            if time.perf_counter() - t0 < WARMUP:
                n_warm = n
                dem_nguoi = 0
                continue
            t_do = time.perf_counter()
            n_warm = n
            dem_nguoi = 0
            continue
        if time.perf_counter() - t_do >= DO_GIAY:
            dem.giay_do = time.perf_counter() - t_do
            dem.n = n - n_warm
            break
    du_lieu = {
        "video": VIDEO_TEN[iv],
        "khung": dem.n,
        "giay": round(dem.giay_do, 3),
        "fps_yolo": round(dem.fps, 2),
        "ms_khung": round(dem.giay_do / dem.n * 1000, 2) if dem.n else 0,
        "nguoi_tb": round(dem_nguoi / dem.n, 2) if dem.n else 0,
    }
    del mo
    _bo_nho_gpu()
    return du_lieu


# --------------------------------------------- giai doan A-D: HAM SAN PHAM

def giai_doan_ad(iv: int) -> dict:
    """Do bang chinh run_analysis() cua cam_ai_core - dung y GUI bat dau."""
    from cam_ai_core import AnalysisConfig, run_analysis

    duong = os.path.join(APP_DIR, "_kk_out", "do_thong_luu", "video_ad")
    os.makedirs(duong, exist_ok=True)

    cau_hinh = {
        "A": dict(no_face=False, conf=0.25),
        "B": dict(no_face=True, conf=0.25),
        "C": dict(no_face=True, conf=0.40),
        "D": dict(no_face=True, conf=0.50),
    }
    ket_qua = {}
    for nhan, tu_khoa in cau_hinh.items():
        cfg = AnalysisConfig(
            input=os.path.join(APP_DIR, VIDEO[iv]),
            output=os.path.join(duong, f"{nhan}_{VIDEO_TEN[iv]}.mp4"),
            model="yolo11n.pt",
            **tu_khoa,
        )
        dem = Dem()
        t_bat_dau = time.perf_counter()
        loi = ""
        try:
            run_analysis(cfg, progress_cb=dem.cb, log=lambda _s: None)
        except Exception as exc:                        # noqa: BLE001
            loi = f"{type(exc).__name__}: {exc}"
        tong = time.perf_counter() - t_bat_dau
        ket_qua[nhan] = {
            "video": VIDEO_TEN[iv],
            "cau_hinh": tu_khoa,
            "khung": dem.n,
            "giay_do": round(dem.giay_do, 3),
            "fps": round(dem.fps, 2),
            "nguoi_tb": round(dem.nguoi_tb, 2),
            "giay_ca_nhap": round(tong, 2),
            "loi": loi,
        }
        print(
            f"  {nhan} {VIDEO_TEN[iv]}: {dem.fps:.2f} fps "
            f"({dem.n} khung / {dem.giay_do:.2f}s) nguoi_tb={dem.nguoi_tb:.2f}"
            f"  nap+tong={tong:.2f}s {loi}",
            flush=True,
        )
        _bo_nho_gpu()
    return ket_qua


# --------------------------------- giai doan E/F/G: vong lap toi gian (core)

def _vong_lap(
    iv: int,
    moi_n_khung: int,
    che_do: str,
    imgsz: int = 640,
    conf: float = 0.25,
) -> dict:
    """Doc video -> YOLO moi N khung -> ByteTrack. KHONG ve, KHONG ghi file.

    che_do:
      "giai_ma"  (E): khung xen ke MANG lai detections cu, KHONG chay tracker
      "tracker" (F): khung xen ke chay tracker.update_with_detections
    """
    import cv2
    import supervision as sv
    from ultralytics import YOLO

    duong = VIDEO[iv]
    cap = cv2.VideoCapture(duong)
    if not cap.isOpened():
        return {"video": VIDEO_TEN[iv], "loi": "khong mo duoc video"}

    mo = YOLO("yolo11n.pt")
    tracker = sv.ByteTrack()
    dem = Dem()

    t0 = None
    t_do = None
    n = 0
    n_warm = 0
    tong_nguoi = 0
    dem_nguoi = 0
    so_khung_yeu = 0
    so_lan_quay = 0
    detections = None
    while True:
        ok, fr = cap.read()
        if not ok:
            # video ngan (video_test.mp4 chi 250 khung): khi chay nhanh hon
            # 4s (warm-up + do) thi het file truoc khi du cua so do.
            # KHUYEN VIDEO VE DAU de luon du 3s do.
            so_lan_quay += 1
            cap.release()
            cap = cv2.VideoCapture(duong)
            ok, fr = cap.read()
            if not ok:
                break
        chay_yolo = (n % moi_n_khung == 0)
        if chay_yolo:
            res = mo(fr, verbose=False, conf=conf, imgsz=imgsz)[0]
            tat_ca = sv.Detections.from_ultralytics(res)
            detections = tat_ca[tat_ca.class_id == 0]
            if che_do == "tracker":
                detections = tracker.update_with_detections(detections)
            so_khung_yeu += 1
        else:
            if detections is None:
                continue
            if che_do == "tracker":
                detections = tracker.update_with_detections(detections)

        nguoi = int(len(detections)) if detections is not None else 0
        n += 1
        if t0 is None:
            t0 = time.perf_counter()
            continue
        if t_do is None:
            if time.perf_counter() - t0 < WARMUP:
                n_warm = n
                dem_nguoi = 0
                continue
            t_do = time.perf_counter()
            n_warm = n
            dem_nguoi = 0
            continue
        dem_nguoi += nguoi
        if time.perf_counter() - t_do >= DO_GIAY:
            dem.giay_do = time.perf_counter() - t_do
            dem.n = n - n_warm
            break
    cap.release()
    du_lieu = {
        "video": VIDEO_TEN[iv],
        "N": moi_n_khung,
        "che_do": che_do,
        "imgsz": imgsz,
        "khung": dem.n,
        "giay": round(dem.giay_do, 3),
        "fps": round(dem.fps, 2),
        "nguoi_tb": round(dem_nguoi / dem.n, 2) if dem.n else 0,
        "ty_le_yeu": round(1.0 / moi_n_khung, 3),
        "so_khung_chay_yolo": so_khung_yeu,
    }
    del mo, tracker
    _bo_nho_gpu()
    return du_lieu


def giai_doan_e(iv: int) -> dict:
    ra = {}
    for n_khung in (1, 2, 3, 5, 10):
        ra[f"N{n_khung}"] = _vong_lap(iv, n_khung, "giai_ma")
        print(
            f"  E N={n_khung} {VIDEO_TEN[iv]}: {ra[f'N{n_khung}']['fps']:.2f} fps"
            f" nguoi_tb={ra[f'N{n_khung}']['nguoi_tb']:.2f}",
            flush=True,
        )
    return ra


def giai_doan_f(iv: int) -> dict:
    ra = {}
    for n_khung in (5, 10):
        ra[f"N{n_khung}"] = _vong_lap(iv, n_khung, "tracker")
        print(
            f"  F N={n_khung} {VIDEO_TEN[iv]}: {ra[f'N{n_khung}']['fps']:.2f} fps"
            f" nguoi_tb={ra[f'N{n_khung}']['nguoi_tb']:.2f}",
            flush=True,
        )
    return ra


def giai_doan_g(iv: int) -> dict:
    ra = {}
    for imgsz in (320, 416, 512, 640):
        ra[f"imgsz{imgsz}"] = _vong_lap(iv, 1, "tracker", imgsz=imgsz)
        print(
            f"  G imgsz={imgsz} {VIDEO_TEN[iv]}: "
            f"{ra[f'imgsz{imgsz}']['fps']:.2f} fps"
            f" nguoi_tb={ra[f'imgsz{imgsz}']['nguoi_tb']:.2f}",
            flush=True,
        )
    return ra


# ------------------------------------------------- giai doan H: nap model

def giai_doan_h(iv: int = 0) -> dict:
    """Model YOLO co duoc dung lai hay nap lai moi lan goi khong?"""
    import time as _t

    from ultralytics import YOLO

    from cam_ai_core import AnalysisConfig

    ra = {"so_lan_goi": 5, "giay_moi_lan": [], "giay_trung_binh": 0.0}
    for _ in range(ra["so_lan_goi"]):
        t = _t.perf_counter()
        YOLO("yolo11n.pt")
        ra["giay_moi_lan"].append(round(_t.perf_counter() - t, 3))
    ra["giay_trung_binh"] = round(sum(ra["giay_moi_lan"]) / len(ra["giay_moi_lan"]), 3)

    t = _t.perf_counter()
    cfg = AnalysisConfig()
    cfg.input = "0"          # webcam: fail ngay, chi de xem co load model truoc khong
    ra["cfg_mac_dinh"] = {
        "model": cfg.model,
        "conf": cfg.conf,
        "no_face": cfg.no_face,
        "thiet_bi": cfg.thiet_bi,
        "tach_o": cfg.tach_o,
    }
    ra["giay_doc_cfg"] = round(_t.perf_counter() - t, 5)
    _bo_nho_gpu()
    return ra


# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    giai_doan = sys.argv[1].strip().lower()
    iv = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if iv < 0 or iv >= len(VIDEO):
        print(f"so video phai tu 0 den {len(VIDEO) - 1}")
        raise SystemExit(2)

    print(f"=== giai doan '{giai_doan}' tren video #{iv} ({VIDEO_TEN[iv]}) ===",
          flush=True)
    if giai_doan == "decode":
        du_lieu = giai_doan_decode(iv)
        print(f"  doc: {du_lieu.get('fps_doc')} fps", flush=True)
    elif giai_doan == "yolo":
        du_lieu = giai_doan_yolo(iv)
        print(f"  yolo: {du_lieu.get('fps_yolo')} fps", flush=True)
    elif giai_doan == "ad":
        du_lieu = giai_doan_ad(iv)
    elif giai_doan == "e":
        du_lieu = giai_doan_e(iv)
    elif giai_doan == "f":
        du_lieu = giai_doan_f(iv)
    elif giai_doan == "g":
        du_lieu = giai_doan_g(iv)
    elif giai_doan == "h":
        du_lieu = giai_doan_h(iv)
    else:
        print(f"giai doan khong ro: {giai_doan}")
        raise SystemExit(2)

    _luu(f"{giai_doan}{iv}", du_lieu)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())