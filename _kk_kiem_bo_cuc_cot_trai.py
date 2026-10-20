# -*- coding: utf-8 -*-
"""
CamAI - KIEM CHUNG BO CUC 4 MUC LON cua cot trai (v3.5).

Kiem tra:
  [1] Dung 4 MUC LON, dung ten + dung mo ta 1 dong
  [2] CHI 1 muc lon mo tai mot thoi (mo muc lon nay -> cac muc lon khac dong)
  [3] MUI TEN XOAY: glyph doi giua ChevronRight (E76C) va ChevronDown (E70D)
  [4] Moi muc lon chua DUNG cac muc con (khong mat, khong thua)
  [5] BAN DICH TIENG ANH cho 4 tieu de + 4 mo ta
  [6] BAM THE VIDEO MAU van chon duoc video (ten + mo ta tieng Viet co dau)
  [7] 4 TINH NANG BAN 3.3 con nguyen: 2 o xem video + 3 nut dac biet

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_kiem_bo_cuc_cot_trai.py
"""

from __future__ import annotations

import os
import sys
import time
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

_REAL_STDOUT = sys.stdout
try:
    _REAL_STDOUT.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


def in_ky(*args) -> None:
    print(*args, file=_REAL_STDOUT, flush=True)


CHEVRON_PHAI = "\ue76c"       # ChevronRight
CHEVRON_XUONG = "\ue70d"      # ChevronDown

MUC_LON = [
    ("NGUỒN", "Chọn video cần phân tích và nơi lưu kết quả"),
    ("PHÂN TÍCH", "Bật các bước nhận diện: người, mặt, ra vào"),
    ("BIỂN SỐ & ẢNH", "Đọc biển số xe và tự chụp ảnh sự kiện"),
    ("CẢNH BÁO & MÔ HÌNH", "Chuông/hộp thoại khi có người lạ, và thông tin AI"),
]

# Muc con thuoc muc lon nao (dung thu tu tren man hinh).
MUC_CON = {
    "NGUỒN": [],
    "PHÂN TÍCH": ["Phát hiện người", "Nhận diện khuôn mặt", "Đếm ra vào",
                  "Canh vùng", "Lưu clip khi có sự kiện", "Thêm vật thể khác",
                  "Nhận người ở xa (chậm hơn)"],
    "BIỂN SỐ & ẢNH": ["Đọc biển số xe", "Tự chụp ảnh khi có sự kiện"],
    "CẢNH BÁO & MÔ HÌNH": ["Cảnh báo (gửi tin ra ngoài)", "Thông tin mô hình AI",
                           "Máy này chạy bằng gì"],
}


def chay() -> int:
    import customtkinter as ctk

    from gui import CamAIGui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(1.0)
    app.update()

    ket_qua = []

    # ------------------------------------------------------- [1] 4 MUC LON
    in_ky("=" * 78)
    in_ky("KIEM CHUNG BO CUC 4 MUC LON - COT TRAI")
    in_ky("=" * 78)
    in_ky("")
    in_ky("[1] DUNG 4 MUC LON, DUNG TEN + DUNG MO TA 1 DONG")
    ds = getattr(app, "_ds_nhom_lon", [])
    in_ky(f"  so muc lon = {len(ds)}")
    ok1 = len(ds) == 4
    for idx, (ten, mo_ta) in enumerate(MUC_LON):
        if idx >= len(ds):
            ok1 = False
            continue
        nlon = ds[idx]
        ten_hien = str(nlon.lbl_ten.cget("text"))
        mo_ta_hien = str(nlon.lbl_mo_ta.cget("text"))
        # MO TA PHAI NAM TREN 1 DUNG: so dong thuc te cua label.
        so_dong = nlon.lbl_mo_ta.cget("wraplength")
        in_ky(f"    {ten_hien!r:24s} mo_ta={mo_ta_hien!r}")
        if ten_hien != ten or mo_ta_hien != mo_ta:
            ok1 = False
            in_ky(f"      -> SAI (mong doi {ten!r} / {mo_ta!r})")
    in_ky(f"  -> {'PASS' if ok1 else 'FAIL'}")
    ket_qua.append(("4 muc lon dung ten + mo ta", ok1))

    # ------------------------------------- [2] CHI 1 MUC LON MO TAI MOT LUC
    in_ky("")
    in_ky("[2] CHI 1 MUC LON MO TAI MOT LUC")
    ok2 = True
    for idx, nlon in enumerate(ds):
        nlon.dat_mo(True)
        app.update()
        app.update_idletasks()
        so_mo = [d.lbl_ten.cget("text") for d in ds if d.dang_mo]
        in_ky(f"    mo muc lon #{idx} -> dang mo: {so_mo}")
        if len(so_mo) != 1:
            ok2 = False
    in_ky(f"  -> {'PASS' if ok2 else 'FAIL'}")
    ket_qua.append(("chi 1 muc lon mo tai mot thoi", ok2))

    # ------------------------------------------------ [3] MUI TEN XOAY
    in_ky("")
    in_ky("[3] MUI TEN XOAY KHI MO / DONG")
    ok3 = True
    for nlon in ds:
        nlon.dat_mo(False)
        app.update()
        glyph_dong = str(nlon.btn_mo.cget("text"))
        nlon.dat_mo(True)
        app.update()
        glyph_mo = str(nlon.btn_mo.cget("text"))
        in_ky(f"    {nlon.lbl_ten.cget('text')!r:24s} "
              f"dong={glyph_dong!r} (U+{ord(glyph_dong):04X})  "
              f"mo={glyph_mo!r} (U+{ord(glyph_mo):04X})")
        if glyph_dong != CHEVRON_PHAI or glyph_mo != CHEVRON_XUONG:
            ok3 = False
    in_ky(f"  -> {'PASS' if ok3 else 'FAIL'}")
    ket_qua.append(("mui ten xoay (ChevronRight / ChevronDown)", ok3))

    # ------------------------------------------ [4] DUNG MUC CON TRONG MUC LON
    in_ky("")
    in_ky("[4] MOI MUC LON CHUA DUNG CAC MUC CON")
    ok4 = True
    for idx, (ten, _mo_ta) in enumerate(MUC_LON):
        if idx >= len(ds):
            ok4 = False
            continue
        nlon = ds[idx]
        nlon.dat_mo(True)
        app.update()
        # Cac widget con truc tiep trong khung cua muc lon.
        con = [w for w in nlon.khung.winfo_children()
               if type(w).__name__ == "NhomTinhNang"]
        ten_con = [str(w.chk.cget("text")) for w in con]
        in_ky(f"    {ten!r:24s} co {len(ten_con)} muc con: {ten_con}")
        if ten_con != MUC_CON[ten]:
            ok4 = False
            in_ky(f"      -> SAI (mong doi {MUC_CON[ten]})")
    in_ky(f"  -> {'PASS' if ok4 else 'FAIL'}")
    ket_qua.append(("dung muc con trong tung muc lon", ok4))

    # -------------------------------------------- [5] BAN DICH TIENG ANH
    in_ky("")
    in_ky("[5] BAN DICH TIENG ANH CHO 4 TIEU DE + 4 MO TA")
    trước = [str(n.lbl_ten.cget("text")) for n in ds] + \
            [str(n.lbl_mo_ta.cget("text")) for n in ds]
    app._doi_ngon_ngu()
    app.update()
    sau = [str(n.lbl_ten.cget("text")) for n in ds] + \
          [str(n.lbl_mo_ta.cget("text")) for n in ds]
    for a, b in zip(trước, sau):
        in_ky(f"    VI {a!r:52s} -> EN {b!r}")
    ok5 = all(a != b for a, b in zip(trước, sau)) and all(b.strip() for b in sau)
    app._doi_ngon_ngu()      # ve lai tieng Viet
    app.update()
    in_ky(f"  -> {'PASS' if ok5 else 'FAIL'}")
    ket_qua.append(("ban dich tieng Anh 8 chuoi moi", ok5))

    # ------------------------------------- [6] BAM THE VIDEO MAU VAN CHON DUOC
    in_ky("")
    in_ky("[6] BAM THE VIDEO MAU VAN CHON DUOC VIDEO")
    app.v_video.set("")
    app._dung_video_mau(0)
    app.update()
    duong_dan = app.v_video.get()
    ten_the = str(app.luu_video_mau._the[0]._ten)
    mo_ta_the = str(app.luu_video_mau._the[0]._mo_ta)
    in_ky(f"    the 0: ten={ten_the!r} mo_ta={mo_ta_the!r}")
    in_ky(f"    -> v_video = {duong_dan!r}")
    ok6 = bool(duong_dan) and duong_dan.endswith("one-by-one-person-detection.mp4")
    in_ky(f"  -> {'PASS' if ok6 else 'FAIL'}")
    ket_qua.append(("bam the video mau chon duoc video", ok6))

    # ---------------------------------- [7] 4 TINH NANG BAN 3.3 CON NGUYEN
    in_ky("")
    in_ky("[7] 4 TINH NANG BAN 3.3 CON NGUYEN")
    ok7 = True
    cap = [
        ("chk_xem_video", "Xem trực tiếp"),
        ("chk_xem_ket_qua", "Xem khung hình kết quả"),
    ]
    for ten, can in cap:
        wdg = getattr(app, ten, None)
        hien = str(wdg.cget("text")) if wdg is not None else "<KHONG CO>"
        in_ky(f"    {ten:18s} = {hien!r}")
        if hien != can:
            ok7 = False
    nut = [
        ("btn_dang_ky", "Đăng ký người quen…"),
        ("btn_doc_bien_so_thu", "Đọc biển số thử…"),
        ("btn_ve_vung_tai_day", "Vẽ vùng ngay tại đây"),
    ]
    for ten, can in nut:
        wdg = getattr(app, ten, None)
        hien = str(wdg.cget("text")) if wdg is not None else "<KHONG CO>"
        in_ky(f"    {ten:18s} = {hien!r}")
        if hien != can:
            ok7 = False
    in_ky(f"  -> {'PASS' if ok7 else 'FAIL'}")
    ket_qua.append(("4 tinh nang ban 3.3 con nguyen", ok7))

    # ------------------------------------------------------------------ tong
    in_ky("")
    in_ky("=" * 78)
    in_ky("KET QUA KIEM CHUNG BO CUC COT TRAI")
    in_ky("=" * 78)
    for ten, ok in ket_qua:
        in_ky(f"  [{'PASS' if ok else 'FAIL'}] {ten}")
    tong = all(ok for _, ok in ket_qua)
    in_ky(f"  TONG KET: {'PASS' if tong else 'FAIL'}")
    in_ky("=" * 78)

    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0 if tong else 1


if __name__ == "__main__":
    try:
        sys.exit(chay())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
