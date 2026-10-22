# -*- coding: utf-8 -*-
"""
Kiem chung TOC DO + HOI QUY cho toi uu detector CamAI (CUDA Graph).

Chay 1 file nay de co bang chung day du:

  1. BANG HO SO component (doc truc tiep trong vong lap that cua cam_ai_core,
     bien moi truong CAMAI_PROFILE=1) - TRUOC (duong cu cu) vs SAU (CUDA Graph).
  2. END-TO-END khung/s tren video_mau/car-detection.mp4 + 1 video dai hon.
     - "TRUOC" = ban goc (git HEAD, file _kk_core_goc.py) - khong dung gi ca nhanh
     - "SAU"   = ban moi (cam_ai_core.py + nhan_dien_nhanh.py)
  3. HOI QUY CSV: CSV khi tat moi tinh nang phai giong het ban goc
     (SHA256 + so dong + so cot).
  4. HOI QUY DEM: so luot dem phuong tien truoc/sau phai khop (chenh <= 1%).

Dung:
    $env:PYTHONIOENCODING='utf-8'
    & 'H:\\AI Project\\cam-ai\\.venv\\Scripts\\python.exe' -W ignore `
        'H:\\AI Project\\cam-ai\\_kk_kiem_toc_do.py'
"""
from __future__ import annotations

import csv
import hashlib
import importlib
import io
import os
import sys
import time

APP = os.path.dirname(os.path.abspath(__file__))
if APP not in sys.path:
    sys.path.insert(0, APP)

OUT = os.path.join(APP, "_kk_out", "toc_do")
VIDEO_CHINH = os.path.join(APP, "video_mau", "car-detection.mp4")
VIDEO_DAI = os.path.join(APP, "video_mau", "people-detection.mp4")
VIDEO_CSV = os.path.join(APP, "video_test.mp4")      # video chuan 250 khung


# ------------------------------------------------------------------ tien ich

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def doc_csv(path: str) -> tuple[int, int, list[str]]:
    """Tra ve (so dong du lieu, so cot, ten cot)."""
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return 0, 0, []
    return len(rows) - 1, len(rows[0]), rows[0]


def chay_analysis(module, video: str, ten: str, **kw):
    """Chay run_analysis cua 1 module cam_ai_core (ban goc hoac ban moi).

    Tra ve (ket_qua, duong_dan_csv, giay_chay, dong_log).
    """
    os.makedirs(OUT, exist_ok=True)
    ra = os.path.join(OUT, f"{ten}.mp4")
    cfg = module.AnalysisConfig(input=video, output=ra, **kw)
    dong = []
    buf = io.StringIO()
    t0 = time.perf_counter()
    ket_qua = module.run_analysis(
        cfg,
        log=lambda s: (dong.append(s), buf.write(str(s) + "\n")),
    )
    giay = time.perf_counter() - t0
    return ket_qua, ket_qua.report_path, giay, dong


def lay_profile(dong_log: list[str]) -> dict:
    """Lay cac dong 'HO SO THOI GIAN' tu log de in ra bang."""
    ra = []
    bat = False
    for d in dong_log:
        if "HO SO THOI GIAN" in d:
            bat = True
        if bat:
            ra.append(d)
        if bat and d.startswith("====") and "HO SO" not in d:
            break
    return ra


def so_khung_video(path: str) -> int:
    import cv2
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    return n


def fps_gia_nghien(dong_log: list[str]) -> float:
    """Doc dong 'GIA NGHIEN (khung 2..N)' tu log ho so."""
    for d in dong_log:
        if "GIA NGHIEN" in d and "khung/s" in d:
            try:
                return float(d.split("khung/s")[0].split("|")[-1].strip())
            except ValueError:
                pass
    return 0.0


def in_bang_profile(nhan: str, dong_log: list[str]) -> None:
    print()
    print(f"--- HO SO: {nhan} ---")
    for d in lay_profile(dong_log):
        print("   " + d)


# ------------------------------------------------------------------ chinh

def do_e2e(module, video, ten, env_off: bool = False, **kw):
    """Chay 1 lan phan tich trong PROCESS RIENG (do wall clock cong bang).

    Chay chung process se lam sai: lan chay sau se duoc CUDA da khoi tao
    (chay dau tien ton ~5 s khoi tao CUDA) -> so do co loi.
    """
    import subprocess
    env = dict(os.environ)
    env["CAMAI_PROFILE"] = "1"
    if env_off:
        env["CAMAI_DETECTOR_NHANH"] = "0"
    else:
        env.pop("CAMAI_DETECTOR_NHANH", None)
    t0 = time.perf_counter()
    ket = subprocess.run(
        [sys.executable, "-W", "ignore", os.path.abspath(__file__),
         f"--phase=single", f"--mod={ten}", f"--video={video}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=APP, env=env,
    )
    giay = time.perf_counter() - t0
    n = 0
    fps_gia = 0.0
    for d in (ket.stdout or "").splitlines():
        if d.startswith("KET_QUA_KHUNG="):
            n = int(d.split("=", 1)[1])
        if "GIA NGHIEN" in d and "khung/s" in d:
            try:
                fps_gia = float(d.split("khung/s")[0].split("|")[-1].strip())
            except ValueError:
                pass
    return {"khung": n, "giay": giay, "fps": n / giay if giay else 0.0,
            "fps_gia": fps_gia}


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    phase = "all"
    ten_mod = ""
    video = ""
    for a in sys.argv[1:]:
        if a.startswith("--phase="):
            phase = a.split("=", 1)[1].strip()
        elif a.startswith("--mod="):
            ten_mod = a.split("=", 1)[1].strip()
        elif a.startswith("--video="):
            video = a.split("=", 1)[1].strip()
    print("=" * 78)
    print("KIEM CHUNG TOC DO + HOI QUY - detector nhanh (CUDA Graph)")
    print(f"phase: {phase}")
    print("=" * 78)

    if phase == "single":
        # Chay 1 lan phan tich, in ra so khung (de parent do wall clock).
        if ten_mod == "goc":
            mod = importlib.import_module("_kk_core_goc")
        else:
            mod = importlib.import_module("cam_ai_core")
        ket, csv_p, giay, dong = chay_analysis(mod, video, "single_" + ten_mod,
                                                no_face=True)
        for d in dong:
            print(d)
        print(f"KET_QUA_KHUNG={ket.frames}")
        return 0

    core_moi = importlib.import_module("cam_ai_core")
    core_goc = importlib.import_module("_kk_core_goc")

    print(f"\nVideo chinh : {VIDEO_CHINH} ({so_khung_video(VIDEO_CHINH)} khung)")
    print(f"Video dai   : {VIDEO_DAI} ({so_khung_video(VIDEO_DAI)} khung)")
    print(f"Video CSV   : {VIDEO_CSV} ({so_khung_video(VIDEO_CSV)} khung)")

    fps_truoc = 0.0
    fps_sau = 0.0
    csv_ok = True

    # =====================================================================
    # 1. HO SO COMPONENT: TRUOC (duong cu cu) vs SAU (CUDA Graph)
    # =====================================================================
    if phase in ("all", "profile"):
        os.environ["CAMAI_PROFILE"] = "1"

        os.environ["CAMAI_DETECTOR_NHANH"] = "0"
        _, csv_truoc_p, g_truoc, log_truoc = chay_analysis(
            core_moi, VIDEO_CHINH, "truoc", no_face=True,
        )
        os.environ["CAMAI_DETECTOR_NHANH"] = "1"
        _, csv_sau_p, g_sau, log_sau = chay_analysis(
            core_moi, VIDEO_CHINH, "sau", no_face=True,
        )
        os.environ.pop("CAMAI_DETECTOR_NHANH", None)
        in_bang_profile("TRUOC (duong cu cu cua ultralytics)", log_truoc)
        in_bang_profile("SAU (CUDA Graph)", log_sau)

        fps_truoc = fps_gia_nghien(log_truoc)
        fps_sau = fps_gia_nghien(log_sau)
        print()
        print(f">>> GIA NGHIEN tren {os.path.basename(VIDEO_CHINH)}: "
              f"TRUOC {fps_truoc:.2f} khung/s -> SAU {fps_sau:.2f} khung/s "
              f"({fps_sau / max(fps_truoc, 1e-9):.2f} lan)")

    # =====================================================================
    # 2. END-TO-END: BAN GOC (git HEAD) vs BAN MOI
    # =====================================================================
    if phase in ("all", "e2e"):
        os.environ.pop("CAMAI_PROFILE", None)

        print()
        print("=" * 78)
        print("END-TO-END (wall clock, bao gom model load) - khung/s")
        print("=" * 78)
        print("Moi lan chay trong PROCESS RIENG -> do wall clock cong bang.")

        for video, nhan in ((VIDEO_CHINH, "car-detection.mp4"),
                            (VIDEO_DAI, "people-detection.mp4")):
            a = do_e2e(core_goc, video, "goc")               # ban goc git HEAD
            c = do_e2e(core_moi, video, "cu", env_off=True)  # duong cu cu co ho so
            b = do_e2e(core_moi, video, "moi")               # ban moi
            print(f"\n{nhan}:")
            print(f"   TRUOC (git HEAD)     : {a['khung']:4d} khung | "
                  f"{a['giay']:7.2f} s | {a['fps']:7.2f} khung/s (wall clock)")
            print(f"   TRUOC (duong cu cu)  : {c['khung']:4d} khung | "
                  f"{c['giay']:7.2f} s | {c['fps']:7.2f} khung/s (wall clock) | "
                  f"{c['fps_gia']:7.2f} khung/s (gia ngien)")
            print(f"   SAU  (moi)           : {b['khung']:4d} khung | "
                  f"{b['giay']:7.2f} s | {b['fps']:7.2f} khung/s (wall clock) | "
                  f"{b['fps_gia']:7.2f} khung/s (gia ngien)")
            if c['fps_gia']:
                print(f"   -> nhanh {b['fps_gia'] / c['fps_gia']:.2f} lan (gia ngien)")
            if a['giay']:
                print(f"   -> wall clock {a['giay'] / b['giay']:.2f} lan "
                      f"(wall clock bao gom khoi dong Python + khoi tao CUDA ~12 s)")

    # =====================================================================
    # 3. HOI QUY CSV: SHA256 + so dong + so cot
    # =====================================================================
    if phase in ("all", "csv"):
        os.environ.pop("CAMAI_PROFILE", None)
        print()
        print("=" * 78)
        print("HOI QUY CSV (tinh nang moi TAT - 10 cot, phai giong het ban goc)")
        print("=" * 78)

        ket_goc, csv_goc, _, _ = chay_analysis(core_goc, VIDEO_CSV, "csv_goc")
        ket_moi, csv_moi, _, _ = chay_analysis(core_moi, VIDEO_CSV, "csv_moi")

        h_goc, h_moi = sha256(csv_goc), sha256(csv_moi)
        d_goc, c_goc, ten_cot_goc = doc_csv(csv_goc)
        d_moi, c_moi, ten_cot_moi = doc_csv(csv_moi)

        print(f"\nBan goc : {csv_goc}")
        print(f"   SHA256 : {h_goc}")
        print(f"   dong   : {d_goc} | cot: {c_goc} | {ten_cot_goc}")
        print(f"Ban moi : {csv_moi}")
        print(f"   SHA256 : {h_moi}")
        print(f"   dong   : {d_moi} | cot: {c_moi} | {ten_cot_moi}")

        csv_ok = (h_goc == h_moi) and (d_goc == d_moi) and (c_goc == c_moi)
        print(f"\n   SHA256 GIONG HET : {'PASS' if h_goc == h_moi else 'FAIL'}")
        print(f"   SO DONG GIONG    : {'PASS' if d_goc == d_moi else 'FAIL'} "
              f"({d_goc} vs {d_moi})")
        print(f"   SO COT GIONG     : {'PASS' if c_goc == c_moi else 'FAIL'} "
              f"({c_goc} vs {c_moi})")
        print(f"   VIDEO KET QUA    : {'PASS' if ket_goc.frames == ket_moi.frames else 'FAIL'}")

    # =====================================================================
    # 4. HOI QUY DEM: so luot dem phuong tien truoc/sau
    # =====================================================================
    if phase in ("all", "dem"):
        os.environ.pop("CAMAI_PROFILE", None)
        print()
        print("=" * 78)
        print("HOI QUY DEM (--dem-phuong-tien): so luot xe truoc/sau phai khop")
        print("=" * 78)

        for video, nhan in ((VIDEO_CHINH, "car-detection.mp4"),
                            (VIDEO_DAI, "people-detection.mp4")):
            kg, _, _, _ = chay_analysis(core_goc, video, "dem_goc_" + nhan,
                                         no_face=True, dem_phuong_tien=True)
            km, _, _, _ = chay_analysis(core_moi, video, "dem_moi_" + nhan,
                                         no_face=True, dem_phuong_tien=True)
            tg, tm = kg.tong_phuong_tien, km.tong_phuong_tien
            chenh = abs(tg - tm)
            pct = (chenh / tg * 100.0) if tg else 0.0
            print(f"\n{nhan}:")
            print(f"   TRUOC: tong luot xe = {tg} | max cung luc = {kg.max_phuong_tien}")
            print(f"   SAU  : tong luot xe = {tm} | max cung luc = {km.max_phuong_tien}")
            print(f"   -> chenh {chenh} ({pct:.2f}%) | "
                  f"{'PASS' if pct <= 1.0 else 'FAIL - CANH BAO'}")
            if pct > 1.0:
                print("   !!! SO DEM KHAC > 1% - PHAI BAO, KHONG DUOC IM LANG")

    # =====================================================================
    print()
    print("=" * 78)
    print("KET LUAN")
    print("=" * 78)
    if fps_truoc or fps_sau:
        print(f"   Video chinh: {fps_truoc:.2f} -> {fps_sau:.2f} khung/s (gia ngien)")
    print(f"   CSV BIT-EXACT (SHA256 giong ban goc): {'PASS' if csv_ok else 'FAIL'}")
    print("=" * 78)
    return 0 if csv_ok else 1


if __name__ == "__main__":
    sys.exit(main())
