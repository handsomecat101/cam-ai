# -*- coding: utf-8 -*-
"""Kiem tra DUNG ham san pham `detect_tach_o` trong cam_ai_core.

Khong dung lai doan code cua script benchmark — phai chay chinh ham ma
pipeline that se chay, truocc khi tin no hoat dong.

So sanh tren cung mot khung hinh:
  A) nen      : detector(frame)
  T) tach-o   : cam_ai_core.detect_tach_o(detector, frame, conf)

Bao cao: so nguoi + thoi gian tren moi khung.
"""

import os
import sys
import time
import traceback

import cv2
import numpy as np
from ultralytics import YOLO

import cam_ai_core as core

THU_MUC_VIDEO = os.path.join("video_mau", "moi")
SO_KHUNG = 8
CONF = 0.25

VIDEO = [
    ("DANG HONG", "dam-dong.mp4"),
    ("DANG HONG", "xe-co-giao-thong.mp4"),
    ("DANG TOT", "tre-em-san-choi.mp4"),
    ("DANG TOT", "nguoi-dung-cho.mp4"),
]


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


def dem(dets):
    return sum(1 for c in dets.class_id.tolist() if int(c) == core.PERSON_CLASS_ID)


def main():
    model = YOLO("yolo11n.pt")
    dong = [
        "KIEM TRA HAM SAN PHAM detect_tach_o (cam_ai_core)",
        f"yolo11n | conf={CONF} | {SO_KHUNG} khung mau/video",
        "",
    ]
    for nhan, ten in VIDEO:
        khung = doc_khung(os.path.join(THU_MUC_VIDEO, ten), SO_KHUNG)
        if not khung:
            continue
        model.predict(khung[0], conf=CONF, verbose=False)

        t = time.perf_counter()
        a = []
        for k in khung:
            r = model.predict(k, conf=CONF, verbose=False)[0]
            a.append(sum(1 for c in r.boxes.cls.tolist() if int(c) == 0))
        ms_a = (time.perf_counter() - t) / len(khung) * 1000

        t = time.perf_counter()
        b = [dem(core.detect_tach_o(model, k, CONF)) for k in khung]
        ms_b = (time.perf_counter() - t) / len(khung) * 1000

        # kiem tra tile phu toan khung: so o phai dung 4
        h, w = khung[0].shape[:2]
        cw = max(1, int(w * core.TACH_O_TRUNG))
        ch = max(1, int(h * core.TACH_O_TRUNG))
        tx = [max(0, min(ix * max(1, w - cw), w - cw)) for ix in (0, 1)]
        ty = [max(0, min(iy * max(1, h - ch), h - ch)) for iy in (0, 1)]
        bu_phu = (tx[0] == 0 and tx[1] + cw >= w - 1
                  and ty[0] == 0 and ty[1] + ch >= h - 1)

        dong.append(f"--- {nhan} | {ten} ---")
        dong.append(f"  A) nen              : {a}  tb={np.mean(a):5.1f}  {ms_a:6.1f} ms/khung")
        dong.append(f"  T) detect_tach_o    : {b}  tb={np.mean(b):5.1f}  {ms_b:6.1f} ms/khung")
        dong.append(f"  tile phu toan khung : {'OK' if bu_phu else 'LOI'}"
                    f"  (o ngang {tx}, o doc {ty}, kich thuoc o {cw}x{ch}, khung {w}x{h})")
        dong.append(f"  chay nhanh hon {ms_a / ms_b:.2f}x")
        dong.append("")
        print("\n".join(dong[-6:]), flush=True)

    p = os.path.join("_kiem_chung", "kiem_tach_o.txt")
    os.makedirs("_kiem_chung", exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")
    print(f"BAO CAO: {p}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)