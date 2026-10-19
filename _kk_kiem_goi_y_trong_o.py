# -*- coding: utf-8 -*-
"""Coordinator: kiem chung GOI Y TRONG O (placeholder) cua nhom bien so.

Muc tieu:
  1. O "Vung can quet" phai hien goi y "de trong = tu tim trong khung".
  2. Bien `textvariable` phai LUON SACH (khong bi nhieu chu goi y).
  3. Khi bien co gia tri -> goi y phai bien mat; khi xoa rong -> quay lai.
  4. Chup anh de TOI MAT thay bang chung.

Chay: .venv\\Scripts\\python.exe -W ignore _kk_kiem_goi_y_trong_o.py
"""
from __future__ import annotations

import ctypes
import os
import sys
import time

import customtkinter as ctk
from PIL import ImageGrab

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from gui import CamAIGui  # noqa: E402

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(APP_DIR, "_kk_out")
u32 = ctypes.windll.user32
u32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u32.GetAncestor.restype = ctypes.c_void_p
u32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
u32.GetWindowRect.restype = ctypes.c_int

NHAN = "tự tìm"


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def _rect(app):
    rc = RECT()
    u32.GetWindowRect(ctypes.c_void_p(u32.GetAncestor(app.winfo_id(), 2)),
                      ctypes.byref(rc))
    return rc


def chup_vung(app, ten, x0, y0, x1, y1):
    duong = os.path.join(OUT, f"{ten}.png")
    img = ImageGrab.grab(bbox=(x0, y0, x1, y1), all_screens=True)
    img.save(duong)
    print(f"  [chup] {ten}: {img.size} -> {duong}", flush=True)
    return duong


def tim_entry_theo_bien(widget, bien):
    """Tra ve CTkEntry co `textvariable` la `bien`."""
    ket = []

    def quet(w):
        for c in w.winfo_children():
            if isinstance(c, ctk.CTkEntry):
                try:
                    if c.cget("textvariable") is bien:
                        ket.append(c)
                except Exception:                     # noqa: BLE001
                    pass
            quet(c)

    quet(widget)
    return ket


def tim_nhan_phu(trong, text):
    """Tra ve CTkLabel trong cay widget co `text` dung `text`."""
    ket = []

    def quet(w):
        for c in w.winfo_children():
            if isinstance(c, ctk.CTkLabel):
                try:
                    if c.cget("text") == text:
                        ket.append(c)
                except Exception:                     # noqa: BLE001
                    pass
            quet(c)

    quet(trong)
    return ket


def tim_scroll(app):
    w = app.nhom_phat_hien
    while w is not None and not hasattr(w, "_parent_canvas"):
        w = w.master
    return w


def cuon_den(app, widget, viet=0.05):
    canvas = tim_scroll(app)._parent_canvas
    for _ in range(12):
        app.update_idletasks()
        cao = canvas.winfo_height()
        lech = (widget.winfo_rooty() - canvas.winfo_rooty()) - viet * cao
        if abs(lech) < 10:
            break
        bbox = canvas.bbox("all")
        total = (bbox[3] if bbox else cao)
        f = canvas.yview()[0]
        canvas.yview_moveto(max(0.0, min(1.0, f + lech / max(1, total - cao))))
        app.update()
        app.update_idletasks()
        time.sleep(0.15)
    app.update()
    time.sleep(0.25)
    app.update()


def chay():
    os.makedirs(OUT, exist_ok=True)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.6)
    app.update()

    ket_qua = {}

    def buoc_0():
        app.nhom_bien_so.dat_mo(True)
        app.after(700, buoc_1)

    def buoc_1():
        cuon_den(app, app.nhom_bien_so.chk, viet=0.04)
        app.after(300, buoc_2)

    def buoc_2():
        entries = tim_entry_theo_bien(app.nhom_bien_so.khung,
                                      app.v_bien_so_vung)
        print(f"  [tim] so o nhap voi bien v_bien_so_vung: {len(entries)}",
              flush=True)
        if not entries:
            app.after(100, buoc_6)
            return
        o = entries[0]
        ket_qua["o"] = o
        inner = getattr(o, "_entry", o)
        inner.focus_force()
        app.update()
        time.sleep(0.3)
        app.update()

        # --- 1. goi y co hien khong ---
        nhan = tim_nhan_phu(o.master, NHAN)
        print(f"  [tim] so nhan goi y: {len(nhan)}", flush=True)
        if not nhan:
            print("  [LOI] KHONG tim thay nhan goi y!", flush=True)
            app.after(100, buoc_6)
            return
        lb = nhan[0]
        ket_qua["nhan"] = lb
        quan_ly = lb.winfo_manager()
        hien = quan_ly == "place"
        print(f"  [1] quan ly nhan    = {quan_ly!r} -> {'HIEN' if hien else 'AN'}")
        print(f"  [1] bien sach       = {app.v_bien_so_vung.get()!r} "
              f"(phai la chuoi rong)")
        print(f"  [1] noi dung o      = {inner.get()!r}")
        app.after(300, buoc_3)

    def buoc_3():
        o = ket_qua["o"]
        lb = ket_qua["nhan"]
        app.attributes("-topmost", True)
        app.lift()
        app.update()
        time.sleep(0.4)
        app.update()
        # Chup vung rong qua o de TOI MAT thay goi y
        x0 = o.winfo_rootx() - 150
        y0 = o.winfo_rooty() - 32
        x1 = o.winfo_rootx() + o.winfo_width() + 40
        y1 = o.winfo_rooty() + o.winfo_height() + 12
        chup_vung(app, "v3_20_goi_y_hien", x0, y0, x1, y1)
        app.after(300, buoc_4)

    def buoc_4():
        o = ket_qua["o"]
        lb = ket_qua["nhan"]
        # --- 2. bien co gia tri -> goi y phai bien mat ---
        app.v_bien_so_vung.set("0,1,1,0")
        app.update()
        time.sleep(0.3)
        app.update()
        quan_ly = lb.winfo_manager()
        print(f"  [2] bien = '0,1,1,0' -> quan ly nhan = {quan_ly!r} "
              f"({'AN dung' if quan_ly == '' else 'LOI: van con'})")
        x0 = o.winfo_rootx() - 150
        y0 = o.winfo_rooty() - 32
        x1 = o.winfo_rootx() + o.winfo_width() + 40
        y1 = o.winfo_rooty() + o.winfo_height() + 12
        chup_vung(app, "v3_21_goi_y_bien_mat", x0, y0, x1, y1)
        app.after(300, buoc_5)

    def buoc_5():
        lb = ket_qua["nhan"]
        # --- 3. xoa rong -> goi y phai quay lai ---
        app.v_bien_so_vung.set("")
        app.update()
        time.sleep(0.3)
        app.update()
        quan_ly = lb.winfo_manager()
        print(f"  [3] bien rong lai -> quan ly nhan = {quan_ly!r} "
              f"({'HIEN lai' if quan_ly == 'place' else 'LOI: khong quay lai'})")
        print(f"  [3] bien cuoi       = {app.v_bien_so_vung.get()!r}")
        app.after(300, buoc_6)

    def buoc_6():
        app.destroy()

    app.after(900, buoc_0)
    app.mainloop()


if __name__ == "__main__":
    chay()
