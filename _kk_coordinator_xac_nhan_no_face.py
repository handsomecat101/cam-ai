"""Coordinator tu do lai: bat/tat nhan dien mat co that nhanh khong?

Khong dung script cua agent. Do truc tiep qua run_analysis() cua cam_ai_core
voi 2 cau hinh giong het ngoai truoc mot bien:
  A = no_face=False (co nhan dien mat)
  B = no_face=True  (chi dem nguoi)

Tieu chi: fps va so nguoi trung binh moi khung.
Ket luan dung khong phai "cam co nhan dien mat" ma la "co nhan dien mat
CHAY TREN KHUNG NAO" - vi no_face + face_every khac nhau.
"""

from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

VIDEO = ROOT / "video_mau" / "moi" / "nguoi-dung-cho.mp4"
OUT = ROOT / "_kiem_chung" / "xac_nhan_no_face.txt"


def do(cau_hinh: str, no_face: bool, seconds: float = 4.0) -> tuple[float, float]:
    """Chay run_analysis roi do fps + so nguoi TB trong cua so thoi gian."""
    from cam_ai_core import AnalysisConfig, run_analysis

    cfg = AnalysisConfig(
        input=str(VIDEO),
        model="yolo11n.pt",
        conf=0.25,
        no_face=no_face,
        thiet_bi="cuda",
    )

    def chay(giay: float) -> tuple[int, float, float]:
        """Chay toi da giay TINH TU KHUNG HINH DAU TIEN.

        Quan trong: thoi gian nap model (15-21s khi bat nhan dien mat) KHONG
        duoc tinh vao, nen dong ho phai bat dau tu callback dau tien chu
        khong phai truoc khi goi run_analysis.
        """
        tong_khung = 0
        tong_nguoi = 0.0
        t0: list[float] = []

        def cb(p):
            nonlocal tong_khung, tong_nguoi
            if not t0:
                # khung dau tien: bat dong ho, dung lai khong tinh vao phep do
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

    # khoi dong: nap model + mo file, KHONG dem vao so do
    chay(0.5)

    tong_khung, tong_nguoi, dien_tich = chay(seconds)
    if tong_khung == 0:
        return 0.0, 0.0
    return tong_khung / dien_tich, tong_nguoi / tong_khung


def main() -> int:
    dong = []
    dong.append("=" * 78)
    dong.append("COORDINATOR TU DO - BAT/TAT NHAN DIEN MAT")
    dong.append("=" * 78)
    dong.append(f"Video     : {VIDEO.name}")
    dong.append("Do bang chinh run_analysis() cua cam_ai_core (co ve khung + ghi file)")
    dong.append("Phep do   : 1 lan khoi dong + 1 lan do that 4 giay")
    dong.append("Model     : yolo11n.pt | thiet bi: cuda")
    dong.append("")

    ket_qua = {}
    for ten, no_face in (("A  co nhan dien mat", False), ("B  chi dem nguoi", True)):
        fps, nguoi = do(ten, no_face)
        ket_qua[no_face] = (fps, nguoi)
        dong.append(f"{ten:24s} | {fps:7.2f} fps | {nguoi:6.2f} nguoi/khung")

    a = ket_qua[False]
    b = ket_qua[True]
    if a[0] > 0:
        he_so = b[0] / a[0]
        dong.append("")
        dong.append(f"HE SO TANG TOC DO = {he_so:.2f} lan")
        dong.append(f"So nguoi: {a[1]:.2f} -> {b[1]:.2f} "
                    f"({'tang' if b[1] > a[1] else 'giam' if b[1] < a[1] else 'khong doi'})")

    # Uoc luong thoi gian quet that cho video 2 tieng (72000 khung) va 8 tieng (288000)
    dong.append("")
    dong.append("UOC LUONG THOI GIAN QUET (25 fps)")
    dong.append("  2 tieng = 180.000 khung | 8 tieng = 720.000 khung")
    for ten, no_face in (("A co nhan dien mat", False), ("B chi dem nguoi", True)):
        fps = ket_qua[no_face][0]
        if fps <= 0:
            continue
        h2 = 180000 / fps / 3600
        h8 = 720000 / fps / 3600
        dong.append(f"  {ten:20s} {fps:6.2f} fps | 2 tieng: {int(h2)}h{int((h2 % 1) * 60):02d}"
                    f" | 8 tieng: {int(h8)}h{int((h8 % 1) * 60):02d}")

    van = "\n".join(dong) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(van, encoding="utf-8", newline="\n")
    print(van)
    print(f"Da luu: {OUT}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)