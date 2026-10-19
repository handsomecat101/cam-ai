r"""Do chi phi tung phan cua 1 vong ve khung hinh xem truc tiep.

Tach rieng: doc frame - YOLO - ve overlay PIL - nen JPEG - gia doi ma JPEG.
Muc tieu: biet bottleneck nam o dau de sua dung cho, thay vi doan.
"""

from __future__ import annotations

import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

import cv2                                    # noqa: E402
import numpy as np                            # noqa: E402
import supervision as sv                      # noqa: E402
from ultralytics import YOLO                  # noqa: E402

import gui_khung as GK                        # noqa: E402

VIDEO = sys.argv[1] if len(sys.argv) > 1 else "video_test_300s.mp4"
SO_LAN = int(sys.argv[2]) if len(sys.argv) > 2 else 30


def tb(v):
    v = sorted(v)
    return sum(v) / len(v) if v else 0.0


def p50(v):
    if not v:
        return 0.0
    v = sorted(v)
    return v[len(v) // 2]


def main() -> int:
    cap = cv2.VideoCapture(VIDEO)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    det = YOLO("yolo11n.pt")
    tracker = sv.ByteTrack()

    ok, frame = cap.read()
    if not ok:
        print("khong doc duoc video")
        return 2

    # warmup (lan dau YOLO rat cham)
    det(frame, verbose=False, conf=0.25)

    t_doc, t_yolo, t_ve, t_jpeg, t_giai, t_grab = [], [], [], [], [], []

    for i in range(SO_LAN):
        t = time.perf_counter()
        cap.grab()
        t_grab.append((time.perf_counter() - t) * 1000)
        ok, frame = cap.read()
        t_doc.append((time.perf_counter() - t) * 1000)
        if not ok:
            break

        t = time.perf_counter()
        tat_ca = sv.Detections.from_ultralytics(det(frame, verbose=False, conf=0.25)[0])
        d = tat_ca[tat_ca.class_id == 0]
        d = tracker.update_with_detections(d)
        t_yolo.append((time.perf_counter() - t) * 1000)

        boxes, nhan, mau, uu = [], [], [], []
        if len(d):
            xy = d.xyxy
            ids = [int(x) for x in d.tracker_id] if d.tracker_id is not None else []
            cf = [float(c) for c in d.confidence]
            for j, box in enumerate(xy):
                boxes.append([float(v) for v in box])
                nhan.append(f"Người {ids[j] if j < len(ids) else j+1} · 34 · Nam")
                mau.append("#22C55E")
                uu.append(0.5)

        t = time.perf_counter()
        hien = GK.ve_khung_hinh(
            frame,
            boxes_nguoi=boxes, nhan_nguoi=nhan, mau_nguoi=mau, uu_tien_nguoi=uu,
            boxes_vat=[], nhan_vat=[],
            zone_px=None, trang_thai_vung="", nguoi_trong_vung=0, nguoi_toi_da=0,
            vao=0, ra=0,
            hien_khung=True, hien_nhan=True, hien_vach=True, hien_vung=False,
            chu_dien=[f"Nguoi: {len(boxes)}", "Nguoi quen: 2"],
            bang_vung=(),
        )
        t_ve.append((time.perf_counter() - t) * 1000)

        t = time.perf_counter()
        ok2, buf = cv2.imencode(".jpg", hien, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        t_jpeg.append((time.perf_counter() - t) * 1000)

        t = time.perf_counter()
        arr = cv2.imdecode(np.frombuffer(buf.tobytes(), np.uint8), cv2.IMREAD_COLOR)
        t_giai.append((time.perf_counter() - t) * 1000)

    tong = tb(t_grab) + tb(t_doc) + tb(t_yolo) + tb(t_ve) + tb(t_jpeg) + tb(t_giai)
    print(f"video: {VIDEO}   so vong: {len(t_doc)}   fps video: {fps:.0f}")
    print(f"so nguoi trung binh tren khung: {len(boxes)}")
    print("")
    print(f"{'phan':<26}{'trung binh ms':>14}{'p50 ms':>10}")
    print("-" * 50)
    for ten, v in (("cap.grab()", t_grab), ("cap.read()", t_doc),
                   ("YOLO + ByteTrack", t_yolo), ("ve_khung_hinh (PIL)", t_ve),
                   ("JPEG encode", t_jpeg), ("JPEG decode", t_giai)):
        print(f"{ten:<26}{tb(v):>14.1f}{p50(v):>10.1f}")
    print("-" * 50)
    print(f"{'TONG 1 VONG':<26}{tong:>14.1f}")
    print(f"{'=> FPS ly tuong':<26}{1000 / tong if tong else 0:>14.1f}")
    print("")
    phan = {"grab": tb(t_grab), "read": tb(t_doc), "yolo": tb(t_yolo),
            "ve PIL": tb(t_ve), "nen JPEG": tb(t_jpeg), "giai JPEG": tb(t_giai)}
    lon = max(phan, key=phan.get)
    print(f"PHA NGHEN CHINH: {lon} ({phan[lon]:.1f} ms, "
          f"{phan[lon] / tong * 100:.0f}% tong thoi gian)")
    cap.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())