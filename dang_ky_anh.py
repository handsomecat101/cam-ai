"""
Dang ky nguoi quen tu video / anh chup - khong can chup anh rieng.

Vi sao can: anh chup mat qua xa, nho, nhay, hay deo kinh -> phan mem
se khong tim thay mat. Video cua camera thuong co mat to hon nhieu.

Cach dung:
    .venv\\Scripts\\python.exe dang_ky_anh.py --input video.mp4 --names An,Binh
    .venv\\Scripts\\python.exe dang_ky_anh.py --input cua_toi.jpg --names Binh

Ket qua: moi nguoi 1 thu muc trong known_faces/<Ten>/, nhieu anh cung lo.
"""

from __future__ import annotations

import argparse
import os
import shutil

import cv2
import numpy as np

from face_engine import FaceEngine

MODEL_DIR = None
OUT_DIR = "known_faces"
MAX_PER_PERSON = 5
SAME_PERSON_SIM = 0.45  # nho hon = cho phep gop nguong hon vao cung 1 nguoi
MIN_FACE_PX = 24


def collect_faces(engine: FaceEngine, source: str, max_frames: int) -> list[dict]:
    cap = cv2.VideoCapture(source)
    if cap.isOpened():
        found: list[dict] = []
        index = 0
        while cap.isOpened() and index < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            index += 1
            for face in engine.app.get(frame):
                x1, y1, x2, y2 = [int(v) for v in face.bbox]
                size = min(x2 - x1, y2 - y1)
                if size < MIN_FACE_PX:
                    continue
                pad = int(size * 0.25)
                crop = frame[
                    max(0, y1 - pad) : min(frame.shape[0], y2 + pad),
                    max(0, x1 - pad) : min(frame.shape[1], x2 + pad),
                ]
                if crop.size == 0:
                    continue
                found.append(
                    {
                        "crop": crop,
                        "embedding": np.asarray(face.normed_embedding, dtype=np.float32),
                        "size": size,
                        "frame": index,
                    }
                )
        cap.release()
        if found:
            print(f"[quet] {source}: {len(found)} mat trong {index} khung hinh")
        else:
            print(f"[canh bao] {source}: khong tim thay mat nao")
        return found

    image = cv2.imread(source)
    if image is None:
        raise SystemExit(f"[loi] khong mo duoc: {source}")
    found = []
    for face in engine.app.get(image):
        x1, y1, x2, y2 = [int(v) for v in face.bbox]
        pad = int(min(x2 - x1, y2 - y1) * 0.25)
        crop = image[
            max(0, y1 - pad) : y2 + pad, max(0, x1 - pad) : x2 + pad
        ]
        if crop.size:
            found.append(
                {
                    "crop": crop,
                    "embedding": np.asarray(face.normed_embedding, dtype=np.float32),
                    "size": min(x2 - x1, y2 - y1),
                    "frame": 0,
                }
            )
    print(f"[quet] {source}: {len(found)} mat")
    return found


def cluster(faces: list[dict], max_people: int) -> list[list[dict]]:
    """Gom mat cua cung mot nguoi vao cung nhom. Nhom moi = mat lon nhat chua co nhom."""
    clusters: list[list[dict]] = []
    for item in sorted(faces, key=lambda f: f["size"], reverse=True):
        for group in clusters:
            center = np.mean([f["embedding"] for f in group], axis=0)
            center /= np.linalg.norm(center) + 1e-9
            if float(np.dot(item["embedding"], center)) >= SAME_PERSON_SIM:
                group.append(item)
                break
        else:
            if len(clusters) < max_people:
                clusters.append([item])
    return clusters


def save_group(group: list[dict], name: str, out_dir: str) -> int:
    folder = os.path.join(out_dir, name)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    os.makedirs(folder, exist_ok=True)

    # Giu cac anh tach xa nhau theo khung hinh, uu tien mat lon.
    picked: list[dict] = []
    used_frames: set[int] = set()
    for item in sorted(group, key=lambda f: f["size"], reverse=True):
        if len(picked) >= MAX_PER_PERSON:
            break
        if any(abs(item["frame"] - p["frame"]) < 3 for p in picked):
            continue
        picked.append(item)
        used_frames.add(item["frame"])

    for number, item in enumerate(picked, start=1):
        cv2.imwrite(
            os.path.join(folder, f"{number:02d}.jpg"), item["crop"], [cv2.IMWRITE_JPEG_QUALITY, 95]
        )
    return len(picked)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dang ky nguoi quen tu video / anh chup")
    parser.add_argument("--input", required=True, help="video hoac duong dan anh")
    parser.add_argument("--names", required=True, help="danh sach ten, tach bang dau phay: An,Binh")
    parser.add_argument("--out", default=OUT_DIR, help="thu muc luu anh mau")
    parser.add_argument("--model", default=None, help="thu muc model ArcFace (mac dinh: tu dong tim)")
    parser.add_argument("--max-frames", type=int, default=250, help="quet toi da bao nhieu khung hinh")
    args = parser.parse_args()

    names = [n.strip() for n in args.names.split(",") if n.strip()]
    if not names:
        raise SystemExit("[loi] --names rong")

    engine = FaceEngine(args.model, faces_dir="__khong_co__")
    faces = collect_faces(engine, args.input, args.max_frames)
    if not faces:
        raise SystemExit(
            "[loi] khong tim thay mat nao.\n"
            "       Thu nghiem: video qua mo, mat nho, hoac cheo nguoi/kinh."
        )

    groups = cluster(faces, len(names))
    print(f"\n[gom nhom] tim thay {len(groups)} nguoi khac nhau")

    if len(groups) < len(names):
        print("[canh bao] chi gom duoc it nguoi hon ten anh da nhap")
        names = names[: len(groups)]

    for name, group in zip(names, groups):
        saved = save_group(group, name, args.out)
        biggest = max(f["size"] for f in group)
        print(f"[dang ky] {name:<12} {saved} anh, mat lon nhat {biggest}px -> {args.out}/{name}/")

    print(f"\nXong. Chay lai phan tinh video de kiem tra.")


if __name__ == "__main__":
    main()
