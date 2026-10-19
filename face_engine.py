"""
CamAI - nhan dien khuon mat bang ArcFace (SCRFD det + ArcFace w600k_r50 + tuoi/gioi tinh).

Da thay the facenet-pytorch (MTCNN + InceptionResnetV1/vggface2).
Ket qua do tren video mau: 500/500 mat rut dung ten (ban cu chi 43/463 va bo sot 1 nguoi).

Tu dong chay GPU neu may co card NVIDIA (nhanh gap ~5.8 lan).

Dung:
    from face_engine import FaceEngine
    engine = FaceEngine()
    for face in engine.analyze(frame_bgr):
        print(face.name, face.age, face.sex, face.score)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import cv2
import numpy as np

logging.getLogger("insightface").setLevel(logging.ERROR)

# Cosine similarity cho ArcFace w600k_r50 trong bo buffalo_l.
# 0.28 = tha long, 0.40 = can bang, 0.50 = chat.
DEFAULT_MATCH_THRESHOLD = 0.40

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

MODEL_DIRS = ("models/face_core", "models/buffalo_l")


def _enable_cuda() -> bool:
    """Nap thu vien CUDA cua torch truoc khi onnxruntime duoc import.

    Tren Windows, onnxruntime can cuDNN 9 + CUDA 12 nam trong torch/lib.
    Phai nap TAI TRUOC, thi onnxruntime moi tim thay va dung duoc GPU.
    """
    if os.name != "nt":
        return False
    try:
        import torch
    except Exception:
        return False
    try:
        if not torch.cuda.is_available():
            return False
        lib_dir = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.isdir(lib_dir):
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(lib_dir)
            if lib_dir not in os.environ.get("PATH", "").split(os.pathsep):
                os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")
        torch.zeros(1, device="cuda")  # nap CUDA runtime vao tien trinh
        return True
    except Exception:
        return False


CUDA_READY = _enable_cuda()
DEFAULT_PROVIDERS = (
    ["CUDAExecutionProvider", "CPUExecutionProvider"] if CUDA_READY
    else ["CPUExecutionProvider"]
)


def resolve_model_dir(preferred: str | None = None) -> str:
    candidates = (preferred,) + MODEL_DIRS if preferred else MODEL_DIRS
    for path in candidates:
        if path and os.path.isdir(path) and any(
            name.endswith(".onnx") for name in os.listdir(path)
        ):
            return path
    raise SystemExit(
        "[loi] khong thay bo model ArcFace.\n"
        "       Chay: .venv\\Scripts\\python.exe tai_tao_model.py"
    )


@dataclass
class FaceResult:
    """Ket qua cho mot khuon mat trong mot khung hinh."""

    box: tuple[int, int, int, int]
    name: str
    score: float
    age: int
    sex: str  # "Nam" | "Nu" | "" (khong do duoc)
    face_size: int  # canh nho nhat cua box, dung de loai mat qua xa

    @property
    def is_known(self) -> bool:
        return self.name != "Nguoi la"

    @property
    def label(self) -> str:
        """Chuoi ngan gon de ghi len khung hinh."""
        parts = [self.name]
        if self.sex:
            parts.append(f"{self.sex} {self.age}" if self.age else self.sex)
        return " | ".join(parts)


class FaceEngine:
    def __init__(
        self,
        model_dir: str | None = None,
        faces_dir: str = "known_faces",
        threshold: float = DEFAULT_MATCH_THRESHOLD,
        providers: list[str] | None = None,
        det_thresh: float = 0.5,
    ) -> None:
        from insightface.app import FaceAnalysis

        self.model_dir = resolve_model_dir(model_dir)
        self.threshold = threshold
        self.det_thresh = det_thresh
        self.providers = providers or list(DEFAULT_PROVIDERS)

        # Chi nap 3 model can dung, bo qua 2 model toa do 3D (137MB) de tai nhanh.
        # Diem nay QUAN TRONG: insightface 2.1 ep CPU khi prepare(ctx_id=-1),
        # phai dung ctx_id=0 de chay GPU.
        self.app = FaceAnalysis(
            name=self.model_dir,
            providers=self.providers,
            allowed_modules=["detection", "recognition", "genderage"],
        )
        self.app.prepare(ctx_id=0, det_thresh=det_thresh)

        active = {
            name: model.session.get_providers()[0] for name, model in self.app.models.items()
        }
        self.device = "GPU" if all("CUDA" in p for p in active.values()) else "CPU"
        print(f"[model] {self.model_dir} | {self.device} | " +
              " | ".join(f"{k}:{v.split('Execution')[0]}" for k, v in active.items()))

        self.known: list[tuple[str, np.ndarray]] = self._load_known(faces_dir)

    # ------------------------------------------------------------------ hoc

    def _embed_image(self, image_bgr: np.ndarray) -> np.ndarray | None:
        faces = self.app.get(image_bgr, max_num=1)
        if not faces:
            return None
        embedding = faces[0].normed_embedding
        return None if embedding is None else np.asarray(embedding, dtype=np.float32)

    def _load_known(self, folder: str) -> list[tuple[str, np.ndarray]]:
        if not os.path.isdir(folder):
            print(f"[canh bao] khong co thu muc '{folder}' -> chi dem duoc, khong rut ten duoc")
            return []

        known: list[tuple[str, np.ndarray]] = []
        for name in sorted(os.listdir(folder)):
            person_dir = os.path.join(folder, name)
            if not os.path.isdir(person_dir):
                continue

            vectors: list[np.ndarray] = []
            for file_name in sorted(os.listdir(person_dir)):
                if not file_name.lower().endswith(IMAGE_EXTS):
                    continue
                image = cv2.imread(os.path.join(person_dir, file_name))
                if image is None:
                    print(f"[bo qua] khong doc duoc: {file_name}")
                    continue
                vector = self._embed_image(image)
                if vector is not None:
                    vectors.append(vector)

            if vectors:
                centroid = np.mean(vectors, axis=0)
                centroid /= np.linalg.norm(centroid) + 1e-9
                known.append((name, centroid))
                print(f"[da hoc] {name} ({len(vectors)} anh)")
            else:
                print(f"[canh bao] '{name}': bo dien dan khong tim thay mat - can anh ro, sang, chinh dien")

        if not known:
            print("[canh bao] chua co ai trong known_faces -> tat ca se la 'Nguoi la'")
        return known

    def reload_known(self, faces_dir: str = "known_faces") -> None:
        self.known = self._load_known(faces_dir)

    # ------------------------------------------------------------------ doan

    def _match(self, embedding: np.ndarray | None) -> tuple[str, float]:
        if embedding is None or not self.known:
            return "Nguoi la", 0.0
        best_name, best_score = "Nguoi la", -1.0
        for name, centroid in self.known:
            score = float(np.dot(embedding, centroid))
            if score > best_score:
                best_name, best_score = name, score
        return best_name, max(best_score, 0.0)

    def analyze(self, frame_bgr: np.ndarray, min_face_px: int = 0) -> list[FaceResult]:
        """Quet mot khung hinh. Tra ve danh sach FaceResult.

        min_face_px: bo qua mat nho hon muc nay (0 = khong bo qua).
        """
        results: list[FaceResult] = []
        for face in self.app.get(frame_bgr):
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            size = min(x2 - x1, y2 - y1)
            if min_face_px and size < min_face_px:
                continue

            name, score = self._match(face.normed_embedding)
            results.append(
                FaceResult(
                    box=(x1, y1, x2, y2),
                    name=name,
                    score=score,
                    age=int(face.age) if face.age is not None else 0,
                    sex="Nam" if face.sex == "M" else ("Nu" if face.sex == "F" else ""),
                    face_size=size,
                )
            )
        return results

    def count_faces(self, frame_bgr: np.ndarray) -> int:
        return len(self.app.get(frame_bgr))