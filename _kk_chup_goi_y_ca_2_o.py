# -*- coding: utf-8 -*-
"""Coordinator: chup ca 2 o co goi y trong o + kiem bien sach.

O 1: "Danh sac lop can nhan"  -> goi y "mac dinh"
O 2: "Vung can quet"          -> goi y "tu tim"

Chay: .venv\\Scripts\\python.exe -W ignore _kk_chup_goi_y_ca_2_o.py
"""
from __future__ import annotations

import os
import sys
import time

import customtkinter as ctk
from PIL import ImageGrab

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from gui import CamAIGui  # noqa: E402

APP_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(APP_DIR, "_kk_out")


def tim_entry_theo_bien(widget, bien):
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


def tim_nhan(trong, text):
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
    for _ in range(14):
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
    time.sleep(0.3)
    app.update()


def chup(ten, o):
    x0 = o.winfo_rootx() - 160
    y0 = o.winfo_rooty() - 12
    x1 = o.winfo_rootx() + o.winfo_width() + 30
    y1 = o.winfo_rooty() + o.winfo_height() + 12
    duong = os.path.join(OUT, f"{ten}.png")
    img = ImageGrab.grab(bbox=(x0, y0, x1, y1), all_screens=True)
    img.save(duong)
    print(f"  [chup] {ten}: {img.size} -> {duong}", flush=True)


def chay():
    os.makedirs(OUT, exist_ok=True)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = CamAIGui()
    app.update()
    app.update_idletasks()
    time.sleep(0.6)
    app.update()

    def buoc_0():
        app.nhom_vat_the.dat_mo(True)
        app.after(800, buoc_1)

    def buoc_1():
        o_lop = tim_entry_theo_bien(app.nhom_vat_the.khung, app.v_lop)
        if not o_lop:
            print("  [LOI] khong tim thay o_lop")
            app.after(100, buoc_5)
            return
        cuon_den(app, o_lop[0], viet=0.10)
        app.after(300, buoc_2)

    def buoc_2():
        o_lop = tim_entry_theo_bien(app.nhom_vat_the.khung, app.v_lop)[0]
        n_lop = tim_nhan(o_lop.master, "mặc định")
        app.attributes("-topmost", True)
        app.lift()
        app.update()
        time.sleep(0.4)
        app.update()
        print(f"  nhan mac dinh: {len(n_lop)}", flush=True)
        if n_lop:
            print(f"  quan ly = {n_lop[0].winfo_manager()!r}", flush=True)
        chup("v3_30_goi_y_mac_dinh", o_lop)
        print(f"  bien v_lop = {app.v_lop.get()!r}", flush=True)
        app.after(300, buoc_3)

    def buoc_3():
        app.nhom_bien_so.dat_mo(True)
        app.after(800, buoc_4)

    def buoc_4():
        o_vung = tim_entry_theo_bien(app.nhom_bien_so.khung,
                                     app.v_bien_so_vung)[0]
        cuon_den(app, o_vung, viet=0.10)
        app.update()
        time.sleep(0.3)
        app.update()
        n_vung = tim_nhan(o_vung.master, "tự tìm")
        print(f"  nhan tu tim: {len(n_vung)}  quan ly="
              f"{n_vung[0].winfo_manager()!r}", flush=True)
        chup("v3_31_goi_y_tu_tim", o_vung)
        print(f"  bien v_bien_so_vung = {app.v_bien_so_vung.get()!r}", flush=True)
        app.after(200, buoc_5)

    def buoc_5():
        app.destroy()

    app.after(900, buoc_0)
    app.mainloop()


if __name__ == "__main__":
    chay()
