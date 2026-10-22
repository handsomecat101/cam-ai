# -*- coding: utf-8 -*-
"""ĐO LẠI có warm-up + end-to-end (coordinator) — tìm bottleneck thật."""
import os
import subprocess
import sys
import time

APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
VIDEO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(APP, "video_mau", "car-detection.mp4")
PY = os.path.join(APP, ".venv", "Scripts", "python.exe")

print("=" * 70)
print("A) YOLO CO WARM-UP (doc lai dung nguon su that)")
print("=" * 70)
import cv2  # noqa: E402
import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

cap = cv2.VideoCapture(VIDEO)
khung = []
for _ in range(160):
    ok, f = cap.read()
    if not ok:
        break
    khung.append(f)
cap.release()
n = len(khung)
print(f"video: {n} khung mau")

model = YOLO(os.path.join(APP, "yolo11n.pt")).to("cuda")

# LAN DAU (chua warm-up) - thuong gom ca khoi tao CUDA
t0 = time.perf_counter()
model(khung[0], verbose=False, conf=0.25)
t_first = (time.perf_counter() - t0) * 1000
print(f"LAN DAU (co khoi tao CUDA): {t_first:.0f} ms/frame  <-- day co the la thu pham")

# WARM-UP 15 khung
for f in khung[1:16]:
    model(f, verbose=False, conf=0.25)

# DO THAT TRANG THAI ON DINH
t0 = time.perf_counter()
for f in khung[16:116]:
    model(f, verbose=False, conf=0.25)
t_yolo = (time.perf_counter() - t0) * 1000 / 100
print(f"TRANG THAI ON DINH       : {t_yolo:.2f} ms/frame = {1000/t_yolo:.1f} frame/s")

# THU: half=True (FP16) tren GPU
try:
    mh = YOLO(os.path.join(APP, "yolo11n.pt")).to("cuda")
    mh.half()
    for f in khung[1:11]:
        mh(f, verbose=False, conf=0.25)
    t0 = time.perf_counter()
    for f in khung[16:116]:
        mh(f, verbose=False, conf=0.25, half=True)
    t_half = (time.perf_counter() - t0) * 1000 / 100
    print(f"FP16 (half=True)         : {t_half:.2f} ms/frame = {1000/t_half:.1f} frame/s")
except Exception as e:  # noqa: BLE001
    print("half=True loi:", e)

# THU: batch nhieu khung 1 lan
try:
    for f in khung[1:11]:
        model(f, verbose=False, conf=0.25)
    t0 = time.perf_counter()
    for i in range(10):
        model(khung[16 + i * 8:16 + (i + 1) * 8], verbose=False, conf=0.25)
    t_batch = (time.perf_counter() - t0) * 1000 / 80
    print(f"BATCH 8 khung/lan       : {t_batch:.2f} ms/frame = {1000/t_batch:.1f} frame/s")
except Exception as e:  # noqa: BLE001
    print("batch loi:", e)

# THU: ONNX + TensorRT (da co yolo11n.onnx san)
onnx = os.path.join(APP, "yolo11n.onnx")
if os.path.exists(onnx):
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(onnx, providers=["CUDAExecutionProvider"])
        inp = sess.get_inputs()[0]
        print(f"ONNX provider: {sess.get_providers()} | input: {inp.name} {inp.shape}")
    except Exception as e:  # noqa: BLE001
        print("ONNX loi:", e)

print("\n" + "=" * 70)
print("B) END-TO-END (cam_ai_core chay that, nhu app dang chay)")
print("=" * 70)
for ten, extra in (("chi nguoi", []),
                   ("nhan vat the tieng Viet", ["--nhan-vat-the", "--lop", "ô tô,xe máy"]),
                   ("doc bien so", ["--doc-bien-so"]),
                   ("nhan dien mat", ["--faces", os.path.join(APP, "known_faces")])):
    out = os.path.join(APP, "_kk_out", "do_e2e")
    os.makedirs(out, exist_ok=True)
    t0 = time.perf_counter()
    p = subprocess.run([PY, "-W", "ignore", os.path.join(APP, "app.py"),
                        "--input", VIDEO, "--output", out] + extra,
                       capture_output=True, timeout=900)
    dt = time.perf_counter() - t0
    import cv2 as _cv2
    cap = _cv2.VideoCapture(VIDEO)
    nk = int(cap.get(_cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    fps_vid = nk / dt if dt else 0
    print(f"{ten:<26} exit={p.returncode} {dt:6.1f}s cho {nk} khung "
          f"=> {fps_vid:5.2f} khung/s (video goc 12,5 fps)")
