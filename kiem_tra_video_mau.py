"""
Quet bo video mau: do bang thong so + so nguoi YOLO thay trong tung video.

Muc dich: biet video nao dung tinh huong nao (it nguoi / dong nguoi / khong co
nguoi) de chon video phu hop khi kiem tra tinh nang dem nguoi, canh vung,
ra vao, nhan dien mat.

Chay:
    .venv\\Scripts\\python.exe kiem_tra_video_mau.py
    .venv\\Scripts\\python.exe kiem_tra_video_mau.py --thu-muc video_mau --buoc 20
    .venv\\Scripts\\python.exe kiem_tra_video_mau.py --chi-face
"""

import argparse
import os

import cv2
from ultralytics import YOLO

PERSON_CLASS_ID = 0


def quet_mot_video(path, detector, buoc):
    """Mo video, quet moi buoc khung hinh, dem nguoi. Tra ve dict ket qua."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return {"loi": "khong mo duoc video"}

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

    counts = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % buoc == 0:
            res = detector.predict(frame, verbose=False)[0]
            n = int((res.boxes.cls == PERSON_CLASS_ID).sum().item())
            counts.append(n)
        idx += 1
    cap.release()

    if not counts:
        return {
            "loi": "khong doc duoc khung hinh nao",
            "width": width,
            "height": height,
        }

    n0 = sum(1 for c in counts if c == 0)
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "total": total,
        "gia": round(total / fps, 1) if fps else 0.0,
        "so_khung": len(counts),
        "buoc": buoc,
        "max": max(counts),
        "tb": round(sum(counts) / len(counts), 2),
        "pct_rong": round(100.0 * n0 / len(counts)),
    }


def goi_y(r):
    """Tu do so nguoi, tan ra tinh huong cua video."""
    if "loi" in r:
        return "LOI: " + r["loi"]
    if r["pct_rong"] >= 95:
        return "KHONG CO NGUOI -> dung de kiem tra phai meo bao nguoi"
    if r["max"] >= 10:
        return "RAT DONG -> vung --vung-max, canh dau"
    if r["max"] >= 4:
        return "NHIEU NGUOI -> vung, dem ra/vao"
    if r["max"] >= 2:
        return "VAI NGUOI -> nhan dien mat, vung nhay"
    return "IT NGUOI -> nhan dien nguoi quen, cham 1 nguoi vao vung"


def main():
    ap = argparse.ArgumentParser(description="quet bo video mau")
    ap.add_argument("--thu-muc", default="video_mau", help="thu muc chua video")
    ap.add_argument("--model", default="yolo11n.pt", help="model phat hien vat the")
    ap.add_argument(
        "--buoc", type=int, default=15, help="quet moi bao nhieu khung hinh (15 = nhanh)"
    )
    ap.add_argument("--chi-face", action="store_true", help="chi quet video co 'face'")
    args = ap.parse_args()

    if not os.path.isdir(args.thu_muc):
        print(f"[loi] khong thay thu muc: {args.thu_muc}")
        return

    files = sorted(f for f in os.listdir(args.thu_muc) if f.lower().endswith(".mp4"))
    if args.chi_face:
        files = [f for f in files if "face" in f.lower()]
    if not files:
        print("[loi] khong co video .mp4 nao de quet")
        return

    print(f"Quet {len(files)} video trong '{args.thu_muc}' (quet moi {args.buoc} khung hinh)")
    print("=" * 78)
    detector = YOLO(args.model)

    for name in files:
        path = os.path.join(args.thu_muc, name)
        r = quet_mot_video(path, detector, args.buoc)
        print()
        print(name)
        if "loi" in r:
            print("  LOI: " + r["loi"])
            continue
        print(
            "  {0}x{1} @ {2:.0f}fps | {3} khung | {4}s | quet {5} mau".format(
                r["width"],
                r["height"],
                r["fps"],
                r["total"],
                r["gia"],
                r["so_khung"],
            )
        )
        print(
            "  nguoi: max={0}  trung binh={1}  khung rong={2}%".format(
                r["max"], r["tb"], r["pct_rong"]
            )
        )
        print("  => " + goi_y(r))

    print()
    print("=" * 78)
    print("Xong.")


if __name__ == "__main__":
    main()