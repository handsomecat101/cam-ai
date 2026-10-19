# -*- coding: utf-8 -*-
"""Coordinator: do CHI PHI THAT cua 2 che do doc bien so + do DO GIAT.

Che do 1: co ROI (vung_bien_so) -> doc crop ROI, khong tim trong ca khung hinh.
Che do 2: KHONG ROI (che do mac dinh khi tick "Doc bien so xe") -> tu tim trong
          ca khung hinh bang engine "co tim chu", co gioi han giam tan.

Do them: tong thoi gian + KHUNG HINH CHAM NHAT (stall) -> day la thu do nguoi
dung cham khi keo cua so.

Chay: .venv\\Scripts\\python.exe -W ignore _kk_do_chi_phi_doc_bien_so.py
"""
import os
import sys
import time

import cv2

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

from bien_so import BoDocBienSo  # noqa: E402

VIDEO = os.path.join(GOC, "video_test.mp4")


def do_chebien(nhan: str, vung) -> None:
    bd = BoDocBienSo(thu_muc_luu="", vung=vung)
    cap = cv2.VideoCapture(VIDEO)
    ts = []
    n = 0
    doc_duoc = []
    t0 = time.perf_counter()
    while True:
        ok, khung = cap.read()
        if not ok:
            break
        t1 = time.perf_counter()
        kq = bd.doc(khung)
        ts.append((time.perf_counter() - t1) * 1000.0)
        if kq:
            doc_duoc.append(kq[0].chuoi)
        n += 1
    cap.release()
    tong = (time.perf_counter() - t0) * 1000.0
    ts_s = sorted(ts)
    print(f"  {nhan:<28} tong {tong:8.0f} ms | tb {tong/max(1,n):6.1f} ms/khung"
          f" | doc 1 bien: median {ts_s[len(ts_s)//2]:6.1f} | p95 {ts_s[int(len(ts_s)*0.95)]:7.1f}"
          f" | CHAM NHAT {max(ts):7.1f} ms | doc duoc: {doc_duoc[:3]}")


def main() -> int:
    print("=" * 110)
    print("CHI PHI DOC BIEN SO - 2 CHE DO - video_test.mp4 (250 khung hinh)")
    print("=" * 110)
    do_chebien("ROI (0.1,0.3,0.9,0.8)", "0.1,0.3,0.9,0.8")
    do_chebien("KHONG ROI (tu tim toan khung)", None)
    print()
    print("GHI CHU: 'CHAM NHAT' = mot khung hinh tre bao gio -> keo cua so se giat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
