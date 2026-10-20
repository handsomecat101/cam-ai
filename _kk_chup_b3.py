# -*- coding: utf-8 -*-
"""
Chup man hinh GUI sau khi bo cuc lai cot trai (4 muc lon) + do kich thuoc.

Luu anh vao `_kk_out/agent_b3/`:
  b3_01_nguon.png     - trang thai mac dinh (NGUON mo san)
  b3_02_phan_tich.png - mo muc lon PHAN TICH
  b3_03_bien_so.png   - mo muc lon BIEN SO & ANH
  b3_04_canh_bao.png  - mo muc lon CANH BAO & MO HINH
  b3_05_cot_trai.png  - cat rieng cot trai (NGUON mo san)
  b3_06_cot_trai_pt.png - cat rieng cot trai (PHAN TICH mo)
"""

from __future__ import annotations

import ctypes
import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

_THU_MUC = os.path.join(APP_DIR, "_kk_out", "agent_b3")
os.makedirs(_THU_MUC, exist_ok=True)

u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def rect_cua_so(app):
    rc = RECT()
    hwnd = u32.GetAncestor(ctypes.c_void_p(int(app.winfo_id())), 2)
    if hwnd:
        u32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rc))
    return rc


def _grab(app, box=None):
    from PIL import ImageGrab

    app.attributes("-topmost", True)
    app.lift()
    app.update()
    time.sleep(0.45)
    app.update()
    rc = rect_cua_so(app)
    if (rc.right - rc.left) < 400 or (rc.bottom - rc.top) < 300:
        # Cua so bi thu nho / chua kip mo - thu lai 2 lan.
        for _ in range(3):
            app.update()
            time.sleep(0.6)
            app.update()
            rc = rect_cua_so(app)
            if (rc.right - rc.left) >= 400 and (rc.bottom - rc.top) >= 300:
                break
    print(f"    rect = {rc.left},{rc.top},{rc.right},{rc.bottom}")
    if box is None:
        box = (rc.left, rc.top, rc.right, rc.bottom)
    else:
        w = rc.right - rc.left
        h = rc.bottom - rc.top
        box = (rc.left + int(box[0] * w), rc.top + int(box[1] * h),
               rc.left + int(box[2] * w), rc.top + int(box[3] * h))
    return ImageGrab.grab(bbox=box, all_screens=True)


def chup(app, ten_file, box=None):
    anh = _grab(app, box)
    duong_dan = os.path.join(_THU_MUC, ten_file)
    anh.save(duong_dan)
    print(f"  [chup] {duong_dan} {anh.size}")
    return duong_dan


def bom(app, giay=0.4):
    moc = time.monotonic()
    while time.monotonic() - moc < giay:
        app.update()
        time.sleep(0.01)


def main() -> int:
    import customtkinter as ctk

    from gui import CamAIGui

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(1.2)
    app.update()

    print("=" * 78)
    print("KICH THUOC COT TRAI + DAI THE VIDEO MAU")
    print("=" * 78)
    for nlon in app._ds_nhom_lon:
        print(f"  muc lon {nlon.lbl_ten.cget('text')!r:24s} mo={nlon.dang_mo} "
              f"tieu_de_r={nlon.lbl_ten.winfo_width()} "
              f"mo_ta_r={nlon.lbl_mo_ta.winfo_width()} "
              f"mo_ta_h={nlon.lbl_mo_ta.winfo_height()} "
              f"the_h={nlon.thanh.winfo_height()}")
    luoi = app.luu_video_mau
    print(f"  dai video mau: luoi_h={luoi.winfo_height()} "
          f"cuon_h={luoi.cuon.winfo_height()} so_the={len(luoi._the)}")
    for i, the in list(luoi._the.items())[:3]:
        print(f"    the {i}: w={the.winfo_width()} h={the.winfo_height()} "
              f"anh={the.o_anh.winfo_width()}x{the.o_anh.winfo_height()}")

    # --- 1. mac dinh: NGUON mo san ---
    chup(app, "b3_01_nguon.png")
    chup(app, "b3_05_cot_trai.png", box=(0.0, 0.05, 0.205, 0.99))

    # --- 2. mo muc lon PHAN TICH ---
    app._ds_nhom_lon[1].dat_mo(True)
    bom(app, 0.6)
    chup(app, "b3_02_phan_tich.png")
    chup(app, "b3_06_cot_trai_pt.png", box=(0.0, 0.05, 0.205, 0.99))

    # --- 3. BIEN SO & ANH ---
    app._ds_nhom_lon[2].dat_mo(True)
    bom(app, 0.6)
    chup(app, "b3_03_bien_so.png")
    # Mo them muc con "Doc bien so xe" de kiem tra khung cau hinh + nut
    # "Doc bien so thu..." con nguyen.
    app.nhom_bien_so.dat_mo(True)
    bom(app, 0.6)
    chup(app, "b3_07_bien_so_mo.png")
    chup(app, "b3_08_cot_trai_bien_so.png", box=(0.0, 0.05, 0.205, 0.99))

    # --- 4. CANH BAO & MO HINH ---
    app._ds_nhom_lon[3].dat_mo(True)
    bom(app, 0.6)
    chup(app, "b3_04_canh_bao.png")

    # --- do lai: chi 1 muc lon mo tai mot thoi ---
    print()
    print("Kiem tra 'chi 1 muc lon mo tai mot thoi':")
    for nlon in app._ds_nhom_lon:
        print(f"   {nlon.lbl_ten.cget('text')!r:24s} dang_mo={nlon.dang_mo}")

    # --- do chieu cao dai video mau ---
    print()
    print(f"CHIEU CAO dai video mau (khung chua the) = {luoi.master.winfo_height()}")

    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
