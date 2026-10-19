# -*- coding: utf-8 -*-
"""
Do chi phi cua `frame_cb` (b3.2) - so khung hinh / giay co va khong co.

Chay: .venv\\Scripts\\python.exe _kk_do_chi_phi_frame_cb.py
"""
from __future__ import annotations

import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

_REAL_STDOUT = sys.stdout
try:
    _REAL_STDOUT.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def in_ky(*args) -> None:
    print(*args, file=_REAL_STDOUT, flush=True)


VIDEO = os.path.join(APP_DIR, "video_test.mp4")
OUT = os.path.join(APP_DIR, "_kk_out", "pc_audit", "V5_batch_preview")
os.makedirs(OUT, exist_ok=True)


def chay(should_count, interval, nhan):
    """should_count=True -> truyen ham dem so khung hinh thuc su duoc gui."""
    from cam_ai_core import AnalysisConfig, run_analysis

    cfg = AnalysisConfig(
        input=VIDEO,
        output=os.path.join(OUT, "chi_phi_" + nhan),
        no_face=False,
        faces_dir=os.path.join(APP_DIR, "known_faces"),
        model="yolo11n.pt",
    )
    dem = {"n": 0, "byte": 0, "loi": 0}

    def cb(jpeg):
        dem["n"] += 1
        dem["byte"] += len(jpeg)

    frame_cb = cb if should_count else None
    t0 = time.perf_counter()
    res = run_analysis(cfg, log=lambda t: None,
                       frame_cb=frame_cb, frame_cb_interval=interval)
    dt = time.perf_counter() - t0
    fps = res.frames / dt if dt else 0
    in_ky(f"  {nhan:<22} | thoi gian={dt:6.2f} s | {res.frames} khung | "
          f"{fps:5.2f} khung/s | callback goi {dem['n']} lan | "
          f"tong {dem['byte']/1024:.0f} KB JPEG")
    return dt, fps, res.frames, dem["n"]


def do_3_lan(nhan_lan: str):
    """Chay 3 cau hinh. Tra ve ket qua (fps, so lan callback, so khung)."""
    dt_khong, fps_khong, khung, _ = chay(False, 0.0, f"CLI_khong_frame_cb_{nhan_lan}")
    in_ky("")
    dt_tat, fps_tat, _, n_tat = chay(True, 0.0, f"GUI_moi_khung_hinh_{nhan_lan}")
    in_ky("")
    dt_10, fps_10, _, n_10 = chay(True, 0.1, f"GUI_gioi_han_10fps_{nhan_lan}")
    in_ky("")
    return {
        "fps_khong": fps_khong, "fps_tat": fps_tat, "fps_10": fps_10,
        "n_tat": n_tat, "n_10": n_10, "khung": khung,
    }


def main() -> int:
    in_ky("=" * 78)
    in_ky("CamAI v3.2 - DO CHI PHI frame_cb (che do phan tich theo lo)")
    in_ky("=" * 78)
    in_ky(f"  video: {VIDEO}")
    in_ky("")

    # 0) WARM-UP (khong tinh): nap model + khoi dong CUDA la lan dau
    # -> cac lan do sau cung bang nhau, khong con nhiem tu thoi gian nap model.
    in_ky("  [warm-up] nap model + dong CUDA (khong tinh vao ket qua)...")
    chay(False, 0.0, "warmup")
    in_ky("")

    # 1) Vong 1 - bo qua (nhiet du, dung de quen may)
    in_ky("  --- VONG 1 (nhiet du, khong lay so lieu) ---")
    do_3_lan("v1")
    in_ky("  --- VONG 2 (so lieu chinh thuc) ---")
    r = do_3_lan("v2")
    in_ky("")

    # 2) Callback nem loi -> pipeline PHAI van chay tiep (khong chet app)
    from cam_ai_core import AnalysisConfig, run_analysis

    cfg_loi = AnalysisConfig(
        input=VIDEO,
        output=os.path.join(OUT, "chi_phi_callback_loi"),
        no_face=False,
        faces_dir=os.path.join(APP_DIR, "known_faces"),
        model="yolo11n.pt",
    )
    dem_loi = {"n": 0}

    def cb_loi(jpeg):
        dem_loi["n"] += 1
        raise RuntimeError("loi gia lap trong callback")

    try:
        res_loi = run_analysis(cfg_loi, log=lambda t: None,
                               frame_cb=cb_loi, frame_cb_interval=0.1)
        in_ky(f"  Callback nem loi         : {res_loi.frames} khung xu ly | "
              f"callback goi {dem_loi['n']} lan | pipeline KHONG CHET (OK)")
    except Exception as exc:  # noqa: BLE001
        in_ky(f"  Callback nem loi         : FAIL - pipeline chet: {exc}")
    in_ky("")
    in_ky("=" * 78)
    in_ky("KET QUA SO SAO (vong 2 - de may da nong)")
    in_ky("=" * 78)
    fps_khong = r["fps_khong"]
    in_ky(f"  Khong co frame_cb        : {fps_khong:5.2f} khung/s")
    in_ky(f"  Co frame_cb moi khung   : {r['fps_tat']:5.2f} khung/s "
          f"({r['fps_tat']/fps_khong*100-100:+.1f}% so voi khong co) | "
          f"callback goi {r['n_tat']} lan")
    in_ky(f"  Co frame_cb gioi han10fps: {r['fps_10']:5.2f} khung/s "
          f"({r['fps_10']/fps_khong*100-100:+.1f}% so voi khong co) | "
          f"callback goi {r['n_10']} lan "
          f"(mua ~{r['n_10']/max(1, r['khung'])*100:.0f}% so khung)")
    in_ky("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
