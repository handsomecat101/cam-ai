# -*- coding: utf-8 -*-
"""
Kiem chung BIT-EXACT: detector nhanh (CUDA Graph) vs duong cu cu cua ultralytics.

Neu 2 duong cho ra cung ket qua (xyxy / conf / cls / ten lop) tren TUNG khung
hinh thi:
  - so dem nguoi/xe giong het
  - CSV giong het (SHA256)
  - video ket qua giong het (1 pixel)

Chay:
    $env:PYTHONIOENCODING='utf-8'
    & 'H:\\AI Project\\cam-ai\\.venv\\Scripts\\python.exe' -W ignore `
        'H:\\AI Project\\cam-ai\\_kk_kiem_bit_exact.py'
"""
from __future__ import annotations

import os
import sys
import time

APP = os.path.dirname(os.path.abspath(__file__))
if APP not in sys.path:
    sys.path.insert(0, APP)

import cv2
import numpy as np
import supervision as sv

from ultralytics import YOLO

from nhan_dien_nhanh import DetectorNhanh

VIDEO = os.path.join(APP, "video_mau", "car-detection.mp4")
VIDEO_2 = os.path.join(APP, "video_mau", "people-detection.mp4")


def so_sanh(a: sv.Detections, b: sv.Detections) -> str:
    """Tra ve chuoi rong neu giong het, nen loi neu khac."""
    if len(a) != len(b):
        return f"SO PHAT HIEN KHAC: {len(a)} vs {len(b)}"
    if len(a) == 0:
        return ""
    if not np.array_equal(a.xyxy, b.xyxy):
        return f"XYXY KHAC (max lech {np.abs(a.xyxy - b.xyxy).max():.9f})"
    if not np.array_equal(a.confidence, b.confidence):
        return f"CONF KHAC (max lech {np.abs(a.confidence - b.confidence).max():.9f})"
    if not np.array_equal(a.class_id, b.class_id):
        return "CLASS_ID KHAC"
    if not np.array_equal(a.data.get("class_name"), b.data.get("class_name")):
        return "TEN LOP KHAC"
    return ""


def kiem(video: str, so_khung: int = 200) -> bool:
    print()
    print("=" * 78)
    print(f"Kiem BIT-EXACT: {os.path.basename(video)} ({so_khung} khung dau)")
    print("=" * 78)

    cap = cv2.VideoCapture(video)
    frames = []
    for _ in range(so_khung):
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    if not frames:
        print("KHONG DOC DUOC VIDEO")
        return False

    yolo = YOLO(os.path.join(APP, "yolo11n.pt")).to("cuda")

    t0 = time.perf_counter()
    goc = []
    for f in frames:
        r = yolo(f, verbose=False, conf=0.25)[0]
        goc.append(sv.Detections.from_ultralytics(r))
    t_goc = (time.perf_counter() - t0) / len(frames) * 1000

    det = DetectorNhanh(yolo, conf=0.25)
    t0 = time.perf_counter()
    nhanh = [det.detect(f) for f in frames]
    t_nhanh = (time.perf_counter() - t0) / len(frames) * 1000

    sai = []
    for i, (a, b) in enumerate(zip(goc, nhanh)):
        loi = so_sanh(a, b)
        if loi:
            sai.append((i, loi))

    print(f"Duong cu cua ultralytics : {t_goc:6.2f} ms/khung")
    print(f"Duong nhanh (CUDA Graph)  : {t_nhanh:6.2f} ms/khung")
    print(f"Trang thai                : {det.thong_tin()}")
    print(f"Tong phat hien - goc      : {sum(len(x) for x in goc)}")
    print(f"Tong phat hien - nhanh    : {sum(len(x) for x in nhanh)}")
    if sai:
        print(f"KET QUA: FAIL - {len(sai)}/{len(frames)} khung KHAC")
        for i, loi in sai[:5]:
            print(f"   khung {i}: {loi}")
        return False
    print(f"KET QUA: PASS - {len(frames)}/{len(frames)} khung BIT-EXACT "
          f"(xyxy / conf / cls / ten lop giong het)")
    return True


def main() -> int:
    ok = True
    ok &= kiem(VIDEO, 200)
    ok &= kiem(VIDEO_2, 200)
    print()
    print("=" * 78)
    print(f"TONG KET: {'PASS' if ok else 'FAIL'}")
    print("=" * 78)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
