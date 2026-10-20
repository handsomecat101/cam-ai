"""Bang tra cuu lop COCO (YOLO11n) <-> tieng Viet.

Module nay KHONG import ultralytics/torch -> import rat re (vai ms).
cam_ai_core.py va app.py import duoc ma khong lam cham khoi dong app.

NGUON SU THAT: 80 lop COCO lay tu model yolo11n.pt (detector.names),
doc ngay 2026-10-20 bang lenh doc truc tiep `YOLO('yolo11n.pt').names`.
Khong doan mo. Bang tra cuu 80 lop doi chieu 100% voi model.

CONG DUNG:
  - TEN_LOP_VIET     : ten lop (tieng Anh) -> ten tieng Viet CO DAU.
  - TRA_CUU_LOP_VIET : nguoi dung go "o to", "xe may", "car" -> "car", "motorcycle".
  - DANH_SACH_LOP_VIET: (class_id, ten_anh, ten_viet) dung ve danh sach chon.
  - GOI_Y_LOP_VIET   : goi y lop gan nhat khi nguoi dung go sai chinh ta.

LUU Y VE NHAN TREN KHUNG HINH:
  Nhan ve bang supervision (cv2.putText + FONT_HERSHEY_SIMPLEX) -> font
  Hershey KHONG ve duoc dau tieng Viet (dau bi BO QUA im lang, xem
  _kk_kiem_lop_viet.py). Nen:
    - khung hinh  -> ten KHONG dau  (cam_ai_core.ten_vat_the)
    - log/bao cao/CSV -> ten CO DAU (ham nay)
"""

import difflib
import unicodedata

__all__ = [
    "TEN_LOP_VIET",
    "TEN_LOP_VIET_KHONG_DAU",
    "XE_PHUONG_TIEN",
    "XE_PHUONG_TIEN_MO_RONG",
    "TRA_CUU_LOP_VIET",
    "TRA_CUU_LOP_VIET_CHI_TIET",
    "TACH_LOP_VIET",
    "DANH_SACH_LOP_VIET",
    "GOI_Y_LOP_VIET",
    "LA_TAT_CA",
    "chuan_hoa",
]

# Khoa "all" - chon tat ca lop tru nguoi (giung hinh nhu cu).
KHOA_TAT_CA = "all"

# 80 lop COCO, dung thu tu id cua model yolo11n.pt (id 0..79).
# Ten tieng Viet CO DAU (chuoi hien thi cho nguoi dung).
TEN_LOP_VIET: dict[str, str] = {
    "person": "người",
    "bicycle": "xe đạp",
    "car": "ô tô",
    "motorcycle": "xe máy",
    "airplane": "máy bay",
    "bus": "xe khách",
    "train": "tàu hỏa",
    "truck": "xe tải",
    "boat": "thuyền",
    "traffic light": "đèn giao thông",
    "fire hydrant": "bình chữa cháy",
    "stop sign": "biển dừng xe",
    "parking meter": "đồng hồ đỗ xe",
    "bench": "ghế băng",
    "bird": "chim",
    "cat": "mèo",
    "dog": "chó",
    "horse": "ngựa",
    "sheep": "cừu",
    "cow": "bò",
    "elephant": "voi",
    "bear": "gấu",
    "zebra": "ngựa vằn",
    "giraffe": "hươu cao cổ",
    "backpack": "ba lô",
    "umbrella": "dù",
    "handbag": "túi xách",
    "tie": "cà vạt",
    "suitcase": "vali",
    "frisbee": "đĩa bay",
    "skis": "ván trượt tuyết",
    "snowboard": "bảng trượt tuyết",
    "sports ball": "bóng thể thao",
    "kite": "diều",
    "baseball bat": "gậy bóng chày",
    "baseball glove": "găng bóng chày",
    "skateboard": "ván trượt",
    "surfboard": "ván lướn",
    "tennis racket": "vợt quần vợt",
    "bottle": "chai",
    "wine glass": "ly rượu",
    "cup": "cốc",
    "fork": "nĩa",
    "knife": "dao",
    "spoon": "thìa",
    "bowl": "bát",
    "banana": "chuối",
    "apple": "táo",
    "sandwich": "bánh mì kẹp",
    "orange": "cam",
    "broccoli": "bông cải xanh",
    "carrot": "cà rốt",
    "hot dog": "xúc xích",
    "pizza": "bánh pizza",
    "donut": "bánh rán",
    "cake": "bánh kem",
    "chair": "ghế",
    "couch": "đi văng",
    "potted plant": "cây trong chậu",
    "bed": "giường",
    "dining table": "bàn ăn",
    "toilet": "bồn cầu",
    "tv": "ti vi",
    "laptop": "máy tính xách tay",
    "mouse": "chuột",
    "remote": "điều khiển",
    "keyboard": "bàn phím",
    "cell phone": "điện thoại",
    "microwave": "lò vi sóng",
    "oven": "lò nướng",
    "toaster": "máy nướng bánh mì",
    "sink": "bồn rửa",
    "refrigerator": "tủ lạnh",
    "book": "sách",
    "clock": "đồng hồ",
    "vase": "bình hoa",
    "scissors": "kéo",
    "teddy bear": "gấu bông",
    "hair drier": "máy sấy tóc",
    "toothbrush": "bàn chải đánh răng",
}

# Cac lop phuong tien (dung mac dinh cho --dem-phuong-tien).
XE_PHUONG_TIEN: list[str] = ["car", "motorcycle", "bicycle", "bus", "truck"]

# Ban mo rong (COCO co them "train" va "boat" - deu la phuong tien).
# Mac dinh van dung 5 lop pho bien o tren; ban mo rong dung khi nguoi dung
# tu chon bang --lop-phuong-tien.
XE_PHUONG_TIEN_MO_RONG: list[str] = XE_PHUONG_TIEN + ["train", "boat"]

# Tu dong nghĩa tieng Viet -> lop COCO (ngoai ra ten chinh trong TEN_LOP_VIET).
# Ghi them bao nhieu cach goi thi nguoi dung Viet khong can nho ten tieng Anh.
_TU_DONG_NGHIA: dict[str, list[str]] = {
    "person": ["con người", "người ta", "người lớn", "người nam", "người nữ"],
    "car": ["xe hơi", "xe ô tô", "xe 4 bánh", "xe bốn bánh", "ô tô con"],
    "motorcycle": ["mô tô", "moto", "xe gắn máy", "xe song", "xe hai bánh"],
    "bicycle": ["xe đạp thể thao", "xe đạp đi"],
    "bus": ["xe buýt", "xe buýt liên tỉnh", "xe lớn", "xe đò"],
    "truck": ["xe hàng", "xe tải lớn", "xe bán"],
    "boat": ["xe thuyền", "tàu thuyền", "xuồng", "ghe"],
    "train": ["tàu lửa", "xe lửa", "tàu điện"],
    "airplane": ["máy bay hành khách", "máy bay thương mại", "máy bay phản lực"],
    "traffic light": ["đèn đỏ", "đèn xanh", "đèn vàng", "tín hiệu giao thông"],
    "fire hydrant": ["cột cứu hỏa", "vòi nước cứu hỏa", "bình chữa cháy cầm tay"],
    "stop sign": ["biển dừng", "biển stop", "biển báo dừng xe", "biển tam giác"],
    "parking meter": ["máy đếm xe", "đồng hồ giữ xe", "cổng đỗ xe"],
    "bench": ["ghế công viên", "ghế gỗ", "ghế ngoài trời"],
    "bird": ["con chim", "chim bay"],
    "cat": ["mèo nhà", "mèo mướp", "mèo hoang"],
    "dog": ["chó nhà", "chó con", "chó hoang"],
    "horse": ["ngựa hoang", "ngựa đua"],
    "sheep": ["dê", "cừu non", "cừu trắng"],
    "cow": ["bò sữa", "bò vàng", "hàm"],
    "elephant": ["voi rừng", "voi châu Á"],
    "bear": ["gấu rừng", "gấu nâu", "gấu trúc"],
    "zebra": ["sơn dương", "ngựa vằn châu Phi"],
    "giraffe": ["hươu cao cổ", "hươu cao cổ châu Phi"],
    "backpack": ["ba lô cấp", "cặp sách lưu", "quang tranh"],
    # Luu y: KHONG them "ô tô" vao day - "ô tô" la ten chinh cua lop car.
    "umbrella": ["ô che mưa", "dù che mưa", "dù gấp", "ô dù"],
    "handbag": ["túi du lịch", "túi đeo", "túi xách tay"],
    "tie": ["cà vạt buộc", "cà vạt kẻ cổ"],
    "suitcase": ["hàm lý", "vali du lịch", "vali cầm tay"],
    "frisbee": ["đĩa bay ném", "đĩa nhảy"],
    "skis": ["ván trượt tuyết", "giày trượt tuyết"],
    "snowboard": ["bảng trượt", "snowboard", "tuyết trượt"],
    "sports ball": ["bóng", "quả bóng", "bóng đá", "bóng chuyền"],
    "kite": ["diều bay", "diều giấy"],
    "baseball bat": ["gậy", "gậy bóng chày", "cần bóng chày"],
    "baseball glove": ["găng tay", "găng bóng chày", "găng đeo"],
    "skateboard": ["ván trượt giày", "ván trượt phủ", "skateboard"],
    "surfboard": ["ván lướn sóng", "ván lướn"],
    "tennis racket": ["vợt", "gậy quần vợt", "rào quần vợt"],
    "bottle": ["chai nước", "bình nước", "lọ", "bình rượu"],
    "wine glass": ["ly rượu vang", "ly uống rượu", "tách rượu"],
    "cup": ["cốc", "tách", "cốc trà"],
    "fork": ["nĩa ăn", "nĩa gắp"],
    "knife": ["dao ăn", "dao gọt", "dao rọc"],
    "spoon": ["thìa canh", "thìa gắp"],
    "bowl": ["bát cơm", "tô", "bát canh"],
    "banana": ["chuối chín", "quả chuối"],
    "apple": ["quả táo", "táo xanh"],
    "sandwich": ["bánh mì", "bánh mì thịt", "bánh mì que"],
    "orange": ["quả cam", "quýt", "cam vàng"],
    "broccoli": ["bông cải", "súp lơ"],
    "carrot": ["cà rốt", "cà rốt đỏ"],
    "hot dog": ["xúc xích", "xúc xích nướng", "hot dog"],
    "pizza": ["pizza", "bánh pizza"],
    "donut": ["donut", "bánh donat", "bánh rán giòn"],
    "cake": ["bánh", "bánh sinh nhật", "bánh kem sinh nhật", "bánh chocolate"],
    "chair": ["ghế", "ghế gỗ", "ghế nhựa"],
    "couch": ["sofa", "ghế sofa", "đi văng phòng khách"],
    "potted plant": ["cây", "chậu cây", "cây xanh", "cây trang trí"],
    "bed": ["giường ngủ", "giường", "nệm"],
    "dining table": ["bàn", "bàn ăn gia đình", "bàn gỗ"],
    "toilet": ["toilet", "nhà vệ sinh", "bàn xả", "thùng rác"],
    "tv": ["tivi", "ti vi", "màn hình", "tivi treo tường"],
    "laptop": ["laptop", "máy tính", "máy tính xách tay", "notebook"],
    "mouse": ["chuột máy tính", "chuột không dây", "con chuột"],
    "remote": ["remote", "điều khiển từ xa", "bộ điều khiển", "điều khiển ti vi"],
    "keyboard": ["bàn phím", "bàn phím máy tính", "keyboard"],
    "cell phone": [
        "điện thoại di động", "điện thoại thông minh", "điện thoại cầm tay",
        "điện thoại để bàn", "smartphone", "smart phone", "mobile", "dien thoai",
    ],
    "microwave": ["lò vi sóng điện", "vi sóng", "lò vi sóng"],
    "oven": ["lò nướng điện", "lò nướng", "lò"],
    "toaster": ["máy nướng bánh mì", "máy nướng bánh", "toaster"],
    "sink": ["bồn rửa bát", "chậu rửa", "bồn rửa mặt"],
    "refrigerator": ["tủ mát", "tủ ướp", "tủ lạnh"],
    "book": ["sách", "quyển sách", "sách vở", "tập sách"],
    "clock": ["đồng hồ treo tường", "đồng hồ bàn", "đồng hồ alarm"],
    "vase": ["lọ hoa", "bình cắm hoa", "bình hoa"],
    "scissors": ["kéo", "kéo cắt", "kéo cắt giấy", "kéo cắt vải"],
    "teddy bear": ["gấu bông", "thú bông", "gấu đồ chơi"],
    "hair drier": ["máy sấy tóc", "sấy tóc", "máy sấy"],
    "toothbrush": ["bàn chải", "bàn chải đánh răng", "vệ sinh răng", "bàn chải điện"],
}


def chuan_hoa(text: str) -> str:
    """Chuan hoa chuoi de so sanh: bo dau, ha chu thuong, gom khoang trang.

    'Ô tô' -> 'o to' | 'Xe  Đạp' -> 'xe dap' | 'cell_phone' -> 'cell phone'
    """
    s = unicodedata.normalize("NFD", str(text or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("-", " ").replace("_", " ").lower()
    s = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    return " ".join(s.split())


# TEN_LOP_VIET KHONG DAU - dung cho nhan tren khung hinh (font Hershey
# khong ve duoc dau) va cho tra cuu nhanh.
TEN_LOP_VIET_KHONG_DAU: dict[str, str] = {
    ten: chuan_hoa(viet) for ten, viet in TEN_LOP_VIET.items()
}


def _tao_bang_tra_cuu() -> dict[str, str]:
    """Bang normalized -> ten lop tieng Anh (khoa goc cua model)."""
    bang: dict[str, str] = {}

    def them(khoa: str, ten_lop: str) -> None:
        khoa = chuan_hoa(khoa)
        if khoa and khoa not in bang:
            bang[khoa] = ten_lop

    for ten_lop in TEN_LOP_VIET:
        them(ten_lop, ten_lop)                       # ten tieng Anh
        them(TEN_LOP_VIET[ten_lop], ten_lop)         # ten tieng Viet co dau
        them(TEN_LOP_VIET_KHONG_DAU[ten_lop], ten_lop)  # ten tieng Viet khong dau
    for ten_lop, danh_sach in _TU_DONG_NGHIA.items():
        for alias in danh_sach:
            them(alias, ten_lop)
    return bang


_BANG_TRA_CUU: dict[str, str] = _tao_bang_tra_cuu()

# Ten lop (tieng Anh) -> normalized, dung de goi y khi nguoi dung go sai.
_TEN_ANH_CHUAN_HOA: list[str] = [chuan_hoa(t) for t in TEN_LOP_VIET]
_TEN_VIET_CHUAN_HOA: list[str] = [chuan_hoa(v) for v in TEN_LOP_VIET.values()]


def LA_TAT_CA(text: str) -> bool:
    """True neu chuoi người dùng nhập là 'all' / 'tất cả'."""
    khoa = chuan_hoa(text)
    return khoa in ("all", "tat ca", "tatca", "tuat ca")


def _tach_vao(text: str) -> list[str]:
    """Tach chuoi nguoi dung nhap thanh tung lop (dau phay hoac cham phay)."""
    raw = str(text or "").replace(";", ",")
    return [phan.strip() for phan in raw.split(",") if phan.strip()]


def TACH_LOP_VIET(text: str) -> list[str]:
    """Tach chuoi nguoi dung nhap thanh tung lop (dau phay hoac cham phay).

    Dung khi can xu ly TUNG token (vd: token nao trung ten lop trong model,
    token nao la tieng Viet can tra cuu).
    """
    return _tach_vao(text)


def _tim_trong_chuoi(phan: str) -> str:
    """Tim 1 lop trong 1 chuoi (dung khi nguoi dung go khong dau phay).

    'o to, xe may' -> 'xe may' (tu 'o to' tim trong 'xe may' khong ra).
    """
    khoa = chuan_hoa(phan)
    if not khoa:
        return ""
    if khoa in _BANG_TRA_CUU:
        return _BANG_TRA_CUU[khoa]
    # Thuong nguoi go "xe o to xe may" khong dau phay: tim lop nao co ten
    # (tieng Viet hoac tieng Anh) la chuoi con cua phan nay, lay ten dai nhat.
    tot_nhat = ""
    ket_qua = ""
    for ten_lop in TEN_LOP_VIET:
        for ung_vien in (
            TEN_LOP_VIET_KHONG_DAU[ten_lop],
            chuan_hoa(ten_lop),
        ):
            if ung_vien and ung_vien in khoa and len(ung_vien) > len(tot_nhat):
                tot_nhat = ung_vien
                ket_qua = ten_lop
    return ket_qua


def TRA_CUU_LOP_VIET_CHI_TIET(text: str) -> tuple[list[str], list[str]]:
    """Tra cuu lop -> (danh sach lop tieng Anh, danh sach tu khong nhan ra).

    Nhan duoc: tieng Viet co dau ('ô tô'), tieng Viet khong dau ('o to'),
    tieng Anh ('car'), tu dong nghia ('xe hơi', 'mô tô', 'xe buýt').
    """
    ra: list[str] = []
    sai: list[str] = []
    for phan in _tach_vao(text):
        ten = _tim_trong_chuoi(phan)
        if not ten:
            sai.append(phan)
        elif ten not in ra:
            ra.append(ten)
    return ra, sai


def TRA_CUU_LOP_VIET(text: str) -> list[str]:
    """Chuoi nguoi dung nhap -> danh sach ten lop COCO tieng Anh.

    'ô tô,xe máy' -> ['car', 'motorcycle'] | 'o to,xe may' -> ['car', 'motorcycle']
    Tu khong nhan ra thi BIEN MAT khoi ket qua (dung ham CHI_TIET de biet
    tu nao sai, de bao loi ro rang cho nguoi dung).
    """
    ra, _sai = TRA_CUU_LOP_VIET_CHI_TIET(text)
    return ra


def DANH_SACH_LOP_VIET() -> list[tuple[int, str, str]]:
    """Danh sach day du 80 lop: (class_id, ten tieng Anh, ten tieng Viet).

    Thu tu class_id dung theo model yolo11n.pt (0..79).
    """
    return [
        (cid, ten_anh, TEN_LOP_VIET[ten_anh])
        for cid, ten_anh in enumerate(TEN_LOP_VIET)
    ]


def GOI_Y_LOP_VIET(text: str) -> str:
    """Goi y lop gan nhat khi nguoi dung go sai chinh ta.

    So sanh tren CA ban co dau va ban khong dau. Tra ve chuoi goi y
    (tieng Viet co dau) hoac '' neu khong doan duoc gi.
    """
    goi_y: list[str] = []
    for phan in _tach_vao(text):
        khoa = chuan_hoa(phan)
        if not khoa or khoa in _BANG_TRA_CUU:
            continue
        # So sanh tren ca 3 che do (co dau / khong dau / tieng Anh) roi lay
        # ty le CAO NHAT - tranh truong hop goi y nham lop khac.
        ung_vien: list[tuple[float, str]] = []

        def them(ten_viet: str, ty_le: float) -> None:
            if ten_viet:
                ung_vien.append((ty_le, ten_viet))

        # 1) chuoi co dau voi ten tieng Viet co dau
        for ten_viet in TEN_LOP_VIET.values():
            ty_le = difflib.SequenceMatcher(
                None, phan.lower(), ten_viet.lower()
            ).ratio()
            if ty_le >= 0.6:
                them(ten_viet, ty_le)
        # 2) chuoi khong dau voi ten tieng Viet khong dau
        for ten_lop in TEN_LOP_VIET:
            ty_le = difflib.SequenceMatcher(
                None, khoa, TEN_LOP_VIET_KHONG_DAU[ten_lop]
            ).ratio()
            if ty_le >= 0.72:
                them(TEN_LOP_VIET[ten_lop], ty_le)
        # 3) chuoi khong dau voi ten tieng Anh
        for ten_lop in TEN_LOP_VIET:
            ty_le = difflib.SequenceMatcher(
                None, khoa, chuan_hoa(ten_lop)
            ).ratio()
            if ty_le >= 0.7:
                them(TEN_LOP_VIET[ten_lop], ty_le)

        if not ung_vien:
            continue
        ten_viet = max(ung_vien, key=lambda c: c[0])[1]
        ten_anh = next(
            (t for t in TEN_LOP_VIET if TEN_LOP_VIET[t] == ten_viet), ""
        )
        goi_y.append(
            f"'{phan}' → có phải là '{ten_viet}'"
            + (f" ({ten_anh})?" if ten_anh else "?")
        )
    return "; ".join(goi_y)
