# -*- coding: utf-8 -*-
"""ĐO nhanh: pipeline phân tích video chậm ở đâu? (coordinator)

Tách riêng từng bước để biết bottleneck thật, không đoán.
"""
import os
import sys
import time

APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)

VIDEO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(APP, "video_mau", "car-detection.mp4")
SO_KHUNG = int(sys.argv[2]) if len(sys.argv) > 2 else 60

import cv2  # noqa: E402
import numpy as np  # noqa: E402

print("=" * 68)
print("DO TOI DO PIPELINE")
print("=" * 68)
print("video:", VIDEO)

cap = cv2.VideoCapture(VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"video: {n} khung | {fps:.2f} fps | {w}x{h} | tong thoi gian {n/max(fps,1):.1f}s")
cap.release()

# --- 1. doc khung thu (I/O) ---
cap = cv2.VideoCapture(VIDEO)
t0 = time.perf_counter()
khung = []
for _ in range(min(SO_KHUNG, n)):
    ok, f = cap.read()
    if not ok:
        break
    khung.append(f)
cap.release()
t_doc = time.perf_counter() - t0
print(f"\n[1] DOC KHUNG      : {t_doc*1000:.0f} ms cho {len(khung)} khung "
      f"= {len(khung)/t_doc:.1f} khung/s")

# --- 2. YOLO detect ---
t0 = time.perf_counter()
from ultralytics import YOLO  # noqa: E402
t_import_yolo = time.perf_counter() - t0
print(f"[2] IMPORT ultralytics: {t_import_yolo*1000:.0f} ms")

t0 = time.perf_counter()
model = YOLO(os.path.join(APP, "yolo11n.pt"))
t_load = time.perf_counter() - t0
print(f"[3] LOAD MODEL     : {t_load*1000:.0f} ms")

import torch  # noqa: E402
dev = "cuda" if torch.cuda.is_available() else "cpu"
t0 = time.perf_counter()
for f in khung:
    model.predict(f, verbose=False, device=dev)
t_yolo = time.perf_counter() - t0
print(f"[4] YOLO ({dev})     : {t_yolo*1000:.0f} ms / {len(khung)} khung "
      f"= {t_yolo/len(khung)*1000:.1f} ms/khung = {len(khung)/t_yolo:.1f} khung/s")

# --- 3. face engine ---
t0 = time.perf_counter()
from face_engine import FaceEngine  # noqa: E402
t_import_face = time.perf_counter() - t0
print(f"[5] IMPORT face_engine: {t_import_face*1000:.0f} ms")

t0 = time.perf_counter()
try:
    fe = FaceEngine(os.path.join(APP, "known_faces"))
    t_fe = time.perf_counter() - t0
    print(f"[6] LOAD FaceEngine: {t_fe*1000:.0f} ms")
    t0 = time.perf_counter()
    for f in khung[:20]:
        fe.detect_and_recognize(f)
    t_face = time.perf_counter() - t0
    print(f"[7] FACE tren {20} khung: {t_face*1000:.0f} ms "
          f"= {t_face/20*1000:.1f} ms/khung")
except Exception as e:  # noqa: BLE001
    print("[6-7] FaceEngine loi:", e)
    t_face = 0.0

# --- 4. OCR bien so ---
t0 = time.perf_counter()
try:
    from bien_so import BienSoEngine  # noqa: E402
    t_import_ocr = time.perf_counter() - t0
    print(f"[8] IMPORT bien_so  : {t_import_ocr*1000:.0f} ms")
    t0 = time.perf_counter()
    ocr = BienSoEngine()
    t_ocr_load = time.perf_counter() - t0
    print(f"[9] LOAD OCR engine : {t_ocr_load*1000:.0f} ms")
except Exception as e:  # noqa: BLE001
    print("[8-9] OCR loi (bo qua):", e)
    t_ocr_load = 0.0

# --- 5. ghi video ---
t0 = time.perf_counter()
out = os.path.join(APP, "_kk_out", "do_toi_do.mp4")
os.makedirs(os.path.dirname(out), exist_ok=True)
vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
for f in khung:
    vw.write(f)
vw.release()
t_write = time.perf_counter() - t0
print(f"[10] GHI VIDEO      : {t_write*1000:.0f} ms / {len(khung)} khung "
      f"= {t_write/len(khung)*1000:.2f} ms/khung")

# --- 6. JPEG nen cho GUI ---
t0 = time.perf_counter()
for f in khung:
    cv2.imencode(".jpg", f, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
t_jpeg = time.perf_counter() - t0
print(f"[11] JPEG (GUI)     : {t_jpeg*1000:.0f} ms / {len(khung)} khung "
      f"= {t_jpeg/len(khung)*1000:.2f} ms/khung")

# --- 7. PIL overlay chu Viet ---
try:
    from PIL import Image, ImageDraw, ImageFont  # noqa: E402
    t0 = time.perf_counter()
    img = Image.fromarray(khung[0])
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("segoeui.ttf", 22)
    except Exception:  # noqa: BLE001
        font = None
    for i in range(len(khung)):
        d.text((10, 10), f"Người 12345", fill=(255, 255, 255), font=font)
    t_pil = time.perf_counter() - t0
    print(f"[12] PIL overlay    : {t_pil*1000:.0f} ms / {len(khung)} khung "
          f"= {t_pil/len(khung)*1000:.2f} ms/khung")
except Exception as e:  # noqa: BLE001
    print("[12] PIL loi:", e)
    t_pil = 0.0

print("\n" + "=" * 68)
print("TONG THOI GIAN MOT KHUNG (khong tinh doc file)")
print("=" * 68)
buoc = [
    ("YOLO detect", t_yolo),
    ("Nhan dien mat (ArcFace)", t_face),
    ("OCR bien so", t_ocr_load),
    ("Ghi video", t_write),
    ("JPEG cho GUI", t_jpeg),
    ("PIL overlay chu Viet", t_pil),
]
for ten, t in buoc:
    if t:
        print(f"  {ten:<26} {t/len(khung)*1000:7.2f} ms/khung")
tong = t_yolo + t_face + t_ocr_load + t_write + t_jpeg + t_pil
print(f"  {'TONG (uoc)':<26} {tong/len(khung)*1000:7.2f} ms/khung "
      f"=> {1000/(tong/len(khung)):7.1f} khung/s")
print(f"  {'Doc file':<26} {t_doc/len(khung)*1000:7.2f} ms/khung")
print("\nLUU Y: doc tep phan tach 1/2 (chay lien tiep se cham gioi han)")
print("=" * 68)
