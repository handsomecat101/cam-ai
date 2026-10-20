"""
CamAI - HANG SO THIET KE + TIEN ICH (design tokens).

Tach rieng khoi `gui.py` de file do khong con chon vui ma hex.
Nguon su that: `design-system/camai/MASTER.md` (design system da chot).

Quy tac cua file nay:
  1. MOI mau deu di qua `MAU` - khong viet hex tay ben ngoai widget.
  2. Font CHI dung font co san tren Windows (app chay 100% offline).
  3. KHONG emoji lam icon: dung font bieu tuong Windows `Segoe MDL2 Assets`.
  4. Comment/docstring tieng Viet KHONG DAU; chuoi hien thi CO DAU.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------- BANG MAU
#
# Phong cach: "dark tech + xanh trang thai" (MASTER.md muc 2).
# TAT CA ma mau cua gui.py deu lay tu dict nay - KHONG viet hex tay ben ngoai.
MAU = {
    "nen":            "#0F172A",   # nen chinh cua cua so
    "the":            "#1B2336",   # nen the / thanh tieu de nhom
    "the_phu":        "#272F42",   # nen phu (o nhap, hang nho)
    "chu":            "#F8FAFC",   # chu chinh
    "chu_phu":        "#94A3B8",   # chu phu tren nen chinh
    "chu_phu_the":    "#CBD5E1",   # chu phu tren nen the (de doc hon)
    "nut":            "#22C55E",   # nut chinh (CTA) + chu bao thanh cong
    "nut_hover":      "#16A34A",
    "chu_nut":        "#052E16",   # chu tren nen nut chinh (tuong phan 5.4:1)
    "nut_phu":        "#334155",   # nut phu
    "nut_phu_hover":  "#475569",
    "vien":           "#334155",   # vien 1px
    "loi":            "#EF4444",   # loi / nguy hiem
    "canh_bao":       "#F59E0B",   # canh bao / cho (v3.3 bo sung)
    "focus":          "#FFFFFF",   # vien sang khi focus
}

# Mau nen cua HUYEN TRANG THAI - nhin la biet ngay, khong phai doc chu.
# Dung 3 mau trang thai xanh / ho phach / do theo quy tac cua skill.
MAU_TRANG_THAI = {
    "chua_chay": MAU["nut_phu"],
    "chay": "#15803D",
    "khung_hinh_day_du": "#15803D",
    "khung_hinh": "#15803D",
    "tam_dung": "#B45309",
    "loi": "#B91C1C",
    "dung_giua": "#B45309",
    "xong": "#15803D",
}

# ---------------------------------------------------------- KHOANG CACH
#
# Luoi khoang cach 4 / 8 / 12 / 16 / 24 / 32 (MASTER.md muc 4).
# Cung mot vai tro LUON dung dung mot gia tri.
KHOANG_CACH = {
    "rat_nho": 4,
    "nho": 8,
    "vua": 12,
    "thuong": 16,
    "lon": 24,
    "rat_lon": 32,
}

# Vai tro dung cu the trong GUI (de goi bang ten de doc, khong phai magic number).
KHOANG_CACH_HANG = 8        # giua 2 hang cau hinh
KHOANG_CACH_KHOC = 24       # giua 2 khoi lon
PADDING_THE = 16            # padding trong the
PADDING_NHOM = 12           # padding trong nhom con
LE_NGOAI = 16               # le ngoai quanh mep cua so

# ------------------------------------------------------------- BO GOC
#
# bo goc: nut 8, o nhap 6, the 10 (MASTER.md muc 4).
BO_GOC = {
    "nut": 8,
    "o_nhap": 6,
    "the": 10,
}

# Giu ten cu de khong pha cho noi dung dang dung (gui.py dang import).
BO_GOC_NUT = BO_GOC["nut"]
BO_GOC_O_NHAP = BO_GOC["o_nhap"]
BO_GOC_THE = BO_GOC["the"]

# ---------------------------------------------------------- KICH THUOC
#
# Nut cao 36, o nhap cao 32, chu nho nhat 12 (MASTER.md muc 1 + muc 4).
KICH_THUOC = {
    "cao_nut": 36,
    "cao_o_nhap": 32,
    "cao_hang_cao": 34,
    "co_chu_nho_nhat": 12,
    "co_chu_than_bai": 13,
}

# ---------------------------------------------------------------- FONT
#
# Font CHI dung font co san tren Windows (app chay 100% offline, khong
# duoc phu thuoc tai font tu Internet). Cac font duoi day deu co san:
#   segoeui.ttf   -> Segoe UI
#   seguisb.ttf   -> Segoe UI Semibold
#   seguibl.ttf   -> Segoe UI Black
#   CascadiaMono.ttf -> Cascadia Mono (so / ma)
#   segmdl2.ttf   -> Segoe MDL2 Assets (bieu tuong)

_THU_MUC_FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def _co_file_font(ten_file: str) -> bool:
    """True neu file font co that tren may."""
    try:
        return os.path.isfile(os.path.join(_THU_MUC_FONT, ten_file))
    except Exception:                                 # noqa: BLE001
        return False


_CO_SEGOE_UI = _co_file_font("segoeui.ttf")
_CO_SEGOE_SEMI = _co_file_font("seguisb.ttf")
_CO_SEGOE_BLACK = _co_file_font("seguibl.ttf")
_CO_CASCADIA = _co_file_font("CascadiaMono.ttf")
_CO_MDL2 = _co_file_font("segmdl2.ttf")

# Gia tri mac dinh (suy tu file font). `xac_nhan_font()` se kiem tra lai
# bang `tkinter.font.families()` ngay khi cua so da co root.
FONT_CHU = "Segoe UI" if _CO_SEGOE_UI else "Tahoma"
FONT_DAM = "Segoe UI Semibold" if _CO_SEGOE_SEMI else FONT_CHU
FONT_DEN = "Segoe UI Black" if _CO_SEGOE_BLACK else FONT_CHU
FONT_SO = "Cascadia Mono" if _CO_CASCADIA else "Consolas"
FONT_BIEU_TUONG = "Segoe MDL2 Assets" if _CO_MDL2 else ""

# Vai tro chu (MASTER.md muc 3): (ten font, co, do dam).
FONT = {
    "ten_app":         (FONT_CHU, 23, "bold"),        # ten app tren thanh dau
    "phien_ban":       (FONT_CHU, 13, "normal"),      # phien ban canh ten app
    "tieu_de_khu_vuc": (FONT_DAM, 15, "normal"),      # "Xem video", "Nhat ky"...
    "nhan_nhom":       (FONT_DAM, 12, "bold"),        # nhan nhom viet HOA
    "nhan_o":          (FONT_CHU, 13, "normal"),      # nhan ben trai 1 hang
    "chu_nhap":        (FONT_CHU, 13, "normal"),      # o nhap, dropdown
    "ghi_chu":         (FONT_CHU, 12, "normal"),      # ghi chu nho
    "so_ma":           (FONT_SO, 12, "normal"),       # so / ma / nhat ky
    "so_lieu":         (FONT_CHU, 28, "bold"),        # 6 o so lieu
    "nut":             (FONT_CHU, 14, "bold"),        # chu tren nut
    "trang_thai":      (FONT_CHU, 12, "bold"),        # huyen trang thai
    "bieu_tuong":      (FONT_BIEU_TUONG, 14, "normal"),
}

# Font cu (tuong thich) cho truong hop `xac_nhan_font` doi phat hien font
# khong co that tren may.
_PHUC_LUC = {
    "chu": ("Segoe UI", "Tahoma", "Arial"),
    "dam": ("Segoe UI Semibold", "Segoe UI", "Tahoma"),
    "den": ("Segoe UI Black", "Segoe UI", "Tahoma"),
    "so": ("Cascadia Mono", "Consolas", "Courier New"),
    "bieu_tuong": ("Segoe MDL2 Assets", "Segoe UI Symbol", "Tahoma"),
}


def _dung_font(families: set, uu_tien: str, phu_luc: tuple) -> str:
    """Chon font dau tien co that trong `families`, neu khong co thi dung
    phu luc, cuoi cung quay ve `uu_tien`."""
    if not families:
        return uu_tien
    if uu_tien in families:
        return uu_tien
    for ten in phu_luc:
        if ten in families:
            return ten
    return uu_tien


def xac_nhan_font(root=None) -> dict:
    """KIEM TRA font bang `tkinter.font.families()` roi fallback ve Segoe UI.

    Gọi 1 lần sau khi cửa sổ Tk đã tồn tại (trong `CamAIGui.__init__`).
    Trả về dict để in ra kiểm chứng. Nếu thiếu font biểu tượng thì
    `FONT_BIEU_TUONG` bị đặt rỗng - nơi gọi phải tự dùng chữ viết tắt.
    """
    global FONT_CHU, FONT_DAM, FONT_DEN, FONT_SO, FONT_BIEU_TUONG, FONT
    families = set()
    try:
        import tkinter.font as tkfont
        families = set(tkfont.families(root))
    except Exception:                                 # noqa: BLE001
        families = set()

    FONT_CHU = _dung_font(families, FONT_CHU, _PHUC_LUC["chu"])
    FONT_DAM = _dung_font(families, FONT_DAM, _PHUC_LUC["dam"])
    FONT_DEN = _dung_font(families, FONT_DEN, _PHUC_LUC["den"])
    FONT_SO = _dung_font(families, FONT_SO, _PHUC_LUC["so"])
    FONT_BIEU_TUONG = _dung_font(families, FONT_BIEU_TUONG,
                                 _PHUC_LUC["bieu_tuong"])
    if not _CO_MDL2 and not families:
        FONT_BIEU_TUONG = ""
    if FONT_BIEU_TUONG not in ("Segoe MDL2 Assets",):
        # Khong co font bieu tuong Windows -> tat ca noi dung dung chu.
        FONT_BIEU_TUONG = ""

    FONT = {
        "ten_app":         (FONT_CHU, 23, "bold"),
        "phien_ban":       (FONT_CHU, 13, "normal"),
        "tieu_de_khu_vuc": (FONT_DAM, 15, "normal"),
        "nhan_nhom":       (FONT_DAM, 12, "bold"),
        "nhan_o":          (FONT_CHU, 13, "normal"),
        "chu_nhap":        (FONT_CHU, 13, "normal"),
        "ghi_chu":         (FONT_CHU, 12, "normal"),
        "so_ma":           (FONT_SO, 12, "normal"),
        "so_lieu":         (FONT_CHU, 28, "bold"),
        "nut":             (FONT_CHU, 14, "bold"),
        "trang_thai":      (FONT_CHU, 12, "bold"),
        "bieu_tuong":      (FONT_BIEU_TUONG, 14, "normal"),
    }
    return {
        "chu": FONT_CHU,
        "dam": FONT_DAM,
        "den": FONT_DEN,
        "so": FONT_SO,
        "bieu_tuong": FONT_BIEU_TUONG,
        "co_font_bieu_tuong": bool(FONT_BIEU_TUONG),
    }


def co_font_bieu_tuong() -> bool:
    """True neu may co font bieu tuong Windows de ve icon."""
    return bool(FONT_BIEU_TUONG)


# ------------------------------------------------------- BIEU TUONG WINDOWS
#
# Font bieu tuong cua Windows: `Segoe MDL2 Assets` (segmdl2.ttf).
# KHONG dung emoji hay ky tu to hop nhu ▶ ✔ ✖ ■ - quy tac cua design system.
BIEU_TUONG = {
    "phat":       "\uE768",   # Play
    "tam_dung":   "\uE769",   # Pause
    "dung":       "\uE71A",   # Stop
    "tick":       "\uE73E",   # CheckMark
    "loi":        "\uE783",   # Error
    "mui_phai":   "\uE76C",   # ChevronRight
    "mui_xuong":  "\uE70D",   # ChevronDown
    "mui_len":    "\uE70E",   # ChevronUp
    "video":      "\uE714",   # Video
    "camera":     "\uE722",   # Camera
    "nguoi":      "\uE716",   # People
    "danh_thiep": "\uE77B",   # Contact
    "cai_dat":    "\uE713",   # Settings
    "luu":        "\uE74E",   # Save
    "mo_thu_muc": "\uE8B7",   # FolderOpen
    "canh_bao":   "\uE7BA",   # Warning
    "thong_tin":  "\uE946",   # Info
    "bao_cao":    "\uE9D9",   # Report
    "them":       "\uE710",   # Add
    "xoa":        "\uE74D",   # Delete
    "xem":        "\uE7B3",   # View
}


def bieu_tượng(ma: str, size: int = 14) -> str:
    """Ky tu bieu tuong Windows theo ten viet tat.

    `ma` la ten trong `BIEU_TUONG` ("phat", "tick", ...) hoac chinh ky tu.
    Font de ve: `FONT_BIEU_TUONG` (Segoe MDL2 Assets).
    `size` chi dung khi ve icon + chu trong cung 1 nut (xem `anh_bieu_tuong`).
    """
    return BIEU_TUONG.get(ma, ma)


# Ban khong dau cua `bieu_tuong` - de goi tu code khong dau tieng Viet.
bieu_tuong = bieu_tượng


def anh_bieu_tuong(ma: str, size: int = 16, mau=(255, 255, 255, 255)):
    """Ve ky tu bieu tuong thanh anh PIL (dung khi can icon + chu trong 1 nut).

    Tk khong ve duoc 2 font khac nhau trong cung 1 chuoi, nen nut co ca
    icon + chu phai dung `image=` cho icon. Tra ve anh PIL, hoac None neu
    may khong co font bieu tuong (khi do nen dung chu viet tat).
    """
    if not FONT_BIEU_TUONG:
        return None
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:                                 # noqa: BLE001
        return None
    ten_file = os.path.join(_THU_MUC_FONT, "segmdl2.ttf")
    if not os.path.isfile(ten_file):
        return None
    ky_tu = bieu_tượng(ma)
    try:
        font = ImageFont.truetype(ten_file, size)
        # Do bang chinh font -> anh vua khu glyph, khong thua trang.
        tmp = Image.new("RGBA", (size * 3, size * 3), (0, 0, 0, 0))
        hop = ImageDraw.Draw(tmp).textbbox((0, 0), ky_tu, font=font)
        rong = max(1, hop[2] - hop[0])
        cao = max(1, hop[3] - hop[1])
        anh = Image.new("RGBA", (rong + 2, cao + 2), (0, 0, 0, 0))
        ImageDraw.Draw(anh).text((1 - hop[0], 1 - hop[1]), ky_tu, font=font,
                                 fill=mau)
        return anh
    except Exception:                                 # noqa: BLE001
        return None
