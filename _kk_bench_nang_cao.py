# -*- coding: utf-8 -*-
"""BENCHMARK 3 phuong án nang cao do nhan dien — CHUA áp dụng vào code san pham.

Muc dich: dua SO DO cho nguoi dung chon giup toc do hay do chinh xac.
Khong sua gui.py / cam_ai_core.py. Chi doc video va do.

Cac kien thuc do:
  A) nen:      yolo11n, frame nguyen            -> moc doi chieu
  B) model:    yolo11s, frame nguyen            -> phuong an 1
  C) phong to: yolo11n, frame x2 (960->1920)    -> phuong an 2
  D) chia o:   yolo11n, frame tach 2x2 co chong -> phuong an 3

Video do:
  - 3 video DANG HONG: nguoi-di-lai, dam-dong, xe-co-giao-thong
  - 1 video DANG TOT  : tre-em-san-choi  (de canh bao neu phuong an nao lam
                        hong khung tot thanh hong)
"""

import os
import sys
import time
import traceback

import cv2
import numpy as np
from ultralytics import YOLO

THU_MUC_VIDEO = os.path.join("video_mau", "moi")
THU_MUC_KC = "_kiem_chung"
PERSON = 0
CONF = 0.25
SO_KHUNG = 8# so khung mau/video (de chay nhanh)

VIDEO_TOT = "tre-em-san-choi.mp4"
VIDEO_HONG = ["nguoi-di-lai.mp4", "dam-dong.mp4", "xe-co-giao-thong.mp4"]


def doc_khung(duong, so):
    cap = cv2.VideoCapture(duong)
    if not cap.isOpened():
        return []
    tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    buoc = max(1, tong // (so + 1))
    ra = []
    for i in range(so):
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(tong - 1, i * buoc + buoc // 2))
        ok, k = cap.read()
        if ok:
            ra.append(k)
    cap.release()
    return ra


def dem_nguoi(model, khung):
    r = model.predict(khung, conf=CONF, verbose=False)[0]
    n = 0
    for cid in r.boxes.cls.tolist():
        if int(cid) == PERSON:
            n += 1
    return n


def kien_A(model, khung):
    return dem_nguoi(model, khung)


def kien_C(model, khung):
    lon = cv2.resize(khung, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    return dem_nguoi(model, lon)


def kien_D(model, khung, n_o=2, trung=0.35):
    """Chia frame thanh n_o x n_o o co chong, do tung o, gop hop + NMS."""
    h, w = khung.shape[:2]
    buoc = int(w * (1 - trung) / max(1, n_o - 1)) if n_o > 1 else 0
    boxes = []
    for iy in range(n_o):
        for ix in range(n_o):
            x0 = min(ix * buoc, w - int(w * trung))
            y0 = min(iy * buoc, h - int(h * trung))
            x1 = min(x0 + int(w * trung), w)
            y1 = min(y0 + int(h * trung), h)
            o = khung[y0:y1, x0:x1]
            if o.size == 0:
                continue
            r = model.predict(o, conf=CONF, verbose=False)[0]
            for xyxy, cid in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist()):
                if int(cid) != PERSON:
                    continue
                boxes.append([xyxy[0] + x0, xyxy[1] + y0, xyxy[2] + x0, xyxy[3] + y0])
    if not boxes:
        return 0
    b = np.array(boxes, dtype=np.float32)
    keep = cv2.dnn.NMSBoxes(
        [list(map(float, x)) for x in b], [1.0] * len(b), 0.4, 0.55
    )
    return len(keep) if isinstance(keep, (list, tuple)) else int(len(keep))


def do_anh(ten, video):
    print(f"\n=== {ten} | {video} ===", flush=True)
    duong = os.path.join(THU_MUC_VIDEO, video)
    khung = doc_khung(duong, SO_KHUNG)
    if not khung:
        print("  khong doc duoc video")
        return

    dong = [f"--- {ten} | {video} ({len(khung)} khung mau) ---"]

    # A) nen
    mo = YOLO("yolo11n.pt")
    t0 = time.perf_counter()
    a = [dem_nguoi(mo, k) for k in khung]
    ms_a = (time.perf_counter() - t0) / len(khung) * 1000
    dong.append(f"  A) nen  yolo11n, frame nguyen    : {a}")
    dong.append(f"     tb={np.mean(a):5.1f} nguoi/khung   {ms_a:6.1f} ms/khung")

    # B) model lon hon
    mo_s = YOLO("yolo11s.pt")
    mo_s.predict(khung[0], conf=CONF, verbose=False)  # warmup
    t0 = time.perf_counter()
    b = [dem_nguoi(mo_s, k) for k in khung]
    ms_b = (time.perf_counter() - t0) / len(khung) * 1000
    dong.append(f"  B) model yolo11s, frame nguyen   : {b}")
    dong.append(f"     tb={np.mean(b):5.1f} nguoi/khung   {ms_b:6.1f} ms/khung")

    # C) phong to x2
    mo.predict(khung[0], conf=CONF, verbose=False)
    t0 = time.perf_counter()
    c = [kien_C(mo, k) for k in khung]
    ms_c = (time.perf_counter() - t0) / len(khung) * 1000
    dong.append(f"  C) yolo11n, phong to x2           : {c}")
    dong.append(f"     tb={np.mean(c):5.1f} nguoi/khung   {ms_c:6.1f} ms/khung")

    # D) chia o 2x2
    t0 = time.perf_counter()
    d2 = [kien_D(mo, k, 2) for k in khung]
    ms_d2 = (time.perf_counter() - t0) / len(khung) * 1000
    dong.append(f"  D) yolo11n, chia o 2x2            : {d2}")
    dong.append(f"     tb={np.mean(d2):5.1f} nguoi/khung   {ms_d2:6.1f} ms/khung")

    # D') chia o 3x3
    t0 = time.perf_counter()
    d3 = [kien_D(mo, k, 3) for k in khung]
    ms_d3 = (time.perf_counter() - t0) / len(khung) * 1000
    dong.append(f"  D') yolo11n, chia o 3x3            : {d3}")
    dong.append(f"     tb={np.mean(d3):5.1f} nguoi/khung   {ms_d3:6.1f} ms/khung")

    dong.append(
        f"  -> tang so nguoi so voi nen: B={np.mean(b)-np.mean(a):+.1f}"
        f"  C={np.mean(c)-np.mean(a):+.1f}"
        f"  D2={np.mean(d2)-np.mean(a):+.1f}"
        f"  D3={np.mean(d3)-np.mean(a):+.1f}"
    )
    print("\n".join(dong), flush=True)
    return dong


def main():
    os.makedirs(THU_MUC_KC, exist_ok=True)
    all_dong = [
        "BENCHMARK phuong an nang cao do nhan dien",
        f"model nen yolo11n.pt | conf={CONF} | {SO_KHUNG} khung mau/video",
        "CHUA ap dung vao code san pham. Chi de nguoi dung chon.",
        "",
    ]
    for v in VIDEO_HONG:
        r = do_anh(f"DANG HONG", v)
        if r:
            all_dong += r + [""]
    r = do_anh("DANG TOT (canh bao hong khung)", VIDEO_TOT)
    if r:
        all_dong += r + [""]

    duong = os.path.join(THU_MUC_KC, "bench_nang_cao.txt")
    with open(duong, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(all_dong) + "\n")
    print(f"\nBAO CAO: {duong}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)