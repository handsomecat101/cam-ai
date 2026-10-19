"""Kiem tra nhanh: model nguoi + model mat + GPU chay that tren mot anh mau."""

import urllib.request

import torch
from PIL import Image

URL = "https://ultralytics.com/images/bus.jpg"
SAMPLE = "sample_bus.jpg"

import supervision as sv
from ultralytics import YOLO
from facenet_pytorch import MTCNN, InceptionResnetV1

urllib.request.urlretrieve(URL, SAMPLE)
image = Image.open(SAMPLE).convert("RGB")
print(f"[anh] {SAMPLE} size={image.size}")

# 1. Phat hien nguoi
detector = YOLO("yolo11n.pt")
result = detector(image)[0]
detections = sv.Detections.from_ultralytics(result)
people = detections[detections.class_id == 0]
print(f"[nguoi] so nguoi = {len(people)} (tong vat the = {len(detections)})")

# 2. Phat hien + nhan dien khuon mat
device = "cuda" if torch.cuda.is_available() else "cpu"
mtcnn = MTCNN(keep_all=True, device=device)
boxes, probs, _ = mtcnn.detect(image, landmarks=True)

if boxes is None:
    print("[mat] khong tim thay mat")
    raise SystemExit(0)

print(f"[mat] so mat = {len(boxes)} (device={device})")
crops = mtcnn.extract(image, boxes, None)
print(f"[mat] kich thuoc crop = {tuple(crops.shape)}")

recognizer = InceptionResnetV1(pretrained="vggface2").eval().to(device)
with torch.no_grad():
    embeddings = recognizer(crops.to(device))

print(f"[nhan dien] vector dac trung = {tuple(embeddings.shape)}")
print(f"[nhan dien] do tin cay mat = {[round(float(p), 3) for p in probs]}")

# 3. So sanh 2 mat voi nhau de kiem do phan biet co hoat dong khong
if embeddings.shape[0] >= 2:
    sim = torch.nn.functional.cosine_similarity(embeddings[0:1], embeddings[1:2])
    print(f"[kiem chung] do giong mat1 vs mat2 = {float(sim):.3f}")