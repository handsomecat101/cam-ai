"""Kiem chung nhan tren khung hinh: class id + ten tieng Viet + font co ve dau hay khong.

Chay:
    .venv\\Scripts\\python.exe _kk_kiem_khung_hinh_xe.py

Doc video ket qua cua lan chay --lop "o to,xe may", in ra class id + ten
tieng Viet cua tung vật thể, va cat anh khung hinh de soi mat.
"""

import os
import sys

import cv2
import numpy as np

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

VIDEO = os.path.join(APP_DIR, "_kk_out", "lop_viet_khong_dau_ket_qua.mp4")
VIDEO_CO_DAU = os.path.join(APP_DIR, "_kk_out", "lop_viet_co_dau_ket_qua.mp4")
OUT_PNG = os.path.join(APP_DIR, "_kk_out", "_kk_nhan_khung_hinh.png")
OUT_PNG2 = os.path.join(APP_DIR, "_kk_out", "_kk_nhan_khung_hinh_2.png")


def main():
    import lop_viet
    from ultralytics import YOLO

    print("=" * 72)
    print("A. CLASS ID + TEN TIENG VIET tren video ket qua (lop_viet_khong_dau)")
    print("=" * 72)
    cap = cv2.VideoCapture(VIDEO)
    model = YOLO(os.path.join(APP_DIR, "yolo11n.pt"))
    names = model.names
    da_tim = False
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        idx += 1
        if idx % 300:
            continue
        r = model(frame, verbose=False, conf=0.25)[0]
        if r.boxes is None or len(r.boxes) == 0:
            continue
        cls = r.boxes.cls.tolist()
        if not any(names[int(c)] in ("car", "motorcycle") for c in cls):
            continue
        print(f"  frame {idx}:")
        for i, c in enumerate(cls):
            ten_anh = names[int(c)]
            print(
                f"    class_id={int(c):>2}  ten_anh={ten_anh:<12} "
                f"ten_viet_co_dau='{lop_viet.TEN_LOP_VIET[ten_anh]}' "
                f"| nhan_khung_hinh='{lop_viet.TEN_LOP_VIET_KHONG_DAU[ten_anh]}'"
            )
        if not da_tim:
            cv2.imwrite(OUT_PNG, frame)
            print(f"  -> da luu anh kiem tra: {OUT_PNG}")
            da_tim = True
        break
    cap.release()

    print()
    print("=" * 72)
    print("B. SO SANH VIDEO KET QUA: co dau vs khong dau -> PHAI GIONG NHAU")
    print("=" * 72)
    cap1 = cv2.VideoCapture(VIDEO)
    cap2 = cv2.VideoCapture(VIDEO_CO_DAU)
    khac_biet = 0
    dem = 0
    while True:
        ok1, f1 = cap1.read()
        ok2, f2 = cap2.read()
        if not (ok1 and ok2):
            break
        dem += 1
        if not np.array_equal(f1, f2):
            khac_biet += 1
    cap1.release()
    cap2.release()
    print(f"  so khung hinh so sanh: {dem}")
    print(f"  so khung hinh KHAC NHAU: {khac_biet}")
    print("  -> '0' = nhan tren khung hinh giong het (khong dau) o ca 2 ban")

    print()
    print("=" * 72)
    print("C. FONT: cv2.putText co ve duoc dau tieng Viet khong?")
    print("=" * 72)
    anh = np.full((120, 760, 3), 25, np.uint8)
    cv2.putText(anh, "xe o to (khong dau)", (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(anh, "o to co dau", (10, 85), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(anh, "xe may co dau", (10, 115), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 255, 0), 1, cv2.LINE_AA)
    cv2.imwrite(OUT_PNG2, anh)
    print(f"  -> da luu anh so sanh font: {OUT_PNG2}")
    print("  (xem anh: neu 'co dau' VAN ra y nguyen 'khong dau' -> font BO QUA dau)")
    print(f"  font supervision LabelAnnotator: CV2_FONT = cv2.FONT_HERSHEY_SIMPLEX")
    return 0


if __name__ == "__main__":
    sys.exit(main())
