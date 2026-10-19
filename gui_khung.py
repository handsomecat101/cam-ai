# -*- coding: utf-8 -*-
"""
CamAI - PHAN VIDEO REALTIME + PANEL "DOI TUONG PHAT HIEN".

File nay tach rieng khoi gui.py de gui.py khong phinh to. gui.py import
3 mon thoi: `ve_khung_hinh`, `PanelDoiTuong`, `cat_anh_moi`.

VAI TRO
------
1. `ve_khung_hinh(...)` ve overlay len khung hinh cua chinh GUI:
   khung nguoi day, nhan co nen (doc duoc), khung vat the, vach dem ra/vao,
   khung vung canh doi mau theo trang thai. KHONG sua cam_ai_core.

2. `cat_anh_moi(...)` cat anh crop cua tung doi tuong (nguoi / vay the / mat).

3. `PanelDoiTuong` la WIDGET gom anh crop vao mot cho: luoi the, bo loc,
   gioi han so the, chi giai ma lai it anh moi vong de khong lam lag UI.

VE CHU TIENG VIET CO DAU
------------------------
`cv2.putText` KHONG ve duoc dau tieng Viet (herhey font chi co ASCII) - nen
phan ve bang PIL voi font `segoeui.ttf` co san tren Windows. Day la ly do
`ve_khung_hinh` doi chieu mau BGR <-> RGB 1 lan duy nhat roi ve bang PIL.

KHONG CO `after()` TRONG FILE NAY: moi thu deu do chu `_hut_hang_doi` cua
gui.py dieu khien, de giu duy nhat 1 vong `after()` (khong giat khi keo).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import customtkinter as ctk

APP_DIR_GUI = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# MAU
# --------------------------------------------------------------------------
# Overlay ve bang OpenCV/PIL -> RGB (PIL dung RGB, khong phai BGR nhu cv2).
MAU_NGUOI = (56, 235, 116)          # xanh la: nguoi chua biet ten
MAU_NGUOI_QUEN = (255, 209, 102)    # vang: nguoi quen
MAU_VAT_THE = (255, 167, 38)        # cam: car, cho, meo...
MAU_VUNG_TRONG = (250, 204, 21)     # vung chua co gi
MAU_VUNG_CO_NGUOI = (52, 211, 153)  # vung dang co nguoi
MAU_VUNG_QUA = (248, 50, 50)        # vuot nguong
MAU_VUNG_DUNG_LAU = (249, 115, 22)  # co nguoi dung lau
MAU_VACH = (255, 255, 255)
MAU_NEN_NHAN = (15, 23, 42)         # nen cua o nhan -> chu trang noi bat
MAU_CHU = (255, 255, 255)

MAU_PANEL = {
    "nen": "#0B1220",
    "the": "#1B2336",
    "the_phu": "#272F42",
    "vien": "#334155",
    "chu": "#F8FAFC",
    "chu_phu": "#94A3B8",
    "nut": "#22C55E",
    "canh": "#F59E0B",
    "loi": "#EF4444",
}

SO_THE_TOI_DA = 24          # giu toi da bao nhieu the trong panel
SO_ANH_GIAI_MA_1_VONG = 3   # toi da bao nhieu the doi lai anh trong 1 vong
KHOANG_QUANG = 6.0          # giay - khong thay trong vung -> the mo nhat toi
BE_THE_ANH = 132            # canh anh crop (vuong)
BO_GOC_THE = 8

# --- ANH XEM TRUOC (THUMBNAIL) CHO VIDEO MAU ----------------------------
# Anh lay tu CHINH file video: mo video, nhay toi ~1 giay, doc 1 khung hinh.
RONG_THUMB = 128            # be rong anh xem truoc cua 1 the video mau
CAO_THUMB = 72              # be cao anh xem truoc (16:9)
THUMB_CACHE = "_thumb_cache"  # thu muc cache anh - mo lai khong phai doc video lai

_LUU_FONT: dict[int, object] = {}


def _font(cỡ: int):
    """Font TTF cho PIL. Windows luon co segoeui.ttf -> ve duoc tieng Viet."""
    if cỡ in _LUU_FONT:
        return _LUU_FONT[cỡ]
    from PIL import ImageFont

    font = None
    for ten in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf",
                "tahoma.ttf"):
        try:
            font = ImageFont.truetype(ten, cỡ)
            break
        except OSError:
            continue
    if font is None:                     # truong hop hiem - font mac dinh
        font = ImageFont.load_default()
    _LUU_FONT[cỡ] = font
    return font


# --------------------------------------------------------------------------
# VE OVERLAY
# --------------------------------------------------------------------------

# Lề đệm quanh mực chữ khi dựng ô nhãn (px).
O_NHAN_DEM_X = 6
O_NHAN_DEM_Y = 4


def _do_o_nhan(ve, chu: str, font, x: int, y: int) -> tuple:
    """Hình chữ nhật NỀN của ô nhãn khi chữ được vẽ neo tại `(x, y)`.

    Đo bằng CHÍNH font + cỡ chữ sẽ vẽ (`ImageDraw.textbbox`) nên rect luôn
    khớp đúng mực chữ thật - không còn suy đoán từ cỡ chữ như trước.
    """
    hop = ve.textbbox((0, 0), chu, font=font)
    return (int(x) + hop[0] - O_NHAN_DEM_X, int(y) + hop[1] - O_NHAN_DEM_Y,
            int(x) + hop[2] + O_NHAN_DEM_X, int(y) + hop[3] + O_NHAN_DEM_Y)


def _ve_o_nhan(ve, rect, chu: str, mau_nen, font) -> None:
    """Vẽ ô nhãn tại đúng rect đã tính sẵn bởi `_do_o_nhan`."""
    hop = ve.textbbox((0, 0), chu, font=font)
    ve.rectangle(list(rect), fill=mau_nen)
    # Đảo đúng công thức của `_do_o_nhan` -> mực chữ nằm đúng trong ô.
    ve.text((rect[0] + O_NHAN_DEM_X - hop[0],
             rect[1] + O_NHAN_DEM_Y - hop[1]), chu, font=font, fill=MAU_CHU)


def _khung(anh, x1, y1, x2, y2, mau, do_day: int) -> None:
    """Khung nguoi: vẽ 2 lớp (vien den + vien mau) để nổi trên nền sáng."""
    from PIL import ImageDraw

    ve = ImageDraw.Draw(anh)
    box = [int(x1), int(y1), int(x2), int(y2)]
    ve.rectangle(box, outline=(0, 0, 0), width=do_day + 3)
    ve.rectangle(box, outline=mau, width=do_day)


# --------------------------------------------------------------------------
# TRÁNH NHÃN CHỒNG NHAU
# --------------------------------------------------------------------------
# Vấn đề: 2 người đứng sát nhau thì 2 nhãn ("Người 1" / "Người 2") cùng nằm
# ngay trên đầu khung -> DỒN LÊN NHAU, đọc không được (đã thấy trong
# `_kiem_chung/kk_29_dang_chay.png`).
#
# Cách sửa: đo trước kích thước mọi nhãn, sắp xếp theo trục Y rồi lần lượt
# tìm chỗ trống. Ưu tiên đúng chỗ mong muốn (ngay trên khung), chồm thì dời
# XUỐNG; dời hết mà vẫn chồm thì dời LÊN. Không còn chỗ nào trong khung hình
# thì ẨN nhãn - tuyệt đối không vẽ đè lên nhau.
#
# Nhãn có tên người quen được xếp TRƯỚC để chiếm chỗ đẹp nhất; nhãn
# "Người N" mới là nhãn phải nhường.

LE_TRANH = 4              # px - khoảng cách tối thiểu giữa 2 nhãn
SO_LAN_TIM_TOI_DA = 60    # giới hạn số bước dò chỗ trống cho 1 nhãn


def _vuot_nhau(a, b, le: int = LE_TRANH) -> bool:
    """2 hình chữ nhật `(x0, y0, x1, y1)` có chồm nhau không.

    `le` là KHOẢNG CÁCH TỐI THIỂU phải chừa ra, nên phải kiểm
    `a.x1 + le <= b.x0`. Trước đây viết `a[2] <= b[0] + le` — tức cho phép
    2 nhãn CHỒM thật tới `le - 1` px (đo được 3 px trên khung 10 người),
    đúng thứ mục tiêu "0 cặp nhãn chồm" chặn.
    """
    return not (a[2] + le <= b[0] or b[2] + le <= a[0]
                or a[3] + le <= b[1] or b[3] + le <= a[1])


def _cho_nhat_trong(r, da_dat, le: int = LE_TRANH) -> bool:
    """`r` có chỗ trống giữa các hình chữ nhật đã đặt trong `da_dat` không."""
    return not any(_vuot_nhau(r, c, le) for c in da_dat)


def _kep_trong_khung(r, rong_kh: int, cao_kh: int):
    """Kẹp rect `r` vào trong khung hình. None nếu rect to hơn cả khung."""
    rong, cao = r[2] - r[0], r[3] - r[1]
    if rong > rong_kh or cao > cao_kh:
        return None
    x0 = max(0, min(int(r[0]), rong_kh - rong))
    y0 = max(0, min(int(r[1]), cao_kh - cao))
    return (x0, y0, x0 + rong, y0 + cao)


def _tim_khong_cham(r, da_dat, rong_kh: int, cao_kh: int,
                    le: int = LE_TRANH):
    """Dò chỗ trống cho rect `r`: XUỐNG/TRÊN trước, rồi mới sang TRÁI/PHẢI.

    Trả về rect mới (đã nằm trong khung, không chạm rect nào trong `da_dat`)
    hoặc None nếu hết chỗ.
    """
    x0, y0, x1, y1 = r
    rong, cao = x1 - x0, y1 - y0
    buoc_y, buoc_x = cao + le, rong + le
    for n in range(SO_LAN_TIM_TOI_DA):
        if n == 0:
            hang_y, cot_x = (y0,), (x0,)
        else:
            hang_y = (y0 + n * buoc_y, y0 - n * buoc_y)
            cot_x = tuple(v for v in (x0 - n * buoc_x, x0 + n * buoc_x)
                          if 0 <= v <= rong_kh - rong)
        for yy in hang_y:
            if yy < 0 or yy + cao > cao_kh:
                continue
            for xx in cot_x:
                rr = (xx, yy, xx + rong, yy + cao)
                if _cho_nhat_trong(rr, da_dat, le):
                    return rr
    return None


def _dat_nhan_khong_cham(anh, ve, font, muc: list[dict], cam=()) -> list:
    """Đặt vị trí nhãn sao cho KHÔNG nhãn nào chồm nhãn nào.

    `muc` = danh sách lệnh vẽ đã đo sẵn, mỗi lệnh có: `chu`, `mau`, `x`,
    `y_mong` (vị trí neo MỰC CHỮ mong muốn), `uu_tien`.
    `cam` = các vùng đã bị chiếm (bảng thống kê vùng, nhãn vùng canh, thẻ số
    đếm, dải nhãn đáy) - nhãn phải né. Lệnh nào không tìm được chỗ sẽ không
    có khoá "rect" -> bị ẩn.

    Hàm TRẢ VỀ list rect nhãn đã đặt: lượt vẽ sau lấy danh sách này làm `cam`
    nên không đường vẽ nào chồm lên đường vẽ trước.
    """
    rong_kh, cao_kh = anh.width, anh.height
    da_dat = [tuple(int(t) for t in v) for v in cam if v]
    moi: list[tuple] = []
    # Ưu tiên nhãn tên người quen; cùng nhóm thì xếp theo Y (trên xuống).
    thu_tu = sorted(
        range(len(muc)),
        key=lambda k: (0 if muc[k]["uu_tien"] else 1, muc[k]["y_mong"], muc[k]["x"]),
    )
    for k in thu_tu:
        m = muc[k]
        r = _kep_trong_khung(
            _do_o_nhan(ve, m["chu"], font, m["x"], m["y_mong"]),
            rong_kh, cao_kh)
        if r is None:
            continue                    # nhãn to hơn cả khung -> ẩn
        r = _tim_khong_cham(r, da_dat, rong_kh, cao_kh)
        if r is None:
            continue                    # hết chỗ -> ẨN, không vẽ đè lên nhau
        da_dat.append(r)
        moi.append(r)
        m["rect"] = r

    for m in muc:
        if "rect" in m:
            _ve_o_nhan(ve, m["rect"], m["chu"], m["mau"], font)
    return moi


def _muc_nhan(ve, font, chu, mau, x: float, y: float) -> dict:
    """Dựng 1 lệnh vẽ nhãn, neo mực chữ sát mép TRÊN khung (không che mặt)."""
    hop = ve.textbbox((0, 0), chu, font=font)
    return {"chu": chu, "mau": mau,
            "x": x + 2, "y_mong": y - 6 - (hop[3] - hop[1]), "uu_tien": False}


def ve_nguoi(anh, boxes, nhan: list[str], mau: list, cỡ_chu: int,
             do_day: int, uu_tien=None, cam=()) -> list:
    """Khung người + nhãn tên/độ tin cậy.

    Nhãn đặt TRÊN khung (không che mặt) và được thuật toán
    `_dat_nhan_khong_cham` giải quyết va chạm: không bao giờ có 2 nhãn chồng
    lên nhau. Ưu tiên giữ chỗ tốt cho nhãn tên người quen.
    `cam` = vùng đã bị chiếm (bảng thống kê, nhãn vùng canh, thẻ số đếm,
    dải nhãn đáy) - nhãn phải né. Trả về list rect nhãn người đã đặt.
    """
    from PIL import ImageDraw

    ve = ImageDraw.Draw(anh)
    font = _font(cỡ_chu)
    muc: list[dict] = []
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = [float(v) for v in box[:4]]
        x1, x1b = max(0.0, x1), min(float(anh.width), x2)
        y1, y1b = max(0.0, y1), min(float(anh.height), y2)
        if x1b - x1 < 4 or y1b - y1 < 4:
            continue
        m = mau[i] if i < len(mau) else MAU_NGUOI
        _khung(anh, x1, y1, x1b, y1b, m, do_day)
        chu = nhan[i] if i < len(nhan) else ""
        if not chu:
            continue
        muc_n = _muc_nhan(ve, font, chu, m, x1, y1)
        muc_n["uu_tien"] = (bool(uu_tien[i])
                            if uu_tien and i < len(uu_tien) else False)
        muc.append(muc_n)
    return _dat_nhan_khong_cham(anh, ve, font, muc, cam)


# --------------------------------------------------------------------------
# BANG THONG KE VUNG (de goc tren trai khung hinh)
# --------------------------------------------------------------------------

def _kich_bang_vung(anh, dong, cỡ_chu: int):
    """Đo khung bảng thống kê vùng mà CHƯA vẽ (để nhãn người né tránh).

    Rộng phải đủ cho CẢ nhãn lẫn giá trị (giá trí căn phải) + khe hở, nếu
    không giá trị sẽ đè lên nhãn.
    """
    from PIL import ImageDraw

    if not dong:
        return ()
    ve = ImageDraw.Draw(anh)
    font = _font(cỡ_chu)
    rong_nhan = 0
    rong_gia = 0
    for nhan, gia_tri in dong:
        rong_nhan = max(rong_nhan, ve.textbbox((0, 0), nhan, font=font)[2])
        rong_gia = max(rong_gia, ve.textbbox((0, 0), gia_tri, font=font)[2])
    rong = rong_nhan + rong_gia + 30      # 9px mỗi bên + 12px khe hở
    cao = (cỡ_chu + 9) * len(dong) + 12
    return (8, 8, 8 + rong, 8 + cao)


def ve_bang_vung(anh, dong, cỡ_chu: int):
    """Bảng thống kê vùng đè lên GÓC TRÊN TRÁI khung hình, nền bán trong.

    `dong` = list[(nhãn, giá trị)]. Vẽ SAU CÙNG nên nằm trên các khung người,
    luôn đọc được. Trả về vùng đã chiếm.
    """
    from PIL import Image, ImageDraw

    if not dong:
        return ()
    x0, y0, x1, y1 = _kich_bang_vung(anh, dong, cỡ_chu)
    rong, cao = x1 - x0, y1 - y0
    # nền bán trong: dán qua 1 mặt nạ alpha (không cần RGBA cho cả khung hình)
    anh.paste(Image.new("RGB", (rong, cao), (8, 14, 28)), (x0, y0),
              Image.new("L", (rong, cao), 170))
    ve = ImageDraw.Draw(anh)
    font = _font(cỡ_chu)
    ve.rectangle([x0, y0, x1, y1], outline=(56, 235, 116), width=2)
    y = y0 + 7
    for nhan, gia_tri in dong:
        ve.text((x0 + 9, y), nhan, font=font, fill=(148, 163, 184))
        hop = ve.textbbox((0, 0), gia_tri, font=font)
        ve.text((x1 - 9 - (hop[2] - hop[0]), y), gia_tri, font=font,
                fill=(248, 250, 252))
        y += cỡ_chu + 9
    return (x0, y0, x1, y1)


def ve_vat_the(anh, boxes, nhan: list[str], cỡ_chu: int, do_day: int,
               cam=()) -> list:
    """Khung vật thể khác (xe, chó, mèo...) - màu cam để phân biệt ngay.

    Nhãn vật thể đi qua CHUNG bộ tránh va chạm với nhãn người (`cam` = rect
    nhãn người đã đặt) nên không bao giờ đè lên nhãn người.
    """
    from PIL import ImageDraw

    ve = ImageDraw.Draw(anh)
    font = _font(cỡ_chu)
    muc: list[dict] = []
    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = [float(v) for v in box[:4]]
        x1, x1b = max(0.0, x1), min(float(anh.width), x2)
        y1, y1b = max(0.0, y1), min(float(anh.height), y2)
        if x1b - x1 < 4 or y1b - y1 < 4:
            continue
        _khung(anh, x1, y1, x1b, y1b, MAU_VAT_THE, do_day)
        chu = nhan[i] if i < len(nhan) else ""
        if chu:
            muc.append(_muc_nhan(ve, font, chu, MAU_VAT_THE, x1, y1))
    return _dat_nhan_khong_cham(anh, ve, font, muc, cam)


def _chu_the_dem(vao: int, ra: int) -> str:
    return f"VÀO: {vao} · RA: {ra}"


def _kich_the_dem(anh, chu: str, cỡ_chu: int):
    """Đo thẻ số đếm ở GÓC DƯỚI TRÁI (chưa vẽ) để nhãn người né tránh."""
    from PIL import ImageDraw

    ve = ImageDraw.Draw(anh)
    font = _font(cỡ_chu)
    hop = ve.textbbox((0, 0), chu, font=font)
    r = _do_o_nhan(ve, chu, font, 8, anh.height - 8 - (hop[3] - hop[1]))
    return _kep_trong_khung(r, anh.width, anh.height) or ()


def ve_vach_dem(anh, x: int, vao: int, ra: int, cỡ_chu: int, do_day: int,
                the_dem=()) -> None:
    """Vạch đếm ra/vào: vạch đứt trắng đậm + mũi tên chiều + thẻ số đếm.

    Vạch nằm đúng giữa khung hình, GIỐNG hệt `cam_ai_core` (start=(w/2,0),
    end=(w/2,h)) để số VÀO/RA trên GUI khớp với video kết quả.

    Thẻ số đếm đặt ở GÓC DƯỚI TRÁI, vẽ đúng theo rect `the_dem` đã đo sẵn
    (`_kich_the_dem`) - nhờ vậy nhãn người đã biết chỗ này và không vẽ đè lên.
    """
    from PIL import ImageDraw

    ve = ImageDraw.Draw(anh)
    h = anh.height
    buoc = max(20, do_day * 7)
    y = 0
    while y < h:                       # vạch đứt để không che mặt người
        ve.rectangle([x - do_day, y, x + do_day, min(h, y + buoc)],
                     fill=MAU_VACH)
        y += buoc * 2
    # tam giác chỉ hướng: VÀO = đi xuống (xanh), RA = đi lên (đỏ)
    r = max(7, do_day * 3)
    ve.polygon([(x, r * 2), (x - r, r), (x + r, r)], fill=(34, 197, 94))
    ve.polygon([(x, h - r * 2), (x - r, h - r), (x + r, h - r)],
               fill=(248, 113, 113))
    chu = _chu_the_dem(vao, ra)
    if not the_dem:
        the_dem = _kich_the_dem(anh, chu, cỡ_chu)
    if the_dem:
        _ve_o_nhan(ve, the_dem, chu, (15, 23, 42), _font(cỡ_chu))


def _mau_chu_vung(trang_thai: str, nguoi_trong_vung: int, nguoi_toi_da: int):
    """Màu + chữ của nhãn vùng theo trạng thái."""
    if trang_thai == "qua":
        return MAU_VUNG_QUA, f"VƯỢT NGƯỠNG {nguoi_toi_da} NGƯỜI"
    if trang_thai == "dung_lau":
        return MAU_VUNG_DUNG_LAU, f"ĐỨNG LÂU · {nguoi_trong_vung} NGƯỜI"
    if trang_thai == "co_nguoi":
        return MAU_VUNG_CO_NGUOI, f"CÓ NGƯỜI · {nguoi_trong_vung}"
    return MAU_VUNG_TRONG, "VÙNG CANH · TRỐNG"


def _dat_nhan_vung(anh, ve, font, chu, mau, xa, ya, xb, yb, cam):
    """Đặt NHÃN VÙNG sao cho vẫn BÁM trong vùng mà không chạm `cam`.

    Nhãn vùng phải nằm TRONG vùng đang canh (trôi đi xa thì người xem không
    biết chữ nói vùng nào) - nên nó lần theo mép trên từ trái sang phải rồi
    xuống dần. Không tìm được chỗ nào trong vùng thì trả về () để nhãn người
    khỏi phải né.
    """
    hop = ve.textbbox((0, 0), chu, font=font)
    rong = hop[2] - hop[0] + 2 * O_NHAN_DEM_X
    cao = hop[3] - hop[1] + 2 * O_NHAN_DEM_Y
    buoc_x = max(8, rong // 2)
    buoc_y = cao + 4
    for n in range(0, 14):                     # 0) mép trên -> 1) xuống dần
        y = ya + 4 + n * buoc_y
        if y + cao > yb - 2:
            break
        for k in range(0, 26):                 # trượt sang phải
            x = xa + 4 + k * buoc_x
            if x + rong > xb - 2:
                break
            r = (x, y, x + rong, y + cao)
            if _cho_nhat_trong(r, cam):
                _ve_o_nhan(ve, r, chu, mau, font)
                return tuple(r)
    return ()


def ve_vung_canh(anh, zone_px, trang_thai: str, nguoi_trong_vung: int,
                 nguoi_toi_da: int, cỡ_chu: int, do_day: int,
                 le_tren: int = 0, cam=()) -> tuple:
    """Khung vùng canh, ĐỔI MÀU + CHỮ theo trạng thái.

    trang_thai: "trong" | "co_nguoi" | "qua" | "dung_lau"
    `le_tren` = chiều cao vùng đã bị chiếm phía trên (bảng thống kê vùng).
    Nhãn vùng đi qua CHUNG bộ tránh va chạm với nhãn người: nó né `cam` và
    dải `le_tren`, rồi rect đã đặt được trả về cho nhãn người né tiếp ->
    không nhãn nào chồm nhãn nào.
    """
    from PIL import Image, ImageDraw

    x1, y1, x2, y2 = [int(v) for v in zone_px]
    xa, xb = min(x1, x2), max(x1, x2)
    ya, yb = min(y1, y2), max(y1, y2)
    mau, chu = _mau_chu_vung(trang_thai, nguoi_trong_vung, nguoi_toi_da)

    if trang_thai != "trong":          # nền mờ trong vùng để thấy rõ vùng đang canh
        vt = (xa, ya, xb, yb)
        rong, cao = max(1, vt[2] - vt[0]), max(1, vt[3] - vt[1])
        anh.paste(Image.new("RGB", (rong, cao), mau), vt[:2],
                  Image.new("L", (rong, cao), 40))
    ve = ImageDraw.Draw(anh)
    ve.rectangle([x1, y1, x2, y2], outline=(0, 0, 0), width=do_day + 3)
    ve.rectangle([x1, y1, x2, y2], outline=mau, width=do_day)

    vung_cam = list(cam)
    if le_tren:
        vung_cam.append((0, 0, anh.width, le_tren))
    return _dat_nhan_vung(anh, ve, _font(cỡ_chu), chu, mau,
                          xa, ya, xb, yb, vung_cam)


def _tach_badge(chu) -> list[str]:
    """Chuỗi gộp "A · B · C" -> list badge; list thì giữ nguyên."""
    if isinstance(chu, str):
        return [s.strip() for s in chu.split("·") if s.strip()]
    return [str(s).strip() for s in chu if str(s).strip()]


def _kich_dai_badge(anh, chu, cỡ_chu: int, le_trai: int = 0,
                    do_dai: int = 0) -> list:
    """Đo vị trí TỪNG badge ở đáy khung hình (chưa vẽ).

    Mỗi badge có nền RIÊNG và khe hở giữa các badge -> không dính chữ.
    Dải nằm CĂN GIỮA, lệch sang phải chỗ thẻ số đếm (`le_trai`); mọi badge
    cũng đi qua bộ tránh va chạm nên không badge nào đè badge nào.
    """
    from PIL import ImageDraw

    chu = _tach_badge(chu)
    if not chu:
        return []
    w, h = anh.width, anh.height
    ve = ImageDraw.Draw(anh)
    font = _font(cỡ_chu)
    khe = 10
    hop = [ve.textbbox((0, 0), s, font=font) for s in chu]
    tong = sum(t[2] - t[0] for t in hop) + khe * 2 * (len(chu) - 1)
    if do_dai:
        tong = min(tong, do_dai)
    cao = max(t[3] - t[1] for t in hop)
    x = max(le_trai, (w - tong) // 2)
    y = h - cao - 12
    cam = [(0, 0, le_trai, h)] if le_trai else []
    ra = []
    for s in chu:
        r = _kep_trong_khung(_do_o_nhan(ve, s, font, x, y), w, h)
        if r is None:
            continue
        r = _tim_khong_cham(r, cam, w, h)
        if r is None:
            continue
        cam.append(r)
        ra.append((r, s))
        x = r[2] + khe
    return ra


def ve_dai_badge(anh, cỡ_chu: int, da_do: list) -> None:
    """Vẽ dải badge đáy theo đúng rect đã đo ở `_kich_dai_badge`.

    Mỗi badge 1 nền + 1 viền riêng và cách nhau 10px -> nhìn tách bạch,
    không dính thành 1 thanh chữ chung.
    """
    from PIL import ImageDraw

    if not da_do:
        return
    ve = ImageDraw.Draw(anh)
    font = _font(cỡ_chu)
    for rect, s in da_do:
        _ve_o_nhan(ve, rect, s, (15, 23, 42), font)
        ve.rectangle(list(rect), outline=(100, 116, 139), width=1)


def ve_khung_hinh(frame, *, boxes_nguoi=(), nhan_nguoi=(), mau_nguoi=(),
                  uu_tien_nguoi=None, boxes_vat=(), nhan_vat=(), zone_px=None,
                  trang_thai_vung="trong", nguoi_trong_vung=0, nguoi_toi_da=0,
                  vao=0, ra=0, hien_khung=True, hien_nhan=True, hien_vach=True,
                  hien_vung=True, chu_dien=(), bang_vung=()):
    """Ve TOAN BO overlay len khung hinh. Tra ve khung hinh moi (BGR).

    Vao: `frame` ndarray BGR cua OpenCV. Ra: ndarray BGR da ve overlay.
    KHONG ve gi khi tat ca thuoc tinh "hien_*" deu False -> tra nguyen `frame`.

    `bang_vung` = list[(nhan, gia_tri)] - bang thong ke vung 5 dong o goc tren
    trai. `uu_tien_nguoi` = list[bool] - nhan co ten nguoi quen giu cho tuyet
    doi. `chu_dien` = list[str] (hoac 1 chuoi "A · B") - moi muc ve thanh 1
    BADGE rieng o day khung hinh.

    THU TU VE (quan trong - tranh nhan chong nhau):
      1) DO TRUOC mọi vung da bi chiem (bang thong ke, the so dem, dai badge
         day) ma CHUA ve - nhan nguoi phai tranh tat ca.
      2) Ve vach dem (duong thang) - ve truoc de khong cat ngan nhan.
      3) Nhan vung canh (dung cung bo tranh va cham) -> tra ve rect.
      4) Nhan nguoi -> tra ve rect -> nhan vat the tranh tiep.
      5) Dai badge + bang thong ke (bang ve CUOI CUNG nen luon doc duoc).
    """
    if not (hien_khung or hien_nhan or hien_vach or hien_vung or chu_dien
            or bang_vung):
        return frame
    if frame is None or frame.size == 0:
        return frame

    cao_nen = frame.shape[0]
    # 1 khung 432px = co so 1.0; video cao hon thi chu to tuong ung.
    sc = max(0.55, min(2.2, cao_nen / 432.0))
    cỡ_chu = max(11, int(15 * sc))
    do_day = max(2, int(3 * sc))

    rgb = cv_rgb(frame)

    # --- 1) KHAO TRUOC vung da chiem (chi DO, chua ve) --------------------
    cam: list[tuple] = []
    vung_bang = _kich_bang_vung(rgb, bang_vung, cỡ_chu) if bang_vung else ()
    if vung_bang:
        cam.append(vung_bang)
    the_dem = ()
    if hien_vach:
        the_dem = _kich_the_dem(rgb, _chu_the_dem(vao, ra), cỡ_chu)
        if the_dem:
            cam.append(the_dem)
    le_trai = (the_dem[2] + 10) if the_dem else 0
    dai_badge = (_kich_dai_badge(rgb, chu_dien, cỡ_chu, le_trai,
                                 int(frame.shape[1] * 0.62))
                 if chu_dien else [])
    cam.extend(r for r, _ in dai_badge)

    # --- 2) ve vach dem TRUOC: no la duong thang, ve sau se cat ngan cac
    # nhan (nhan vung canh) ma khong can gi den do pho ---
    if hien_vach:
        ve_vach_dem(rgb, int(frame.shape[1] / 2), vao, ra, cỡ_chu, do_day,
                    the_dem=the_dem)

    # --- 3) nhan vung canh (dung cung bo tranh va cham) --------------------
    vung_nhan = ()
    if hien_vung and zone_px is not None:
        vung_nhan = ve_vung_canh(rgb, zone_px, trang_thai_vung,
                                 nguoi_trong_vung, nguoi_toi_da, cỡ_chu,
                                 do_day,
                                 le_tren=vung_bang[3] if vung_bang else 0,
                                 cam=cam)
        if vung_nhan:
            cam.append(vung_nhan)

    # --- 4) khung + nhan nguoi, roi nhan vat the --------------------------
    if hien_khung:
        if len(boxes_nguoi):
            cam.extend(ve_nguoi(rgb, boxes_nguoi, list(nhan_nguoi),
                                list(mau_nguoi), cỡ_chu, do_day,
                                uu_tien=uu_tien_nguoi, cam=cam))
        if len(boxes_vat):
            ve_vat_the(rgb, boxes_vat, list(nhan_vat), cỡ_chu, do_day, cam=cam)

    # --- 5) ve dai badge + bang thong ke (bang ve CUOI CUNG) ---------------
    ve_dai_badge(rgb, cỡ_chu, dai_badge)
    if bang_vung:
        ve_bang_vung(rgb, bang_vung, cỡ_chu)
    return rgb_bgr(rgb)


def cv_rgb(frame_bgr):
    """ndarray BGR -> PIL RGB (copy, de ve khong lam hong frame goc)."""
    import numpy as np
    from PIL import Image

    return Image.fromarray(np.ascontiguousarray(frame_bgr[:, :, ::-1]))


def rgb_bgr(anh):
    """PIL RGB -> ndarray BGR."""
    import numpy as np

    return np.ascontiguousarray(np.asarray(anh)[:, :, ::-1])


def cat_anh_moi(frame, box, canh: int = 12, co_ban: bool = True):
    """Cat 1 anh crop VUONG (khong méo) quanh `box` co nhung viền.

    Dùng cho panel đối tượng. `co_ban`: có vẽ viền trắng cho dễ thấy nữa không.
    """
    import cv2
    import numpy as np

    if frame is None or frame.size == 0:
        return None
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in box[:4]]
    x1 -= canh
    y1 -= canh
    x2 += canh
    y2 += canh
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    canh_max = max(x2 - x1, y2 - y1)
    x1, x2 = cx - canh_max / 2.0, cx + canh_max / 2.0
    y1, y2 = cy - canh_max / 2.0, cy + canh_max / 2.0
    # canh vuong, dam bao khong tran ra khung hinh
    if canh_max > max(w, h):
        canh_max = float(max(w, h))
        x1, x2 = cx - canh_max / 2.0, cx + canh_max / 2.0
        y1, y2 = cy - canh_max / 2.0, cy + canh_max / 2.0
    x1 = max(0.0, min(x1, w - 1))
    y1 = max(0.0, min(y1, h - 1))
    x2 = min(float(w), x2)
    y2 = min(float(h), y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return None
    if co_ban:
        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                      (255, 255, 255), 2)
    return frame[int(y1):int(y2), int(x1):int(x2)].copy()


# --------------------------------------------------------------------------
# DU LIEU 1 THE
# --------------------------------------------------------------------------

@dataclass
class DoiTuong:
    """Mot the trong panel 'Do tuong phat hien'."""
    khoa: str                       # dinh danh duy nhat (lop + id theo doi)
    ten: str = ""                   # ten nguoi quen, hoac ten lop
    lop: str = ""                   # "Nguoi" | "Car" | ...
    tin_do: float = 0.0
    so_lan: int = 0                 # so lan XUAT HIEN (khong phai so khung hinh)
    la_quen: bool = False
    la_mat: bool = False            # anh la crop khuon mat (khong phai toan nguoi)
    jpeg: bytes = b""               # anh JPEG chua giai ma
    lan_cuoi: float = 0.0           # time.monotonic() lan cap nhat gan nhat
    the = None                      # widget, do PanelDoiTuong gan
    o_anh = None
    lbl_ten = None
    lbl_chi_tiet = None


# --------------------------------------------------------------------------
# ANH XEM TRUOC (THUMBNAIL) CHO THE VIDEO MAU
# --------------------------------------------------------------------------

def _duong_dan_thumb(ten_file: str) -> str:
    """Đường dẫn file cache của 1 ảnh xem trước.

    Khoá theo TÊN FILE + KÍCH THƯỚC, nên đổi kích thước thẻ là tự vẽ lại,
    còn video đổi nội dung mà giữ tên thì vẫn dùng cache cũ (chấp nhận được).
    """
    import hashlib

    # "v3" = phien ban cach chon khung. DOI ban dau thi doi so nay nen cache
    # cu (anh chon khum khac) khong bi dung lai.
    khoa = hashlib.md5(
        f"v3|{ten_file}|{RONG_THUMB}x{CAO_THUMB}".encode()).hexdigest()[:12]
    return os.path.join(APP_DIR_GUI, THUMB_CACHE, f"{khoa}.jpg")


def _diem_roi_noi(khung) -> float:
    """Đo 'độ có nội dung' của 1 khung hình (càng nhiều cạnh càng cao).

    Video nhiều lúc mở đầu lại quay chỗ trống (sàn, trần, tường trơn) - dùng
    làm ảnh xem trước thì người dùng thấy "video trống" dù video có nội dung.
    Nên chọn khung nào CHẬT nhất.
    """
    import cv2
    import numpy as np

    xam = cv2.cvtColor(khung, cv2.COLOR_BGR2GRAY)
    nho = cv2.resize(xam, (64, 36), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(nho, cv2.CV_64F).var()) + float(nho.mean()) * 0.01


def _khung_roi_noi(cap, fps: float, tong: int):
    """Chọn khung hình ĐÁNG ĐỂ LÀM ẢNH XEM TRƯỚC trong video.

    Thử vài vị trí (khoảng 1 giây, 1/3, 1/2, 2/3 video), lấy khung nào có
    nhiều nội dung nhất. Chi doc ~4 khung, ket qua duoc cache lai nen chi
    ton mot lan cho moi video.
    """
    import cv2

    # Thu nhieu vi tri de tranh chon nham khung toan san (sanh trong, tuong).
    # Chi doc ~10 khung MOT LAN, ket qua duoc cache lai nen khong ton gi la.
    ung = [fps]
    if tong > 1:
        ung += [tong * k / 10.0 for k in range(1, 10)]
    tot_nhat, diem_nhat = None, -1.0
    for giay in ung:
        if giay <= 0:
            continue
        chi_so = int(max(0, min(giay, tong - 1)))
        cap.set(cv2.CAP_PROP_POS_FRAMES, chi_so)
        ok, khung = cap.read()
        if not ok or khung is None:
            continue
        d = _diem_roi_noi(khung)
        if d > diem_nhat:
            diem_nhat, tot_nhat = d, khung
    if tot_nhat is None:                     # het thu -> quay lai dau video
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, tot_nhat = cap.read()
    return tot_nhat


def doc_thumb(duong_dan_video: str, thu_muc_cache: str):
    """Đọc 1 ảNH XEM TRƯỚC từ chính file video. Trả về PIL Image RGB.

    - CÓ CACHE: file cache đã tồn tại -> dùng luôn, KHÔNG mở video.
    - KHÔNG có cache: mở video, nảy ~1 giây, đọc 1 khung, thu nhỏ về RONG_THUMB
      x CAO_THUMB, lưu cache.
    - Video hỏng / không đọc được -> trả None (KHÔNG ném lỗi ra ngoài, để GUI
      còn sống; thẻ sẽ hiện ô xám "không đọc được").

    Gọi trên THREAD NÊN: có mở file + giải mã.
    """
    from PIL import Image

    if not duong_dan_video or not os.path.isfile(duong_dan_video):
        return None

    ten_file = os.path.basename(duong_dan_video)
    duong_cache = _duong_dan_thumb(ten_file)
    if os.path.isfile(duong_cache) and os.path.getsize(duong_cache) > 0:
        try:
            with Image.open(duong_cache) as im:
                return im.convert("RGB")
        except Exception:                                # noqa: BLE001
            pass                                        # cache hong -> doc lai

    try:
        import cv2

        cap = cv2.VideoCapture(duong_dan_video)
        if not cap.isOpened():
            return None
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            tong = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            khung = _khung_roi_noi(cap, fps, tong)
            if khung is None:
                return None
            cao_h, rong_h = khung.shape[:2]
            if rong_h <= 0 or cao_h <= 0:
                return None
            # Thu nho cho vua khung the, GIU NGUYEN ti le goc (khong keo meo).
            ty_le = min(RONG_THUMB / float(rong_h), CAO_THUMB / float(cao_h))
            rong_moi = max(1, int(round(rong_h * ty_le)))
            cao_moi = max(1, int(round(cao_h * ty_le)))
            nho = cv2.resize(khung, (rong_moi, cao_moi),
                             interpolation=cv2.INTER_AREA)
        finally:
            cap.release()

        # Phan du thia bang nen: canh chay giua, hai ben chua mau the.
        nen = Image.new("RGB", (RONG_THUMB, CAO_THUMB), (10, 14, 26))
        nen.paste(Image.fromarray(cv2.cvtColor(nho, cv2.COLOR_BGR2RGB)),
                  ((RONG_THUMB - rong_moi) // 2, (CAO_THUMB - cao_moi) // 2))
        try:
            os.makedirs(os.path.dirname(duong_cache), exist_ok=True)
            nen.save(duong_cache, "JPEG", quality=85)
        except Exception:                                # noqa: BLE001
            pass                                        # khong ghi duoc cache
        return nen
    except Exception:                                    # noqa: BLE001
        return None


# --------------------------------------------------------------------------
# PANEL DOI TUONG
# --------------------------------------------------------------------------

LOC_HET = "Tất cả"
LOC_NGUOI = "Người"
LOC_VAT_THE = "Vật thể khác"
LOC_QUEN = "Người quen"


class PanelDoiTuong(ctk.CTkFrame):
    """Panel gom ANH CROP của từng đối tượng phát hiện vào một chỗ.

    * Mỗi đối tượng = 1 thẻ: ảnh crop + tên lớp + tin cậy + số lần xuất hiện.
    * Lọc theo lớp (Tất cả / Người / Vật thể khác / Người quen) + chỉ hiện
      người quen.
    * Tối đa `SO_THE_TOI_DA` thẻ, thẻ mới đẩy thẻ cũ nhất.
    * Mỗi vòng cập nhật chỉ giai mã lại tối đa `SO_ANH_GIAI_MA_1_VONG` ảnh
      (đi vòng) -> không giật dù đang phân tích.
    * KHONG tự gọi after(): gui.py gọi `nhan_danh_sach()` trong vòng bơm
      duy nhất của nó.
    """

    SO_COT = 2

    def __init__(self, master, dich=None, font_nho=None, font_nho_bold=None):
        super().__init__(master, fg_color=MAU_PANEL["the"], corner_radius=BO_GOC_THE,
                         border_width=1, border_color=MAU_PANEL["vien"])
        self._dich = dich or (lambda s: s)
        self.font_nho = font_nho
        self.font_nho_bold = font_nho_bold

        self._the: dict[str, DoiTuong] = {}
        self._dang_gan: list[str] = []          # thu tu the dang hien tren luoi
        self._vong_anh = 0                     # con tro xoay vong de giai ma anh
        self._anh_dang_co = None               # giu tham chieu ImageTk

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- tieu de ---
        tieu_de = ctk.CTkFrame(self, fg_color="transparent")
        tieu_de.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        tieu_de.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tieu_de, text="Đối tượng phát hiện",
                     font=self.font_nho_bold, text_color=MAU_PANEL["chu"],
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.lbl_dem = ctk.CTkLabel(tieu_de, text=f"0 / {SO_THE_TOI_DA}",
                                    font=self.font_nho,
                                    text_color=MAU_PANEL["chu_phu"], anchor="e")
        self.lbl_dem.grid(row=0, column=1, sticky="e")

        # --- bo loc ---
        loc = ctk.CTkFrame(self, fg_color="transparent")
        loc.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 4))
        loc.grid_columnconfigure(0, weight=1)
        self.v_loc = ctk.StringVar(value=LOC_HET)
        self.om_loc = ctk.CTkOptionMenu(loc, values=[LOC_HET, LOC_NGUOI,
                                                    LOC_VAT_THE, LOC_QUEN],
                                        variable=self.v_loc, width=120,
                                        height=26, font=self.font_nho,
                                        command=self._loc_doi)
        self.om_loc.grid(row=0, column=0, sticky="w")
        self.v_chi_quen = ctk.StringVar(value="0")
        self.chk_quen = ctk.CTkCheckBox(
            loc, text="Chỉ người quen", variable=self.v_chi_quen,
            font=self.font_nho, command=self._loc_doi, onvalue="1", offvalue="0"
        )
        self.chk_quen.grid(row=0, column=1, sticky="e")

        # --- lưới thẻ ---
        self.lưới = ctk.CTkScrollableFrame(self, fg_color=MAU_PANEL["nen"],
                                           corner_radius=6)
        self.lưới.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        for cot in range(self.SO_COT):
            self.lưới.grid_columnconfigure(cot, weight=1, uniform="the")

        self.lbl_rong = ctk.CTkLabel(self, text="Chưa có đối tượng nào",
                                     font=self.font_nho,
                                     text_color=MAU_PANEL["chu_phu"])
        self.lbl_rong.grid(row=3, column=0, pady=(0, 10))

    # ------------------------------------------------------------ bo loc

    def _loc_doi(self, _gia_tri=None) -> None:
        self._ve_lai()

    def _pass_loc(self, t: DoiTuong) -> bool:
        if self.v_chi_quen.get() == "1" and not t.la_quen:
            return False
        loc = self.v_loc.get()
        if loc == LOC_NGUOI:
            return t.lop == "Nguoi"
        if loc == LOC_VAT_THE:
            return t.lop != "Nguoi"
        if loc == LOC_QUEN:
            return t.la_quen
        return True

    # ------------------------------------------------------------ cap nhat

    def nhan_danh_sach(self, danh_sach: list[dict]) -> None:
        """CHAY TREN LUONG UI. Nạp danh sách đối tượng mới từ luồng phân tích.

        Mỗi phần tử: {khoa, ten, lop, tin_do, la_quen, la_mat, jpeg}
        `so_lan` do panel tự đếm: +1 mỗi lần đối tượng XUẤT HIỆN LẠI
        (tức là vừa biến mất ở vòng trước rồi xuất hiện lại).
        """
        if not danh_sach:
            self._co_mat()
            return

        co_trong = {d["khoa"] for d in danh_sach}
        truoc = set(self._dang_thay)
        for d in danh_sach:
            khoa = d["khoa"]
            the = self._the.get(khoa)
            if the is None:
                the = DoiTuong(khoa=khoa, so_lan=0)
                self._the[khoa] = the
            if khoa not in truoc:
                the.so_lan += 1                      # xuất hiện lại -> +1 lần
            the.ten = d.get("ten", "") or d.get("lop", "")
            the.lop = d.get("lop", "")
            the.tin_do = float(d.get("tin_do", 0.0) or 0.0)
            the.la_quen = bool(d.get("la_quen", False))
            the.la_mat = bool(d.get("la_mat", False))
            if d.get("jpeg"):
                the.jpeg = d["jpeg"]
                the.lan_cuoi = time.monotonic()
        self._dang_thay = co_trong

        self._cat_bua(toi_da=SO_THE_TOI_DA)
        # TAO THE TRUOC, giai ma anh sau: neu dao lai, the moi tao ra o luot
        # nay chua kip giai ma -> nhin thay the trong khong co anh.
        self._ve_lai()
        self._giai_ma_anh_bgio()
        self._lam_moi_chu_the()

    _dang_thay: set = set()

    def _cat_bua(self, toi_da: int) -> None:
        """Giữ tối đa `toi_da` thẻ; thẻ mới nhất được ưu tiên giữ lại."""
        if len(self._the) <= toi_da:
            return
        # thứ tự chèn: giữ lại toi_da thẻ có lan_cuoi mới nhất
        xep = sorted(self._the.items(), key=lambda kv: kv[1].lan_cuoi,
                     reverse=True)
        for khoa, the in xep[toi_da:]:
            if the.the is not None:
                the.the.grid_remove()
                try:
                    the.the.destroy()
                except Exception:                        # noqa: BLE001
                    pass
            self._the.pop(khoa, None)

    def _giai_ma_anh_bgio(self) -> None:
        """Giải mã tối đa N ảnh mỗi vòng, đi vòng - không bao giờ decode hết."""
        if not self._the:
            return
        can = [t for t in self._the.values() if t.jpeg and t.the is not None]
        if not can:
            return
        can.sort(key=lambda t: t.lan_cuoi)
        for i in range(min(SO_ANH_GIAI_MA_1_VONG, len(can))):
            t = can[(self._vong_anh + i) % len(can)]
            if self._do_anh(t):
                self._vong_anh = (self._vong_anh + i + 1) % len(can)

    def _do_anh(self, t: DoiTuong) -> bool:
        """Giải mã 1 ảnh crop và đưa vào thẻ (giữ đúng tỉ lệ, nền đen)."""
        if not t.jpeg or t.o_anh is None:
            return False
        try:
            import io

            from PIL import Image, ImageTk

            img = Image.open(io.BytesIO(t.jpeg)).convert("RGB")
            img.thumbnail((BE_THE_ANH, BE_THE_ANH), Image.LANCZOS)
            nen = Image.new("RGB", (BE_THE_ANH, BE_THE_ANH), (8, 12, 22))
            nen.paste(img, ((BE_THE_ANH - img.width) // 2,
                            (BE_THE_ANH - img.height) // 2))
            tk_img = ImageTk.PhotoImage(nen)
        except Exception:                                # noqa: BLE001
            return False
        t.o_anh.configure(image=tk_img, text="")
        t._tk = tk_img                                  # giu tham chieu!
        return True

    # ------------------------------------------------------------ ve the

    def _ve_lai(self) -> None:
        """Đặt lại vị trí các thẻ theo bộ lọc hiện tại (chỉ khi thay đổi)."""
        hien = [t for t in self._the.values() if self._pass_loc(t)]
        khoa_hien = [t.khoa for t in hien]
        if khoa_hien == self._dang_gan:
            return
        for khoa in self._dang_gan:
            if khoa not in khoa_hien:
                the = self._the.get(khoa)
                if the is not None and the.the is not None:
                    the.the.grid_remove()
        for i, t in enumerate(hien):
            the = self._tao_the(t)
            the.grid(row=i // self.SO_COT, column=i % self.SO_COT,
                     sticky="nsew", padx=4, pady=4)
        self._dang_gan = khoa_hien
        self._cap_nhat_dem(len(hien))

    def _tao_the(self, t: DoiTuong) -> ctk.CTkFrame:
        if t.the is not None:
            return t.the
        the = ctk.CTkFrame(self.lưới, fg_color=MAU_PANEL["the_phu"],
                           corner_radius=6, border_width=1,
                           border_color=MAU_PANEL["vien"])
        t.the = the
        the.grid_columnconfigure(0, weight=1)
        t.o_anh = ctk.CTkLabel(the, text="...", width=BE_THE_ANH,
                               height=BE_THE_ANH,
                               text_color=MAU_PANEL["chu_phu"], font=self.font_nho)
        t.o_anh.grid(row=0, column=0, padx=4, pady=(4, 0))
        t.lbl_ten = ctk.CTkLabel(the, text=t.ten or t.lop, anchor="w",
                                 font=self.font_nho_bold,
                                 text_color=MAU_PANEL["chu"], wraplength=BE_THE_ANH)
        t.lbl_ten.grid(row=1, column=0, sticky="ew", padx=6, pady=(3, 0))
        t.lbl_chi_tiet = ctk.CTkLabel(the, text="", anchor="w",
                                      font=self.font_nho,
                                      text_color=MAU_PANEL["chu_phu"])
        t.lbl_chi_tiet.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 4))
        return the

    def _cap_nhat_dem(self, so_hien: int) -> None:
        self.lbl_dem.configure(text=f"{so_hien} / {len(self._the)}")
        if self._the:
            self.lbl_rong.grid_remove()
        else:
            self.lbl_rong.grid()

    def _lam_moi_chu_the(self) -> None:
        """Cập nhật chữ trên thẻ (tên + tin cậy + số lần), có dấu 'đã khuất'."""
        now = time.monotonic()
        for t in self._the.values():
            if t.the is None or t.lbl_chi_tiet is None:
                continue
            chu = self._chi_tiet(t)
            if now - t.lan_cuoi > KHOANG_QUANG and t.lan_cuoi > 0:
                chu += " · đã khuất"
            if getattr(t, "_chu_ten_cuoi", None) != (t.ten or t.lop):
                t.lbl_ten.configure(text=t.ten or t.lop)
                t._chu_ten_cuoi = t.ten or t.lop
            if getattr(t, "_chu_chi_cuoi", None) != chu:
                t.lbl_chi_tiet.configure(text=chu)
                t._chu_chi_cuoi = chu

    def _chi_tiet(self, t: DoiTuong) -> str:
        phan = [f"{t.tin_do * 100:.0f}%", f"{t.so_lan} lần"]
        if t.la_quen:
            phan.insert(0, "QUEN")
        if t.la_mat:
            phan.append("mặt")
        return " · ".join(phan)

    def _co_mat(self) -> None:
        """Không có đối tượng nào trong khung hình lần này."""
        for t in self._the.values():
            if t.the is not None:
                t.the.grid_remove()
        self._dang_gan = []
        self._cap_nhat_dem(0)

    # ------------------------------------------------------------ tien ich

    def xoa_het(self) -> None:
        for t in list(self._the.values()):
            if t.the is not None:
                try:
                    t.the.destroy()
                except Exception:                        # noqa: BLE001
                    pass
        self._the.clear()
        self._dang_gan = []
        self._dang_thay = set()
        self._cap_nhat_dem(0)


# --------------------------------------------------------------------------
# DANH SACH SU KIEN (TIMELINE) - COT PHAI CUA GIAO DIEN
# --------------------------------------------------------------------------
# Theo mau tham chieu: moi su kien = 1 THE, co anh crop THAT cua nguoi do +
# gio + ten + do tin cay + loai su kien + gioi + khuau trang. The moi nhat
# luon o DUNG DAU danh sach (gui.py giu danh sach roi day xuong).

# Mau theo loai su kien: vao = xanh, ra = cam, vi pham/dung lau = do.
MAU_SU_KIEN = {
    "vao_vung": "#22C55E",        # xanh - vao vung
    "ra_vung": "#F59E0B",         # cam - ra vung
    "dung_lau": "#EF4444",        # do - dung lau qua nguong
    "vuot_nguong": "#EF4444",     # do - vuot nguong nguoi
    "phat_hien_moi": "#38BDF8",   # xanh duong - nguoi moi xuat hien
    "qua_vach_vao": "#22C55E",
    "qua_vach_ra": "#F59E0B",
}
TEN_SU_KIEN = {
    "vao_vung": "Vào vùng",
    "ra_vung": "Ra vùng",
    "dung_lau": "Đứng lâu",
    "vuot_nguong": "Vượt ngưỡng",
    "phat_hien_moi": "Phát hiện mới",
    "qua_vach_vao": "Qua vạch (vào)",
    "qua_vach_ra": "Qua vạch (ra)",
}
SO_SU_KIEN_TOI_DA = 60           # giu toi da bao nhieu the su kien
BE_ANH_SU_KIEN = 72              # canh anh crop trong the su kien


class PanelSuKien(ctk.CTkFrame):
    """Danh sach SU KIEN dang chay, moi su kien 1 the, moi nhat len dau.

    KHONG tu `after()`: gui.py goi `them_su_kien()` trong vong bom hang doi.
    KHONG tu `after()` va KHONG goi tu thread nen.
    """

    def __init__(self, master, dich=None, font_nho=None, font_nho_bold=None):
        super().__init__(master, fg_color=MAU_PANEL["the"], corner_radius=BO_GOC_THE,
                         border_width=1, border_color=MAU_PANEL["vien"])
        self._dich = dich or (lambda s: s)
        self.font_nho = font_nho
        self.font_nho_bold = font_nho_bold

        self._the: list[ctk.CTkFrame] = []
        self._tk: list = []                 # giu tham chieu ImageTk

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        tieu_de = ctk.CTkFrame(self, fg_color="transparent")
        tieu_de.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 0))
        tieu_de.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(tieu_de, text="Danh sách sự kiện",
                     font=self.font_nho_bold, text_color=MAU_PANEL["chu"],
                     anchor="w").grid(row=0, column=0, sticky="w")
        self.lbl_dem = ctk.CTkLabel(tieu_de, text="0",
                                    font=self.font_nho,
                                    text_color=MAU_PANEL["chu_phu"], anchor="e")
        self.lbl_dem.grid(row=0, column=1, sticky="e")

        self.cuon = ctk.CTkScrollableFrame(self, fg_color=MAU_PANEL["nen"],
                                           corner_radius=6)
        self.cuon.grid(row=1, column=0, sticky="nsew", padx=8, pady=(6, 8))
        self.cuon.grid_columnconfigure(0, weight=1)

        self.lbl_rong = ctk.CTkLabel(
            self, text="Chưa có sự kiện nào", font=self.font_nho,
            text_color=MAU_PANEL["chu_phu"])
        self.lbl_rong.grid(row=2, column=0, pady=(0, 10))

    # ---------------------------------------------------------------- them

    def them_su_kien(self, su_kien: dict) -> None:
        """CHAY TREN LUONG UI. Them 1 the su kien vao DUNG DAU danh sach.

        `su_kien`: {loai, ten, tin_do, gioi, khuau_trang, gio, jpeg}
        """
        the = self._tao_the(su_kien)
        # Moi nhat len dau -> day lai tat ca the (thu tu trong `_the`).
        self._the.insert(0, the)
        self._ve_lai()
        self._cat_bua()

    def _tao_the(self, s: dict) -> ctk.CTkFrame:
        loai = s.get("loai", "phat_hien_moi")
        mau = MAU_SU_KIEN.get(loai, "#38BDF8")
        the = ctk.CTkFrame(self.cuon, fg_color=MAU_PANEL["the_phu"],
                           corner_radius=6, border_width=1,
                           border_color=MAU_PANEL["vien"])
        the.grid_columnconfigure(1, weight=1)

        # --- COT TRAI: anh crop THAT cua nguoi ---
        o_anh = ctk.CTkLabel(the, text="", width=BE_ANH_SU_KIEN,
                             height=BE_ANH_SU_KIEN,
                             fg_color=MAU_PANEL["nen"])
        o_anh.grid(row=0, column=0, rowspan=4, sticky="n", padx=(6, 8), pady=6)
        self._gan_anh(o_anh, s.get("jpeg"))

        # --- COT PHAI: cac dong chu ---
        tin_do = float(s.get("tin_do", 0.0) or 0.0)
        phan_tram = f"{tin_do * 100:.0f}%" if 0.0 < tin_do <= 1.0 else f"{tin_do:.0f}%"
        ctk.CTkLabel(the, text=f"{s.get('gio', '')}  ·  {phan_tram}",
                     font=self.font_nho_bold, text_color=mau,
                     anchor="w").grid(row=0, column=1, sticky="ew",
                                      padx=(0, 6), pady=(6, 0))
        ctk.CTkLabel(the, text=s.get("ten", "") or "Người lạ",
                     font=self.font_nho_bold, text_color=MAU_PANEL["chu"],
                     anchor="w").grid(row=1, column=1, sticky="ew",
                                      padx=(0, 6))
        ctk.CTkLabel(the, text=f"Event: {TEN_SU_KIEN.get(loai, loai)}",
                     font=self.font_nho, text_color=MAU_PANEL["chu"],
                     anchor="w").grid(row=2, column=1, sticky="ew",
                                      padx=(0, 6))
        ctk.CTkLabel(the,
                     text=f"Gender: {s.get('gioi', 'Chưa rõ')}  ·  "
                          f"Mask: {s.get('khuau_trang', 'Chưa rõ')}",
                     font=self.font_nho, text_color=MAU_PANEL["chu_phu"],
                     anchor="w").grid(row=3, column=1, sticky="ew",
                                      padx=(0, 6), pady=(0, 6))
        return the

    def _gan_anh(self, o_anh, jpeg: bytes | None) -> None:
        """Gan anh crop that vao o. KHONG giai ma lai nhieu lan 1 vong."""
        if not jpeg:
            return
        try:
            import io

            from PIL import Image, ImageTk

            img = Image.open(io.BytesIO(jpeg)).convert("RGB")
            img.thumbnail((BE_ANH_SU_KIEN, BE_ANH_SU_KIEN), Image.LANCZOS)
            nen = Image.new("RGB", (BE_ANH_SU_KIEN, BE_ANH_SU_KIEN), (8, 12, 22))
            nen.paste(img, ((BE_ANH_SU_KIEN - img.width) // 2,
                            (BE_ANH_SU_KIEN - img.height) // 2))
            tk_img = ImageTk.PhotoImage(nen)
        except Exception:                                # noqa: BLE001
            return
        o_anh.configure(image=tk_img)
        self._tk.append(tk_img)                 # giu tham chieu!
        if len(self._tk) > SO_SU_KIEN_TOI_DA:
            self._tk.pop(0)

    def _ve_lai(self) -> None:
        for dong, the in enumerate(self._the):
            the.grid(row=dong, column=0, sticky="ew", padx=2, pady=2)
        if self._the:
            self.lbl_rong.grid_remove()
        else:
            self.lbl_rong.grid()
        self.lbl_dem.configure(text=str(len(self._the)))

    def _cat_bua(self) -> None:
        while len(self._the) > SO_SU_KIEN_TOI_DA:
            the = self._the.pop()
            try:
                the.destroy()
            except Exception:                            # noqa: BLE001
                pass

    def xoa_het(self) -> None:
        for the in self._the:
            try:
                the.destroy()
            except Exception:                            # noqa: BLE001
                pass
        self._the.clear()
        self._tk.clear()
        self._ve_lai()


# --------------------------------------------------------------------------
# LUOI THE VIDEO MAU (ANH XEM TRUOC THAT)
# --------------------------------------------------------------------------

class TheVideoMau(ctk.CTkFrame):
    """1 the video mau: ANH XEM TRUOC THAT + ten ngan + dong mo ta.

    Bam vao the = chon luon (mot cham, khong can bam nut rieng).
    Vien sang = the dang duoc chon.

    KHONG tu `after()`: gui.py goi `dem_anH_ve()` trong vong bom hang doi.
    """

    def __init__(self, master, chi_so, ten, mo_ta, dich=None, font_nho=None,
                 font_nho_bold=None, command=None):
        super().__init__(master, fg_color=MAU_PANEL["the_phu"],
                         corner_radius=BO_GOC_THE, border_width=2,
                         border_color=MAU_PANEL["vien"])
        self._dich = dich or (lambda s: s)
        self.font_nho = font_nho
        self.font_nho_bold = font_nho_bold
        self.chi_so = chi_so
        self._command = command
        self._tk = None
        self.dang_chon = False
        self._ten = ten
        self._mo_ta = mo_ta

        self.grid_columnconfigure(0, weight=1)
        # O anh: khi chua co anh (chua doc xong / doc loi) hien chu "..."
        self.o_anh = ctk.CTkLabel(self, text="…", width=RONG_THUMB,
                                  height=CAO_THUMB,
                                  fg_color=MAU_PANEL["nen"], text_color="#5A6B85",
                                  font=self.font_nho)
        self.o_anh.grid(row=0, column=0, padx=4, pady=(3, 0))
        self.lbl_ten = ctk.CTkLabel(self, text="", anchor="w",
                                    font=self.font_nho_bold,
                                    text_color=MAU_PANEL["chu"],
                                    wraplength=RONG_THUMB)
        self.lbl_ten.grid(row=1, column=0, sticky="ew", padx=6, pady=(3, 0))
        self.lbl_mo_ta = ctk.CTkLabel(self, text="", anchor="w",
                                      font=self.font_nho,
                                      text_color=MAU_PANEL["chu_phu"],
                                      wraplength=RONG_THUMB)
        self.lbl_mo_ta.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 3))

        self.lam_moi_chu()
        self.bind("<Button-1>", self._bam)
        for w in (self.o_anh, self.lbl_ten, self.lbl_mo_ta):
            w.bind("<Button-1>", self._bam)
            w.configure(cursor="hand2")

    def _bam(self, _e=None) -> None:
        if self._command is not None:
            self._command(self.chi_so)

    def lam_moi_chu(self) -> None:
        """Dua lai chu sau khi doi ngon ngu."""
        self.lbl_ten.configure(text=self._dich(self._ten))
        self.lbl_mo_ta.configure(text=self._dich(self._mo_ta))

    def dat_chon(self, chon: bool) -> None:
        self.dang_chon = bool(chon)
        self.configure(
            border_color=MAU_PANEL["canh"] if chon else MAU_PANEL["vien"],
            fg_color="#31405C" if chon else MAU_PANEL["the_phu"],
        )

    def dat_anh(self, tk_anh) -> None:
        """Dat anh xem truoc. `tk_anh` = ImageTk.PhotoImage hoac None = loi."""
        if tk_anh is None:
            # Video hong / khong doc duoc: o xam co chu, khong de trong.
            self.o_anh.configure(text="không đọc được", image=None,
                                 text_color=MAU_PANEL["chu_phu"])
            return
        self._tk = tk_anh                    # giu tham chieu!
        self.o_anh.configure(image=tk_anh, text="")


class LuoiVideoMau(ctk.CTkFrame):
    """Luoi the video mau co anh xem truoc. Moi the = 1 video.

    Anh duoc DOC TREN THREAD NEN roi day vao hang doi (khong giu widget Tk o
    thread nen). gui.py goi `dat_anh()` trong vong bom hang doi: tao
    PhotoImage va gan vao the - day la viec RHE (doc file nho da san).
    """

    SO_COT = 2

    def __init__(self, master, danh_sach, dich=None, font_nho=None,
                 font_nho_bold=None, command=None, so_cot=None):
        super().__init__(master, fg_color="transparent")
        self._dich = dich or (lambda s: s)
        self.font_nho = font_nho
        self.font_nho_bold = font_nho_bold
        self._command = command
        self._the: dict[int, TheVideoMau] = {}
        self._cho_doc = 0
        # So video mau da vuot so the vua kip cua cua so (xem VIDEO_MAU).
        # Xep luoi theo SO_COT se ep moi the lai nho den khong doc noi.
        # Vi vay: THE CO DINH KICH THUOC + DAI CUON NGANG - them bao nhieu video
        # mau cung khong lam nho the, khong lam cua so bi tran.
        self.SO_COT = int(so_cot) if so_cot else self.SO_COT
        self.RONG_THE = RONG_THUMB + 18
        self.CAO_DAI = CAO_THUMB + 64

        if not self._co_video(danh_sach):
            ctk.CTkLabel(
                self, text="Chưa có video mẫu nào", font=self.font_nho,
                text_color=MAU_PANEL["chu_phu"], anchor="w",
            ).pack(anchor="w", pady=2)
            return

        self.cuon = ctk.CTkScrollableFrame(
            self, orientation="horizontal", height=self.CAO_DAI,
            fg_color="transparent", bg_color="transparent",
            scrollbar_button_color=MAU_PANEL["vien"],
        )
        self.cuon.pack(fill="x", expand=False)

        for i, (_ten_day_du, ten_ngan, mo_ta, ten_file, _dl) in enumerate(danh_sach):
            the = TheVideoMau(
                self.cuon, i, ten_ngan, mo_ta, dich=self._dich, font_nho=font_nho,
                font_nho_bold=font_nho_bold, command=self._bam,
            )
            the.configure(width=self.RONG_THE)
            the.grid(row=0, column=i, padx=3, pady=3)
            self._the[i] = the
            # Chi tao the cho video that su co tren dia.
            if os.path.isfile(os.path.join(APP_DIR_GUI, "video_mau", ten_file)):
                self._cho_doc += 1

    def _co_video(self, danh_sach) -> bool:
        """Thu muc video_mau co that khong (rỗng / thiếu -> False)."""
        thu_muc = os.path.join(APP_DIR_GUI, "video_mau")
        if not os.path.isdir(thu_muc):
            return False
        return any(os.path.isfile(os.path.join(thu_muc, m[3])) for m in danh_sach)

    def _bam(self, chi_so: int) -> None:
        if self._command is not None:
            self._command(chi_so)

    def dat_chon(self, chi_so: int) -> None:
        for i, the in self._the.items():
            the.dat_chon(i == chi_so)

    def lam_moi_chu(self) -> None:
        for the in self._the.values():
            the.lam_moi_chu()

    def con_cho_doc(self) -> int:
        return self._cho_doc

    def dat_anh(self, chi_so: int, tk_anh) -> None:
        the = self._the.get(chi_so)
        if the is None:
            return
        the.dat_anh(tk_anh)
        if self._cho_doc > 0:
            self._cho_doc -= 1