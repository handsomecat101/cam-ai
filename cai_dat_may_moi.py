#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cai_dat_may_moi.py - Cai dat CamAI tren may moi (Windows 10/11).

Chay (may moi, chua co .venv):
    python cai_dat_may_moi.py
hoac
    .venv\\Scripts\\python.exe cai_dat_may_moi.py

Script chay 6 buoc, KHONG dung khi mot buoc bi loi. Buoc loi se duoc in
ra roi bo qua, cac buoc sau van chay tiep:

    1. Kiem tra moi truong: phien ban Python, thu muc goc, model YOLO
    2. Tao moi truong ao .venv (neu chua co)
    3. Cai thu vien: nang pip -> cai torch cu126 -> cai requirements.txt
    4. Tai model YOLO (yolo11n.pt) neu chua co
    5. Tai model khuon mat ArcFace (models/face_core) neu chua co
    6. Tong ket ket qua + huong dan chay app

Bien moi truong (tuy chon, dung de kiem chung nhanh):
    CAMAI_SKIP_INSTALL=1    bo qua buoc 3 (cai thu vien)
    CAMAI_SKIP_DOWNLOAD=1   bo qua buoc 4 va 5 (tai model)

Exit code: 0 = moi thu quan trong da xong, 1 = con thieu.
"""

import os
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Duong dan
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"
REQUIREMENTS = ROOT / "requirements.txt"
YOLO_FILE = ROOT / "yolo11n.pt"
FACE_CORE_DIR = ROOT / "models" / "face_core"
FACE_CORE_FILE = FACE_CORE_DIR / "w600k_r50.onnx"
KNOWN_FACES_DIR = ROOT / "known_faces"
TAI_TAO_MODEL = ROOT / "tai_tao_model.py"
VBS_FILE = ROOT / "Mo CamAI.vbs"

# --------------------------------------------------------------------------
# Index chinh thuc cua PyTorch (ban +cu126 khong co tren PyPI)
# --------------------------------------------------------------------------
INDEX_CU126 = "https://download.pytorch.org/whl/cu126"
INDEX_CPU = "https://download.pytorch.org/whl/cpu"
URL_PYTORCH = "https://pytorch.org/get-started/locally/"
TORCH_PIN = ["torch==2.14.0", "torchvision==0.29.0"]

# Cac goi CamAI can co - dung de loc dong "da co san" khi in tien do pip
GOC_CAMAI = (
    "torch",
    "torchvision",
    "ultralytics",
    "supervision",
    "insightface",
    "onnxruntime",
    "onnxruntime-gpu",
    "opencv-python",
    "numpy",
    "customtkinter",
    "pillow",
    "rapidocr-onnxruntime",
    "openpyxl",
    "pywin32",
)

# Tu khoa quyet dinh dong pip nao duoc in ra (bo qua ~10000 dong thua)
TU_KHOA = (
    "Collecting ",
    "Downloading ",
    "Using cached",
    "Installing collected",
    "Successfully installed",
    "ERROR",
    "error:",
    "WARNING",
    "Building wheel",
    "Attempting uninstall",
    "Requirement already satisfied",
)

MAX_DONG_IN = 80

# Moi tien trinh con duoc ep dung UTF-8 de tieng Viet khong loi khi xuat
# ra cong hoac khi duoc chuyen tiep vao tien trinh cha.
ENV_CHILD = dict(os.environ)
ENV_CHILD["PYTHONIOENCODING"] = "utf-8"


# --------------------------------------------------------------------------
# Ham in thong bao
# --------------------------------------------------------------------------
def _chuan_hoa_console() -> None:
    """Dat stdout/stderr sang UTF-8 de tieng Viet khong loi tren Windows."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def tieu_de(buoc: int, tong: int, text: str) -> None:
    print("")
    print("=" * 72)
    print(f"  BƯỚC {buoc}/{tong}: {text}")
    print("=" * 72)


def ok(text: str) -> None:
    print(f"  [OK] {text}")


def canh_bao(text: str) -> None:
    print(f"  [CẢNH BÁO] {text}")


def loi(text: str) -> None:
    print(f"  [LỖI] {text}")


def chi_tiet(text: str) -> None:
    print(f"         {text}")


# --------------------------------------------------------------------------
# Chay lenh con
# --------------------------------------------------------------------------
def _dong_hay_roi(dong: str) -> bool:
    """Chi giu nhung dong pip dang quan tam, bo qua phan lon du lieu thua."""
    if dong.startswith("Requirement already satisfied"):
        # Chi giu khi chinh goi CamAI da co san, bo qua phan phu thuoc.
        phan = dong.split(":", 1)[-1].strip()
        ten = phan.split(" in ", 1)[0]
        for ky in ("==", ">=", "<=", "~=", ">", "<"):
            ten = ten.split(ky, 1)[0]
        return ten.strip().lower() in GOC_CAMAI
    return any(tu in dong for tu in TU_KHOA)


def chay_lenh(cmd, tieu_de_lenh: str = "", max_dong: int = MAX_DONG_IN) -> int:
    """
    Chay mot lenh con trong thu muc du an, in tien do theo dong.
    Tra ve ma thoat (0 = thanh cong).
    """
    hien = " ".join(str(c) for c in cmd)
    print(f"  > {hien}")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=ENV_CHILD,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        loi(f"Không chạy được lệnh ({tieu_de_lenh}): {exc}")
        return 1

    dem = 0
    bo_qua = 0
    try:
        for dong in proc.stdout:
            dong = dong.rstrip()
            if not dong:
                continue
            if _dong_hay_roi(dong):
                if dem < max_dong:
                    print(f"      {dong}")
                    dem += 1
                else:
                    bo_qua += 1
    except Exception as exc:  # noqa: BLE001
        canh_bao(f"Lỗi khi đọc tiến độ lệnh: {exc}")
    finally:
        proc.wait()

    if bo_qua:
        print(f"      ... (đã bỏ qua {bo_qua} dòng thừa)")
    return proc.returncode


def chay_lenh_imat(code: str) -> tuple:
    """Chay mot doan code Python trong .venv, tra ve (ma_thoat, chuoi_ket_qua)."""
    try:
        ket = subprocess.run(
            [str(VENV_PY), "-c", code],
            cwd=str(ROOT),
            env=ENV_CHILD,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return 1, str(exc)
    return ket.returncode, (ket.stdout or "").strip()


# --------------------------------------------------------------------------
# Buoc 1: kiem tra moi truong
# --------------------------------------------------------------------------
def buoc_1_kiem_tra_moi_truong() -> None:
    tieu_de(1, 6, "Kiểm tra môi trường")
    print(f"  Python đang chạy   : {sys.version.split()[0]}")
    chi_tiet(sys.executable)
    print(f"  Thư mục gốc dự án : {ROOT}")
    print(f"  requirements.txt   : {'có' if REQUIREMENTS.exists() else 'THIẾU'}")
    if YOLO_FILE.exists():
        khoang = YOLO_FILE.stat().st_size / (1024 * 1024)
        ok(f"Model YOLO đã có: {YOLO_FILE.name} ({khoang:.1f} MB)")
    else:
        canh_bao(f"Model YOLO chưa có: {YOLO_FILE.name} (sẽ tải ở bước 4)")
    if VENV_PY.exists():
        ok(f"Môi trường ảo đã có: {VENV_PY}")
    else:
        chi_tiet("Chưa có .venv (sẽ tạo ở bước 2)")


# --------------------------------------------------------------------------
# Buoc 2: tao moi truong ao
# --------------------------------------------------------------------------
def buoc_2_tao_venv() -> bool:
    tieu_de(2, 6, "Tạo môi trường ảo .venv")
    if VENV_PY.exists():
        ok(f"Môi trường ảo .venv đã có sẵn: {VENV_PY}")
        return True

    print(f"  Tạo môi trường ảo tại: {VENV_DIR}")
    chi_tiet(f"Lệnh: {sys.executable} -m venv .venv")
    try:
        ket = subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            cwd=str(ROOT),
            env=ENV_CHILD,
        )
    except OSError as exc:
        loi(f"Không tạo được .venv: {exc}")
        return False

    if ket.returncode == 0 and VENV_PY.exists():
        ok(f"Đã tạo xong môi trường ảo: {VENV_PY}")
        return True

    loi(
        "Không tạo được .venv. Hãy chạy lại với quyền Administrator, "
        "và chắc chắn Python có sẵn trên máy (python --version)."
    )
    return False


# --------------------------------------------------------------------------
# Buoc 3: cai thu vien
# --------------------------------------------------------------------------
def in_huong_dan_torch() -> None:
    """In huong dan cai torch thu cong (lay tu trang chinh thuc pytorch.org)."""
    print("")
    print(f"  >>> HƯỚNG DẪN CÀI TORCH THỦ CÔNG (trang chính thức: {URL_PYTORCH})")
    chi_tiet("Máy có GPU NVIDIA - dùng bản CUDA 12.6:")
    chi_tiet(
        r"  .venv\Scripts\python.exe -m pip install torch==2.14.0 torchvision==0.29.0"
        f" --index-url {INDEX_CU126}"
    )
    chi_tiet("Máy không có GPU NVIDIA - dùng bản CPU:")
    chi_tiet(
        r"  .venv\Scripts\python.exe -m pip install torch==2.14.0 torchvision==0.29.0"
        f" --index-url {INDEX_CPU}"
    )
    print("")


def phien_ban_torch() -> str:
    """Tra ve phien ban torch dang co trong .venv, chuoi rong neu chua co."""
    ma, ket = chay_lenh_imat("import torch; print(torch.__version__)")
    if ma == 0 and ket:
        return ket.splitlines()[-1].strip()
    return ""


def cai_torch() -> bool:
    """Cai torch + torchvision, thu CUDA 12.6 truoc, roi CPU, roi PyPI."""
    for nhan, extra in (
        ("CUDA 12.6 (máy có GPU NVIDIA)", ["--index-url", INDEX_CU126]),
        ("CPU (máy không có GPU NVIDIA)", ["--index-url", INDEX_CPU]),
        ("PyPI (bản mặc định)", []),
    ):
        print(f"  -> Thử cài torch bản {nhan}")
        ma = chay_lenh(
            [str(VENV_PY), "-m", "pip", "install"] + TORCH_PIN + extra,
            tieu_de_lenh=f"torch {nhan}",
        )
        if ma == 0:
            ok(f"Đã cài torch bản {nhan}")
            return True
        canh_bao(f"Không cài được torch bản {nhan} (mã lỗi {ma}).")

    loi("Không cài được torch tự động.")
    in_huong_dan_torch()
    return False


def _site_packages_venv():
    """Tra ve danh sach thu muc site-packages nam trong .venv."""
    ket = []
    for mau in ("Lib/site-packages", "lib/python*/site-packages"):
        ket.extend(VENV_DIR.glob(mau))
    return ket


def _co_dist_info_venv(ten: str) -> bool:
    """Kiem tra goi `ten` co duoc cai TRONG .venv hay khong."""
    for sp in _site_packages_venv():
        if any(sp.glob(f"{ten}-*.dist-info")):
            return True
    return False


def khoi_phuc_onnxruntime_gpu() -> None:
    """
    rapidocr-onnxruntime keo theo ban onnxruntime (CPU) va ghi de file
    cua onnxruntime-gpu trong .venv. Cai lai onnxruntime-gpu de GPU
    hoat dong dung. Chi kich hoat khi ca hai ban deu nam trong .venv.
    """
    co_gpu = _co_dist_info_venv("onnxruntime_gpu")
    co_cpu = _co_dist_info_venv("onnxruntime")
    if not (co_gpu and co_cpu):
        return

    canh_bao(
        "Trong .venv có cả onnxruntime-gpu và onnxruntime (CPU) - "
        "bản CPU có thể ghi đè file của bản GPU."
    )
    print("  -> Cài lại onnxruntime-gpu để ưu tiên GPU")
    ma = chay_lenh(
        [
            str(VENV_PY),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-deps",
            "onnxruntime-gpu==1.23.2",
        ],
        tieu_de_lenh="onnxruntime-gpu",
    )
    if ma == 0:
        ok("Đã khôi phục onnxruntime-gpu (ưu tiên GPU).")
    else:
        canh_bao(f"Không khôi phục được onnxruntime-gpu (mã lỗi {ma}).")


def buoc_3_cai_thu_vien() -> bool:
    tieu_de(3, 6, "Cài thư viện (pip)")

    if not VENV_PY.exists():
        loi("Không có .venv\\Scripts\\python.exe - bỏ qua bước cài thư viện.")
        return False

    if os.environ.get("CAMAI_SKIP_INSTALL") == "1":
        canh_bao("CAMAI_SKIP_INSTALL=1 - bỏ qua bước cài thư viện.")
        return True

    print("  [3.1] Nâng cấp pip")
    chay_lenh(
        [str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip"],
        tieu_de_lenh="pip --upgrade",
    )

    print("  [3.2] Cài torch + torchvision")
    ban = phien_ban_torch()
    if ban:
        ok(f"torch đã có sẵn trong .venv ({ban})")
    else:
        cai_torch()

    print("  [3.3] Cài requirements.txt")
    if not REQUIREMENTS.exists():
        loi("Không tìm thấy requirements.txt - bỏ qua bước cài thư viện.")
        return False
    ma = chay_lenh(
        [str(VENV_PY), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        tieu_de_lenh="pip install -r requirements.txt",
    )
    if ma != 0:
        loi(f"Cài requirements.txt thất bại (mã lỗi {ma}).")
        canh_bao("Nguyên nhân thường gặp:")
        chi_tiet("- Dòng 'torch' trong requirements.txt đã bị COMMENT (bắt buộc) -> cài torch thủ công.")
        chi_tiet("- Bản torch +cu126 không có trên PyPI -> phải cài từ index cu126.")
        chi_tiet("- onnxruntime-gpu cần GPU NVIDIA -> máy không có GPU thì đổi sang onnxruntime (CPU).")
        in_huong_dan_torch()
        return False

    ok("Đã cài xong requirements.txt")
    khoi_phuc_onnxruntime_gpu()
    return True


# --------------------------------------------------------------------------
# Buoc 4: tai model YOLO
# --------------------------------------------------------------------------
def buoc_4_tai_model_yolo() -> bool:
    tieu_de(4, 6, "Tải model YOLO (yolo11n.pt)")
    if YOLO_FILE.exists():
        khoang = YOLO_FILE.stat().st_size / (1024 * 1024)
        ok(f"Model YOLO đã có sẵn: {YOLO_FILE.name} ({khoang:.1f} MB)")
        return True

    if os.environ.get("CAMAI_SKIP_DOWNLOAD") == "1":
        canh_bao("CAMAI_SKIP_DOWNLOAD=1 - bỏ qua bước tải model YOLO.")
        return False

    if not VENV_PY.exists():
        loi("Không có .venv - không tải được model YOLO.")
        return False

    print("  Đang tải yolo11n.pt (khoảng 6 MB)...")
    ma = chay_lenh(
        [
            str(VENV_PY),
            "-c",
            "from ultralytics import YOLO; YOLO('yolo11n.pt'); print('[OK] Đã tải xong yolo11n.pt')",
        ],
        tieu_de_lenh="tai yolo11n.pt",
    )
    if ma == 0 and YOLO_FILE.exists():
        ok(f"Đã tải xong model YOLO: {YOLO_FILE.name}")
        return True
    loi(f"Tải model YOLO thất bại (mã lỗi {ma}). Cần Internet và thư viện ultralytics.")
    return False


# --------------------------------------------------------------------------
# Buoc 5: tai model khuon mat ArcFace
# --------------------------------------------------------------------------
def buoc_5_tai_model_mat() -> bool:
    tieu_de(5, 6, "Tải model khuôn mặt ArcFace (models/face_core)")
    if FACE_CORE_FILE.exists():
        khoang = FACE_CORE_FILE.stat().st_size / (1024 * 1024)
        ok(f"Model mặt đã có sẵn: {FACE_CORE_FILE.name} ({khoang:.1f} MB)")
        return True

    if os.environ.get("CAMAI_SKIP_DOWNLOAD") == "1":
        canh_bao("CAMAI_SKIP_DOWNLOAD=1 - bỏ qua bước tải model khuôn mặt.")
        return False

    if not VENV_PY.exists():
        loi("Không có .venv - không tải được model khuôn mặt.")
        return False

    if not TAI_TAO_MODEL.exists():
        loi(f"Không tìm thấy {TAI_TAO_MODEL.name} trong thư mục dự án.")
        return False

    print("  Đang tải bộ model buffalo_l (~325 MB) và tạo models/face_core...")
    print("  (có thể mất vài phút)")
    ma = chay_lenh(
        [str(VENV_PY), str(TAI_TAO_MODEL)],
        tieu_de_lenh="tai_tao_model.py",
    )
    if ma == 0 and FACE_CORE_FILE.exists():
        ok("Đã tải xong model khuôn mặt vào models/face_core.")
        return True
    loi(f"Tải model khuôn mặt thất bại (mã lỗi {ma}). Cần Internet và thư viện insightface.")
    return False


# --------------------------------------------------------------------------
# Buoc 6: tong ket
# --------------------------------------------------------------------------
def dem_known_faces() -> tuple:
    """Tra ve (so_nguoi, so_anh)."""
    if not KNOWN_FACES_DIR.exists():
        return 0, 0
    nguoi = 0
    anh = 0
    for muc in KNOWN_FACES_DIR.iterdir():
        if not muc.is_dir():
            continue
        nguoi += 1
        for tep in muc.iterdir():
            if tep.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
                anh += 1
    return nguoi, anh


def in_bang_goi_da_cai() -> None:
    """In bang phien ban cac goi CamAI trong .venv."""
    ma, ket = chay_lenh_imat(
        "import importlib.metadata as m; "
        "names=%r; "
        "\nfor n in names:\n"
        "    try: print(n, m.version(n))\n"
        "    except Exception: print(n, 'CHUA CAI')\n" % (list(GOC_CAMAI),)
    )
    if ma != 0 or not ket:
        return
    print("  Các gói trong .venv:")
    for dong in ket.splitlines():
        dong = dong.strip()
        if not dong:
            continue
        if " " in dong:
            ten, phi = dong.split(" ", 1)
        else:
            ten, phi = dong, ""
        if phi == "CHUA CAI":
            canh_bao(f"{ten}: chưa cài")
        else:
            chi_tiet(f"{ten} = {phi}")


def buoc_6_tong_ket() -> None:
    tieu_de(6, 6, "Tổng kết")

    co_venv = VENV_PY.exists()
    co_yolo = YOLO_FILE.exists()
    co_mat = FACE_CORE_FILE.exists()

    print(f"  Môi trường ảo .venv      : {'OK' if co_venv else 'THIẾU'}")
    print(f"  Model YOLO (yolo11n.pt) : {'OK' if co_yolo else 'THIẾU'}")
    print(f"  Model mặt (face_core)   : {'OK' if co_mat else 'THIẾU'}")

    if FACE_CORE_DIR.exists():
        tep = sorted(p.name for p in FACE_CORE_DIR.glob("*.onnx"))
        if tep:
            print(f"  File trong models/face_core: {', '.join(tep)}")

    nguoi, anh = dem_known_faces()
    if KNOWN_FACES_DIR.exists():
        print(f"  known_faces: {nguoi} người / {anh} ảnh")
        if nguoi == 0:
            canh_bao("known_faces rỗng - app sẽ không nhận diện được ai.")
            chi_tiet(f"Thêm ảnh vào {KNOWN_FACES_DIR} theo tên, ví dụ: known_faces\\An\\an1.jpg")
    else:
        canh_bao(f"Không tìm thấy thư mục {KNOWN_FACES_DIR}")

    print("")
    in_bang_goi_da_cai()

    print("")
    print("  CÁCH CHẠY APP:")
    chi_tiet(f'Double-click: "{VBS_FILE}"')
    chi_tiet("Nếu app không mở, dùng bản xem lỗi: Mo CamAI.bat")
    print("")


# --------------------------------------------------------------------------
# Chinh
# --------------------------------------------------------------------------
def main() -> int:
    _chuan_hoa_console()
    print("=" * 72)
    print("  CAMAI - CÀI ĐẶT TRÊN MÁY MỚI")
    print(f"  Thư mục: {ROOT}")
    print("=" * 72)

    buoc_1_kiem_tra_moi_truong()
    buoc_2_tao_venv()
    buoc_3_cai_thu_vien()
    buoc_4_tai_model_yolo()
    buoc_5_tai_model_mat()
    buoc_6_tong_ket()

    thieu = []
    if not VENV_PY.exists():
        thieu.append("môi trường ảo .venv")
    if not YOLO_FILE.exists():
        thieu.append("model YOLO (yolo11n.pt)")
    if not FACE_CORE_FILE.exists():
        thieu.append("model khuôn mặt (models/face_core)")

    print("=" * 72)
    if thieu:
        loi("CÀI ĐẶT CHƯA XONG. Còn thiếu: " + ", ".join(thieu))
        print("  Chạy lại script này, hoặc làm theo hướng dẫn in ở bước 3.")
        return 1

    ok("CÀI ĐẶT HOÀN TẤT. App sẵn sàng chạy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
