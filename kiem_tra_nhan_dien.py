"""
Kiem tra nhan dien khuon mat (ArcFace) co chay khong.

Chay:
    .venv\\Scripts\\python.exe kiem_tra_nhan_dien.py video_test.mp4

In ra: so mat tim thay, rut duoc ten gi, va uoc luong tuoi/giới tính.
"""

import sys
from collections import Counter

import cv2

from face_engine import FaceEngine


def main() -> None:
    video = sys.argv[1] if len(sys.argv) > 1 else "video_test.mp4"
    max_frames = int(sys.argv[2]) if len(sys.argv) > 2 else 250

    engine = FaceEngine()

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise SystemExit(f"[loi] khong mo duoc video: {video}")

    total_faces = 0
    matched = Counter()
    ages: list[int] = []
    sexes = Counter()
    index = 0

    while cap.isOpened() and index < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        index += 1

        for result in engine.analyze(frame):
            total_faces += 1
            if result.is_known:
                matched[result.name] += 1
            if result.age:
                ages.append(result.age)
            if result.sex:
                sexes[result.sex] += 1

    cap.release()

    print("\n========== KET QUA ==========")
    print(f"Video             : {video}")
    print(f"Khung hinh quet   : {index}")
    print(f"Tong so mat thay  : {total_faces}")
    print(f"Rut duoc ten      : {sum(matched.values())} lan")
    for name, count in matched.most_common():
        print(f"   - {name:<12} {count} lan")
    if not matched:
        print("   - (khong rut duoc ten nao)")
    if ages:
        print(f"Uoc luong tuoi    : {min(ages)} - {max(ages)} tuoi")
    if sexes:
        print(f"Uoc luong gioi tinh: {dict(sexes)}")
    print("==============================\n")
    print("Hien thi:\n"
          "  [ten co]     Da hoc truoc trong known_faces/<Ten>/.\n"
          "  [Nguoi la]   Chua cho may xem mat nguoi nay -> them anh vao known_faces.\n"
          "  [tuoi/gioi]  Chi uoc luong, dung de thong ke - khong phai do chinh xac.\n")


if __name__ == "__main__":
    main()