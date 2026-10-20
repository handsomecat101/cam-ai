# -*- coding: utf-8 -*-
"""
CamAI - DO KICH THUOC COT TRAI + DAI 'VIDEO MAU DUNG THU'.

Dung khi sua bo cuc cot trai: biet ngay cot trai cao bao nhieu, dai video
mau cao bao nhieu, 4 muc lon nao dang mo, muc con nao dang mo.

Chay:
    .venv\\Scripts\\python.exe -W ignore _kk_do_kich_thuoc_cot_trai.py
"""

from __future__ import annotations

import os
import sys
import time

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import customtkinter as ctk  # noqa: E402

from gui import CamAIGui  # noqa: E402


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(1.2)
    app.update()
    for _ in range(40):          # cho `after(300)` chay
        app.update()
        time.sleep(0.02)

    luoi = app.luu_video_mau
    print("=" * 78)
    print("KICH THUOC COT TRAI + DAI 'VIDEO MAU DUNG THU'")
    print("=" * 78)
    print(f"  cua so                       = {app.winfo_width()}x{app.winfo_height()}")
    for nlon in app._ds_nhom_lon:
        print(f"  muc lon {nlon.lbl_ten.cget('text')!r:24s} "
              f"mo={nlon.dang_mo} the_h={nlon.thanh.winfo_height()} "
              f"mo_ta_1_dong={nlon.lbl_mo_ta.winfo_height() <= 30}")
    print()
    print(f"  dai video mau (khung chua)   = {luoi.master.winfo_height()}px")
    print(f"  luoi (LuoiVideoMau)          = {luoi.winfo_height()}px")
    print(f"  cuon (khung cuon ngang)      = {luoi.cuon.winfo_height()}px")
    print(f"  1 the video mau              = "
          f"{list(luoi._the.values())[0].winfo_height()}px")
    print(f"  so the                       = {len(luoi._the)}")
    print()
    print("  Muc con dang MO (khung cau hinh hien thi):")
    for ten, nhom in app.danh_sach_nhom():
        if nhom.dang_mo:
            print(f"    - {ten}")

    try:
        app.stop_flag.set()
        app.destroy()
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
