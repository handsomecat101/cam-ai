"""
CamAI - SỔ ĐĂNG KÝ MODEL (model registry) cho giao diện.

Mục đích: giao diện hiển thị rõ tên model đang chạy, nó lấy từ đây,
để chủ sở hữu (không rành công nghệ) biết:

    - CamAI đang dùng model nào?
    - Model đó làm gì?
    - File nằm đâu, nặng bao nhiêu?
    - Thiếu file thì có chạy được không?

Cách dùng:

    from model_info import ALL_MODELS, bang_tt_tong_hop, kiem_tra_trang_thai, lay_phien_ban

    for d in bang_tt_tong_hop():
        print(d["ten"], d["model_id"], d["trang_thai"])

Xem nhanh trên màn hình:

    .venv\\Scripts\\python.exe model_info.py

Không sửa bất kỳ file nào khác. File này chỉ ĐỌC dữ liệu và kiểm tra file trên đĩa.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, asdict
from importlib import metadata
from pathlib import Path

# Thư mục chứa file model_info.py. Mọi đường dẫn đều resolve từ đây,
# nên chạy từ thư mục nào cũng ra kết quả giống nhau.
THU_MUC_GOC = Path(__file__).resolve().parent

# 1 MB = 1024 * 1024 byte (đúng cách hiển thị dung lượng file của Windows)
_BYTE_TRONG_MB = 1024 * 1024

# Nhãn trạng thái dùng cho code (giữ đúng chữ không dấu theo quy ước).
# Giao diện hiển thị cho người dùng thì lấy bản CÓ DẤU ở TRANG_THAI_HIEN_THI.
TRANG_THAI_SAN_SANG = "san sang"
TRANG_THAI_THIEU_FILE = "thieu file"

TRANG_THAI_HIEN_THI = {
    TRANG_THAI_SAN_SANG: "sẵn sàng (đủ dùng chạy được)",
    TRANG_THAI_THIEU_FILE: "thiếu file (chưa đủ dùng chạy)",
}


@dataclass
class ModelInfo:
    """Thông tin của 1 model AI."""

    key: str
    """Khóa ngắn (dùng cho code), ví dụ: "nhan_dien"."""

    ten: str
    """Tên tiếng Việt dễ hiểu, ví dụ: "Nhận diện người quen"."""

    model_id: str
    """Tên model kỹ thuật đúng chính tả, ví dụ: "ArcFace w600k_r50"."""

    thu_vien: str
    """Thư viện xử lý, ví dụ: "insightface 2.1"."""

    file: str
    """Đường dẫn tương đối tới file model, ví dụ: "models/face_core/w600k_r50.onnx"."""

    kich_thuoc_mb: float
    """Dung lượng file model, đơn vị MB (số đo chính thức của nhà sản xuất)."""

    vai_tro: str
    """Model này làm gì, viết bằng tiếng Việt dễ hiểu."""

    bat_buoc: bool
    """True = không có model này thì chức năng chính không chạy được."""

    def duong_dan(self) -> Path:
        """Đường dẫn đầy đủ của file model, không phụ thuộc thư mục làm việc."""
        return THU_MUC_GOC / self.file


# ----------------------------------------------------------------------
# DANH SÁCH 4 MODEL ĐANG CHẠY THẬT TRONG CamAI
# ----------------------------------------------------------------------
ALL_MODELS: list[ModelInfo] = [
    ModelInfo(
        key="phat_hien",
        ten="Phát hiện người",
        model_id="YOLO11n",
        thu_vien="ultralytics",
        file="yolo11n.pt",
        kich_thuoc_mb=5.4,
        vai_tro=(
            "Tìm trong khung hình có bao nhiêu NGƯỜI (và cả xe, chó, mèo…). "
            "Đây là bước đầu tiên, mọi thứ khác đều dựa vào kết quả bước này."
        ),
        bat_buoc=True,
    ),
    ModelInfo(
        key="tim_mat",
        ten="Tìm khuôn mặt",
        model_id="SCRFD 10G",
        thu_vien="insightface 2.1",
        file="models/face_core/det_10g.onnx",
        kich_thuoc_mb=16.1,
        vai_tro=(
            "Khoanh vùng khuôn mặt của người đã tìm thấy. "
            "Nếu tắt model này thì không nhận diện được ai."
        ),
        bat_buoc=True,
    ),
    ModelInfo(
        key="nhan_dien",
        ten="Nhận diện người quen",
        model_id="ArcFace w600k_r50",
        thu_vien="insightface 2.1",
        file="models/face_core/w600k_r50.onnx",
        kich_thuoc_mb=166.3,
        vai_tro=(
            'Đây là model "nhận diện": so khuôn mặt người lạ với ảnh đã lưu, '
            'đúng thì gọi tên, sai thì ghi "Người lạ". '
            "Đây là model quan trọng nhất với chủ sở hữu."
        ),
        bat_buoc=True,
    ),
    ModelInfo(
        key="tuoi_gioi_tinh",
        ten="Ước lượng tuổi và giới tính",
        model_id="genderage",
        thu_vien="insightface 2.1",
        file="models/face_core/genderage.onnx",
        kich_thuoc_mb=1.3,
        vai_tro=(
            "Ước lượng khoảng tuổi và giới tính của khuôn mặt. "
            "Chỉ là ƯỚC LƯỢNG, không chính xác tuyệt đối."
        ),
        bat_buoc=False,
    ),
]

# Tra cứu nhanh theo key, ví dụ: TRA_CUNG["nhan_dien"].ten
TRA_CUNG: dict[str, ModelInfo] = {m.key: m for m in ALL_MODELS}


# ----------------------------------------------------------------------
# THÔNG SỐ KỸ THUẬT
# ----------------------------------------------------------------------
THONG_SO_KY_THUAT: dict = {
    "nguong_khop_mat": 0.40,
    "thu_muc_anh_da_hoc": "known_faces",
    "so_nguoi_da_hoc_mau": 2,
    "gia_tri_nguong_khop_mat": (
        "0,40 là mức cân bằng. Cao hơn = dễ nhận nhầm, thấp hơn = dễ không nhận ra."
    ),
    "canh_bao_anh_mau": (
        "2 người đã học sẵn trong thư mục known_faces là DỮ LIỆU GIẢ LẬP "
        "(không phải người thật). Khi dùng thật, hãy xoá chúng trước khi thêm người thật vào."
    ),
}


# ----------------------------------------------------------------------
# KIỂM TRA FILE MODEL TRÊN ĐĨA
# ----------------------------------------------------------------------
def kiem_tra_trang_thai() -> list[dict]:
    """Kiểm tra 4 model có tồn tại trên đĩa không.

    Trả về 1 danh sách, mỗi phần tử là 1 dict:
        {"key", "ten", "model_id", "file", "duong_dan",
         "co_file", "kich_thuoc_mb_thuc", "trang_thai"}

    "trang_thai" chỉ có 2 giá trị: "san sang" hoặc "thieu file".
    """
    ket_qua: list[dict] = []
    for m in ALL_MODELS:
        duong_dan = m.duong_dan()
        co_file = duong_dan.is_file()
        kich_thuoc = 0.0
        if co_file:
            try:
                kich_thuoc = round(duong_dan.stat().st_size / _BYTE_TRONG_MB, 1)
            except OSError:
                co_file = False
        trang_thai = TRANG_THAI_SAN_SANG if co_file else TRANG_THAI_THIEU_FILE
        ket_qua.append(
            {
                "key": m.key,
                "ten": m.ten,
                "model_id": m.model_id,
                "file": m.file,
                "duong_dan": str(duong_dan),
                "co_file": co_file,
                "kich_thuoc_mb_thuc": kich_thuoc,
                "trang_thai": trang_thai,
                "trang_thai_tieng_viet": TRANG_THAI_HIEN_THI[trang_thai],
            }
        )
    return ket_qua


# ----------------------------------------------------------------------
# PHIÊN BẢN PHẦN MỀM VÀ GPU
# ----------------------------------------------------------------------
# Tên gói trong requirements.txt -> tên hiển thị
_GOI_HIEN_THI = (
    ("insightface", "insightface"),
    ("ultralytics", "ultralytics"),
    ("onnxruntime", "onnxruntime"),
    ("onnxruntime-gpu", "onnxruntime-gpu"),
    ("opencv-python", "opencv-python"),
)


def _lay_phien_ban_mot(goi: str) -> str | None:
    """Đọc phiên bản của 1 gói cài đặt. Trả None nếu chưa cài (không báo lỗi)."""
    try:
        return metadata.version(goi)
    except Exception:
        return None


def _phien_ban_ort_dang_chay() -> str | None:
    """Phiên bản onnxruntime THẬT SỰ đang chạy trong tiến trình này.

    Đọc thẳng module đang được import, KHÔNG đọc metadata của gói.

    Lý do: máy này cài song song cả gói CPU (`onnxruntime`) lẫn gói GPU
    (`onnxruntime-gpu`). Hai gói nằm ở hai thư mục khác nhau và metadata
    của mỗi gói nằm cạnh thư mục đó, nên đọc metadata sẽ ra HAI con số
    khác nhau (1.20.1 và 1.23.2) dù máy chỉ chạy một.

    Module đang chạy mới là con số duy nhất đáng tin cho câu hỏi
    "máy đang dùng cái gì". Xem ISSUE_LOG #8.
    """
    try:
        import onnxruntime as ort

        return getattr(ort, "__version__", None)
    except Exception:
        return None


def _co_cuda() -> bool:
    """Kiểm tra onnxruntime có chạy được trên GPU NVIDIA hay không."""
    try:
        import onnxruntime as ort

        return "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


def lay_phien_ban() -> dict:
    """Phiên bản thật của các thành phần đang chạy.

    Trả về dict gồm phiên bản từng phần mềm + khóa "cuda" (bool).
    Gói chưa cài sẽ có giá trị None thay vì báo lỗi.
    """
    ket_qua: dict = {}
    for goi, ten_hien_thi in _GOI_HIEN_THI:
        ket_qua[ten_hien_thi] = _lay_phien_ban_mot(goi)
    ket_qua["cuda"] = _co_cuda()
    return ket_qua


# ----------------------------------------------------------------------
# BẢNG TỔNG HỢP CHO GIAO DIỆN
# ----------------------------------------------------------------------
def bang_tt_tong_hop() -> list[dict]:
    """Gộp tất cả thông tin lại, giao diện chỉ cần một lệnh là lấy được cả bảng.

    Mỗi dòng gồm: thông tin model + trạng thái file trên đĩa + vai trò + phiên bản.
    """
    phien_ban = lay_phien_ban()
    co_gpu = phien_ban.get("cuda", False)
    bang: list[dict] = []
    for m, tt in zip(ALL_MODELS, kiem_tra_trang_thai()):
        dong = asdict(m)
        dong["co_file"] = tt["co_file"]
        dong["kich_thuoc_mb_thuc"] = tt["kich_thuoc_mb_thuc"]
        dong["trang_thai"] = tt["trang_thai"]
        dong["trang_thai_tieng_viet"] = tt["trang_thai_tieng_viet"]
        dong["duong_dan"] = tt["duong_dan"]
        # Phiên bản của thư viện đang dùng cho model này
        goi = "ultralytics" if m.thu_vien.startswith("ultralytics") else "insightface"
        phien_ban_thu_vien = phien_ban.get(goi)
        # "insightface 2.1" đã có số phiên bản trong tên rồi thì không nối thêm lần nữa
        if phien_ban_thu_vien and phien_ban_thu_vien not in m.thu_vien:
            dong["ten_thu_vien_day_du"] = f"{m.thu_vien} {phien_ban_thu_vien}"
        else:
            dong["ten_thu_vien_day_du"] = m.thu_vien
        dong["phien_ban_thu_vien"] = phien_ban_thu_vien
        dong["co_gpu"] = co_gpu
        bang.append(dong)
    return bang


# ----------------------------------------------------------------------
# IN RA MÀN HÌNH CONSOLE
# ----------------------------------------------------------------------
def _chuan_hoa_console() -> None:
    """Bảo đảm tiếng Việt có dấu không bị lỗi khi in ra console Windows.

    Console Windows mặc định dùng bảng mã cũ (cp1252/437) nên in tiếng Việt
    có dấu sẽ báo lỗi hoặc ra chữ lỗi. Ép stdout dùng UTF-8 trước khi in.
    """
    try:
        "Nhận diện".encode(sys.stdout.encoding or "ascii")
    except Exception:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _cat_mot_dong(text: str, gioi_han: int = 96) -> str:
    """Cắt chuỗi về 1 dòng để bảng không bị vỡ hàng khi in ra console."""
    text = " ".join(text.split())
    if len(text) <= gioi_han:
        return text
    return text[: gioi_han - 3].rstrip() + "..."


def in_bang_console() -> None:
    """In bảng tóm tắt 4 model + thông số + phiên bản."""
    print("")
    print("=" * 100)
    print("CamAI – CÁC MÔ HÌNH AI ĐANG DÙNG TRONG PHẦN MỀM")
    print("=" * 100)

    bang = bang_tt_tong_hop()
    for so, dong in enumerate(bang, start=1):
        bat_buoc = "bắt buộc phải có" if dong["bat_buoc"] else "không bắt buộc"
        print("")
        print(f"{so}. {dong['ten']}   [{bat_buoc}]")
        print(
            f"   Model kỹ thuật : {dong['model_id']}"
            f"   |  Thư viện: {dong['ten_thu_vien_day_du']}"
        )
        print(
            f"   File trên đĩa   : {dong['file']}"
            f"   |  Trạng thái: {dong['trang_thai_tieng_viet']}"
        )
        print(
            f"   Kích thước      : {dong['kich_thuoc_mb']} MB"
            f"   |  Đo được trên máy này: {dong['kich_thuoc_mb_thuc']} MB"
        )
        print(f"   Vai trò         : {_cat_mot_dong(dong['vai_tro'])}")

    print("")
    print("-" * 100)
    print("THÔNG SỐ KỸ THUẬT")
    print("-" * 100)
    print(
        f"  Ngưỡng khớp mặt (ArcFace) : {THONG_SO_KY_THUAT['nguong_khop_mat']:.2f}"
        f"   ({THONG_SO_KY_THUAT['gia_tri_nguong_khop_mat']})"
    )
    print(f"  Thư mục ảnh đã học        : {THONG_SO_KY_THUAT['thu_muc_anh_da_hoc']}")
    print(f"  Số người trong mẫu        : {THONG_SO_KY_THUAT['so_nguoi_da_hoc_mau']}")
    print(f"  CẢNH BÁO                  : {THONG_SO_KY_THUAT['canh_bao_anh_mau']}")

    print("")
    print("-" * 100)
    print("PHIÊN BẢN PHẦN MỀM")
    print("-" * 100)
    phien_ban = lay_phien_ban()
    for ten in ("insightface", "ultralytics", "opencv-python"):
        print(f"  {ten.ljust(20)} : {phien_ban.get(ten) or 'chưa cài đặt'}")

    # onnxruntime: CHỈ in MỘT dòng, và đó phải là bản đang chạy thật.
    # Trước đây in 2 dòng (1.20.1 rồi 1.23.2) khiến chủ sở hữu tưởng máy
    # đang chạy hai phiên bản cùng lúc. Thực tế chỉ 1 gói được nạp — xem ISSUE_LOG #8.
    ban_dang_chay = _phien_ban_ort_dang_chay()
    if ban_dang_chay:
        print(f"  {'onnxruntime-gpu'.ljust(20)} : {ban_dang_chay}   <- ĐANG CHẠY THẬT trên máy này")
    else:
        print(
            f"  {'onnxruntime-gpu'.ljust(20)} : "
            f"{phien_ban.get('onnxruntime-gpu') or 'chưa cài đặt'}"
        )

    # Bản CPU chỉ in ra làm ghi chú, KHÔNG in thành dòng phiên bản song song.
    ban_cpu = phien_ban.get("onnxruntime")
    if ban_cpu and ban_cpu != ban_dang_chay:
        print("")
        print(f"  Lưu ý: máy này còn cài gói onnxruntime {ban_cpu} (bản CPU) ở bên cạnh.")
        print(f"         Nhưng bản GPU ở trên mới là bản đang chạy.")
        print(f"         Hai gói nằm ở 2 thư mục khác nhau nên hiện chưa đụng nhau.")
        print(f"         Nếu sau này cài gói CPU vào .venv thì có thể ghi đè bản GPU,")
        print(f"         làm phần mềm chậm lại mà KHÔNG báo lỗi.")

    print("")
    if phien_ban["cuda"]:
        gpu = "có – phần mềm chạy được bằng card màn hình NVIDIA"
    else:
        gpu = "không – phần mềm chạy bằng CPU"
    print(f"  {'Chạy trên GPU (CUDA)'.ljust(20)} : {gpu}")

    thieu = [d for d in bang if not d["co_file"]]
    print("")
    if thieu:
        print("  CẢNH BÁO: thiếu file model: " + ", ".join(d["ten"] for d in thieu))
    else:
        print("  Đã kiểm tra trên đĩa: đủ cả 4/4 file model đều có sẵn.")
    print("=" * 100)
    print("")


if __name__ == "__main__":
    _chuan_hoa_console()
    in_bang_console()
