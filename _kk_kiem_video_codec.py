"""Kiem chung codec video CamAI (H.264 / OpenH264).

Chay:  python _kk_kiem_video_codec.py            -> tat ca cac buoc
       python _kk_kiem_video_codec.py --buoc 1   -> chi buoc 1 (probe VideoWriter)
       python _kk_kiem_video_codec.py --buoc 2   -> chi chay app.py 1 lan
       python _kk_kiem_video_codec.py --buoc 3   -> chay app.py 5 lan (do crash)
       python _kk_kiem_video_codec.py --buoc 5   -> kiem tra hoi quy CSV
       python _kk_kiem_video_codec.py --buoc 6   -> kiem tra encoding file da sua

Ket qua ghi vao _kk_out/_kk_kiem_video_codec.txt va in ra man hinh.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

DU_AN = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(DU_AN, "_kk_out")
os.makedirs(OUT_DIR, exist_ok=True)
BAO_CAO = os.path.join(OUT_DIR, "_kk_kiem_video_codec.txt")

VIDEO_MAU = os.path.join(DU_AN, "video_mau", "car-detection.mp4")
VIDEO_KET_QUA = os.path.join(DU_AN, "output_ket_qua.mp4")
CSV_KET_QUA = os.path.join(DU_AN, "output_bao_cao.csv")
DLL_OPENH264 = os.path.join(DU_AN, "openh264-2.5.0-win64.dll")

PYTHON = os.path.join(DU_AN, ".venv", "Scripts", "python.exe")
if not os.path.isfile(PYTHON):
    PYTHON = sys.executable

DONG_LOG_DO = "Failed to load OpenH264 library"
DONG_LOI_WRITER = "Failed to initialize VideoWriter"

_dong = []


def _ghi(text: str = "") -> None:
    print(text)
    _dong.append(text)


def _ffprobe(path: str) -> dict:
    """Tra thong tin stream video bang ffprobe; khong co ffprobe -> {}."""
    exe = shutil.which("ffprobe")
    if not exe:
        return {}
    try:
        r = subprocess.run(
            [exe, "-v", "error", "-show_entries",
             "stream=codec_name,codec_tag_string,width,height,nb_frames,duration",
             "-of", "json", path],
            capture_output=True, text=True, timeout=60,
        )
        du_lieu = json.loads(r.stdout or "{}")
        return (du_lieu.get("streams") or [{}])[0]
    except Exception as exc:                                  # noqa: BLE001
        _ghi(f"    [ffprobe loi] {exc}")
        return {}


def _dem_khung(path: str) -> int:
    """Dem khung hinh doc lai duoc bang cv2.VideoCapture."""
    import cv2

    cap = cv2.VideoCapture(path)
    n = 0
    try:
        if cap.isOpened():
            while True:
                ok, _ = cap.read()
                if not ok:
                    break
                n += 1
    finally:
        cap.release()
    return n


def _chay_app(label: str) -> dict:
    """Chay app.py 1 lan, tra thong tin exit code + log do."""
    t0 = time.time()
    r = subprocess.run(
        [PYTHON, os.path.join(DU_AN, "app.py"), "--input", VIDEO_MAU],
        cwd=DU_AN, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    tong = (r.stdout or "") + (r.stderr or "")
    ket_qua = {
        "label": label,
        "exit_code": r.returncode,
        "red_log": tong.count(DONG_LOG_DO),
        "loi_writer": tong.count(DONG_LOI_WRITER),
        "secs": round(time.time() - t0, 1),
        "stdout_tail": (r.stdout or "")[-1500:],
        "stderr_tail": (r.stderr or "")[-1500:],
    }
    _ghi(f"  {label}: exit={ket_qua['exit_code']} "
         f"log_do={ket_qua['red_log']} loi_writer={ket_qua['loi_writer']} "
         f"{ket_qua['secs']}s")
    return ket_qua


# ------------------------------------------------------------------ buoc 1
def buoc_1() -> None:
    _ghi("=" * 70)
    _ghi("BUOC 1: VideoWriter fourcc 'avc1' (H.264)")
    _ghi("=" * 70)
    import cv2
    import numpy as np

    # Chay o thu muc du an: dung nhu launcher "Mo CamAI.vbs" (cwd = thu muc du an).
    os.chdir(DU_AN)

    _ghi(f"  cwd = {os.getcwd()}")
    _ghi(f"  DLL OpenH264 trong thu muc du an: {os.path.isfile(DLL_OPENH264)}")
    if os.path.isfile(DLL_OPENH264):
        _ghi(f"  kich thuoc DLL: {os.path.getsize(DLL_OPENH264)} bytes")

    # --- A) cv2.VideoWriter thuan (raw) voi fourcc avc1
    out = os.path.join(OUT_DIR, "_kk_probe_avc1.mp4")
    if os.path.exists(out):
        os.remove(out)
    w = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"avc1"), 10.0, (64, 64))
    mo = w.isOpened()
    backend = w.getBackendName() if hasattr(w, "getBackendName") else "?"
    if mo:
        khung = np.full((64, 64, 3), 200, np.uint8)
        for _ in range(5):
            w.write(khung)
    w.release()
    _ghi(f"  [A] cv2.VideoWriter raw avc1: isOpened={mo} backend={backend}")
    if os.path.exists(out):
        _ghi(f"      kich thuoc = {os.path.getsize(out)} bytes")
        _ghi(f"      ffprobe   = {_ffprobe(out)}")
        _ghi(f"      so khung doc lai = {_dem_khung(out)}")

    # --- B) duong dan that cua app: cam_ai_core._mo_video_writer
    sys.path.insert(0, DU_AN)
    import cam_ai_core

    _ghi(f"  [B] cam_ai_core._fourcc_ket_qua() = {cam_ai_core._fourcc_ket_qua()}")
    _ghi(f"      DLL da nap: {cam_ai_core._duong_dan_dll_openh264()}")
    out2 = os.path.join(OUT_DIR, "_kk_probe_app.mp4")
    if os.path.exists(out2):
        os.remove(out2)
    try:
        wr, fcc = cam_ai_core._mo_video_writer(out2, 10.0, (64, 64))
        khung = np.full((64, 64, 3), 200, np.uint8)
        for _ in range(5):
            wr.write(khung)
        wr.release()
        _ghi(f"      _mo_video_writer -> fourcc='{fcc}' "
             f"size={os.path.getsize(out2)} bytes")
        _ghi(f"      ffprobe = {_ffprobe(out2)}")
    except Exception as exc:                                  # noqa: BLE001
        _ghi(f"      _mo_video_writer LOI: {exc}")


# ------------------------------------------------------------------ buoc 2
def buoc_2() -> None:
    _ghi("=" * 70)
    _ghi("BUOC 2: chay app.py --input video_mau/car-detection.mp4")
    _ghi("=" * 70)
    kq = _chay_app("app")
    if os.path.exists(VIDEO_KET_QUA):
        _ghi(f"  video ket qua: {os.path.getsize(VIDEO_KET_QUA)} bytes")
        _ghi(f"  ffprobe: {_ffprobe(VIDEO_KET_QUA)}")
        _ghi(f"  so khung doc lai = {_dem_khung(VIDEO_KET_QUA)}")
    if os.path.exists(CSV_KET_QUA):
        with open(CSV_KET_QUA, "r", encoding="utf-8-sig") as f:
            dong = f.read().splitlines()
        _ghi(f"  CSV: {len(dong)} dong (1 dong header + {max(0, len(dong) - 1)} dong du lieu)")
        if dong:
            _ghi(f"  CSV header ({len(dong[0].split(','))} cot): {dong[0]}")


# ------------------------------------------------------------------ buoc 3
def buoc_3() -> None:
    _ghi("=" * 70)
    _ghi("BUOC 3: chay app.py 5 lan lien tiep -> ty le crash")
    _ghi("=" * 70)
    ket_qua = []
    for i in range(1, 6):
        ket_qua.append(_chay_app(f"run{i}"))
    crash = [k for k in ket_qua if k["exit_code"] != 0]
    red = [k for k in ket_qua if k["red_log"] > 0]
    _ghi("")
    _ghi(f"  TONG: {len(ket_qua)} lan chay | CRASH (exit != 0): {len(crash)} "
         f"| co log do OpenH264: {len(red)}")
    for k in crash:
        _ghi(f"  CRASH: {k['label']} exit={k['exit_code']}")
        _ghi(f"    stderr: {k['stderr_tail'][-400:]}")
    with open(os.path.join(OUT_DIR, "_kk_ket_qua_5_lan.json"), "w",
              encoding="utf-8") as f:
        json.dump(ket_qua, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------ buoc 5
def buoc_5() -> None:
    _ghi("=" * 70)
    _ghi("BUOC 5: hoi quy - CSV va codec video ket qua")
    _ghi("=" * 70)
    if not os.path.exists(CSV_KET_QUA):
        _ghi("  !! khong co CSV")
        return
    with open(CSV_KET_QUA, "r", encoding="utf-8-sig") as f:
        dong = f.read().splitlines()
    cot = dong[0].split(",") if dong else []
    _ghi(f"  CSV: {len(dong)} dong x {len(cot)} cot")
    _ghi(f"  header: {dong[0]}")
    tham_chieu = os.path.join(OUT_DIR, "_kk_csv_tham_chieu.json")
    if os.path.exists(tham_chieu):
        with open(tham_chieu, "r", encoding="utf-8") as f:
            tc = json.load(f)
        _ghi(f"  tham chieu: {tc}")
        _ghi(f"  KHONG DOI (dong): {len(dong) == tc['dong']} | "
             f"(cot): {len(cot) == tc['cot']} | "
             f"(header): {dong[0] == tc['header']}")
    else:
        with open(tham_chieu, "w", encoding="utf-8") as f:
            json.dump({"dong": len(dong), "cot": len(cot), "header": dong[0]}, f,
                      ensure_ascii=False, indent=2)
        _ghi("  (da luu tham chieu moi - chay lai de so sanh)")
    tt = _ffprobe(VIDEO_KET_QUA) if os.path.exists(VIDEO_KET_QUA) else {}
    _ghi(f"  codec video ket qua: {tt.get('codec_name')} "
         f"(tag={tt.get('codec_tag_string')})")


# ------------------------------------------------------------------ buoc 6
def buoc_6() -> None:
    _ghi("=" * 70)
    _ghi("BUOC 6: encoding cac file da sua (BOM=False, CR=0)")
    _ghi("=" * 70)
    for ten in ("cam_ai_core.py", "_kk_kiem_video_codec.py", ".gitignore"):
        duong_dan = os.path.join(DU_AN, ten)
        if not os.path.isfile(duong_dan):
            _ghi(f"  {ten}: khong ton tai")
            continue
        du_lieu = open(duong_dan, "rb").read()
        bom = du_lieu[:3] == b"\xef\xbb\xbf"
        cr = du_lieu.count(b"\r")
        lf = du_lieu.count(b"\n")
        _ghi(f"  {ten}: BOM={bom} | CR={cr} | LF={lf}")


def main() -> None:
    buoc = None
    if "--buoc" in sys.argv:
        buoc = int(sys.argv[sys.argv.index("--buoc") + 1])
    buoc_list = [buoc] if buoc else [1, 2, 3, 5, 6]
    for b in buoc_list:
        globals()[f"buoc_{b}"]()
    with open(BAO_CAO, "w", encoding="utf-8") as f:
        f.write("\n".join(_dong) + "\n")
    print(f"\n[da luu bao cao] {BAO_CAO}")


if __name__ == "__main__":
    main()
