"""Coordinator chup anh GUI voi nhom 'May nay chay bang gi' da mo.

Dung de kiem chung bang mat: dropdown co hien dung khong, co bi cat khong,
co tran khong. Khong tin bao cao cua agent.
"""

import ctypes
import time
import traceback
from ctypes import wintypes
from pathlib import Path

import customtkinter as ctk
from PIL import ImageGrab

import gui as G
from gui import CamAIGui

u32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


THU_MUC = Path("_kiem_chung")


def chup(app, ten: str):
    """Ép cửa sổ lên trước rồi chụp đúng vùng cửa sổ thật."""
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    app.update_idletasks()
    time.sleep(1.2)
    app.update()

    hwnd = u32.GetAncestor(app.winfo_id(), 2) or app.winfo_id()
    rc = RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(rc))
    bbox = (rc.left, rc.top, rc.right, rc.bottom)
    anh = ImageGrab.grab(bbox=bbox, all_screens=True)
    duong_dan = THU_MUC / ten
    duong_dan.parent.mkdir(parents=True, exist_ok=True)
    anh.save(duong_dan)
    return duong_dan, bbox, anh.size


def main() -> int:
    app = CamAIGui()
    app.geometry("1610x980+0+0")
    app.update()

    # Thu gọn TAT CA nhom truoc, roi chi mo nhom thiet bi.
    # Ly do: khong co canvas cuon trong gui.py, nen nhom 9 (nam o day)
    # se bi cat duoi man hinh neu cac nhom khac dang mo.
    danh_sach = []
    for ten_attr in dir(app):
        if not ten_attr.startswith("nhom_"):
            continue
        doi_tuong = getattr(app, ten_attr, None)
        if hasattr(doi_tuong, "dat_mo"):
            danh_sach.append((ten_attr, doi_tuong))

    for ten_attr, nhom in danh_sach:
        nhom.dat_mo(False)
    app.update_idletasks()
    time.sleep(0.4)

    # Chi mo nhom can xac nhan
    app.nhom_thiet_bi.dat_mo(True)
    app.update_idletasks()
    time.sleep(0.6)
    print(f"da thu gon {len(danh_sach)} nhom, chi mo nhom_thiet_bi")

    # CUON XUONG DUOI trong cot trai (CTkScrollableFrame) de thay dropdown.
    # Kiem tra canvas noi bo cua CTkScrollableFrame.
    print("\n--- CUON COT TRAI XUONG DUOI ---")
    tim_thay_canvas = [None]
    for ten_attr in ("cot_trai", "f_trai", "khung_trai"):
        doi = getattr(app, ten_attr, None)
        if doi is not None:
            print(f"  app.{ten_attr} = {type(doi).__name__}")

    # Nham CTkScrollableFrame cua cot TRAI, dung canvas noi bo cua no.
    def quet(widget):
        if tim_thay_canvas[0] is not None:
            return
        for con in widget.winfo_children():
            if type(con).__name__ == "CTkScrollableFrame":
                print("  tim thay CTkScrollableFrame -> dung _parent_canvas")
                tim_thay_canvas[0] = getattr(con, "_parent_canvas", None)
                return
            quet(con)

    quet(app)
    if tim_thay_canvas[0] is not None:
        print(f"  canvas = {tim_thay_canvas[0]}")
        tim_thay_canvas[0].yview_moveto(1.0)
        app.update_idletasks()
        time.sleep(0.5)
        print(f"  yview = {tim_thay_canvas[0].yview()}")
    else:
        print("  KHONG tim thay CTkScrollableFrame")
    app.update_idletasks()
    time.sleep(0.6)
    # Kiểm tra mapping nhãn -> giá trị trong AnalysisConfig
    print("\n--- DROPDOWN 'Chay bang gi' ---")
    om = getattr(app, "v_thiet_bi", None)
    if om is None:
        print("KHONG CO v_thiet_bi")
        return 1

    print(f"mac dinh = {om.get()!r}")
    for gia_tri in G.GIA_TRI_CHE_THIET_BI:
        print(f"  nhan {gia_tri!r} -> thiet_bi = "
              f"{G.GIA_TRI_CHE_THIET_BI.get(gia_tri)!r}")
    print(f"tat ca khoa: {list(G.GIA_TRI_CHE_THIET_BI)}")

    # Đặt lại mặc định rồi chụp
    om.set("Tự động")
    app.update_idletasks()

    duong_dan, bbox, kich = chup(app, "kk_37_chay_bang_gi.png")
    print(f"\nda luu : {duong_dan}")
    print(f"bbox   : {bbox}")
    print(f"kich thuoc: {kich}")

    # Đo widget trong nhóm để phát hiện bị cắt
    nhom = app.nhom_thiet_bi
    khung = nhom.khung
    print(f"\n--- KHUONG NOI NHOM ({khung.winfo_width()}x{khung.winfo_height()}) ---")
    for tre in khung.winfo_children():
        if hasattr(tre, "winfo_y"):
            print(f"  - {tre.__class__.__name__:<20} y={tre.winfo_y():<5} "
                  f"h={tre.winfo_height():<5} text={getattr(tre, 'text', '')!r}")
            # widget con 1 cap
            for cháu in tre.winfo_children():
                if hasattr(cháu, "winfo_y"):
                    print(f"      · {cháu.__class__.__name__:<18} "
                          f"y={cháu.winfo_y():<5} h={cháu.winfo_height():<5} "
                          f"text={getattr(cháu, 'text', '')!r}")

    app.destroy()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)