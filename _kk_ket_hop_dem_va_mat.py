"""TRA LOI: co the KET HOP dem nguoi + nhan dien khuon mat khong?

Y kien: face_every bo qua engine mat o nhung khung khong khop, con YOLO
dem nguoi van chay o MOI khung. Neu dung thi:
  - dem nguoi: khong doi
  - nhan dien mat: chi co tren 1/face_every khung
  - toc do: nhanh gap lan so voi tat hoan toan

Do face_every = 1, 2, 5, 10 va so sanh voi tat nhan dien mat.
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

VIDEO = ROOT / "video_mau" / "moi" / "nguoi-dung-cho.mp4"
OUT = ROOT / "_kiem_chung" / "ket_hop_dem_nguoi_va_nhan_dien_mat.txt"
LAN = 2
GIAY = 3.0


def do(no_face: bool, face_every: int) -> tuple[float, float, float, float]:
    """Tra ve (fps, nguoi TB/khung, mat TB/khung, % khung co mat)."""
    from cam_ai_core import AnalysisConfig, run_analysis

    cfg = AnalysisConfig(
        input=str(VIDEO),
        model="yolo11n.pt",
        conf=0.25,
        no_face=no_face,
        face_every=face_every,
        thiet_bi="cuda",
    )

    def chay(giay: float) -> tuple[int, float, float, int, float]:
        tong_khung = 0
        tong_nguoi = 0.0
        tong_mat = 0.0
        khung_co_mat = 0
        t0: list[float] = []

        def cb(p):
            nonlocal tong_khung, tong_nguoi, tong_mat, khung_co_mat
            if not t0:
                t0.append(time.perf_counter())
                return True
            tong_khung += 1
            tong_nguoi += p.so_nguoi
            tong_mat += p.so_mat
            if p.so_mat > 0:
                khung_co_mat += 1
            if time.perf_counter() - t0[0] >= giay:
                return False
            return True

        truoc = time.perf_counter()
        run_analysis(cfg, progress_cb=cb, log=lambda s: None)
        tong_thoi_gian = time.perf_counter() - truoc
        if tong_khung == 0 or not t0:
            return 0, 0.0, 0.0, 0, tong_thoi_gian
        return (tong_khung, tong_nguoi, tong_mat, khung_co_mat,
                tong_thoi_gian - (t0[0] - truoc))

    chay(0.5)
    k, ng, mt, kcm, dt = chay(GIAY)
    if k == 0:
        return 0.0, 0.0, 0.0, 0.0
    return k / dt, ng / k, mt / k, kcm / k * 100


def main() -> int:
    d = []
    d.append("=" * 86)
    d.append("KET HOP DEM NGUOI + NHAN DIEN KHUON MAT - SO DO THAT")
    d.append("=" * 86)
    d.append(f"Video : {VIDEO.name}  (~10 nguoi/khung)")
    d.append("Model : yolo11n.pt | cuda | moi cau hinh do 2 lan, 3s moi lan")
    d.append("")
    d.append("Cau hinh                      |   fps  | nguoi/khung |  mat/khung | "
             "% khung co mat")
    d.append("-" * 86)

    kq = {}
    truong = [
        ("mat moi khung (face_every=1)", False, 1),
        ("mat 1/2 khung (face_every=2)", False, 2),
        ("mat 1/5 khung (face_every=5)", False, 5),
        ("mat 1/10 khung (face_every=10)", False, 10),
        ("TAT hoan toan (no_face)", True, 1),
    ]
    for ten, nf, fe in truong:
        fps_list = []
        ng_list = []
        mt_list = []
        pc_list = []
        for _ in range(LAN):
            fps, ng, mt, pc = do(nf, fe)
            fps_list.append(fps)
            ng_list.append(ng)
            mt_list.append(mt)
            pc_list.append(pc)
        tb = lambda x: sum(x) / len(x)
        kq[ten] = (tb(fps_list), tb(ng_list), tb(mt_list), tb(pc_list))
        d.append(f"{ten:30s} | {tb(fps_list):6.2f} | {tb(ng_list):10.2f} | "
                 f"{tb(mt_list):10.2f} | {tb(pc_list):11.1f}%")

    d.append("-" * 86)
    co_mat = kq["mat moi khung (face_every=1)"][0]
    tat = kq["TAT hoan toan (no_face)"][0]
    d.append("")
    d.append("NHAN XET:")
    for ten in kq:
        f = kq[ten][0]
        d.append(f"  {ten:30s} {f:6.2f} fps  = nhanh gap {f / co_mat:5.2f} lan so voi "
                 f"mac dinh")
    d.append("")
    d.append("  Dem nguoi KHONG DOI o moi cau hinh -> YOLO doc lap voi engine mat.")
    d.append("  Mat chi giam do quet muon, van nhan dien dung nguoi khi co mat.")

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