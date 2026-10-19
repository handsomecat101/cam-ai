"""Coordinator tu kiem chung so do CPU khong GPU cho vai model YOLO11.

Do lai bang chinh script nay, khong tin bao cao cua subagent.
Chay: .venv\Scripts\python.exe -W ignore _kk_xac_nhan_cpu.py
"""

import sys
import time
from pathlib import Path

import torch
from ultralytics import YOLO

SO_KHUNG = 60
IMGSZ = 640
CONF = 0.25


def do_model(path, frames):
    model = YOLO(path)
    model.to("cpu")
    model.fuse()

    # warm-up: chay 5 khung de model nap trong RAM
    for i in range(5):
        model.predict(frames[i % len(frames)], imgsz=IMGSZ, conf=CONF,
                      device="cpu", verbose=False)

    bat_dau = time.perf_counter()
    for i in range(SO_KHUNG):
        model.predict(frames[i % len(frames)], imgsz=IMGSZ, conf=CONF,
                      device="cpu", verbose=False)
    tong = time.perf_counter() - bat_dau
    return SO_KHUNG / tong


def nap_khung():
    import cv2

    video = Path("video_mau") / "moi" / "nguoi-dung-cho.mp4"
    cap = cv2.VideoCapture(str(video))
    khung = []
    doc = 0
    while doc < 12:
        ok, frame = cap.read()
        if not ok:
            break
        khung.append(frame)
        doc += 1
    cap.release()
    if not khung:
        raise SystemExit("Khong doc duoc video mau")
    return khung


def main():
    print("cuda:", torch.cuda.is_available())
    print("so khung moi model:", SO_KHUNG)
    print()

    khung = nap_khung()
    print("video mau:", khung[0].shape)

    ket_qua = {}
    for ten in ("yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt"):
        if not (Path(ten)).exists():
            print(ten, "-> THIEU FILE, bo qua")
            continue
        fps = do_model(ten, khung)
        ket_qua[ten] = fps
        print(f"{ten:12s} CPU {fps:6.2f} fps")
        print()

    print("=" * 46)
    print("KET LUA (CPU, khong GPU)")
    for ten, fps in ket_qua.items():
        print(f"  {ten:12s} {fps:6.2f} fps")
    print("=" * 46)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)