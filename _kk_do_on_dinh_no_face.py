"""Do lai NHIEU LAN de lay do on dinh cua hai so do:
  - he so 2.22x (agent) hay 5.09x (coordinator lan truoc)?
  - chi phi nhan dien mat co tang theo SO NGUOI trong khung khong?

Ket luan nay quyet dinh con so hien thi tren GUI nen phai lap lai
nhieu lan, khong duoc lay mot lan roi bao cao.
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

VIDEO = ROOT / "video_mau" / "moi" / (sys.argv[1] if len(sys.argv) > 1 else "nguoi-dung-cho.mp4")
OUT = ROOT / "_kiem_chung" / f"do_on_dinh_no_face_{VIDEO.stem}.txt"
LAN = 2
GIAY = 3.0


def do(no_face: bool) -> tuple[float, float, float]:
    """Tra ve (fps, so nguoi TB, ms/khung)."""
    from cam_ai_core import AnalysisConfig, run_analysis

    cfg = AnalysisConfig(
        input=str(VIDEO),
        model="yolo11n.pt",
        conf=0.25,
        no_face=no_face,
        thiet_bi="cuda",
    )

    def chay(giay: float) -> tuple[int, float, float]:
        tong_khung = 0
        tong_nguoi = 0.0
        t0: list[float] = []

        def cb(p):
            nonlocal tong_khung, tong_nguoi
            if not t0:
                t0.append(time.perf_counter())
                return True
            tong_khung += 1
            tong_nguoi += p.so_nguoi
            if time.perf_counter() - t0[0] >= giay:
                return False
            return True

        truoc = time.perf_counter()
        run_analysis(cfg, progress_cb=cb, log=lambda s: None)
        tong_thoi_gian = time.perf_counter() - truoc
        if tong_khung == 0 or not t0:
            return 0, 0.0, tong_thoi_gian
        return tong_khung, tong_nguoi, tong_thoi_gian - (t0[0] - truoc)

    chay(0.5)
    tong_khung, tong_nguoi, dien_tich = chay(GIAY)
    if tong_khung == 0:
        return 0.0, 0.0, 0.0
    return tong_khung / dien_tich, tong_nguoi / tong_khung, dien_tich / tong_khung * 1000


def main() -> int:
    d = []
    d.append("=" * 78)
    d.append("DO ON DINH - BAT/TAT NHAN DIEN MAT (lap lai nhieu lan)")
    d.append("=" * 78)
    d.append(f"Video   : {VIDEO.name}")
    d.append(f"Model   : yolo11n.pt | cuda | do moi lan {GIAY}s sau 0.5s khoi dong")
    d.append(f"So lan  : {LAN}")
    d.append("")

    kq = {}
    for ten, nf in (("A co nhan dien mat", False), ("B chi dem nguoi", True)):
        d.append(f"--- {ten} ---")
        fps_list = []
        for i in range(LAN):
            fps, nguoi, ms = do(nf)
            fps_list.append(fps)
            d.append(f"  lan {i + 1}: {fps:6.2f} fps | {ms:6.1f} ms/khung | "
                     f"{nguoi:5.2f} nguoi/khung")
        tb = sum(fps_list) / len(fps_list)
        kq[nf] = (tb, min(fps_list), max(fps_list))
        d.append(f"  TB = {tb:.2f} fps   (thap nhat {min(fps_list):.2f} / "
                 f"cao nhat {max(fps_list):.2f})")
        d.append("")

    a, b = kq[False], kq[True]
    d.append("=" * 78)
    d.append(f"HE SO (TB/TB)     = {b[0] / a[0]:.2f} lan")
    d.append(f"HE SO (TB/khong)   = {b[0] / a[2]:.2f} lan")
    d.append(f"HE SO (TB/thap nhat)= {b[0] / a[1]:.2f} lan")
    d.append("")
    d.append("=> Dung khoang giua cac he so tren de hien thi tren UI.")
    d.append("   Video nay CO ~10 nguoi/khung - moi nguoi them 1 mat phai nhan dien.")

    van = "\n".join(d) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(van, encoding="utf-8", newline="\n")
    print(van)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)