"""Kiem tra GPU + tai ve cac model co ban cho pipeline detect nguoi."""

import sys


def check_torch() -> bool:
    import torch

    print(f"[torch] {torch.__version__}")
    ok = torch.cuda.is_available()
    print(f"[cuda] available={ok}")
    if ok:
        print(f"[gpu] {torch.cuda.get_device_name(0)}")
    return ok


def download_yolo(name: str) -> bool:
    try:
        from ultralytics import YOLO

        YOLO(name)  # tu tai weights ve lan dau
        print(f"[ok] tai xong {name}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[fail] {name}: {exc}")
        return False


if __name__ == "__main__":
    cuda_ok = check_torch()
    targets = ["yolo11n.pt", "yolov8n-face.pt"]

    for model_name in targets:
        download_yolo(model_name)

    import supervision as sv

    print(f"[ok] supervision {sv.__version__}")

    sys.exit(0 if cuda_ok else 1)