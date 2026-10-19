# -*- coding: utf-8 -*-
"""Thu nghiem phuong an GOP: toan khung + chia o 2x2 dung chung.

Ly do: lan doan tach 2x2 giup nguoi o xa nhung LAM MAT nguoi o gan
(nguoi bi cat o ranh o). Vay th toan khung de doi la phai dung.

KHONG sua code san pham. Chi do.
"""

import os
import sys
import time
import traceback

import cv2
import numpy as np
from ultralytics import YOLO

THU_MUC_VIDEO = os.path.join("video_mau", "moi")
PERSON = 0
CONF = 0.25
SO_KHUNG = 8

VIDEO = [
    ("DANG HONG", "nguoi-di-lai.mp4"),
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


def hop_nms(boxes, nms=0.45, ionn=0.55):
    if not boxes:
        return 0
    b = np.array(boxes, dtype=np.float32)
    k = cv2.dnn.NMSBoxes(
        [list(map(float, x)) for x in b], [1.0] * len(b), nms, ionn
    )
    return len(k) if isinstance(k, (list, tuple)) else int(len(k))


def boxes_thuan(model, o, xo=0, yo=0):
    r = model.predict(o, conf=CONF, verbose=False)[0]
    ra = []
    for xyxy, cid in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist()):
        if int(cid) == PERSON:
            ra.append([xyxy[0] + xo, xyxy[1] + yo, xyxy[2] + xo, xyxy[3] + yo])
    return ra


def o_2x2(model, khung, trung=0.35):
    h, w = khung.shape[:2]
    buoc = int(w * (1 - trung))
    boxes = []
    for iy in range(2):
        for ix in range(2):
            x0 = min(ix * buoc, w - int(w * trung))
            y0 = min(iy * buoc, h - int(h * trung))
            x1 = min(x0 + int(w * trung), w)
            y1 = min(y0 + int(h * trung), h)
            boxes += boxes_thuan(model, khung[y0:y1, x0:x1], x0, y0)
    return boxes


def hop_a(model, khung):
    return len(boxes_thuan(model, khung))


def hop_gop(model, khung):
    b = boxes_thuan(model, khung) + o_2x2(model, khung)
    return hop_nms(b)


def hop_gop_chon(model, khung):
    """Gop nhung uu tien nhan toan khung khi it nguoi (canh gan),
    dung o khi nhieu nguoi nho (canh xa)."""
    b0 = boxes_thuan(model, khung)
    if len(b0) >= 4:
        return hop_nms(b0)
    return hop_nms(b0 + o_2x2(model, khung))


def main():
    mo = YOLO("yolo11n.pt")
    dong = [
        "THU NGHIEM PHUONG AN GOP: toan khung + o 2x2",
        f"yolo11n | conf={CONF} | {SO_KHUNG} khung mau/video",
        "",
    ]
    for nhan, ten in VIDEO:
        duong = os.path.join(THU_MUC_VIDEO, ten)
        khung = doc_khung(duong, SO_KHUNG)
        if not khung:
            continue
        mo.predict(khung[0], conf=CONF, verbose=False)

        t = time.perf_counter()
        a = [hop_a(mo, k) for k in khung]
        ms_a = (time.perf_counter() - t) / len(khung) * 1000

        t = time.perf_counter()
        g = [hop_gop(mo, k) for k in khung]
        ms_g = (time.perf_counter() - t) / len(khung) * 1000

        t = time.perf_counter()
        c = [hop_gop_chon(mo, k) for k in khung]
        ms_c = (time.perf_counter() - t) / len(khung) * 1000

        dong.append(f"--- {nhan} | {ten} ---")
        dong.append(f"  A  toan khung          : {a}  tb={np.mean(a):5.1f}  {ms_a:6.1f} ms")
        dong.append(f"  G  toan khung + o 2x2   : {g}  tb={np.mean(g):5.1f}  {ms_g:6.1f} ms")
        dong.append(f"  C  gop co chon (<4 nguoi): {c}  tb={np.mean(c):5.1f}  {ms_c:6.1f} ms")
        dong.append("")
        print("\n".join(dong[-5:]), flush=True)

    p = os.path.join("_kiem_chung", "bench_gop.txt")
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