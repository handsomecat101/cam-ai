r"""MUC TIEU 2: dem cap nhan CHONG tren khung hinh co >=10 nguoi don cuc.

Cach do:
1. Tim trong cac video demo khung hinh co NHIEU nguoi nhat (>=10).
2. Ve that su bang ham `ve_nguoi` cua gui_khung (dung ham dat nhan + font that).
3. Ham tra ve list rect cua TUNG nhan da dat -> dem moi CAP co chong nhau.
4. Luu anh ket qua de mat xem bang mat.

Khong tinh vao cac vung da bi chiem (bang thong ke, nhan vung) o day: ham
`_dat_nhan_khong_cham` nhan `cam` va tra ve rect - nhan tu KHONG chong nhan.
"""

from __future__ import annotations

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

KT = os.path.join(APP_DIR, "_kiem_chung")
VIDEO = [
    os.path.join(APP_DIR, "video_mau", "moi", "dam-dong.mp4"),
    os.path.join(APP_DIR, "video_mau", "moi", "nguoi-dung-cho.mp4"),
    os.path.join(APP_DIR, "video_mau", "moi", "tre-em-san-choi.mp4"),
    os.path.join(APP_DIR, "video_mau", "moi", "nguoi-di-lai.mp4"),
    os.path.join(APP_DIR, "video_test_300s.mp4"),
]


def main() -> int:
    os.makedirs(KT, exist_ok=True)
    import cv2
    from PIL import Image
    from ultralytics import YOLO

    import gui_khung as GK

    import numpy as np

    det = YOLO("yolo11n.pt")
    det(np.zeros((540, 960, 3), dtype=np.uint8), verbose=False)   # warmup

    best = None                            # (so_nguoi, video, frame_index, frame)
    for duong_dan in VIDEO:
        if not os.path.isfile(duong_dan):
            continue
        cap = cv2.VideoCapture(duong_dan)
        if not cap.isOpened():
            continue
        i = 0
        buoc = 15
        while True:
            cap.grab()
            if i % buoc:
                i += 1
                continue
            ok, frame = cap.read()
            if not ok:
                break
            i += 1
            r = det(frame, verbose=False, conf=0.25)[0]
            n = 0
            if r.boxes is not None:
                for c in r.boxes.cls.tolist():
                    if int(c) == 0:
                        n += 1
            if best is None or n > best[0]:
                best = (n, duong_dan, i, frame.copy())
                if n >= 15:          # du don, dung lai
                    break
            if i > 2500:
                break
        cap.release()
        if best and best[0] >= 10:
            break

    if best is None:
        print("KHONG tim duoc khung hinh nao")
        return 2

    n, duong_dan, chi_so, frame = best
    print(f"khung hinh nhieu nguoi nhat: {n} nguoi")
    print(f"  video : {os.path.basename(duong_dan)}  khung {chi_so}")

    if n < 10:
        print("KHONG DAT: can it nhat 10 nguoi")
        return 1

    r = det(frame, verbose=False, conf=0.25)[0]
    boxes, nhan, mau, uu = [], [], [], []
    ten = ["An", "Binh", "Chi", "Duc"]
    for j, b in enumerate(r.boxes.xyxy.tolist()):
        if int(r.boxes.cls[j]) != 0:
            continue
        boxes.append(b)
        # MOI nguoi deu co nhan - day la ban KHO CHAT nhat cho thuat toan.
        if j % 4 == 0:
            nhan.append(f"{ten[(j // 4) % len(ten)]} · {30 + j % 40} · Nam")
            uu.append(0.9)
        else:
            nhan.append(f"Người {j + 1}")
            uu.append(0.4)
        mau.append("#22C55E")

    nhan_co = [x for x in nhan if x]
    print(f"so nhan can ve        : {len(nhan_co)} / {len(boxes)} khung")

    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    rects = GK.ve_nguoi(img, boxes, nhan, mau, 15, 2, uu_tien=uu)

    print(f"so nhan THUC SU ve    : {len(rects)}")

    # --- dem moi cap co chong nhau ---
    cap_chong = 0
    for a in range(len(rects)):
        ax1, ay1, ax2, ay2 = rects[a]
        for b in range(a + 1, len(rects)):
            bx1, by1, bx2, by2 = rects[b]
            giao_x = min(ax2, bx2) - max(ax1, bx1)
            giao_y = min(ay2, by2) - max(ay1, by1)
            if giao_x > 0 and giao_y > 0:
                cap_chong += 1
                print(f"  CHONG: {rects[a]} <-> {rects[b]}"
                      f"  giao {giao_x}x{giao_y}px")

    # --- nhan co trong khung khong? ---
    trong = all(0 <= v[0] and 0 <= v[1] and v[2] <= img.width and v[3] <= img.height
                for v in rects)

    duong = os.path.join(KT, "kk_35_don_cuc_10_nguoi.png")
    img.save(duong)

    print("")
    print(f"SO CAP NHAN CHONG    : {cap_chong}")
    print(f"tat ca nhan trong khung: {trong}")
    print(f"anh luu               : {duong}")
    print("")
    if cap_chong == 0 and n >= 10:
        print("KET LUAN: DAT (0 cap chong tren khung >=10 nguoi)")
        return 0
    print("KET LUAN: CHUA DAT")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())