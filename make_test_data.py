"""Tao video test (co nguoi that) + bo anh 'nguoi quen' de kiem chuoi nhan dien."""

import os

import cv2
import numpy as np
from PIL import Image

SAMPLE = "sample_bus.jpg"
TEST_VIDEO = "video_test.mp4"
FACES_DIR = "known_faces"
NAMES = ["An", "Binh"]


def build_video() -> str:
    image = cv2.imread(SAMPLE)
    height, width = image.shape[:2]
    out_w, out_h = 960, 540
    writer = cv2.VideoWriter(TEST_VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), 25, (out_w, out_h))

    for frame_index in range(250):
        # zoom cham tu khung rong den khung hep -> nguoi di chuyen trong khung hinh
        ratio = 1.0 - 0.28 * (frame_index / 249)
        crop_w = int(width * ratio)
        crop_h = int(height * ratio)
        x0 = int((width - crop_w) / 2 * (0.5 + 0.5 * np.sin(frame_index / 40)))
        y0 = max(0, int((height - crop_h) * 0.15))
        crop = image[y0 : y0 + crop_h, x0 : x0 + crop_w]
        writer.write(cv2.resize(crop, (out_w, out_h)))

    writer.release()
    return TEST_VIDEO


def build_known_faces() -> None:
    import torch
    from facenet_pytorch import MTCNN

    device = "cuda" if torch.cuda.is_available() else "cpu"
    detector = MTCNN(keep_all=True, device=device)

    image = Image.open(SAMPLE).convert("RGB")
    rgb = cv2.cvtColor(cv2.imread(SAMPLE), cv2.COLOR_BGR2RGB)
    boxes, _probs = detector.detect(rgb, landmarks=False)
    if boxes is None:
        print("[canh bao] khong tim thay mat nao trong anh mau")
        return

    crops = detector.extract(rgb, boxes, None)  # tensor (N,3,160,160)
    for index, name in enumerate(NAMES[: crops.shape[0]]):
        folder = os.path.join(FACES_DIR, name)
        os.makedirs(folder, exist_ok=True)
        array = (crops[index].permute(1, 2, 0).cpu().numpy() + 1) / 2 * 255
        Image.fromarray(array.astype(np.uint8)).save(
            os.path.join(folder, "anh_1.jpg"), quality=95
        )
        print(f"[tao] known_faces/{name}/anh_1.jpg")


if __name__ == "__main__":
    print(f"[tao video] {build_video()}")
    build_known_faces()