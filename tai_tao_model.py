"""
Tai lai bo model nhan dien khuon mat (ArcFace) neu may bi xoa model.

Chay:
    .venv\\Scripts\\python.exe tai_tao_model.py

Tai ve:
    models/buffalo_l/   - bo model day du (~325MB) tu insightface
    models/face_core/   - 3 file duy nhat CamAI dung (~183MB, lien ket cung dia)
"""

import os
import shutil

# Chi 3 file CamAI that su. Bo qua 1k3d68/2d106det (toa do 3D, 142MB, khong dung).
NEEDED = ("det_10g.onnx", "w600k_r50.onnx", "genderage.onnx")


def main() -> None:
    try:
        from insightface.utils import ensure_available
    except ImportError:
        raise SystemExit("[loi] chua cai insightface. Chay: pip install insightface==2.1")

    root = os.path.dirname(os.path.abspath(__file__))
    full_dir = ensure_available("models", "buffalo_l", root=root)
    print(f"[1/2] bo model day du: {full_dir}")

    core_dir = os.path.join(root, "models", "face_core")
    os.makedirs(core_dir, exist_ok=True)

    print("[2/2] tao models/face_core (chi 3 file can dung):")
    for name in NEEDED:
        source = os.path.join(full_dir, name)
        target = os.path.join(core_dir, name)
        if not os.path.exists(source):
            print(f"      [thieu] {name} - khong tim thay trong bo model")
            continue
        if os.path.exists(target):
            os.remove(target)
        try:
            # Lien ket cung dia: khong ton them dung luong.
            os.link(source, target)
            how = "lien ket"
        except OSError:
            shutil.copy2(source, target)
            how = "sao chep"
        size = os.path.getsize(target) / 1024 / 1024
        print(f"      {name:<18} {size:7.1f} MB ({how})")

    print("\nXong. Chay kiem tra:")
    print("    .venv\\Scripts\\python.exe kiem_tra_nhan_dien.py video_test.mp4")


if __name__ == "__main__":
    main()